# License Server - Firebase Runbook

This document covers the full license-server workflow: Firebase-only deployment, app prompt enablement, admin license management, break-glass recovery, and key rotation.

## Architecture

The license system has two parts:

1. Desktop app client
   - Shows the activation prompt when `licensing.required: true`.
   - Calls Firebase Cloud Functions for first-time activation and periodic validation.
   - Stores a local machine-bound JWT token after activation.
   - Verifies that token offline with `src/tekla_nest/licensing/public_key.pem`.
2. Firebase license server
   - Cloud Functions expose `/activate`, `/validate`, and admin endpoints.
   - Firestore stores license records and machine bindings.
   - Firebase Functions secrets store signing and admin credentials.

No separate Google Cloud CLI flow is required for normal (day-to-day) operation. `license-server/terraform/` is an optional, one-time alternative to the manual `gcloud`/Console steps in **Initial Firebase setup** below — it enables the required GCP APIs, creates the Firestore database, and provisions the Functions service account and secret placeholders. It is not run automatically by `make`; use it instead of the manual steps if you prefer IaC for initial project bootstrap.

## Secrets

| Secret | Purpose | Who uses it | Storage guidance |
| --- | --- | --- | --- |
| `JWT_PRIVATE_KEY` | Signs app license JWTs | Firebase Functions only | Firebase secret; generated from `keys/private_key.pem`; never commit |
| `ADMIN_API_KEY` | Normal admin API bearer token | Admin CLI / admin operators | Password vault; rotate if exposed or staff access changes |
| `MASTER_ADMIN_API_KEY` | Break-glass admin bearer token | Emergency recovery only | Separate restricted vault or offline recovery store |

The master admin key does **not** bypass end-user licensing inside the desktop app. It only authorizes the same server admin endpoints as `ADMIN_API_KEY` if the regular admin key is lost.

## Admin quick map

Use this section when something is not working and you need to decide where to look.

| Area | What it means | Where to check |
| --- | --- | --- |
| Customer license key | The key the customer types into Tekla Nest | Admin CLI or Firestore `licenses` collection |
| Local validation file | The customer machine's saved activation token | Customer PC: `~/.teklanest/license.dat` |
| Public key in app | Lets the app verify server-issued tokens offline | App package/source: `src/tekla_nest/licensing/public_key.pem` |
| Private signing key | Lets the server issue activation tokens | Firebase secret `JWT_PRIVATE_KEY` |
| Admin key | Lets admins create/revoke/release licenses | Firebase secret `ADMIN_API_KEY` |
| Master admin key | Emergency admin recovery key | Firebase secret `MASTER_ADMIN_API_KEY` |
| License database | Server-side customer/license records | Firebase Console > Firestore Database > `licenses` |
| Server logs | Why an endpoint failed | Firebase Console > Functions logs or Cloud Logging |

## Where licensing data and validation files live

### On the customer computer

After successful activation, Tekla Nest stores a local machine-bound validation file:

| Platform | Path |
| --- | --- |
| Windows | `C:\Users\<user>\.teklanest\license.dat` |
| macOS | `/Users/<user>/.teklanest/license.dat` |
| Linux | `/home/<user>/.teklanest/license.dat` |

What admins should know:

- This file is created only after successful activation.
- It is tied to that machine and should not be copied to another computer.
- Deleting it forces Tekla Nest to ask for activation again.
- If it is copied, corrupted, or moved between machines, the app will ask the user to reactivate.
- It does not replace the server license record; it is only the local offline validation token.

Safe reset for a customer machine:

1. Close Tekla Nest.
2. Delete `license.dat` from the `.teklanest` folder.
3. Open Tekla Nest.
4. Activate again with the customer's license key.

### In the app release

Licensed builds must include:

```text
src/tekla_nest/licensing/public_key.pem
```

This public key must match the private key uploaded as `JWT_PRIVATE_KEY`. If the keys do not match, activations may succeed on the server but the app will reject or fail to validate the returned token.

### In Firebase

Firebase stores the live server data:

| Firebase area | What is stored |
| --- | --- |
| Firestore `licenses` collection | License keys, customer names, expiry dates, machine bindings, revoked flag |
| Functions secrets | `JWT_PRIVATE_KEY`, `ADMIN_API_KEY`, `MASTER_ADMIN_API_KEY` |
| Functions / Cloud Run | Deployed endpoints: `activate`, `validate`, `admin_create`, `admin_list`, `admin_release`, `admin_revoke`, `admin_status` |
| Logs | Errors, deploy events, startup events, function failures |

