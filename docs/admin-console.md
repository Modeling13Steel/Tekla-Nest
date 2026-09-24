# Tekla Nest Admin Console

The **Tekla Nest Admin Console** is a Windows desktop admin app for managing Tekla Nest software licences.

It is for **administrators and support staff**, not end users. Use it to:

1. Issue a new customer licence.
2. Revoke a licence.
3. Release a machine binding so a customer can activate again.
4. Delete a revoked or expired licence record.
5. List licences and check their current status.

The console talks to the Tekla Nest licence server over HTTPS — the `license-server/` Firebase Functions service in this repository (see [Infrastructure](infrastructure.md)).

| Term | Meaning |
| --- | --- |
| Licence key | The key given to a customer so Tekla Nest can be activated. |
| Admin API key | A secret token that lets an administrator call admin endpoints on the licence server. |
| Bearer token | The admin key is sent in the HTTPS `Authorization: Bearer <admin-key>` header. |
| Machine binding | The server record that says a licence has been activated on a specific computer. |

## Prerequisites and connection settings

You need two values before the console can connect.

| Setting | Where it comes from | What the app does |
| --- | --- | --- |
| Licence server URL | The deployed Firebase Functions base URL, for example `https://europe-west1-<project-id>.cloudfunctions.net` | The GUI shows a **License server URL** field, pre-filled from the root `config.yaml`'s `licensing.server_url`; if blank or wrong, paste the URL manually. The app requires it to start with `http://` or `https://`. |
| `ADMIN_API_KEY` | The normal admin key stored as a Firebase Functions secret | Paste it into the GUI **Admin key** field. The field is password-hidden. The GUI does not load it from an environment variable and does not save it for the next session. |

When you click **Connect and refresh** or **Test connection**, the app creates an API client with those two values. The client removes any trailing slash from the server URL and sends the key as:

```text
Authorization: Bearer <admin-key>
```

The **Using recovery key** checkbox only shows a warning in the GUI. It does not change the request. If you paste the `MASTER_ADMIN_API_KEY`, the same admin-key field is used.

## How to run or install it

The admin console is **part of the single `tekla-nest` package** — not a separate workspace
package. It lives in `src/tekla_nest/admin/` and shares config/i18n/branding with the nesting
app.

| Item | Value |
| --- | --- |
| Python package | `tekla_nest` (submodule `tekla_nest.admin`) |
| Entry point | `tekla-nest-admin` |
| Dev make target | `make run-admin` |

### Run from source

From the repository root:

```bash
make install
make run-admin
```

`make run-admin` runs:

```bash
uv run tekla-nest-admin
```

### Install on Windows

For normal admin users, install the Windows setup file:

```text
tekla-nest-admin-setup.exe
```

This installer is built by the GitHub Actions workflow **Build Windows Packages** on Windows (`make installer-admin` locally, which needs Inno Setup — see [Getting started](getting-started.md)). It is packaged separately from:

- the customer-facing Tekla Nest app installer;
- the licence-server infrastructure bundle.

## Common tasks

### 1. Connect to the licence server

1. Launch **Tekla Nest Admin**.
2. Enter the licence server base URL.
3. Paste the normal `ADMIN_API_KEY`.
4. Click **Connect and refresh**.
5. Confirm the licence table loads.

For a connection-only check, click **Test connection**.

### 2. Issue a licence

In the GUI:

1. Click **Create**.
2. Enter the customer or company name.
3. Set **Duration days**.
   - Default: `365` days.
   - Allowed range in the GUI: `1` to `3650` days.
4. Set **Max machines**.
   - Default: `1` machine.
   - Allowed range in the GUI: `1` to `25` machines.
5. Click **OK**.
6. The new licence key is copied to the clipboard.
7. Send the licence key to the customer through the approved support channel.

CLI equivalent, from `license-server/`:

```bash
python scripts/admin_cli.py create --customer "Acme Corporation" --days 365 --machines 1
```

### 3. Revoke a licence

Use this when a licence must no longer validate.

In the GUI:

1. Select the licence row.
2. Click **Revoke**.
3. Read the confirmation message.
4. Confirm only if you are sure.

CLI equivalent:

```bash
python scripts/admin_cli.py revoke --key <license-key>
```

!!! warning
    Revocation affects future online validation. If a customer is offline, the app may continue until its next required server validation.

### 4. Release a machine binding

Use this when a customer changes computer, reinstalls Windows, or needs to activate again.

In the GUI, to release all machines for the selected licence:

1. Select the licence row.
2. Click **Release all**.
3. Confirm the action.
4. Ask the customer to activate again.

To release one specific machine:

1. Select the licence row.
2. In **License Detail**, choose a machine under **Machine to release**.
3. Click **Release selected machine**.
4. Confirm the action.

CLI equivalents:

```bash
python scripts/admin_cli.py release --key <license-key>
python scripts/admin_cli.py release --key <license-key> --machine <machine-id>
```

### 5. Delete a licence

Use this to permanently remove a licence record that's no longer needed — for example to
clean up old **revoked** or **expired** licences from the list. This is a GUI-only action
(there is currently no `admin_cli.py delete` command).

1. Select a licence row whose status is **Revoked** or **Expired**.
2. Click **Delete**.
3. Read the confirmation message — this cannot be undone.
4. Confirm only if you are sure.

The **Delete** action is disabled for **Active**, **Unactivated** or **Full** licences — the
server rejects the request unless the licence is already revoked or expired, so revoke it
first if you need to remove an active licence.

### 6. List licences and check status

In the GUI:

1. Click **Refresh** to reload all licences.
2. Use the search box to find a customer, licence key, or machine.
3. Use the status filter for **Active**, **Unactivated**, **Full**, **Expired**, or **Revoked**.
4. Select a row to see details such as expiry date, days remaining, machines, activation time, and last validation time.
5. Click **Status** to fetch the latest server status for the selected licence.
6. Use **Copy license key** if you need to paste the selected key into a support message.

CLI equivalents:

```bash
python scripts/admin_cli.py list
python scripts/admin_cli.py status --key <license-key>
```

## Command-line alternative

The script `license-server/scripts/admin_cli.py` is supported for scripting, automation, and fallback support work. It reuses the same `tekla_nest.admin.api_client.AdminApiClient` as the GUI (create/list/status/revoke/release only — delete is GUI-only, see above).

Set these environment variables first:

```bash
export LICENSE_SERVER_URL="https://europe-west1-<project-id>.cloudfunctions.net"
export ADMIN_API_KEY="$ADMIN_KEY"
```

Then run commands from `license-server/`:

```bash
python scripts/admin_cli.py list
```

On Windows, if `python` isn't recognised, use the launcher instead: `py scripts\admin_cli.py list` (see [Getting started](getting-started.md#4-windows-notes-path-shims-venvs)).

## Security notes

!!! warning "Protect admin keys"
    `ADMIN_API_KEY` and `MASTER_ADMIN_API_KEY` can perform admin licence operations. Never commit them, paste them into issue trackers, include them in screenshots, or store them in release artifacts.

| Key | Use | Storage |
| --- | --- | --- |
| `ADMIN_API_KEY` | Normal daily admin work | Team password vault. Rotate if exposed or when staff access changes. |
| `MASTER_ADMIN_API_KEY` | Break-glass recovery only, for example when the normal key is lost | Separate restricted vault or offline recovery store. |

Break-glass process:

1. Use `MASTER_ADMIN_API_KEY` only when the normal `ADMIN_API_KEY` is unavailable.
2. Paste it into the same **Admin key** field.
3. Check **Using recovery key** so the warning is visible.
4. Do only the recovery task.
5. Rotate the normal `ADMIN_API_KEY` immediately if it was lost.
6. Close the admin app and return to the normal key.

The master key does **not** unlock the customer desktop app. It only authorizes the same licence-server admin endpoints as the normal admin key.

## Small commands table

| Task | Command |
| --- | --- |
| Install dependencies | `make install` |
| Run admin GUI from source | `make run-admin` |
| Run the entry point directly | `uv run tekla-nest-admin` |
| Set CLI server URL | `export LICENSE_SERVER_URL="https://europe-west1-<project-id>.cloudfunctions.net"` |
| Set CLI admin key | `export ADMIN_API_KEY="$ADMIN_KEY"` |
| CLI: create licence | `python scripts/admin_cli.py create --customer "Acme" --days 365 --machines 1` |
| CLI: list licences | `python scripts/admin_cli.py list` |
| CLI: check status | `python scripts/admin_cli.py status --key <license-key>` |
| CLI: revoke licence | `python scripts/admin_cli.py revoke --key <license-key>` |
| CLI: release all machines | `python scripts/admin_cli.py release --key <license-key>` |
| CLI: release one machine | `python scripts/admin_cli.py release --key <license-key> --machine <machine-id>` |
| Delete licence | GUI only — select a **Revoked**/**Expired** row → **Delete** |
