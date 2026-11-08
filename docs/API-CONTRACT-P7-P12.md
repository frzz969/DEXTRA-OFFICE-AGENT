# DEXTRA API CONTRACT — Identity, Authorization, Tokens, Security, Catalog (P7–P12)

Base path: `/api/v1`. All responses are JSON unless stated. Dates are ISO-8601 UTC.

This document is the contract the dashboard consumes. If an endpoint is not here, it does
not exist. Nothing here requires the client to enforce authorization — every rule below is
enforced on the server.

---

## 0. Authentication model

Two credential types, one resolution path.

| Type | Transport | Notes |
| --- | --- | --- |
| Session (human) | Cookie `dextra_session` (HttpOnly, SameSite=Lax) | Created by `POST /auth/login` |
| API token | `Authorization: Bearer dx_…` | Created by `POST /tokens`, shown once |

**CSRF.** Every `POST` that carries a session cookie must send `X-CSRF-Token` with the
value of the `dextra_csrf` cookie (readable by JS). Missing or wrong → `403` with
`{"detail": "...", "code": "csrf_failed"}`. Bearer-token requests are exempt.
`POST /auth/login` is exempt because no session exists yet; it validates `Origin` instead.

**Error shape.** Validation errors use FastAPI's default `{"detail": [...]}`. Domain errors
use `{"detail": "message"}` or `{"detail": {"code": "...", "message": "..."}}`.

**Status codes used consistently:** `401` not authenticated · `403` authenticated but not
permitted · `404` not found *or* belongs to another tenant (never `403`, to avoid
confirming existence) · `409` state conflict · `422` invalid input · `429` throttled.

---

## 1. Auth — `/auth`

### `POST /auth/login`
```json
{ "email": "budi@dextra.local", "password": "…", "tenant": "dextra-demo" }
```
`tenant` is optional; omit to use the user's default tenant. Sets both cookies.

`200`:
```json
{
  "authenticated": true,
  "mfa_required": false,
  "principal": {
    "principal_id": "usr_…", "display_name": "Budi Santoso", "email": "budi@dextra.local",
    "tenant_id": "ten_…", "tenant_slug": "dextra-demo", "role": "approver",
    "capabilities": ["view_own", "view_all", "create_request", "approve", "..."],
    "mfa_enabled": false, "pending_mfa": false
  },
  "session": { "id": "ses_…", "expires_at": "…", "idle_expires_at": "…" },
  "csrf_token": "…"
}
```
`401` `"Email atau password salah."` — identical for unknown email, wrong password,
inactive account, and unknown tenant. `429` + `Retry-After` when throttled.

If `mfa_required` is `true`: cookies are set but `capabilities` is `[]` and every
capability-guarded call returns `403` until `POST /auth/mfa/verify` succeeds.

### `POST /auth/logout` → `204`, revokes the session and clears cookies. Requires CSRF.

### `GET /auth/session`
Returns `{ authenticated, auth_kind, pending_mfa, scope, capabilities, principal,
tenant?, role?, mfa_enabled? }`. `auth_kind` ∈ `session | user_token | service_token |
legacy_token`.

### `POST /auth/mfa/enroll` → `{ secret, otpauth_uri, active: false }`
MFA is **not** active until a code is verified.

### `POST /auth/mfa/activate` `{ "code": "123456" }` → `{ active: true, mfa_enabled: true }`
Rotates the session. `400` on a wrong code.

### `POST /auth/mfa/verify` `{ "code": "…" }` → same shape as login (without `mfa_required`).
Rotates the session; the old one is revoked.

### `POST /auth/mfa/disable` `{ "password": "…", "code": "…" }` → `{ active: false }`

### `POST /auth/password` `{ "current_password": "…", "new_password": "…" }`
→ `{ changed: true, sessions_revoked: n }`. Revokes all other sessions and rotates the
current one. `422` if the new password is shorter than 12 characters.

### `GET /auth/sessions` → `{ items: [{ id, issued_at, last_seen_at, expires_at, ip_address, user_agent, mfa_verified, current }] }`

### `POST /auth/sessions/{session_id}/revoke` → `{ revoked: true, id }` · `404` if not yours.

### `GET /auth/google` · `GET /auth/google/callback` — **bukan jalur login**