Admins should not edit secrets by hand unless rotating keys. Editing Firestore records manually should be rare; prefer the admin CLI.

## Automated deploy

`scripts/deploy.py` automates everything below (tool install, login, one-time
bootstrap, deploy) and works on macOS, Linux, and Windows:

```bash
python3.12 scripts/deploy.py
```

It prompts before installing missing CLIs or creating secrets. Use
`--deploy-only` for a routine redeploy once bootstrap is done, or `--yes` to
skip prompts (e.g. in CI). Run `python3.12 scripts/deploy.py --help` for all
options. The sections below describe what the script does step by step, and
remain the manual/troubleshooting reference.

## Initial Firebase setup

Install tools:

```bash
npm install -g firebase-tools
python3.12 --version
python3.12 -m pip install cryptography requests
```

Sign in and select the project:

```bash
firebase login
cd license-server
firebase use --add
```

When prompted, choose the Firebase project and assign an alias such as `default`.

In the Firebase Console:

1. Enable billing for the project because Cloud Functions require it.
2. Create a Firestore database in native mode.
3. Choose `eur3` for the Firestore database location unless you have a project-specific data residency reason to choose another location.

CLI equivalent:

```bash
PROJECT_ID="teklanest-d2699"

gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"
gcloud firestore databases create \
  --project="$PROJECT_ID" \
  --database="(default)" \
  --location=eur3
```

The Firestore database location cannot be changed after creation.

## Generate signing keys

From `license-server/`:

```bash
python scripts/generate_keys.py
```

This creates:

| File | Purpose |
| --- | --- |
| `keys/private_key.pem` | Server signing key; upload to Firebase; do not commit |
| `keys/public_key.pem` | Generated public key copy |
| `../src/tekla_nest/licensing/public_key.pem` | Public key embedded in the desktop app |

Keep the private key secret. The desktop app only receives the public key.

## Bootstrap the Firebase Functions Python environment

Firebase CLI analyzes Python functions before deploying and expects a virtual environment at `license-server/functions/venv`. If this venv is missing, deploy fails with:

```text
Failed to find location of Firebase Functions SDK: Missing virtual environment at venv directory.
```

Create the venv from `license-server/`:

```bash
python3.12 scripts/bootstrap_functions_venv.py
```

The script creates `functions/venv` and installs `functions/requirements.txt`.

Manual equivalent:

```bash
cd functions
python3.12 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
cd ..
```

On Windows, use `venv\Scripts\python.exe` instead of `./venv/bin/python`.

## Create Firebase Functions secrets

Upload the JWT signing key:

```bash
firebase functions:secrets:set JWT_PRIVATE_KEY < keys/private_key.pem
```

Create the normal admin key:

```bash
ADMIN_KEY=$(openssl rand -hex 32)
echo "$ADMIN_KEY"
printf "%s" "$ADMIN_KEY" | firebase functions:secrets:set ADMIN_API_KEY
```

Create the break-glass master key:

```bash
MASTER_ADMIN_KEY=$(openssl rand -hex 48)
echo "$MASTER_ADMIN_KEY"
printf "%s" "$MASTER_ADMIN_KEY" | firebase functions:secrets:set MASTER_ADMIN_API_KEY
```

Store `ADMIN_KEY` in the normal team password vault. Store `MASTER_ADMIN_KEY` separately with stricter access. Do not store either value in the repository, shell history notes, issue trackers, or release artifacts.

## Deploy the license server

Confirm the functions venv exists before deploy:

```bash
test -d functions/venv || python3.12 scripts/bootstrap_functions_venv.py
```

```bash
firebase deploy --only functions
```

Firebase prints URLs like:

```text
https://europe-west1-<project-id>.cloudfunctions.net/activate
```

The base URL for app/admin configuration is the URL without the final function name:

```text
https://europe-west1-<project-id>.cloudfunctions.net
```

If deployment partially succeeds, do not enable the desktop activation prompt until both client endpoints exist:

- `/activate`
- `/validate`

## Troubleshooting deploys

### Missing build service account permission

Symptom:

```text
Build failed with status: FAILURE. Could not build the function due to a missing permission on the build service account.
```

This can happen on new Firebase projects after Cloud Functions, Cloud Build, Cloud Run, Eventarc, Artifact Registry, and Secret Manager are enabled for the first time. Firebase deploys Cloud Functions on top of Google Cloud infrastructure, so this one-time IAM repair may be required even though the normal workflow remains Firebase CLI based.

