# Helm v1 — Final Product & UX Decisions

*Author: Kimi (product consolidator; UX/visual/copy authority under the
decision rules). This document is the last word on what Helm v1 looks like,
reads like, and feels like. It consumes — and does not amend — the
consolidated technical plan
(`docs/superpowers/plans/2026-09-03-helm-v1-switch-consolidated.md`); where a
decision here touches a technical surface it is marked **CONFLICT** or
**CROSS-DOMAIN** and routed to the owning role per the decision rules. Every
decision marked **(K)** is final within my domain.*

**Spec:** `docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md` (rev 2).
**Technical plan:** the consolidated plan named above.
**v0 baseline:** `nixosModules/helm.nix`, `pkgs/helm/collect.py` (the renderer
these decisions physically extend).

---

## 0. Decision frame

I am not redesigning Helm. Helm v0 is a shipped, reviewed, tested product with
a working visual language and a working trust model. Helm v1 adds **two verbs**
(Switch, Open) to a page that already had **nine nouns** (the status tiles).
The product discipline of this whole document is: *the verbs must look and
behave like they belong to the same instrument as the nouns* — same palette,
same tile grammar, same flat tone — because the operator's willingness to click
"change what my machine is" rests entirely on the page already having earned
their trust as a read-only dashboard.

Three technical facts from the consolidated plan shape everything below and are
accepted as fixed inputs, not re-opened:

- **D10**: the active profile is read from `/etc/helm/profile` **at serve
  time** by `helm-serve`; the nine v0 tiles are baked into
  `/var/lib/helm/index.html` by the collector every 300 s. The Profile section
  is *live*; the dashboard is *periodic*. This asymmetry is §3.1.