Keduanya ada dan terdaftar, tetapi **belum menerbitkan sesi**: `GET /auth/google` hanya
mengembalikan `{ authorization_url }`, dan callback mengembalikan profil Google tanpa
cookie sesi. Tanpa `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` keduanya menjawab `503`.
Jangan memakainya sebagai login sampai sesi benar-benar diterbitkan di sana; gunakan
`POST /auth/login`.

---

## 1b. Intropeksi kontrak — `/permissions`, `/meta`

| Method | Path | Auth | Returns |
| --- | --- | --- | --- |
| GET | `/permissions` | authenticated | Capability milik pemanggil + kebenaran sistem |
| GET | `/meta` | authenticated | `api_prefix`, daftar capability, versi |

`/permissions` → `{ scope, principal, capabilities, enforced_capabilities,
unbacked_capabilities, all_capabilities, scope_capabilities }`.

`/meta` → `{ api_prefix, capabilities, enforced_capabilities, unbacked_capabilities,
auth_kind }`. Keduanya **butuh autentikasi** — tidak ada endpoint terbuka selain
`/health` dan `POST /auth/login`.

Tiga daftar itu berbeda artinya dan tidak boleh dicampur:

- `capabilities` — yang dimiliki pemanggil sekarang.
- `enforced_capabilities` — yang punya penegak nyata (dependency HTTP atau tool MCP).
  Dihitung saat impor router, bukan ditulis tangan.
- `unbacked_capabilities` — yang dikenal tetapi belum dijaga endpoint mana pun.
  Saat ini kosong: `edit_policy` punya penegak sejak `PATCH`/`DELETE /policies` ada.

---

## 2. Tokens — `/tokens`

| Method | Path | Capability | Notes |
| --- | --- | --- | --- |
| GET | `/tokens` | authenticated | Without `manage_integrations`, only your own tokens |
| POST | `/tokens` | session | Creates a token |
| POST | `/tokens/{token_id}/revoke` | owner or `manage_integrations` | Immediate |
| POST | `/tokens/{token_id}/rotate` | owner or `manage_integrations` | Old token dies |

`POST /tokens` body:
```json
{ "name": "cli", "scopes": ["view_own", "view_all"], "expires_in_days": 30,
  "service_account_id": null }
```
`service_account_id` requires `manage_integrations`. Requested scopes must be a subset of
the owner's capabilities, otherwise `422` `"Scope token melebihi wewenang pemiliknya."`

`201` returns the full token object **plus** `"token": "dx_…"` and
`"note": "Simpan token ini sekarang…"`. This is the only time the secret appears; `GET`
never includes it.

Token object: `{ id, name, prefix, scopes, status, owner, owner_id, created_at,
expires_at, last_used_at, revoked_at, rotated_from_id }`.

Creation requires a **session**, not an existing token — a leaked token cannot mint its
replacement.

---

## 3. Service identities — `/service-accounts`