The build service account needs the Cloud Build Service Account role. For the project from the deploy output:

```bash
PROJECT_ID="teklanest-d2699"
PROJECT_NUMBER="228361706735"
BUILD_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/cloudbuild.builds.builder"
```

If using the Google Cloud Console instead:

1. Open IAM for the Firebase project.
2. Grant access to `<project-number>-compute@developer.gserviceaccount.com`.
3. Add the role **Cloud Build Service Account**.
4. Save.

Then redeploy the functions codebase:

```bash
firebase deploy --only functions:license-server
```

If Firebase reports that the codebase selector is unsupported, run the full functions deploy:

```bash
firebase deploy --only functions
```

### `/activate` returns platform 403 after deploy

Symptom:

```bash
curl https://europe-west1-<project-id>.cloudfunctions.net/activate
```

returns an HTML `403 Forbidden` page instead of the function JSON response:

```json
{"error": "POST required"}
```

This means the Cloud Run service exists but unauthenticated clients cannot invoke it. The desktop app needs `/activate` to be publicly invokable because license-key authorization happens inside the function.

Fix:

```bash
PROJECT_ID="teklanest-d2699"

gcloud run services add-iam-policy-binding activate \
  --project="$PROJECT_ID" \
  --region=europe-west1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

Verify:

```bash
curl https://europe-west1-teklanest-d2699.cloudfunctions.net/activate
```

Expected response for a GET request:

```json
{"error": "POST required"}
```

### Admin CLI returns a non-JSON 500 response

Symptom:

```text
python scripts/admin_cli.py list
Error: Server returned a non-JSON response (500): 500 Internal Server Error
```

Check function logs:

```bash
gcloud functions logs read admin_list \
  --gen2 \
  --region=europe-west1 \
  --project=teklanest-d2699 \
  --limit=30
```

If logs say `Cloud Firestore API has not been used... or it is disabled`, enable Firestore and create the default database:

```bash
PROJECT_ID="teklanest-d2699"

gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"
gcloud firestore databases create \
  --project="$PROJECT_ID" \
  --database="(default)" \
  --location=eur3
```

If the database already exists, wait a few minutes for the API enablement to propagate and retry:

```bash
python scripts/admin_cli.py list
```

If the local CLI fails with `ModuleNotFoundError: No module named 'requests'`, install the admin CLI dependency:

```bash
python3.12 -m pip install requests
```

## Enable the license prompt in a release

The license prompt appears only in builds where licensing is enabled in `config.yaml`.

Before building a licensed release:

1. Confirm `src/tekla_nest/licensing/public_key.pem` exists and matches the deployed `JWT_PRIVATE_KEY`.
2. Set licensing config:

   ```yaml
   licensing:
     required: true
     server_url: "https://europe-west1-<project-id>.cloudfunctions.net"
     revalidation_days: 30
   ```

3. Rebuild the app binary or installer.
4. Ship the rebuilt artifact.

Existing binaries do not update automatically. A binary built with `licensing.required: false` will not show the prompt.

## Admin GUI setup

The preferred non-technical admin workflow is the separate **Tekla Nest Admin** desktop app. It is packaged separately from the customer-facing Tekla Nest app and separately from the Firebase/license-server infrastructure.

Use the admin GUI for daily operations:

1. Launch **Tekla Nest Admin**.
2. Enter the license server base URL:

   ```text
   https://europe-west1-<project-id>.cloudfunctions.net
   ```

3. Paste the normal `ADMIN_API_KEY`.
4. Click **Connect and refresh**.
5. Use the license table to search customers, copy license keys, create licenses, revoke licenses, and release machine bindings.

The admin GUI intentionally does **not** store the admin key by default. Paste it from the password vault for each admin session.

If you must use the master recovery key:

1. Paste `MASTER_ADMIN_API_KEY` into the same admin-key field.
2. Check **Using recovery key** so the warning is visible.
3. Perform only the recovery task.
4. Rotate the normal admin key if needed.
5. Close the admin app.

The admin GUI never displays or manages `JWT_PRIVATE_KEY`, `ADMIN_API_KEY`, or `MASTER_ADMIN_API_KEY` values from Firebase. It only uses the key provided by the admin for that session.

## Admin CLI setup

The CLI remains supported for automation, remote debugging, and fallback use when the GUI is unavailable.

Use the normal admin key for daily operations:

```bash
export LICENSE_SERVER_URL="https://europe-west1-<project-id>.cloudfunctions.net"
export ADMIN_API_KEY="$ADMIN_KEY"
```

Create a license:

```bash
python scripts/admin_cli.py create \
  --customer "Acme Corporation" \
  --days 365 \
  --machines 1
