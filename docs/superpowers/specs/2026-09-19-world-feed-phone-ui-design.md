# The world feed becomes a phone app

Design, 2026-09-19. Subsystem: the ComfyUI generation worlds
(`media/pkgs/comfy-worlds`, `media/nixosModules/comfyui-worlds.nix`).
Successor to `2026-09-18-world-feed-ui-design.md`, whose GN series landed the
deck, the verb rail, the world switch and the LAN face. This spec covers the
four changes the operator asked for on 2026-09-19 once the feed was live on a
phone.

## 1. Why

The feed works. Using it exposed four gaps, three of them measured in this
tree before this spec was written:

- **Dislike scrolls backwards.** `app.js`'s `dislikeCard` splices the card
  out, after which `cards[idx]` *is* the next photo — then decrements
  `current` and scrolls there. Disliking B in `[A, B, C]` lands on A. The
  hard delete itself is correct and stays (`feed.py` `_dislike`: record the
  verdict in `dislikes`, then `target.unlink(missing_ok=True)`).
- **Regenerate is fire-and-forget.** `regenerateCard` POSTs and returns. No
  placeholder, no scroll, no progress. The *edit* sheet does insert a
  placeholder and poll at 5 s, but never scrolls to it.
- **Nothing measures how long a regenerate takes.** The `jobs` table carries
  `created` and `updated` only. The operator wants to know what it costs to
  interrupt the production run, load the models and render one photo.
- **There is no way to keep a photo.** No folder, album or collection exists
  anywhere in the package. Like is a signal, not a filing cabinet.

And the surface, while phone-*shaped* (a 480 px column, a snap deck,
full-bleed images, a right-edge rail), does not feel like an app: text labels
in round buttons, no safe-area insets, no press states, sheets that appear
rather than slide.

## 2. Decisions taken before design

Four questions were put to the operator on 2026-09-19. Their answers are
load-bearing; the plan does not reopen them.

| # | Question | Answer |
|---|----------|--------|
| 1 | What is a folder, physically? | A shared library at `<root>/saved/<folder>/`, hardlinked, one library across every world. |
| 2 | Where does the regenerate ETA come from? | Measured history — phase timestamps on the job row, median of recent jobs. |
| 3 | Where does the pending card go on regenerate? | Inserted below the current card, and the deck snaps to it. |
| 4 | How far does "look like phone UI" go? | Full app shell: a persistent bottom tab bar, Feed / Saved / Worlds. |

A fifth was put and left unanswered; §8 records it with the default this
spec applies.

**A limitation stated before it is designed around.** Answer 2 rules out a
live-progress client, and without one "load the models" cannot be separated
from "render": both happen inside a single ComfyUI execution that reports
nothing back to a stdlib poller. Three spans *are* measurable and this spec
names them for what they are, never as a load/render split:

- `enqueued → submitted` — the feed's own overhead.
- `submitted → started` — ComfyUI finishing whatever the production run had
  in flight. This is the "stop the production run" cost and is expected to
  dominate.
- `started → done` — model load *plus* sampling, fused.

The total ETA is unaffected by the fusion; only the breakdown is coarser.

## 3. Goals and non-goals

Goals. Dislike advances forward. Regenerate shows a countdown against
measured history and puts you on the photo being made. A save verb files a
render into any number of folders from a sheet that works with a thumb. The
whole surface reads as an app.

Programme goal, recorded here and built by a later round: **the controls that
decide what gets made need a surface too.** This spec covers consumption —
looking at renders and judging them. Production is still raw config, and on
2026-09-19 it failed in all three of its available ways at once while the UI
reported health:

- The brief — the single most load-bearing string in the pipeline, the whole
  system prompt to the authoring model — ships as the literal placeholder
  `REPLACE ME` in an untracked `lab/manifest.toml`, editable only by hand on
  the host. The nsfw world ran 6 155 renders under it.
- Nothing validates that file on write. A bare line typed above `brief`
  broke the TOML, and `_load_author_table`'s exit 2 surfaced nowhere.
- The generator dot reads `is-active comfy-world-<w>.target`, which stayed
  `active` for hours while `comfy-run-<w>.service` sat `failed`. The dot
  reports the GPU's target, never the authoring loop — so the one indicator
  in the interface asserted health that did not exist.

