# Helm and worlds GUI — design

Status: draft, awaiting operator review. Size: M.

## 1. What this is

Two operator surfaces, one visual language, and one new backend.

The Helm's v2 page (`GET /` on the API port) renders six data domains as
unstyled default HTML and has never been opened in a browser — `surface='home'`
has never been written to `ledger/engagement`, and the operator confirmed it
directly on 2026-09-23. Its Start control has been broken since it landed
(`api_home.py` posts `{mode}`; `api_seats.py` requires `{mode, workspace}`), and
nothing links to the page. There is no compatibility to preserve.

The worlds feed is the opposite: used daily from a phone, and structurally
honest about nothing. On 2026-09-19 production failed in three ways at once
while the UI reported health, because the generator indicator reads
`is-active` on the world target, which stays active while the supervisor sits
failed.

This spec redesigns the Helm page around the surface brief §2 goal 5 actually
asks for, resumes the 2026-09-19 worlds consumption round with its design
errata closed, and specifies the one backend neither has.

### Goals moved

Per brief §2 (`:96-97`), a wave names the goals it moves.

- **Goal 5** (surface area shrinks) — directly. This builds the card-with-a-
  default surface the goal is measured on, and the divergence measurement that
  makes it legible.
- **Goal 4** (a world runs as an OS function) — partially. The worlds gain an
  operator surface that does not lie about whether the loop is running.

## 2. Decisions

**D1 — Helm is built properly now, and kept portable.** The tvix-aios spec
classes Helm as scaffolding "retired in the step whose daemon module makes it
redundant, never before". That is a retirement precondition, not an investment
freeze, and goal 5 is measured on the Helm meanwhile. Both hold if every
backend call sits behind one client module, so the move to `/run/aiosd.sock` is
a single seam. *Rejected:* treating Helm as scaffolding and building the
minimum — goal 5 has no other carrier.

**D2 — The decision queue is a deferred inbox, not a live handoff.** An ask is
written with a recommended default and work **proceeds under that default**;
the operator answers later and the answer corrects course. *Rejected:* parking
the session until answered — it relocates blocking rather than removing it, and
goal 5's second half is that chat questions per landed task fall.

**D3 — Ask text lives outside the evidence store.** `ledger/operator` forbids
the field names `question` and `answer` across every kind; adding text is "a
decision amending 18b, not a task" (`pkgs/evidence/SCHEMA.md:53`). A pending ask
is therefore a file in a spool directory, and only the measurement row reaches
the store. *Rejected:* amending 18b — the store's text-free property is
deliberate and worth more than the convenience.

**D4 — Two Helm ports stay this round.** The control port is the only Helm
surface with a stylesheet, the only one the operator uses, and the only one with
a LAN face. Retiring it in the same round that redesigns the API page would
delete the working dashboard and the remote path together. *Rejected:*
retiring it now; the precondition for a later round is the API page at parity
plus its own LAN site and host aliases.

**D5 — The visual language extends the collector's, it does not replace it.**
`pkgs/helm/collect.py` already defines system-ui type, both themes via
`prefers-color-scheme`, a card grid, and status carried on a left border with a
four-value semantic scale matching the collector's own verdicts. *Rejected:* a
clean slate — it would make the two ports read as different products.

**D6 — Hierarchy is carried by order and width, never by new colour.** The
decision band is full-width and first; everything else is the existing grid. The
colour scale stays semantic. *Rejected:* an accent colour for "needs you" — it
would put a fifth meaning into a four-value scale.

**D7 — Helm proxies the feed; it never crosses the user boundary.** Every worlds
unit is a systemd *user* unit and the API runs as a system service. The feed
already runs inside that user manager and already shells `systemctl --user`.
*Rejected:* `machinectl`/setuid — it buys a privilege path for no new
capability.

**D8 — Controls are named for what they do.** A deck request is what starts the
generator (`media/pkgs/comfy-worlds/feed.py`, the low-water arm), so the
affordance is "Make more renders", not "Refresh". *Rejected:* conventional
refresh copy — it would misdescribe the side effect.

**D9 — Worlds status never collapses two facts into one indicator.** World-up
and generation-running are separate rows, and their disagreement is stated in
words. *Rejected:* a single dot — that is the 2026-09-19 failure exactly.

**D10 — The API page suppresses profile state.** Profile switching is
abandoned; rendering `active_profile` or the control document would re-entrench
a retired mechanism. *Rejected:* rendering it because the route exists.

## 3. The decision queue

