# Helm API — the 7710 contract

The JSON/HTML API the patched dsh web UI codes against, served by
`helm-api.service` on a second loopback port, **7710**, distinct from the
read-only status page on 7700. Every response is loopback-only and fails
closed; a `POST` body over 256 bytes is refused `413` before any handler runs.
A request whose `Host` header is outside the allowlist is refused `400`. A
request carrying an `Origin` header outside the allowlist is refused `403`. A
known path with an unregistered method is refused `405` with an `Allow` header
naming the registered methods. There is no switch route; the switch stays
behind the desktop password on 7700.

### GET /

The web home page, `text/html` (the one non-JSON response), rendered in
process: declared flakes, the session list with Start/Stop/Attach, the patch
queue, the status tiles and the operator's links.

- `200` — the page; a domain that is down renders `unavailable: <error>`, the
  page still answers.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET` (with `Allow: GET`).

### GET /v1/status

The collector's status document (`status.json` under `services.helm.out_dir`),
one entry per health tile.

- `200` — the tile document.
- `404` — no status document collected yet.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### GET /v1/control

The profile card (`read_state`): the active profile, the last switch, and the
allowed profiles and hosts.

- `200` — the control document.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### GET /v1/home

The declared flakes (`/etc/helm/home.json`).

- `200` — `{"flakes": [...]}`, or `{"flakes": []}` when the file is absent.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### GET /v1/seats

The session list: the spool's jobs joined with the live `systemctl list-units`
state, sorted by id.

- `200` — `{"seats": [{"id", "unit", "state", "port", "url", "exit_code"}, ...]}`.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### POST /v1/seats

Body: `{"mode": "web" | "drive", "workspace": "<absolute path>"}` — nothing
else is admitted. Runs `seat-submit` through the allowlisted seam.

- `202` — accepted; `{"id": "<job id>"}`.
- `400` — an unknown key, a relative workspace, an unknown mode, or a bad
  `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `POST` (with `Allow: POST`).
- `413` — body over 256 bytes.

### POST /v1/seats/<id>/stop

Stops `seat@<id>.service` through the allowlisted seam.

- `202` — accepted; `{"id": "<id>", "unit": "seat@<id>.service"}`.
- `400` — an `<id>` that fails the strict pattern, or a bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `POST`.
- `413` — body over 256 bytes.

### POST /v1/seats/<id>/attach

The loopback URL for a started seat's web UI, read from the spool's `job.json`.

- `200` — `{"url": "http://127.0.0.1:<port>/"}`.
- `400` — an `<id>` that fails the strict pattern, or a bad `Host`.
- `403` — bad `Origin`.
- `404` — no such job.
- `405` — a method other than `POST`.
- `409` — the job has no port yet.
- `413` — body over 256 bytes.

### GET /v1/patches

The patch queue (`docs/ledger/patches.toml` at `services.helm.repo`'s `HEAD`)
joined with the running generation.

- `200` — `{"running_generation", "head", "patches": [...]}`, each row carrying
  `carried_by_next_switch`.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### GET /v1/tasks

The derived task queue (`python3 pkgs/evidence/tasks.py --root <repo> json`),
passed through with a top-level `source` marker.

- `200` — the task document.
- `400` — bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `GET`.

### POST /v1/engage

Body (JSON whatever the `Content-Type`, since `sendBeacon` sends `text/plain`):
`{"counter": <COUNTERS>, "n": <int >= 1>, "surface": <SURFACES>}` — folds one
increment into the local engagement ledger.

- `204` — folded; no body.
- `400` — an unknown counter, an out-of-enum surface, a non-positive `n`, an
  extra key, a non-JSON body, or a bad `Host`.
- `403` — bad `Origin`.
- `405` — a method other than `POST`.
- `413` — body over 256 bytes.