```

Other admin operations:

```bash
python scripts/admin_cli.py list
python scripts/admin_cli.py status --key <license-key>
python scripts/admin_cli.py revoke --key <license-key>
python scripts/admin_cli.py release --key <license-key>
python scripts/admin_cli.py release --key <license-key> --machine <machine-id>
```

## End-user activation flow

1. User launches a licensed build.
2. The activation dialog appears.
3. User enters a license key created through the admin CLI.
4. The app calls `/activate`.
5. The server validates the license, binds it to the machine, and returns a JWT.
6. The app stores a local machine-bound token and unlocks.
7. The app works offline until the next configured revalidation interval.
8. Revoked, expired, or machine-mismatched licenses fail on the next required validation.

Activation runs in a background Qt worker, so slow network calls do not freeze the dialog.

## Non-technical troubleshooting guide

Use this as a first-response checklist before escalating to engineering.

### App does not show the activation prompt

Likely causes:

- The build was created with `licensing.required: false`.
- The user is running an old binary.
- The user already has a valid local `license.dat`.

What to do:

1. Confirm the shipped `config.yaml` has `licensing.required: true`.
2. Confirm the app was rebuilt after the config change.
3. Ask the user to close the app and delete their local `license.dat` if you intentionally want to force reactivation.
4. Relaunch Tekla Nest.

### App shows activation prompt but activation fails

Ask for:

- Screenshot of the error.
- Customer name.
- License key only through a secure channel.
- Machine ID shown in the activation dialog, or at least the first 16 characters displayed there.
- Whether the machine has internet access.

Checks:

1. Verify the server URL in `config.yaml`:

   ```yaml
   server_url: "https://europe-west1-teklanest-d2699.cloudfunctions.net"
   ```

2. Check that `/activate` reaches the function:

   ```bash
   curl https://europe-west1-teklanest-d2699.cloudfunctions.net/activate
   ```

   Expected GET response:

   ```json
   {"error": "POST required"}
   ```

3. Check the license exists:

   ```bash
   python scripts/admin_cli.py status --key <license-key>
   ```

4. Confirm it is not revoked, expired, or already at the machine limit.

### Customer moved to a new PC

If the license is limited to one machine, release the old machine binding:

```bash
python scripts/admin_cli.py release --key <license-key>
```

Then ask the customer to activate on the new PC.

If you only want to release one machine and keep other machines active:

```bash
python scripts/admin_cli.py release --key <license-key> --machine <machine-id>
```

### Customer says "license file is corrupted"

Likely causes:

- The local validation file was copied from another machine.
- The file was partially written or damaged.
- The machine fingerprint changed enough that the file no longer matches.

Safe fix:

1. Close Tekla Nest.
2. Delete the local validation file:

   ```text
   C:\Users\<user>\.teklanest\license.dat
   ```

3. Relaunch Tekla Nest.
4. Activate again.

If activation says the license is already used on another machine, release the machine binding from the admin CLI.

### Admin CLI says "Invalid admin API key"

Likely causes:

- `ADMIN_API_KEY` environment variable is missing.
- The key was copied with an extra space or newline.
- The regular admin key was rotated.

What to do:

1. Re-copy the normal admin key from the password vault.
2. Set it again:

   ```bash
   export ADMIN_API_KEY="<admin-key>"
   ```

3. Retry:

   ```bash
   python scripts/admin_cli.py list
   ```

If the normal key is lost, use the break-glass recovery flow and rotate the normal key immediately.

### Admin CLI returns a 500 error

Most common causes:

- Firestore was not enabled.
- Firestore database was not created.
- Firebase Functions runtime service account lacks a permission.
- A server bug occurred.

First checks:

```bash
gcloud functions logs read admin_list \
  --gen2 \
  --region=europe-west1 \
  --project=teklanest-d2699 \
  --limit=30