All require `manage_integrations`.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/service-accounts` | `{ items: [{ id, name, kind, status, scopes, token_count, … }], kinds }` |
| POST | `/service-accounts` | Session only |
| GET | `/service-accounts/{service_account_id}` | Includes `tokens[]` |
| POST | `/service-accounts/{service_account_id}/revoke` | Revokes the identity **and** all its tokens |

`kind` ∈ `worker | mcp | agent | integration`. Credentials for these identities are issued
through `POST /tokens` with `service_account_id` — there is no second credential endpoint.

---

## 4. Security Center — `/security`

| Method | Path | Capability | Returns |
| --- | --- | --- | --- |
| GET | `/security/overview` | `view_audit` | Counts from real tables (see below) |
| GET | `/security/events` | `view_audit` | `?limit&offset&event_type&hours` |
| GET | `/security/login-history` | `view_audit` | Login/logout events only |
| GET | `/security/sessions` | `manage_users` | Active sessions of the whole tenant |
| POST | `/security/sessions/{session_id}/revoke` | `manage_users` | `404` if other tenant |
| GET | `/security/tokens` | `manage_integrations` | Inventory, no secrets |
| GET | `/security/service-identities` | `manage_integrations` | Inventory with active token counts |
| GET | `/security/mfa-status` | `manage_users` | Per-member MFA state |

`GET /security/overview`:
```json
{
  "tenant_id": "ten_…", "generated_at": "…",
  "sessions": { "active": 2 },
  "tokens": { "active": 3, "total": 5 },
  "service_accounts": { "active": 1 },
  "members": { "active": 4, "mfa_enabled": 1 },
  "last_24h": { "events_by_type": { "login_succeeded": 7 }, "failed_logins": 2, "denied": 0 },
  "capabilities": { "can_revoke_sessions": true }
}
```
Every number is a `COUNT` over `sessions`, `api_tokens`, `service_accounts`,
`memberships`, or `security_events`. Empty tables produce zeros, not estimates.

---

## 5. Members and roles — `/users`, `/roles`

Both require `manage_users` and are scoped to the caller's tenant.

`GET /users` → `{ items: [{ id, email, display_name, role, status, is_default, joined_at }],
tenant_id }`

`GET /roles` → `{ items: [{ id, name, description, is_system, capabilities }] }`
Includes system roles (`is_system: true`) plus tenant-specific roles.

---

## 6. Skill Registry — `/skills`

| Method | Path | Capability |
| --- | --- | --- |
| GET | `/skills` | `view_own` |
| GET | `/skills/{slug}` | `view_own` |
| POST | `/skills` | `manage_integrations` |
| POST | `/skills/{slug}/versions` | `manage_integrations` |
| POST | `/skills/{slug}/status` | `manage_integrations` |

Create body: `{ slug, display_name, description, version (semver), input_schema,
output_schema, required_capabilities[], manifest?, notes? }`.

Status transitions: `draft → active | disabled`, `active ↔ disabled`, either `→ deprecated`.
`deprecated` is terminal. Violations return `409` with `code: "INVALID_TRANSITION"`.

Validation errors (`422`, `detail.code`): `INVALID_SLUG`, `INVALID_SEMVER`,
`UNKNOWN_CAPABILITY`, `PRIVILEGED_CAPABILITY_FORBIDDEN`, `DUPLICATE_SKILL_ID`.

A skill may not request `approve`, `issue_mandate`, `revoke_mandate`, `execute`,
`edit_policy`, `manage_users`, or `manage_integrations` — a skill runs *inside* a mandate
and cannot grant itself the authority to approve or execute.

---

## 7. Workflows — `/workflows`

| Method | Path | Capability |
| --- | --- | --- |
| GET | `/workflows` | `view_own` |
| POST | `/workflows` | `manage_integrations` |
| POST | `/workflows/{workflow_id}/activate` | `manage_integrations` |
| POST | `/workflows/{workflow_id}/runs` | `create_request` |
| GET | `/workflows/runs` · `/workflows/runs/{run_id}` | `view_own` |
| POST | `/workflows/runs/{run_id}/gates/{step_id}/approve` | `approve` |
| POST | `/workflows/runs/{run_id}/resume` | `create_request` |

Definition body:
```json
{ "name": "alur-notulen", "description": "…", "steps": [
  { "id": "siapkan", "type": "noop" },
  { "id": "persetujuan", "type": "approval_gate", "depends_on": ["siapkan"] },
  { "id": "kirim", "type": "execute", "depends_on": ["persetujuan"],
    "params": { "mandate_id": "mnd_…", "action_id": "act_…", "action_type": "send_email",
                "payload": { "to": "…" } }, "max_attempts": 2 }
]}
```
`type` ∈ `noop | approval_gate | execute`. Definitions must be a DAG; cycles, unknown
dependencies, or a missing root step return `422` with `code: "INVALID_DEFINITION"`.

Run body: `{ "idempotency_key": "…", "inputs": {} }`. The same key returns the same run.

Run object: `{ id, workflow_id, status, idempotency_key, state, checkpoint_at, started_at,
finished_at, error, steps: [{ step_id, status, attempts, error, output, started_at,
finished_at, approved_by }] }`.

`status` ∈ `running | waiting_approval | succeeded | failed | cancelled`.
When a run reaches a gate it stops at `waiting_approval`; approving resumes it from the
checkpoint. An `execute` step by a caller without `execute` fails the run with
`error` naming the missing capability — it does not silently skip.

---

## 8. Office Agent — `/office-agent`

| Method | Path | Capability |
| --- | --- | --- |
| POST | `/office-agent/plans` | `create_request` |
| GET | `/office-agent/plans` · `/office-agent/plans/{plan_id}` | `view_own` |
| POST | `/office-agent/plans/{plan_id}/actions/{action_id}/approve` | `approve` |

Submit body:
```json
{ "request_id": "req-…", "plan_id": "pln-…", "plan_hash": "…",
  "source": { "kind": "markdown" }, "document": { "sha256": "…", "blocks": 12 },
  "actions": [{ "action_id": "act-1", "action_type": "send_email",
                "params": { "to": "…" }, "source_ref": { "block": 4 } }],
  "findings": [{ "code": "CALENDAR_CONFLICT", "severity": "warning" }],
  "validation": { "checks_passed": 10, "checks_total": 10 } }
