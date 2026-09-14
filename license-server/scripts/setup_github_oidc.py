#!/usr/bin/env python3.12
"""One-time bootstrap: let GitHub Actions deploy this project via OIDC.

Creates (idempotent — safe to re-run):
  1. A Workload Identity Pool + OIDC provider trusting GitHub's OIDC issuer,
     restricted to a single GitHub repository (no branch restriction).
  2. A dedicated "github-deployer" service account with the minimum roles
     needed to validate secrets and run `firebase deploy --only functions`.
  3. An IAM binding letting that repository impersonate the deployer SA.
  4. The GitHub Environment the deploy job is gated behind, with required
     reviewers (users only — pass --reviewer, or let it auto-infer the
     repo's admin collaborators + the current `gh` user).

No JSON service-account key is ever created or downloaded — GitHub Actions
authenticates by exchanging its own OIDC token for short-lived GCP
credentials at workflow run time (see google-github-actions/auth).

This is plain `gcloud` — Terraform is NOT required to run this script.
--repo defaults to the current directory's GitHub repo (via `gh repo view`).

Usage:
    python3.12 scripts/setup_github_oidc.py                       # auto-detect repo + reviewers
    python3.12 scripts/setup_github_oidc.py --repo OWNER/REPO --project my-id
    python3.12 scripts/setup_github_oidc.py --set-github-vars --reviewer alice --reviewer bob
    python3.12 scripts/setup_github_oidc.py --force                # prompt to reconcile drifted resources
    python3.12 scripts/setup_github_oidc.py --destroy               # tear the whole bootstrap back down

--force: resources here are otherwise idempotent no-ops once they exist. The
only one with meaningful drift to reconcile is the OIDC provider's repo lock
(--attribute-condition) — e.g. after --repo changes. With --force, if the
provider already exists this prompts to update it in place; other resources
(pool, service account, additive IAM bindings) have nothing updatable and are
left untouched either way.

--destroy: removes everything this script creates, in dependency order (IAM
bindings, the deployer service account, the OIDC provider, the workload
identity pool, the GitHub environment, and the GitHub repo variables it set).
Pool/provider deletion in GCP is a *soft* delete with a ~30-day grace period —
the same POOL_ID/PROVIDER_ID cannot be recreated until that window elapses or
you `gcloud ... undelete`. Requires confirmation unless --yes is also given.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # license-server/
POOL_ID = "github-actions-pool"
PROVIDER_ID = "github-provider"
DEPLOYER_SA_ID = "github-deployer"
FUNCTIONS_SA_ID = "license-functions"  # must match terraform/main.tf functions_sa
ISSUER_URI = "https://token.actions.githubusercontent.com"
ENVIRONMENT_NAME = "license-server-deploy"  # must match .github/workflows/license-server-deploy.yml

# Minimum roles the deployer identity needs to validate secrets and run
# `firebase deploy --only functions`. Deliberately excludes anything that
# could create/rotate/read secret *values* (secretmanager.viewer only).
DEPLOYER_PROJECT_ROLES = [
    "roles/cloudfunctions.developer",
    "roles/run.developer",
    "roles/secretmanager.viewer",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
]


def run(cmd: list[str], *, check: bool = True, capture: bool = False,
        input_data: str | None = None) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, cwd=ROOT, text=True, capture_output=capture, input=input_data)


def which(name: str) -> str | None:
    return shutil.which(name)


def confirm(prompt: str, *, default: bool = False, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    return default if not answer else answer in ("y", "yes")


def resolve_project_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    firebaserc = ROOT / ".firebaserc"
    if firebaserc.exists():
        try:
            projects = json.loads(firebaserc.read_text()).get("projects", {})
        except (OSError, json.JSONDecodeError):
            projects = {}
        if projects:
            return next(iter(projects.values()))
    project_id = input("GCP project ID: ").strip()
    if not project_id:
        raise SystemExit("A project ID is required.")
    return project_id


def project_number(project_id: str) -> str:
    result = run(
        ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"],
        capture=True,
    )
    number = result.stdout.strip()
    if not number:
        raise SystemExit(f"Could not resolve the project number for {project_id}.")
    return number


def pool_exists(project_id: str) -> bool:
    result = run(
        ["gcloud", "iam", "workload-identity-pools", "describe", POOL_ID,
         f"--project={project_id}", "--location=global"],
        capture=True, check=False,
    )
    return result.returncode == 0


def provider_exists(project_id: str) -> bool:
    result = run(
        ["gcloud", "iam", "workload-identity-pools", "providers", "describe", PROVIDER_ID,
         f"--project={project_id}", "--location=global", f"--workload-identity-pool={POOL_ID}"],
        capture=True, check=False,
    )
    return result.returncode == 0


def service_account_exists(email: str, project_id: str) -> bool:
    result = run(
        ["gcloud", "iam", "service-accounts", "describe", email, f"--project={project_id}"],
        capture=True, check=False,
    )
    return result.returncode == 0


def ensure_pool(project_id: str) -> None:
    if pool_exists(project_id):
        print(f"\u2714 Workload identity pool {POOL_ID} already exists")
        return
    run([
        "gcloud", "iam", "workload-identity-pools", "create", POOL_ID,
        f"--project={project_id}", "--location=global",
        "--display-name=GitHub Actions",
        "--description=Pool for GitHub Actions OIDC deploys of the license server",
    ])


_PROVIDER_ATTRIBUTE_MAPPING = (
    "google.subject=assertion.sub,"
    "attribute.repository=assertion.repository,"
    "attribute.repository_owner=assertion.repository_owner,"
    "attribute.ref=assertion.ref"
)


def ensure_provider(project_id: str, repo: str, *, force: bool = False) -> None:
    if provider_exists(project_id):
        if not force:
            print(f"\u2714 OIDC provider {PROVIDER_ID} already exists")
            return
        if not confirm(
            f"OIDC provider {PROVIDER_ID} already exists. Update it so its repo lock matches "
            f"'{repo}' (in case it was previously bootstrapped for a different repo)?",
            default=False,
        ):
            print(f"\u2139 Leaving existing OIDC provider {PROVIDER_ID} as-is.")
            return
        run([
            "gcloud", "iam", "workload-identity-pools", "providers", "update-oidc", PROVIDER_ID,
            f"--project={project_id}", "--location=global", f"--workload-identity-pool={POOL_ID}",
            f"--issuer-uri={ISSUER_URI}",
            f"--attribute-mapping={_PROVIDER_ATTRIBUTE_MAPPING}",
            f"--attribute-condition=assertion.repository=='{repo}'",
        ])
        print(f"\u2714 Updated OIDC provider {PROVIDER_ID} to lock onto {repo}")
        return
    run([
        "gcloud", "iam", "workload-identity-pools", "providers", "create-oidc", PROVIDER_ID,
        f"--project={project_id}", "--location=global", f"--workload-identity-pool={POOL_ID}",
        "--display-name=GitHub OIDC",
        f"--issuer-uri={ISSUER_URI}",
        f"--attribute-mapping={_PROVIDER_ATTRIBUTE_MAPPING}",
        f"--attribute-condition=assertion.repository=='{repo}'",
    ])


def ensure_deployer_sa(email: str, project_id: str) -> None:
    if service_account_exists(email, project_id):
        print(f"\u2714 Service account {email} already exists")
        return
    run([
        "gcloud", "iam", "service-accounts", "create", DEPLOYER_SA_ID,
        f"--project={project_id}",
        "--display-name=GitHub Actions deployer (license-server)",
    ])


def ensure_project_roles(email: str, project_id: str) -> None:
    for role in DEPLOYER_PROJECT_ROLES:
        existing = run(
            ["gcloud", "projects", "get-iam-policy", project_id,
             f"--flatten=bindings[].members", f"--filter=bindings.role={role} AND bindings.members:{email}",
             "--format=value(bindings.role)"],
            capture=True, check=False,
        )
        if existing.stdout.strip():
            print(f"\u2714 {email} already has {role}")
            continue
        run([
            "gcloud", "projects", "add-iam-policy-binding", project_id,
            f"--member=serviceAccount:{email}", f"--role={role}", "--condition=None",
        ])


def ensure_act_as_functions_sa(deployer_email: str, functions_email: str, project_id: str) -> None:
    """Let the deployer impersonate the Functions runtime SA during `firebase deploy`."""
    existing = run(
        ["gcloud", "iam", "service-accounts", "get-iam-policy", functions_email,
         f"--project={project_id}", "--flatten=bindings[].members",
         f"--filter=bindings.role=roles/iam.serviceAccountUser AND bindings.members:{deployer_email}",
         "--format=value(bindings.role)"],
        capture=True, check=False,
    )
    if existing.stdout.strip():
        print(f"\u2714 {deployer_email} can already act as {functions_email}")
        return
    run([
        "gcloud", "iam", "service-accounts", "add-iam-policy-binding", functions_email,
        f"--project={project_id}",
        f"--member=serviceAccount:{deployer_email}",
        "--role=roles/iam.serviceAccountUser",
    ])


def ensure_workload_identity_binding(deployer_email: str, project_id: str,
                                      proj_number: str, repo: str) -> None:
    member = (
        f"principalSet://iam.googleapis.com/projects/{proj_number}"
        f"/locations/global/workloadIdentityPools/{POOL_ID}/attribute.repository/{repo}"
    )
    existing = run(
        ["gcloud", "iam", "service-accounts", "get-iam-policy", deployer_email,
         f"--project={project_id}", "--flatten=bindings[].members",
         f"--filter=bindings.role=roles/iam.workloadIdentityUser AND bindings.members:{member}",
         "--format=value(bindings.role)"],
        capture=True, check=False,
    )
    if existing.stdout.strip():
        print(f"\u2714 {repo} can already impersonate {deployer_email}")
        return
    run([
        "gcloud", "iam", "service-accounts", "add-iam-policy-binding", deployer_email,
        f"--project={project_id}",
        f"--member={member}",
        "--role=roles/iam.workloadIdentityUser",
    ])


def remove_project_roles(email: str, project_id: str) -> None:
    """Strip the deployer's project-level role bindings (call before deleting the SA — a project IAM
    policy binding for an already-deleted member becomes an unremovable `deleted:serviceAccount:...`
    entry, so this must happen first, not after)."""
    for role in DEPLOYER_PROJECT_ROLES:
        run(
            ["gcloud", "projects", "remove-iam-policy-binding", project_id,
             f"--member=serviceAccount:{email}", f"--role={role}", "--condition=None"],
            check=False,
        )


def remove_act_as_binding(deployer_email: str, functions_email: str, project_id: str) -> None:
    run(
        ["gcloud", "iam", "service-accounts", "remove-iam-policy-binding", functions_email,
         f"--project={project_id}", f"--member=serviceAccount:{deployer_email}",
         "--role=roles/iam.serviceAccountUser"],
        check=False,
    )


def delete_deployer_sa(email: str, project_id: str) -> None:
    if not service_account_exists(email, project_id):
        print(f"\u2139 Service account {email} does not exist — nothing to delete")
        return
    run(["gcloud", "iam", "service-accounts", "delete", email, f"--project={project_id}", "--quiet"])


def delete_provider(project_id: str) -> None:
    if not provider_exists(project_id):
        print(f"\u2139 OIDC provider {PROVIDER_ID} does not exist — nothing to delete")
        return
    run([
        "gcloud", "iam", "workload-identity-pools", "providers", "delete", PROVIDER_ID,
        f"--project={project_id}", "--location=global", f"--workload-identity-pool={POOL_ID}", "--quiet",
    ])


def delete_pool(project_id: str) -> None:
    if not pool_exists(project_id):
        print(f"\u2139 Workload identity pool {POOL_ID} does not exist — nothing to delete")
        return
    run([
        "gcloud", "iam", "workload-identity-pools", "delete", POOL_ID,
        f"--project={project_id}", "--location=global", "--quiet",
    ])


def delete_environment(repo: str) -> None:
    if not which("gh"):
        print("\u26a0 `gh` CLI not found — delete the environment manually if you no longer want it.")
        return
    exists = run(["gh", "api", f"repos/{repo}/environments/{ENVIRONMENT_NAME}"],
                 capture=True, check=False).returncode == 0
    if not exists:
        print(f"\u2139 Environment '{ENVIRONMENT_NAME}' does not exist — nothing to delete")
        return
    run(["gh", "api", "-X", "DELETE", f"repos/{repo}/environments/{ENVIRONMENT_NAME}"], check=False)
    print(f"\u2714 Deleted environment '{ENVIRONMENT_NAME}'")


def unset_github_vars(repo: str, names: list[str]) -> None:
    if not which("gh"):
        return
    for name in names:
        run(["gh", "variable", "delete", name, "--repo", repo], check=False)


def destroy(project_id: str, repo: str, deployer_email: str, functions_email: str, *, auto_yes: bool) -> None:
    """Tear down everything this script creates, in dependency order."""
    print(f"Project:  {project_id}")
    print(f"Repo:     {repo}")
    print(f"Deployer: {deployer_email}")
    print("\nThis will remove:")
    print(f"  - The '{ENVIRONMENT_NAME}' GitHub environment and its required reviewers")
    print("  - The GCP_PROJECT_ID / GCP_WORKLOAD_IDENTITY_PROVIDER / GCP_DEPLOYER_SA_EMAIL repo variables")
    print(f"  - The {deployer_email} service account and its IAM role bindings")
    print(f"  - The {PROVIDER_ID} OIDC provider and {POOL_ID} workload identity pool")
    print("\nNote: pool/provider deletion in GCP is a soft delete with a ~30-day grace period — the same "
          "IDs cannot be recreated until that window elapses (or you `gcloud ... undelete`).")
    if not confirm("Proceed with destroying the GitHub OIDC bootstrap above?", default=False, auto_yes=auto_yes):
        raise SystemExit("Aborted.")

    remove_project_roles(deployer_email, project_id)
    if service_account_exists(functions_email, project_id):
        remove_act_as_binding(deployer_email, functions_email, project_id)
    delete_deployer_sa(deployer_email, project_id)
    delete_provider(project_id)
    delete_pool(project_id)
    delete_environment(repo)
    unset_github_vars(repo, ["GCP_PROJECT_ID", "GCP_WORKLOAD_IDENTITY_PROVIDER", "GCP_DEPLOYER_SA_EMAIL"])

    print("\n\u2714 GitHub OIDC bootstrap destroyed.")


def resolve_repo(explicit: str | None) -> str:
    """Return OWNER/REPO — from --repo if given, else auto-detected via `gh`."""
    if explicit:
        return explicit
    if not which("gh"):
        raise SystemExit("--repo not given and `gh` CLI not found — pass --repo OWNER/REPO explicitly.")
    result = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                 capture=True, check=False)
    repo = result.stdout.strip()
    if result.returncode != 0 or not repo:
        raise SystemExit("Could not auto-detect the GitHub repo. Run this from inside a clone with a "
                          "GitHub remote and `gh auth login` done, or pass --repo OWNER/REPO explicitly.")
    return repo


def resolve_reviewer(username: str, repo: str) -> dict:
    """Resolve a GitHub username to an environment reviewer object (users only — no teams)."""
    username = username.removeprefix("user:")
    result = run(["gh", "api", f"users/{username}", "--jq", ".id"], capture=True)
    return {"type": "User", "id": int(result.stdout.strip())}


def infer_reviewers(repo: str) -> list[str]:
    """Auto-infer required reviewers: the repo's admin collaborators + the current `gh` user."""
    logins: set[str] = set()

    me = run(["gh", "api", "user", "--jq", ".login"], capture=True, check=False)
    if me.returncode == 0 and me.stdout.strip():
        logins.add(me.stdout.strip())

    admins = run(["gh", "api", f"repos/{repo}/collaborators", "-f", "affiliation=all",
                  "--jq", ".[] | select(.permissions.admin == true) | .login"],
                 capture=True, check=False)
    if admins.returncode == 0:
        logins.update(line.strip() for line in admins.stdout.splitlines() if line.strip())

    return sorted(logins)