The fix is a Worlds tab that is more than a switch: the brief editable in
place behind the three checks that would each have caught the above (TOML
safe, non-empty, no banned token inside the brief's own text), and a dot that
reads the authoring loop. It is named here so the goal is on the record and
so §7's tab bar is built with a real destination in mind. **No task in this
round builds it** — the scope below is unchanged.

Non-goals. No framework, no bundler, no node toolchain — the stdlib-only,
zero-outbound rule of the parent spec holds unchanged. No live ComfyUI
progress client. No multi-user model. No change to `author.py`, `mutate.py`
or `run.py`. No move, rename, or unsave-from-folder verb in this round.

## 4. Dislike advances

`app.js` `dislikeCard`, after the splice: leave `current` where it is,
clamp it to `cards.length - 1` when the deleted card was the tail, and call
`afterSettle()` after the scroll. The third part is not cosmetic — a
programmatic scroll to an index that has not changed fires no settle, so
today the newly-shown card is never reported to `POST /seen` and never counts
as consumed. The deck's demand signal is that count.

Server side is unchanged. `_dislike` already records before it deletes so the
verdict survives a stuck file, and already tolerates a missing file.

Test (red first): a deck fixture `[A, B, C]`; dislike B settles on C; dislike
the tail settles on the new tail; the `seen` report names the card actually
shown.

## 5. Regenerate: timing, telemetry, ETA

### 5.1 Phases on the job row

`jobs` gains four nullable `REAL` columns — `t_enqueued`, `t_submitted`,
`t_started`, `t_done` — stamped by `queue.enqueue`, `queue.submit` and
`queue.poll`. `t_started` is taken the first poll at which ComfyUI reports
the prompt is no longer pending.

The migration is additive and idempotent: `ensure_schema` reads
`PRAGMA table_info(jobs)` and issues `ALTER TABLE jobs ADD COLUMN` for each
missing column. Existing rows read `NULL` and are excluded from every median
rather than counted as zero.

### 5.2 The ETA route

`GET /w/<world>/eta` → `{"median_total": s, "median_queue_wait": s,
"median_execute": s, "samples": n}`, computed over the last 20 `done` jobs of
kind `regenerate` or `edit` for that world that carry a complete set of
stamps. Below three samples every median is `null` and `samples` reports the
true count — the client must be able to tell "no history" from "fast".

JSON always, errors included, matching the deck route's contract.

### 5.3 The readout

`comfy-feed timings <world>` prints the per-phase table — count, median, p90
and max for each span — so the production-run stall can be read without a
browser. A subcommand beside `index --rebuild` and `queue --run-once`, not a
new binary.

### 5.4 Telemetry out

The existing engagement flush gains three bare counters: `regen_count`,
`regen_total_s`, `regen_queue_wait_s`. Counters only — no name, no prompt, no
seed. The zero-outbound rule and the "bare counters, never content" rule of
the parent spec both hold.

### 5.5 The client

Tapping regenerate inserts a rendering card directly below the current one
and snaps to it; the original stays one swipe up until the operator decides.
The edit sheet routes through the same code path and gains the snap it never
had, so both verbs behave identically.

The card shows a timer:

- **With history** (`samples >= 3`): counts **down** from `median_total`.
  Past zero it reads `any moment now` — never a negative number.
- **Without history**: counts **up** as elapsed, labelled `estimating`. No
  invented number is ever displayed.

The timer ticks locally at 1 s from the client clock. The job poll is a
separate, slower loop at 2 s (down from 5 s) whose only job is to correct
state: `done` swaps the placeholder for the render in place — not a whole
`fetchDeck(true)`, which today throws the deck away and loses the reader's
position — and `failed` marks the card failed and leaves it.

The ETA is fetched once per pending card, not per tick.

## 6. Save and folders

### 6.1 On disk

`<root>/saved/<folder>/<name>.png`, hardlinked from
`<root>/worlds/<world>/output/<name>`. One library across every world: a
photo saved from `sfw` and one from `nsfw` sit in the same folder if the
operator files them there.

Hardlink, not copy: no disk cost, and the saved copy survives both a pruned
output directory and a later dislike of the original, because the delete
unlinks one name and the data lives while another name holds it. `os.link`
raising `EXDEV` falls back to `shutil.copy2` — `saved/` and `worlds/` share a
root and so in practice a device, but the fallback exists rather than
crashing the route if they ever do not.

### 6.2 Schema

A new top-level `<root>/saved.sqlite` — not per-world, because the library
crosses worlds:

```
folders(name TEXT PRIMARY KEY, created_at REAL)
saves(folder TEXT, name TEXT, world TEXT, saved_at REAL,
      PRIMARY KEY(folder, name))
```

The directory is the artifact; the table is the index that makes membership
cheap to read for the sheet's checkboxes. A folder directory present on disk
with no row is adopted on open, so the operator can make a folder with
`mkdir` and the app agrees.

### 6.3 Routes

- `GET /saved` and `GET /worlds` — the two new shell pages the tab bar
  links to, HTML like `/w/<world>/`.
- `GET /folders` → `{"folders": [{"name", "count"}], ...}`, the JSON the
  sheet and the Saved page both read.
- `POST /folders` with `name` → creates the directory and the row.
  Idempotent: an existing folder is `{"ok": true, "created": false}`.
- `POST /w/<world>/save` with repeated `folder` values and one `name` →
  links the render into each named folder, `{"ok": true, "folders": [...]}`.
  Idempotent per folder.
- `GET /w/<world>/folders?name=<render>` → the folders that render is already
  in, so the sheet opens with the right boxes ticked.

### 6.4 The name is the security surface

A folder name becomes a filesystem path component. It is validated **before
any path is built**, against `^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$`: no
separator, no `..`, no leading dot, no empty string, no control character,
length capped. A name that fails is a 400 and nothing touches the disk. The
resolved path is then re-checked to sit under `<root>/saved/` with
`realpath -m` semantics, the belt-and-braces discipline the world names and
`/out/<name>` already get in `feed.py`.

This is the one genuinely dangerous route in the change and the plan marks it
so: its tasks carry negative tests for traversal, absolute paths, separators
and the empty name, and the section is a candidate for the parallel Opus gate
that security-critical keys take.

### 6.5 The sheet

A full-height bottom sheet. One row per folder: a large checkbox, the folder
name, the count. **Save** is pinned bottom-left, as asked. **+ New folder**
is a first-class row at the top of the list that opens an inline text field
and the on-screen keyboard — never `window.prompt`, which is exactly what
misbehaves or is suppressed on mobile browsers. Creating a folder ticks it
and leaves the sheet open so the save that follows is one tap.

Saving is additive: the card stays in the deck, the rail's save icon goes
filled, no auto-advance. Save is filing, not a verdict.

## 7. The app shell

The fixed top bar retires. A persistent bottom tab bar takes its place —
**Feed**, **Saved**, **Worlds** — sitting above the home indicator with
`env(safe-area-inset-bottom)` padding.

- **Feed** is today's deck, unchanged in mechanic.
- **Worlds** is where the switch and the generator dot move. The dot keeps
  refreshing off the deck fetch; no state route and no polling loop is added,
  per the parent spec.
- **Saved** opens the folder list.

The tab bar is rendered **server-side in the shell HTML as three plain
links** (`/w/<world>/`, `/saved`, `/worlds`). The no-JavaScript article path
therefore keeps working and keeps its navigation instead of becoming
unreachable when the top bar goes.

The rest of the pass: icon glyphs replace the rail's text labels (inline SVG
in the stylesheet's own markup — no icon font, no external URL); 48 px
minimum targets; `:active` press states; sheets that translate up rather than
appear; `env(safe-area-inset-*)` on every fixed edge. The deck's snap
mechanic, the full-bleed `object-fit: cover` and the 480 px column are
untouched.

## 8. The open operator question

**Does the Saved tab browse, or only list folders?** The ask was a save
*menu*, but a tab called Saved that opens a list of names and stops is a dead
end.

*Default applied by this spec, absent an answer:* a minimal browse view —
folder list → thumbnail grid → tap for full screen. Move, rename, delete and
unsave-from-folder are explicitly out of this round. The plan carries it as
its own task so it can be dropped without disturbing the others if the
operator says list-only.

## 9. Testing

Every claim above is testable without a GPU.

- **Dislike** — deck fixtures asserting forward advance, tail behaviour and
  the `seen` report. Red before the change: today's client fails the forward
  case by construction.
- **Phases** — `queue` unit tests that the four stamps are written in order
  and that `ensure_schema` is idempotent against both a fresh and a legacy
  `jobs` table.
- **ETA** — seeded job rows; assert the median, assert `samples < 3` yields
  `null`, assert incomplete rows are excluded rather than counted as zero.
- **Folders** — the validator's negative table (`../`, `/`, ``, `.`, a
  control character, 65 characters) is the first test written and must fail
  against an unvalidated route. Link, `EXDEV` fallback, idempotent save,
  adoption of a `mkdir`-made folder.
- **Shell** — the no-JS path still renders three working links; the shell
  asserts the tab bar is server-rendered, not script-built.

`lint` covers the JS and CSS through the existing prettier and oxlint gate;
the Python arm goes through `ruff` and the package's pytest suite
(`media/tests/comfy-worlds/`).

## 10. Files

Changed: `media/pkgs/comfy-worlds/app.js`, `app.css`, `feed.py`, `queue.py`,
`feed_index.py`; `media/tests/comfy-worlds/test_feed.py`. The worlds module
is untouched: there is no configured ETA fallback to add, because §5.5
displays elapsed time rather than an invented estimate when history is
short. New:
`media/pkgs/comfy-worlds/saved.py` — the folder library, its own module
rather than another 200 lines in a 1167-line `feed.py`.

Untouched: `author.py`, `mutate.py`, `run.py`, `nixosModules/lanAccess.nix`.