- **D8**: the 409 busy response is a fully-rendered page (already agreed and
  recorded in the plan's cross-role table).
- **D5**: the Firefox form-submit gate is proven from the real browser in
  acceptance, not assumed (my flag #2, carried into Task 6).

---

## 1. Product identity (final)

**Helm v1 is the helm, not a dashboard with buttons.** The one-sentence promise
— *"no code, no password, loopback-only"* — must be legible on the page, not
just true underneath it. The page now *does* something, and that something is
the most consequential act available without a reboot. Two product principles
follow, and they are **(K)** final:

1. **The verbs are primary; the tiles are their instrumentation.** Layout,
   visual weight, and reading order all subordinate the nine v0 tiles to the
   two new sections. This is not a cosmetic preference — it is the product
   telling the truth about what it is now *for*.
2. **The dashboard is the safety case for the switch.** The operator dares to
   click `gaming` without a password because the same page proved the
   environment healthy (backups green, drift green, basket doctor passing) ten
   seconds ago. This is already encoded in acceptance ("drift tile still
   green" after a switch) and is promoted here to a stated product principle,
   to be carried into the runbook (§7).

The mental model the page must teach, once and consistently — **(K)** final:

> **Now, not forever.** A click changes the *running* machine in seconds-to-a-
> minute; a reboot always lands back on `base`. Nothing here touches the boot
> menu; nothing here asks for a password, because the page can only ever ask
> for the few things it was built to allow.

This framing converts the `test`-only technical constraint into the product's
core virtue: the switch is *fearless because it is reversible-by-reboot*.

---

## 2. The two verbs and their flows (final)

### Flow A — Switch profile (the headline act)

The interaction vocabulary is deliberately minimal and is **(K)** final:
**the form IS the product.** Click → POST → block → full-page result. No
JavaScript, no spinner we control — the browser's own tab loading indicator is
the progress signal, and we do not apologize for it. For this operator, a plain
form that navigates is *more* trustworthy than a fake-async UI, because it is
honest about blocking and leaves an auditable request in the browser history.

- **Blocking POST, asymmetric timeouts (D8).** The request blocks up to 6 min
  worst case, realistically seconds-to-a-minute. Accepted as-is; no UX
  mitigation attempted (none is possible without JS, and adding JS to gain a
  spinner would trade the page's entire zero-script security posture for a
  cosmetic — a bad trade, and not mine to make anyway).
- **Success.** The response page renders the *whole* Helm page with one
  addition: a banner directly under the header. Banner copy: **"Now running:
  gaming"** (§5). The Profile section below it already shows the new active
  profile, because it re-read the marker at serve time — the banner and the
  section can never disagree.
- **Failure.** Same page, fail-colored banner: **"Switch to gaming did not
  finish — the machine is still on base."** plus a copyable command string
  `journalctl -u helm-switch@gaming.service` (rendered as inline code text,
  *not* a link — the page is not a terminal; the operator has one).
- **Busy (409).** A second click during a running switch returns 409 rendered
  as a **full Helm page** with an amber banner: **"A switch is already in
  progress. Wait for it to finish, then reload."** **(K)** final, and already
  ratified cross-role in the plan's D8/table: *every non-2xx from an action
  route is a fully-rendered Helm page with a banner — never a bare status
  line.* An operator staring at a white page reading "409" will conclude Helm
  broke; that is a product failure, not an HTTP detail.

### Flow B — Open a workspace

- **Spawn-and-forget.** Unlike Switch, Open returns *immediately* (D3's
  `systemd-run --user` detach). Response page banner: **"Opening gaming — a
  terminal window should appear on your desktop."** The GNOME Console window
  appears a beat later, already in the flake's dev shell running `claude`.
- **The basket ceremony stays human (non-goal honored, endorsed as design).**
  If a workspace is basket-gated, the terminal opens and prints the exact
  `sudo basket mount …` command and waits for Enter. The page never mounts
  baskets — the YubiKey touch is a physical security ceremony and it happens
  *in the terminal, in front of the operator*, not behind a web button. The
  page's only job is to have **told the operator in advance**: the workspace
  row shows `basket: not mounted` (amber) *before* they click, so the prompt
  is expected, not surprising. **(K)** final, and the runbook copy for it is
  in §5/§7.
- **Failure (curl-only path).** Unknown workspace → 403 page, plain reason.
  Not reachable from the page's own buttons; no UI affordance needed.

### Flow C — Look before you leap (the passive flow)

The flow nobody clicks but everyone uses: *"If I switch now, will anything I
care about break?"* Answered at a glance, in priority order — **(K)** this
priority order is final and drives layout:

1. **Profile** (new) — current profile, last switch result, when.
2. **Drift** — am I on the commit I think I am? (the operator's trust anchor;
   acceptance explicitly re-checks it post-switch).
3. **Backups** — is the safety net fresh?
4. **Host / GPU** — is the machine under duress right now?
5. Everything else (timers, basket doctor, broker, flake check) in v0's
   existing relative order.

### Flow D — The reboot expectation (off-page, designed-for)

Operator reboots while on `gaming` → machine boots `base` → opens Helm → sees
**base — active**. This must read as *the system keeping a promise*, not
losing state. **(K)** final: the Profile section shows `base` neutrally — no
"recovered", no warning, no amber. The "Now, not forever" note (§3.2) is what
makes this moment feel correct. Flagged explicitly because this is the flow
where a wrong mental model would surface as a bug report, and the fix is copy,
not code.

---

## 3. Page structure and visual direction (final)

### 3.1 The one real design tension — and its resolution

The consolidated plan (D10) creates a genuine two-clock page, and I am
deciding it deliberately rather than letting it be discovered in review:

- The **Profile** and **Workspaces** sections are injected by `helm-serve`
  **at serve time** — they read the marker and the journal live, so they are
  always current (subject only to the 60 s `<meta refresh>`).
- The **nine v0 tiles** are baked into `index.html` by the collector every
  **300 s** — they can be up to five minutes stale, plus the refresh interval.

**(K) resolution — embrace the asymmetry, don't hide it, and don't "fix" it.**
The two clocks measure different things and that is correct: the Profile
section must be *instantly* truthful because it is the confirmation surface
for the act the operator just took ("did my switch land?"); the dashboard tiles
are *periodic health instrumentation* and their staleness is already a designed
property of v0 (the header literally prints `generated … · next …`). Forcing
the tiles live would require per-request collection (expensive, slow, and it
would make the *switch confirmation* wait on a `restic snapshots` call) — a
clearly worse product. The resolution is therefore:

1. **The banner is the point of truth for the action just taken.** It is
   rendered serve-time from the post-switch marker. The operator never has to
   wait for the 300 s collector to *believe* a switch landed — the POST
   response itself is the confirmation, and the app grid is the out-of-band
   physical proof. (Acceptance: "the operator should not need to reload to
   believe it.")
2. **No visual lie about tile freshness.** The v0 header's
   `generated … · next …` line stays exactly as-is; it already discloses the
   tiles' cadence. I am adding nothing that implies the tiles are live.
3. **One honest affordance:** the Profile section carries its own tiny
   serve-time timestamp (§3.3), visually subordinate to the header, so the
   operator can see *"this section is as of right now"* without it competing
   with the page header. This is the only concession to the two-clock reality
   and it costs one short line of muted text.

### 3.2 Where the new sections live

**(K)** final — reading order = verb order = the goal statement's order
(switch first, then open):

```
┌────────────────────────────────────────────────────┐
│ Helm · core · generated 21:44 · next 21:49         │  ← v0 header, UNCHANGED
│ [ banner — only on action-response pages ]         │  ← success/fail/busy
├────────────────────────────────────────────────────┤
│ PROFILE                              (live · 21:44)│  ← serve-time, first
│  ● base — active                                   │
│  ┌───────┐ ┌───────┐ ┌───────┐                     │
│  │ base  │ │ gaming│ │ media │  one form/button    │
│  └───────┘ └───────┘ └───────┘                     │
│  Last switch: base → gaming · ok · 21:03           │
│  Switches apply to the running machine only.       │
│  A restart always returns to base.                 │
├────────────────────────────────────────────────────┤
│ WORKSPACES                           (live · 21:44)│  ← serve-time, second
│  nixos-agent-env  ~/nixos-agent-env        [Open]  │
│    abc1234 · clean · memory ✓                      │
│  gaming           ~/flakes/gaming          [Open]  │
│    def5678 · dirty · memory ✓ · basket: not mounted│  ← amber state word
│  strategy         ~/strategy               [Open]  │
│    not a git repo                                  │
├────────────────────────────────────────────────────┤
│ (v0 tile grid — backups, timers, basket doctor,    │  ← collector-time,
│  broker, GPU, host, drift, flake check)            │    UNCHANGED
└────────────────────────────────────────────────────┘
```

The injection point is the consolidated plan's `render_control(status_html,
cfg, token)`, inserting the two sections **before `</main>`**. **(K)**
decision: the two sections render *above* the v0 grid (visually first), even
though the injection point is at the end of `<main>` — the renderer orders the
sections explicitly inside its own injected markup; it does not depend on
source position for visual order. (If the implementer finds the cleanest
injection is literally before `</main>`, the CSS grid order property or a
wrapper reorders them — this is an implementation detail, not a design
compromise. The *visual* outcome — Profile first, Workspaces second, then the
grid — is the decision and is not negotiable.)

### 3.3 Visual language — strict inheritance

**(K)** final: the v1 sections **inherit v0's visual system wholesale**. No
new colors, no new type scale, no new component vocabulary beyond the minimum
the verbs require.

- **Palette.** Reuse v0's `_STATUS_COLOR` exactly: ok `#2e7d32`, warn
  `#ed6c02`, fail `#c62828`, unknown `#616161`, light `#fafafa/#111`, dark
  `#121212/#eee`. **Do not invent a fifth color.** The Profile status dot and
  the banner use only these four semantics.
- **Tile grammar.** Profile and Workspaces render as `section.tile` blocks in
  the same card style (left status border, same radius, same shadow, same
  `prefers-color-scheme` dark variants) so they are visually *of* the page.
  Their status border reflects their own state: Profile = last-switch status
  (ok/warn/fail); Workspaces = worst workspace state (amber if any basket
  unmounted, else ok).
- **Two visual tiers of action (the only new vocabulary).** This is the single
  deliberate departure and it is **(K)** final:
  - **Profile buttons** are the only large, *filled*, saturated-color
    interactive elements on the page — switching reconfigures the machine.
  - **Workspace Open buttons** are secondary: outline style, not filled —
    opening a window is a lighter act.
  Two weight classes of action get two weight classes of button, so the page's
  visual hierarchy teaches the trust hierarchy.
- **Typography.** Profile/workspace names render **verbatim lowercase**
  (`base`, `gaming`, `media`) — no title-casing. The operator thinks in these
  exact strings because they match `specialisation.<name>` and the journal
  lines. The same word on the page, in the journal, and in the config is a
  feature.
- **Constraints honored (restated as design, not obligation):** inline
  `<style>` only; `prefers-color-scheme`; no `<script`, no `src=`, no
  `href="http`; `<meta refresh="60">` retained. The 60 s refresh on an
  action-response page is *acceptable*: the result was already seen, and the
  journal + the Profile section's "last switch" line preserve the record.

### 3.4 The active-profile button — resolved

The open question from my earlier pass is settled by the consolidated plan's
cross-role table (DeepSeek agreed; the VM `base↔alt` round-trip is unaffected):
**(K) final — render-disable + complete backend allowlist.**

- The *active* profile's button is rendered **disabled**, with a `● active`
  marker, because POSTing a switch to the profile you are already on is a
  no-op the UI should *prevent*, not permit. This is a pure render-layer
  decision.
- The backend allowlist stays **complete** — a self-switch POST remains
  accepted (it is an idempotent re-`test`). Render-time disabling never
  narrows the security surface, so the VM round-trip and the bats/pytest gates
  are untouched. This is the resolution already recorded; I am confirming it
  as the final product call, not re-opening it.

---

## 4. The banner component (final)

The banner is the *only* structural addition to the page chrome, and it appears
**only** on action-response pages (the result of a Switch or Open POST) —
never on the passive dashboard. **(K)** final spec:

- **Position:** directly under the `<header>`, above the Profile section.
  One place the eyes go; everything below it is familiar context (the drift
  tile sitting green right under a success banner *is* the reassurance).
- **Color = outcome**, using only the v0 palette: green = success, red =
  failure, amber = busy (409). No fourth state.
- **Form:** a full-width block, left status border matching the tile grammar,
  flat statement text, no icon beyond the colored border. It is a tile turned
  sideways into a full-width stripe — same component family.
- **Dismissal:** none needed. It lives only on the response page; the next
  60 s refresh returns to the plain dashboard, and the Profile section's
  "last switch" line is the durable record. No close button (that would need
  JS or a round-trip; not worth it).

---

## 5. Copy deck (final — every word is mine)

Tone rule **(K)**: flat, exact, present tense. No exclamation marks, no
"Congratulations", no scare language. The page speaks like the runbook.

| Where | Copy (verbatim) |
|---|---|
| Profile heading | `Profile` |
| Active indicator | `● base — active` |
| Serve-time stamp (Profile/Workspaces, muted) | `live · 21:44` |
| Note under profiles | `Switches apply to the running machine only. A restart always returns to base.` |
| Last-switch, ok | `Last switch: base → gaming · ok · 21:03` |
| Last-switch, failed | `Last switch: base → gaming · failed — see journal` |
| Last-switch, in progress | `Switching to gaming… (started 21:44)` |
| Last-switch, none yet | `No switches since boot.` |
| Success banner | `Now running: gaming` |
| Failure banner | `Switch to gaming did not finish — the machine is still on base. Details: journalctl -u helm-switch@gaming.service` |
| Busy banner (409) | `A switch is already in progress. Wait for it to finish, then reload.` |
| Workspaces heading | `Workspaces` |
| Open banner | `Opening gaming — a terminal window should appear on your desktop.` |
| Basket state, mounted | `basket: mounted` |
| Basket state, unmounted (amber) | `basket: not mounted` |
| Workspace meta, git | `abc1234 · clean · memory ✓` / `def5678 · dirty · memory ✓` |
| Workspace meta, non-git | `not a git repo` |
| Terminal basket prompt (launcher, prefix added) | `This workspace needs its basket. Run:` / `<exact sudo basket mount … line>` / `…then press Enter.` |
| Runbook, "what it never does" | three bullets: *never changes the boot menu*; *never mounts baskets*; *never restarts the agent, broker, basket or backup services* — each naming the mechanism that guarantees it (the `test` action; the launcher design; the agent-unit assertion). |
| Runbook, the two-clock note | "The Profile and Workspaces sections are read live when the page is served. The health tiles are collected every five minutes; the header shows when. After a switch, believe the banner and the Profile section immediately; the tiles catch up on the next collection." |
| Runbook, page-vs-journal trust | "If the page and `journalctl` ever disagree about a switch, believe the journal — and file it, because that is a bug." |

---

## 6. Product coherence with the rest of the system (final)

- **One story, two tellers.** Every action emits a journal line; every switch
  emits `helm-switch: begin/end`. The Profile section's "last switch" line is
  rendered *from those same journal lines* (via `status.json`), so the page
  and `journalctl` can never disagree. This is the same trust pattern as the
  drift tile (page vs. `nixos-version`). **(K)** I want this stated as a
  principle in the runbook (copy above): *the dashboard is the safety case for
  the switch, and the journal is the court of appeal.*
- **Trust inheritance is the whole reason this is shippable.** v1's buttons sit
  atop v0's instrumentation. Restated as the product principle of §1.
- **What v1 deliberately does not do** (protecting the non-goals in product
  language, **(K)**): no LAN, no auth (Phase 10's job — the page stays a
  single-seat instrument); no basket mounting (the YubiKey ceremony stays
  human); no boot-default change (ever); no Claude *desktop* deep-link (the
  terminal *is* the interface — and it is the better one for a workspace:
  shell, claude, and that folder's memory in one window).
- **Naming.** "The switch" is good internal shorthand; the *page* never says
  it. Product naming stays boring and literal: **Helm**, **Profile**,
  **Workspaces**. **(K)** final.
- **Firefox reality check (carried, not re-litigated).** The whole no-JS form
  flow depends on the hardened Firefox sending `Sec-Fetch-Site: same-origin`
  or `Origin` on a same-origin loopback form POST. This is my #1 product risk
  because the failure mode is *silent and total* (every button 403s) and only
  shows in the real browser. It is already owned by acceptance (D5: Task 6
  must do a **real Firefox form submit**, not only curl) and by DeepSeek's
  fallback re-derivation if observation contradicts the spec. Rule 1 governs:
  if Firefox's actual behavior contradicts the spec's assumption, the spec
  loses, and the copy/banner for that state gets written then — I do not
  pre-write copy for a failure we have not observed.

---

## 7. What the operator should *feel* (the actual deliverable)

One paragraph, because this is what is being built. The operator opens the page
mid-afternoon, glances: backups green, drift green, profile `base`. Clicks
**gaming**. The tab spins for twenty seconds; the page returns with a green
banner — *Now running: gaming* — and the drift tile still green directly under
it. Steam is in the app grid. They game. Later they click **base**, get the
same green banner in reverse, click **Open** on `strategy`, and a Console
window pops up already running claude in the right folder with the right
memory. At no point did they type a command, a password, or wonder "did that
work?" — the page answered before they asked. And when they reboot tomorrow
and the machine comes up on `base`, the page showing `base — active` feels
like the system keeping a promise, not losing state. That is the product.

---

## 8. Flags to other roles (cross-domain, per rule 5)

These are the only points where a product decision here touches a surface I do
not own. None re-open the technical plan; two ask for concurrence, one is a
standing risk already owned elsewhere.

1. **→ GLM (workflow/implementation) — CONCURRENCE REQUESTED on render order.**
   §3.2 requires Profile and Workspaces to render *visually first* even though
   the injection seam is "before `</main>`". If the implementer finds that a
   literal before-`</main>` injection plus CSS `order` (or a marked injection
   point) is the clean path, that satisfies the design; the *visual outcome*
   is fixed, the mechanism is theirs. Please confirm the renderer can place
   the two sections above the v0 grid without restructuring v0's
   `render_html` — I have kept the requirement at the level of "visually
   first" precisely to leave the mechanism open.

2. **→ GLM + DeepSeek — CONCURRENCE on the two-clock disclosure.** §3.1 adds a
   serve-time `live · <time>` stamp to the two new sections and keeps v0's
   header unchanged. This is copy+layout (mine), but it asserts a fact about
   serve-time vs. collector-time rendering that the implementation must make
   true (Profile/Workspaces re-read marker+journal per request; tiles come
   from the baked file). Confirming the implementation actually re-reads per
   request (D10 already says it does) closes this.

3. **→ DeepSeek (technical) — STANDING RISK, already owned.** §6 Firefox
   header behavior. No new ask; restating that it is the #1 first-run product
   risk and is gated by the real-browser acceptance step (D5).

**No conflicts with the technical plan.** Every decision here is satisfiable
within the consolidated plan as written; the two concurrence items are
implementation-placement confirmations, not change requests. Rule 5 is
satisfied for the one cross-domain call that needed it (render-disable +
complete allowlist) — it is already recorded as agreed by DeepSeek in the
consolidated plan's cross-role table, and I confirm it here as the final
product decision.

---

## 9. Decisions register (one line each, all final in my domain)

- **(K1)** Helm v1 is a control surface with a dashboard attached; verbs are
  primary, tiles are instrumentation.
- **(K2)** The dashboard is the safety case for the switch — stated product
  principle, carried to the runbook.
- **(K3)** Mental model taught once: *Now, not forever.* Switch is runtime-only;
  reboot returns to base.
- **(K4)** The form is the product: click → POST → block → full-page result;
  no JavaScript, no apology.
- **(K5)** Every non-2xx from an action route is a fully-rendered Helm page
  with a banner — never a bare status line. (Ratifies D8.)
- **(K6)** Two-clock page embraced, not hidden: banner + Profile are serve-time
  truth; tiles stay collector-time; one muted `live · <time>` stamp discloses
  it.
- **(K7)** Visual order: Profile, Workspaces, then the v0 grid — reading order
  = verb order.
- **(K8)** Two visual tiers of action: filled buttons for Switch, outline for
  Open.
- **(K9)** Strict inheritance of v0 palette/tile grammar; no fifth color.
- **(K10)** Profile/workspace names verbatim lowercase; same word on page,
  journal, and config.
- **(K11)** Active-profile button render-disabled with `● active`; backend
  allowlist complete. (Confirms the cross-role resolution.)
- **(K12)** Banner appears only on action-response pages, directly under the
  header, color = outcome, no dismiss control.
- **(K13)** Basket ceremony stays in the terminal, human-touched; the page only
  forewarns (`basket: not mounted`, amber).
- **(K14)** Reboot-to-base is shown neutrally as `base — active` — a kept
  promise, not an error.
- **(K15)** Copy deck §5 verbatim; flat, present tense, no exclamation marks.
- **(K16)** Naming stays literal: Helm, Profile, Workspaces — the page never
  says "the switch".