def ensure_environment(repo: str, reviewers: list[dict]) -> None:
    """Create/update the deploy-approval GitHub Environment (idempotent PUT)."""
    exists = run(["gh", "api", f"repos/{repo}/environments/{ENVIRONMENT_NAME}"],
                 capture=True, check=False).returncode == 0
    body = json.dumps({"reviewers": reviewers, "deployment_branch_policy": None})
    run(["gh", "api", "-X", "PUT", f"repos/{repo}/environments/{ENVIRONMENT_NAME}", "--input", "-"],
        input_data=body)
    verb = "Updated" if exists else "Created"
    print(f"\u2714 {verb} environment '{ENVIRONMENT_NAME}' with {len(reviewers)} required reviewer(s)")


def set_github_vars(repo: str, values: dict[str, str]) -> None:
    if not which("gh"):
        print("\u26a0 GitHub CLI (`gh`) not found — set these repository variables manually (see below).")
        return
    for name, value in values.items():
        run(["gh", "variable", "set", name, "--repo", repo, "--body", value])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", help="GitHub repo allowed to deploy, as OWNER/REPO "
                                        "(default: auto-detected from the current `gh` repo)")
    parser.add_argument("--project", help="GCP project ID (default: read from .firebaserc)")
    parser.add_argument("--set-github-vars", action="store_true",
                         help="Also set the resulting values as GitHub Actions repo variables via `gh`")
    parser.add_argument("--reviewer", action="append", default=[], metavar="USERNAME",
                         help="Required reviewer (GitHub username) for the deploy-approval environment "
                              f"('{ENVIRONMENT_NAME}'). Repeatable. Default: auto-infer from the repo's "
                              "admin collaborators + the current `gh` user.")
    parser.add_argument("--no-reviewers", action="store_true",
                         help="Skip environment/reviewer setup entirely (you'll configure it manually)")
    parser.add_argument("--force", action="store_true",
                         help="If a resource already exists, prompt to reconcile it with the current "
                              "settings instead of silently leaving it as-is (currently only meaningful "
                              "for the OIDC provider's repo lock)")
    parser.add_argument("--destroy", action="store_true",
                         help="Tear down everything this script creates (pool, provider, deployer SA, "
                              "IAM bindings, GitHub environment, GitHub repo variables) instead of "
                              "creating/verifying it")
    parser.add_argument("--yes", "-y", action="store_true", help="Don't prompt for confirmation")
    args = parser.parse_args()

    args.repo = resolve_repo(args.repo)

    if "/" not in args.repo:
        raise SystemExit("--repo must be OWNER/REPO, e.g. Modeling13Steel/Tekla-Nest")

    project_id = resolve_project_id(args.project)
    deployer_email = f"{DEPLOYER_SA_ID}@{project_id}.iam.gserviceaccount.com"
    functions_email = f"{FUNCTIONS_SA_ID}@{project_id}.iam.gserviceaccount.com"

    if args.destroy:
        destroy(project_id, args.repo, deployer_email, functions_email, auto_yes=args.yes)
        return

    print(f"Project:  {project_id}")
    print(f"Repo:     {args.repo}")
    print(f"Deployer: {deployer_email}")
    if not confirm("Proceed with creating/verifying the GitHub OIDC bootstrap above?",
                    default=True, auto_yes=args.yes):
        raise SystemExit("Aborted.")

    run(["gcloud", "config", "set", "project", project_id])
    run(["gcloud", "services", "enable", "iam.googleapis.com", "iamcredentials.googleapis.com",
         "sts.googleapis.com", f"--project={project_id}"])

    proj_number = project_number(project_id)

    ensure_pool(project_id)
    ensure_provider(project_id, args.repo, force=args.force)
    ensure_deployer_sa(deployer_email, project_id)
    ensure_project_roles(deployer_email, project_id)
    if service_account_exists(functions_email, project_id):
        ensure_act_as_functions_sa(deployer_email, functions_email, project_id)
    else:
        print(f"\u26a0 {functions_email} does not exist yet (created by `terraform apply` or the first "
              f"`deploy.py` run) — re-run this script with --yes after it exists so the deployer can act as it.")
    ensure_workload_identity_binding(deployer_email, project_id, proj_number, args.repo)

    provider_resource_name = (
        f"projects/{proj_number}/locations/global/workloadIdentityPools/{POOL_ID}"
        f"/providers/{PROVIDER_ID}"
    )
    github_vars = {
        "GCP_PROJECT_ID": project_id,
        "GCP_WORKLOAD_IDENTITY_PROVIDER": provider_resource_name,
        "GCP_DEPLOYER_SA_EMAIL": deployer_email,
    }

    print("\n\u2714 GitHub OIDC bootstrap complete.\n")
    print("Set these as GitHub Actions repository *variables* (Settings → Secrets and "
          "variables → Actions → Variables) — none of them are secret:\n")
    for name, value in github_vars.items():
        print(f"  {name} = {value}")

    if args.set_github_vars:
        set_github_vars(args.repo, github_vars)
    else:
        print(f"\nOr re-run with --set-github-vars to have `gh` set them for you "
              f"(requires `gh auth login` with admin rights on {args.repo}).")

    if args.no_reviewers:
        print(f"\n\u2139 --no-reviewers given — the '{ENVIRONMENT_NAME}' environment was not touched. "
              "Create it with at least one required reviewer before the first deploy runs, or this "
              "workflow's approval gate will be a no-op (see GUIDE.md).")
    elif not which("gh"):
        print(f"\n\u26a0 `gh` CLI not found — create the '{ENVIRONMENT_NAME}' environment manually "
              "(see GUIDE.md).")
    else:
        usernames = args.reviewer or infer_reviewers(args.repo)
        if not usernames:
            print(f"\n\u26a0 Could not determine any reviewers (no --reviewer given, and no repo admins "
                  f"or current user found) — create the '{ENVIRONMENT_NAME}' environment manually "
                  "(see GUIDE.md).")
        else:
            source = "given via --reviewer" if args.reviewer else "auto-inferred: repo admins + you"
            print(f"\nReviewers ({source}): {', '.join(usernames)}")
            reviewers = [resolve_reviewer(u, args.repo) for u in usernames]
            ensure_environment(args.repo, reviewers)


if __name__ == "__main__":
    main()
