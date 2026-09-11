# Infrastructure (license server)

This is the small **cloud service** that checks whether a Tekla Nest licence is valid. You
deploy it **once**. After that it mostly runs itself.

!!! note "You only need this if you run your own license server"
    If someone already deployed it and gave you a server address, you can skip to
    [After deploying](#7-after-deploying). This page is for the person doing the one-time setup.

## 1. What it is (plain words)

```
Desktop apps  ──HTTPS──►  License server (Firebase Cloud Functions)  ──►  Firestore database
(Nesting / Admin)          /activate  /validate  /admin_*                 (stores licences)
```

- **Firebase / Google Cloud** — Google's cloud platform. "Firebase" is the friendly layer on
  top of Google Cloud.
- **Cloud Functions** — small programs that run on demand in the cloud (our 7 endpoints).
- **Firestore** — the cloud database that stores the licence records.
- **Secret Manager** — a safe place for the secret keys.
- **Terraform** — an optional tool that can create the cloud pieces from a script.

At the small volumes this service handles, the cost is **effectively €0** (free tier); a
payment card is still required on the account.

## 2. Accounts to create

1. A **Google account** (if you don't have one).
2. A **Firebase project** at <https://console.firebase.google.com> → *Add project*.
3. **Enable billing** on that project (Google Cloud → Billing). Cloud Functions require the
   pay-as-you-go **Blaze** plan, which needs a card — but usage stays within the free tier.

!!! warning
    Keep the project ID handy (e.g. `tekla-nest-licences`). You'll use it in the commands
    below wherever it says `<project-id>`.

## 3. Tools to install

| Tool | Install |
|---|---|
| **Node.js + Firebase CLI** | Node from <https://nodejs.org>, then `npm install -g firebase-tools` |
| **Google Cloud CLI (`gcloud`)** | <https://cloud.google.com/sdk/docs/install> |
| **Python 3.12** | <https://www.python.org/downloads/> |
| **Terraform** *(optional)* | <https://developer.hashicorp.com/terraform/install> |

All commands below run from the **`tekla_package/tekla-iac/`** folder.

## 4. Deploy roadmap (do these in order)

!!! note
    This mirrors the authoritative runbook, `tekla-iac/GUIDE.md`. If anything here differs,
    the GUIDE is the source of truth.

**Step 1 — Sign in**
```bash
firebase login
gcloud auth login
export PROJECT_ID="<project-id>"
```

**Step 2 — Turn on the database**
```bash
gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"
gcloud firestore databases create --location=eur3 --project="$PROJECT_ID"
```

**Step 3 — Generate the signing keys** (creates `keys/private_key.pem` + `keys/public_key.pem`)
```bash
python scripts/generate_keys.py
```

!!! warning "Never share or commit the private key"
    `keys/private_key.pem` lets the server issue licences — treat it like a master password.
    Only the **public** key is embedded in the desktop app.

**Step 4 — Prepare the Functions environment** (the Firebase CLI expects a local venv)
```bash
python scripts/bootstrap_functions_venv.py
```

**Step 5 — Store the three secrets**
```bash
firebase functions:secrets:set JWT_PRIVATE_KEY < keys/private_key.pem
printf "%s" "<your-admin-key>"  | firebase functions:secrets:set ADMIN_API_KEY
printf "%s" "<your-master-key>" | firebase functions:secrets:set MASTER_ADMIN_API_KEY
```

**Step 6 — Deploy the server**
```bash
firebase deploy --only functions
```

When it finishes, Firebase prints the **function URLs** — note the base address, e.g.
`https://europe-west1-<project-id>.cloudfunctions.net`.

!!! tip "Optional: Terraform instead of manual setup"
    Steps 2 and part of 5 can be provisioned with Terraform (Firestore, Secret Manager, IAM):
    ```bash
    cd terraform
    cp terraform.tfvars.example terraform.tfvars   # fill in project_id, region, firestore_location
    terraform init && terraform apply
    ```
    The Functions themselves are still deployed with `firebase deploy` (Step 6).

## 5. Environment / configuration

| Where | Setting |
|---|---|
| `terraform/terraform.tfvars` | `project_id`, `region`, `firestore_location` |
| `.firebaserc` | the Firebase project alias |
| `functions/main.py` | function region (default `europe-west1`) |

## 6. Common deploy problems

| Symptom | Fix (from GUIDE.md) |
|---|---|
| Deploy fails on a brand-new project (build service account permission) | Grant the Cloud Build role: `gcloud projects add-iam-policy-binding "$PROJECT_ID" --member=... --role="roles/cloudbuild.builds.builder"`, then redeploy. |
| `/activate` returns **403** after deploy | Allow public invocation: `gcloud run services add-iam-policy-binding activate --member="allUsers" --role="roles/run.invoker" ...`. |
| Deploy fails: missing `functions/venv` | Re-run **Step 4** (`bootstrap_functions_venv.py`). |

See `tekla-iac/GUIDE.md` for the exact troubleshooting commands.

## 7. After deploying

Point the desktop apps at your server: set **`licensing.server_url`** in
`tekla-common/src/tekla_common/config.yaml` to the base URL from Step 6. Then use the
[Admin console](admin-console.md) to issue licences.

## 8. Secrets & security

| Secret | Purpose | Storage |
|---|---|---|
| `JWT_PRIVATE_KEY` | Signs licence tokens | Firebase secret; generated locally; **never commit** |
| `ADMIN_API_KEY` | Normal admin operations | Team password vault |
| `MASTER_ADMIN_API_KEY` | Emergency break-glass | Separate restricted vault |

- `keys/*.pem` are git-ignored — never commit them.
- Rotate keys per the runbook if exposed.

## 9. About the automated checks

The `iac.yml` GitHub Action only **validates** the infrastructure (`terraform fmt` /
`validate`, and a Functions syntax check). It **never deploys** — deployment is always the
manual, operator-run process above.