```
`request_id` is the idempotency key: resubmitting returns the stored plan unchanged.
Duplicate `action_id` within one plan → `422`.

The worker submits; a human approves. `approve` returns
`{ approval_id, mandate_id, action_id, decision, next }`. Execute afterwards with
`POST /executions` using that `mandate_id` and the **same params**. A worker holding only
`create_request` gets `403` on its own plan's approval — that is the point.

---

## 8b. Operational writes — `/agents`, `/work-packages`, `/tasks`, `/policies`

Every write in this group follows the same rules, and they are the rules the frontend
should assume without asking:

- `tenant_id` comes from the caller's identity. A `tenant_id` in the request body is
  ignored — the server never reads it.
- A resource owned by another tenant answers **`404`**, not `403`. `403` would confirm
  that the row exists.
- A caller with no tenant (legacy gateway token without `DEXTRA_LEGACY_TENANT`) is
  rejected: `400` on writes, `404` on resource lookups.
- Rows with `tenant_id IS NULL` are legacy data that belongs to nobody. They are never
  visible to a tenant-bound caller and are never adopted by the seed.

| Method | Path | Permission | Body | Response |
|---|---|---|---|---|
| PATCH | `/agents/{slug}` | `manage_integrations` | `{ display_name?, description?, status?, is_enabled?, model_provider? }` | agent |
| DELETE | `/agents/{slug}` | `manage_integrations` | — | `{ deleted: true, slug, id }` |
| PATCH | `/work-packages/{package_id}` | `create_request` | `{ title?, status?, priority?, due_at? }` | `{ id, title, status, priority }` |
| DELETE | `/work-packages/{package_id}` | `create_request` | — | `{ deleted: true, id }` |
| PATCH | `/tasks/{task_id}` | `create_request` | `{ title?, description?, status?, sort_order? }` | task |
| DELETE | `/tasks/{task_id}` | `create_request` | — | `{ deleted: true, id }` |
| GET | `/tasks/{task_id}/assignments` | any authenticated | — | `{ items: [{ id, task_id, agent_id, role }] }` |
| POST | `/tasks/{task_id}/assignments` | `create_request` | `{ agent_slug, role? }` | `{ id, task_id, agent_id, role, created }` |
| DELETE | `/tasks/{task_id}/assignments/{assignment_id}` | `create_request` | — | `{ deleted: true, id }` |
| PATCH | `/policies/{slug}` | `edit_policy` | `{ title?, scope?, is_active?, rules_json?, change_note? }` | policy + `version` |
| DELETE | `/policies/{slug}` | `edit_policy` | — | `{ deleted: true, slug, id }` |

Rules specific to each:

- **Agent status** must be one of `active`, `idle`, `busy`, `disabled`, `error`; anything
  else is `422` and the row is not touched.
- **Task status** must be one of the `WORK_STATUSES` lifecycle values (`draft`,
  `pending_approval`, `approved`, `executing`, `completed`, `rejected`, `revoked`,
  `failed`, `cancelled`), otherwise `422`.
- **Assignment** is idempotent: the same `agent_slug` + `role` returns the existing row
  with `created: false`. Uniqueness is enforced by a database constraint on
  `(task_id, agent_id, role)`, so two concurrent requests cannot both create a row. Both the task and the agent must belong to the caller's tenant;
  a foreign agent is `404` and no assignment row is written. Assigning sets the task's
  `assigned_agent_id`; unassigning clears it when it pointed at that agent.
- **Policy** writes never overwrite history: supplying `rules_json` appends a
  `PolicyVersion` with `version = max + 1` and returns it as `version`. Omitting
  `rules_json` only changes metadata. Deleting a policy removes its versions with it.

Example — a foreign task, from a caller in another tenant:

```
PATCH /api/v1/tasks/tsk_other_tenant
{ "status": "approved" }
→ 404 { "detail": "Task tidak ditemukan." }
```

The status of the other tenant's task is unchanged. That is asserted in
`tests/integration/test_operational_writes_isolation.py`, which re-reads the row from the
database after every rejection.

---

## 9. What the frontend must not do

- Do not infer permissions from the UI; render `capabilities` from `/auth/session`.
- Do not send `approver_id` as a client-chosen identity for Office Agent approvals — the
  server records the verified principal.
- Do not cache a token secret; it is returned once and never again.
- Do not treat `403` on `/security/*` as a bug: `view_audit` and `manage_users` are
  different capabilities and auditors deliberately cannot revoke sessions.

---

## 10. Daftar rute terverifikasi

Rute yang benar-benar dilayani (diambil dari skema OpenAPI).

DELETE /api/v1/agents/{slug}
DELETE /api/v1/policies/{slug}
DELETE /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}/assignments/{assignment_id}
DELETE /api/v1/work-packages/{package_id}
GET /api/v1/agents
GET /api/v1/agents/{slug}
GET /api/v1/alerts/plans
GET /api/v1/analytics/daily
GET /api/v1/approvals
GET /api/v1/audit-events
GET /api/v1/audit-events/verify
GET /api/v1/auth/google
GET /api/v1/auth/google/callback
GET /api/v1/auth/session
GET /api/v1/auth/sessions
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}
GET /api/v1/conversations/{conversation_id}/messages
GET /api/v1/data/export
GET /api/v1/executions
GET /api/v1/integrations/status
GET /api/v1/mandates
GET /api/v1/mandates/{mandate_id}
GET /api/v1/meta
GET /api/v1/office-agent/intake/{intake_id}
GET /api/v1/office-agent/plans
GET /api/v1/office-agent/plans/{plan_id}
GET /api/v1/overview
GET /api/v1/permissions
GET /api/v1/policies
GET /api/v1/policies/{slug}/versions
GET /api/v1/roles
GET /api/v1/search
GET /api/v1/security/events
GET /api/v1/security/login-history
GET /api/v1/security/mfa-status
GET /api/v1/security/overview
GET /api/v1/security/service-identities
GET /api/v1/security/sessions
GET /api/v1/security/tokens
GET /api/v1/service-accounts
GET /api/v1/service-accounts/{service_account_id}
GET /api/v1/settings
GET /api/v1/skills
GET /api/v1/skills/{slug}
GET /api/v1/tasks
GET /api/v1/tasks/{task_id}/assignments
GET /api/v1/tokens
GET /api/v1/users
GET /api/v1/work-packages
GET /api/v1/work-packages/{package_id}
GET /api/v1/workflows
GET /api/v1/workflows/runs
GET /api/v1/workflows/runs/{run_id}
GET /health
PATCH /api/v1/agents/{agent_id}
PATCH /api/v1/agents/{slug}
PATCH /api/v1/policies/{slug}
PATCH /api/v1/roles/{role_id}
PATCH /api/v1/settings
PATCH /api/v1/tasks/{task_id}
PATCH /api/v1/users/{user_id}
PATCH /api/v1/work-packages/{package_id}
POST /api/v1/agents
POST /api/v1/approvals
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/mfa/activate
POST /api/v1/auth/mfa/disable
POST /api/v1/auth/mfa/enroll
POST /api/v1/auth/mfa/verify
POST /api/v1/auth/password
POST /api/v1/auth/sessions/{session_id}/revoke
POST /api/v1/conversations
POST /api/v1/conversations/{conversation_id}/messages
POST /api/v1/data/reset
POST /api/v1/data/seed
POST /api/v1/executions
POST /api/v1/mandates/{mandate_id}/revoke
POST /api/v1/office-agent/intake
POST /api/v1/office-agent/intake/{intake_id}/clarify
POST /api/v1/office-agent/plans
POST /api/v1/office-agent/plans/{plan_id}/actions/{action_id}/approve
POST /api/v1/policies/evaluate
POST /api/v1/roles
POST /api/v1/security/sessions/{session_id}/revoke
POST /api/v1/service-accounts
POST /api/v1/service-accounts/{service_account_id}/revoke
POST /api/v1/skills
POST /api/v1/skills/{slug}/status
POST /api/v1/skills/{slug}/versions
POST /api/v1/tasks
POST /api/v1/tasks/{task_id}/assignments
POST /api/v1/tasks/{task_id}/transition
POST /api/v1/tokens
POST /api/v1/tokens/{token_id}/revoke
POST /api/v1/tokens/{token_id}/rotate
POST /api/v1/users
POST /api/v1/workflows
POST /api/v1/workflows/runs/{run_id}/gates/{step_id}/approve
POST /api/v1/workflows/runs/{run_id}/resume
POST /api/v1/workflows/{workflow_id}/activate
POST /api/v1/workflows/{workflow_id}/runs