```

If logs mention Firestore, follow the Firestore setup in the troubleshooting section above.

### Server deploy succeeds but one endpoint is missing

Do not enable licensing in the desktop app until both customer endpoints work:

```bash
curl https://europe-west1-teklanest-d2699.cloudfunctions.net/activate
curl https://europe-west1-teklanest-d2699.cloudfunctions.net/validate
```

Expected GET response for both:

```json
{"error": "POST required"}
```

If `/activate` returns an HTML 403 page, apply the `/activate` invoker fix in the deploy troubleshooting section.

## Admin operating checklist

### Daily admin flow

1. Set environment variables:

   ```bash
   export LICENSE_SERVER_URL="https://europe-west1-teklanest-d2699.cloudfunctions.net"
   export ADMIN_API_KEY="<admin-key-from-vault>"
   ```

2. Create a license:

   ```bash
   python scripts/admin_cli.py create --customer "Customer Name" --days 365 --machines 1
   ```

3. Send only the license key to the customer.
4. Keep customer/license details in your admin records.

### Monthly checks

1. Run:

   ```bash
   python scripts/admin_cli.py list
   ```

2. Confirm active licenses look correct.
3. Check Firebase billing/usage.
4. Confirm the master admin key is still stored in the restricted recovery vault.

### Before releasing a licensed app build

1. Confirm functions are deployed.
2. Confirm `/activate` and `/validate` return JSON for GET requests.
3. Confirm `src/tekla_nest/licensing/public_key.pem` exists.
4. Confirm `config.yaml` has licensing enabled and the correct `server_url`.
5. Rebuild the app.
6. Test activation with a temporary license.

## Information to collect before escalation

For customer activation issues:

- Customer name.
- License key, only through a secure channel.
- Screenshot of the activation error.
- Machine ID prefix shown in the dialog.
- App version.
- Whether this is a new install, renewal, or machine move.
- Whether the computer has internet access.

For server/admin issues:

- Exact command that failed.
- Exact error output.
- Which key was used: normal admin or break-glass, but never paste the key value.
- Function logs for the affected endpoint.
- Whether Firestore and functions were recently deployed or changed.

Do not collect private keys, admin key values, master key values, full imported customer files, or screenshots containing secrets.

## Break-glass recovery if `ADMIN_API_KEY` is lost

Use this only if the normal admin key is unavailable.

1. Retrieve `MASTER_ADMIN_KEY` from the restricted recovery store.
2. Use it as the admin bearer token:

   ```bash
   export LICENSE_SERVER_URL="https://europe-west1-<project-id>.cloudfunctions.net"
   export ADMIN_API_KEY="$MASTER_ADMIN_KEY"
   ```

3. Confirm access:

   ```bash
   python scripts/admin_cli.py list
   ```

4. Rotate the normal admin key immediately:

   ```bash
   NEW_ADMIN_KEY=$(openssl rand -hex 32)
   echo "$NEW_ADMIN_KEY"
   printf "%s" "$NEW_ADMIN_KEY" | firebase functions:secrets:set ADMIN_API_KEY
   firebase deploy --only functions
   ```

5. Store `NEW_ADMIN_KEY` in the normal team vault.
6. Switch day-to-day admin operations back to the normal key:

   ```bash
   export ADMIN_API_KEY="$NEW_ADMIN_KEY"
   ```

Do not continue using the master key after recovery.

## Key rotation

### Rotate the normal admin key

```bash
NEW_ADMIN_KEY=$(openssl rand -hex 32)
echo "$NEW_ADMIN_KEY"
printf "%s" "$NEW_ADMIN_KEY" | firebase functions:secrets:set ADMIN_API_KEY
firebase deploy --only functions
```

Store the new value in the normal team password vault.

### Rotate the break-glass master key

```bash
NEW_MASTER_ADMIN_KEY=$(openssl rand -hex 48)
echo "$NEW_MASTER_ADMIN_KEY"
printf "%s" "$NEW_MASTER_ADMIN_KEY" | firebase functions:secrets:set MASTER_ADMIN_API_KEY
firebase deploy --only functions
```

Store this value separately from the normal admin key.

### Rotate JWT signing keys

```bash
python scripts/generate_keys.py
firebase functions:secrets:set JWT_PRIVATE_KEY < keys/private_key.pem
firebase deploy --only functions
```

JWT signing-key rotation invalidates existing local license tokens. Rebuild and redistribute the desktop app because it embeds the new public key.

## Security rules

- Never commit `keys/`, Firebase `.env` files, private keys, or admin keys.
- Use `ADMIN_API_KEY` for daily work and `MASTER_ADMIN_API_KEY` only for recovery.
- Store the master key separately from the regular key.
- Rotate `ADMIN_API_KEY` after using the master key.
- Rotate `MASTER_ADMIN_API_KEY` if anyone outside the recovery group sees it.
- Do not send license keys, machine IDs, or admin keys in screenshots, logs, issues, or support tickets.

## FAQ for license admins

### Is the master admin key a way for customers to bypass licensing?

No. It only authorizes server admin endpoints. It does not unlock the desktop app and should not be shared with customers.

### Where is the customer activation stored?

On the customer machine, activation is stored in `~/.teklanest/license.dat`. On the server, the license and machine binding are stored in Firestore under the `licenses` collection.

### Can I copy `license.dat` from one PC to another?

No. The file is machine-bound. Copying it will usually cause a corruption or machine mismatch error.

### What happens if a customer deletes `license.dat`?

Tekla Nest will ask for activation again. The server license record still exists.

### What should I do when a customer changes computers?

Release the machine binding with:

```bash
python scripts/admin_cli.py release --key <license-key>
```

Then ask the customer to activate on the new computer.

### What does `--machines` mean when creating a license?

It is the number of different machines allowed to activate the same license key. Use `--machines 1` for a single-user/single-PC license.

### Can a license work offline?

Yes, after first activation. First activation requires internet access. After that, the app uses the local validation file and periodically phones home based on `revalidation_days`.

### What happens when a license is revoked?

The app will fail the next required online validation. If the user is offline, the app may continue until the next validation attempt can reach the server.

### What happens when a license expires?

The local token includes expiry information. Once expired, the app will reject it and require renewal/reactivation.

### How do I renew a customer?

Create a new license with a new duration, or update the Firestore `expires_at` only if you are comfortable editing Firestore timestamps. Prefer issuing a new license key unless there is a strong reason to preserve the old one.

### What if the admin key is lost?

Use `MASTER_ADMIN_API_KEY` only long enough to rotate `ADMIN_API_KEY`, then return to normal admin key usage.

### What if the master admin key is lost?

If you still have normal admin access, rotate `MASTER_ADMIN_API_KEY` immediately. If both admin keys are lost, use Firebase Console access to set new Functions secrets, then redeploy.

### What if I rotate `JWT_PRIVATE_KEY`?

You must rebuild and redistribute the desktop app because the app embeds the matching public key. Existing local validation files will no longer validate.

### Why does Firebase mention Google Cloud or Secret Manager?

Firebase Functions runs on Google Cloud infrastructure. The day-to-day workflow is Firebase CLI/Console, but logs, IAM, Cloud Run, Artifact Registry, Firestore, and Secret Manager are the underlying services.

### What URL goes into `config.yaml`?

Use the shared Cloud Functions base URL:

```yaml
server_url: "https://europe-west1-teklanest-d2699.cloudfunctions.net"
```

Do not use a per-function `run.app` URL in the desktop app config.

### What are the minimum checks before telling a customer "try again"?

1. `/activate` returns `{"error": "POST required"}` for GET.
2. `/validate` returns `{"error": "POST required"}` for GET.
3. `python scripts/admin_cli.py status --key <license-key>` works.
4. License is not revoked or expired.
5. Machine limit is not already used up.

## Smoke checks

After deploying functions:

```bash
export LICENSE_SERVER_URL="https://europe-west1-<project-id>.cloudfunctions.net"
export ADMIN_API_KEY="$ADMIN_KEY"
python scripts/admin_cli.py list
```

After building a licensed app:

1. Launch the app on a clean machine/profile.
2. Confirm the activation dialog appears.
3. Create a test license with the admin CLI.
4. Activate the app with that license.
5. Relaunch the app and confirm it opens without prompting again.

## File structure

```text
license-server/
├── firebase.json
├── functions/
│   ├── main.py
│   └── requirements.txt
├── scripts/
│   ├── admin_cli.py
│   ├── bootstrap_functions_venv.py
│   ├── deploy.py
│   └── generate_keys.py
├── terraform/          # optional IaC alternative to manual gcloud setup
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── .gitignore

src/tekla_nest/
├── licensing/
│   ├── __init__.py
│   ├── activation_client.py
│   ├── license_crypto.py
│   ├── license_manager.py
│   ├── license_validator.py
│   ├── machine_id.py
│   ├── models.py
│   ├── self_integrity.py
│   ├── requirements.txt
│   └── public_key.pem
└── views/
    └── activation_dialog.py
```