### Store

One file per pending ask under a configured spool directory, id-keyed, the same
idiom as the seat spool:

```
<asks_dir>/<ask_id>.json
{ "ask_id": "<16 hex>", "created": "<iso8601>",
  "header": "<= 12 chars", "question": "<text>",
  "options": [ { "label": "<text>", "description": "<text>" } ],
  "recommended_index": <int>, "proceeded_with": <int>,
  "key": "<task key>",            // optional
  "context": "<what was done under the default>",
  "cost": "free" | "<what changing it costs>" }
```

`cost` is load-bearing, not decoration: an ask that has already had work done on
it must say so where the operator decides, or the inbox silently misrepresents
what a change costs.

### Routes

- **`GET /v1/asks`** → `200 {"asks": [ ... ]}`, pending only, sorted oldest
  first. Absent or unreadable spool directory answers `{"asks": []}`, matching
  the seats route's degradation.
- **`POST /v1/asks/<ask_id>`** → body `{"chosen_index": <int>}` → `204`, empty
  body. Writes the `phase: "answer"` row to `ledger/operator` with
  `surface: "helm"` — the value the enum already reserves — then archives the
  ask file.

`<ask_id>` matches the seat route's id pattern and is validated before any path
is built. Failure arms: `400 {"error": "body"}` for a key set other than
`{"chosen_index"}` or a non-integer; `400 {"error": "id"}`; `404 {"error": "no
such ask"}`; `409 {"error": "already answered"}` when the file is gone.

### What it measures

`chosen_index` against `recommended_index` is already in the schema, as is
`took_recommended`. Because work proceeds under the default rather than
waiting, a confirmation means no rework occurred and a divergence means the
recommendation was wrong and was caught. The **divergence rate** is a better
instrument for goal 5 than a question count, and it costs no new field.

## 4. Helm home

Sections in order. Each names its route and its empty state; nothing is silent.

1. **Decisions** — `GET /v1/asks`. Full-width cards: header chip, age, question,
   one button per option with the in-effect option marked, a first-person
   past-tense effect line naming what was done and what changing it costs, and
   the context line. Empty is the resting state and reads as such, not as an
   error.
2. **Sessions** — `GET /v1/seats`. Table with `id`, `state`, `port`,
   `exit_code`, and attach/stop. `exit_code` is rendered with its meaning where
   one is known; the current page drops it entirely. Start is an action **on a
   flake card**, never free-standing — see §4.1.
3. **Health** — `GET /v1/status`. One tile per collector tile, rendering
   `summary`, `since` and, behind a disclosure, `detail`. The current page
   renders `name: status` and discards the rest. Staleness comes from
   `generated_at` against `interval_s`.
4. **Patches** — `GET /v1/patches`. Carried rows first, with `running_generation`
   and `head`. This route never returns 500; a GUI must check for an `error` key
   inside a 200.
5. **Flakes** — `GET /v1/home`. Empty today because `services.helm.home` is
   enabled nowhere, so the empty state names that cause and its fix rather than
   printing "No flakes declared".
6. **Links** — from config.

`GET /v1/control` and `GET /v1/tasks` are **not** rendered: the first by D10,
the second because a task graph is a different product from a decision surface
and this round does not build it. Both stay available.

### 4.1 Start, and the workspace

The seat API takes `workspace` per request while `dsh_home`, `model` and
`effort` come from config, because the other three are machine-wide and the
workspace is the flake being worked on. The 2026-09-04 design already settled
this: the verb is "work here", where *here* is the card. Start is therefore a
control on a flake card, and its `workspace` is that flake's declared path.

**Enabling `services.helm.home` is a precondition for a working Start.** Until
the flakes list is non-empty there is no workspace to offer, which is why the
current control has never succeeded.

## 5. Worlds consumption

Resumes `docs/superpowers/specs/2026-09-19-world-feed-phone-ui-design.md`: the
three-tab shell (Feed / Saved / Worlds) rendered server-side as plain links so
the no-JavaScript path survives, a shared hardlinked library across worlds,
inline SVG glyphs with no icon font or external URL, 48 px targets, and
`env(safe-area-inset-*)`.

Two keys have landed since that spec was written and it must be re-read against
them: the deck's demand signal now returns immediately, and the author is told
its length window.

### Design errata closed

The 2026-09-19 plan draft scored 35/42 with 23 errata. Seventeen are plan
hygiene and bind the implementation plan, not this spec. Six bind a spec, and
two more come from the Opus judge's reasons without reaching the errata table.
Each is answered here as a rule:

- **Saving a deleted render.** Dislike unlinks the file but leaves the index row,
  so saving afterwards raises an uncaught `FileNotFoundError`. **Rule:** dislike
  removes the index row, so the name is genuinely gone and the save route's
  existing membership check is sufficient. *Rejected:* catching ENOENT in the
  link path — it leaves the index lying about what exists.
- **Saving with no folder selected.** The rule "every folder value passes the
  charset check" is vacuously true at zero values. **Rule:** zero folders is
  `400`, stated and tested. Vacuous rules are a named defect class here.
- **Partial state on a multi-folder save.** **Rule:** two passes — resolve every
  folder first, any failure aborts with nothing linked, then link and insert.
- **An unwritable library.** The window between the operator creating the path
  and the switch that widens the feed unit's sandbox is real. **Rule:** the
  folder routes answer a `500` naming the cause, with a stderr line.
- **Where glyphs are authored.** **Rule:** inline SVG in the server-rendered
  markup, per the parent spec. A departure is a numbered decision, not a silent
  choice.
- **CLI shape.** The parent spec pinned a positional argument where flags
  matched the existing subcommands. **Rule:** this spec states contracts, not
  argument shapes, unless the shape is load-bearing.
- **A route widening what the LAN face serves.** Serving saved files off a
  user-writable directory is a different exposure from serving the output
  directory. **Rule:** framed as a reach decision, with the path rule stated as
  a rule and the existing basename guard as its precedent.
- **Invariants cited where they bind.** Named at the specific constraint, not
  gestured at in a preamble.

### Honesty rules

- World-up and generation-running are separate facts with separate indicators,
  and their disagreement is stated in words (D9).
- The demand affordance is named for its side effect (D8).
- A render with no recorded workflow shows regenerate and edit disabled with
  the reason, rather than answering `409` after a tap.

## 6. Constraints, cited where they bind

- **Both servers bind loopback**, asserted at eval and at process start
  (`nixosModules/helm.nix`, `media/nixosModules/comfyui-worlds.nix`). Neither
  new route changes a bind.
- **No CORS and no `OPTIONS` handler** exist on the API. The page is served by
  the server that answers its calls; a page served from any other origin is
  refused. This is why the design is server-rendered with progressive
  enhancement rather than a client application.
- **CSP** is `default-src 'none'; script-src 'sha256-…'; style-src
  'unsafe-inline'; connect-src 'self'; form-action 'none'`. No `<form>` element,
  no external font, image or script, one inline script block whose hash is
  computed at import. POST bodies stay under 256 bytes — `{"chosen_index": N}`
  is well inside it.
- **Toolchain** is stdlib HTML, CSS and JavaScript. No framework, no bundler, no
  node toolchain — the parent spec's non-goal, and a new language would drag its
  formatter and linter into the same task.
- **Brief §3 invariant 8** binds the worlds' engagement telemetry: a world's
  learning signal is user data, and the declaration is Nix with a default of
  none. **`dwell` stays unwired in this round.** A probe for declared data
  classes returned nothing, so whether wiring the existing `dwell` route is
  permitted is unresolved; the affordance is designed, the wiring is a separate
  task with its own gate.
- **Brief §3 invariant 7** binds this file: specs classify `publish`, so it
  carries no host paths, operator names or LAN addresses.

## 7. Out of scope

- The worlds **production-control surface** — the manifest brief, LoRA cards,
  checkpoint rotation, batch history, prune. Named as the next round; this round
  leaves the Worlds tab as its attachment point rather than a switch.
- A **task-graph board** on `/v1/tasks`.
- A **spend tile** — blocked on a budget line and its period, which come from
  the operator before the tile is planned.
- **Helm faces for `derived/gates` and `ledger/openrouter-usage`.**
- **Retiring the control port** (D4), and **a LAN site for the API port**.

## 8. Open questions

1. Whether the worlds' engagement telemetry is a declared data class. Blocks
   `dwell` wiring only; everything else proceeds.
2. Whether the disagreement banner fires often enough to become wallpaper. Only
   operation will say; if it does, it needs a quieter resting form.
3. Whether the archive of answered asks earns a surface of its own, or stays a
   file nobody reads until something goes wrong.

## 9. Reference implementation

Two complete screens exist as stdlib HTML and CSS, built against the real
payload shapes and this spec's rules. They are reference artifacts for the
implementation plan, not landed code, and they live outside the repository.
