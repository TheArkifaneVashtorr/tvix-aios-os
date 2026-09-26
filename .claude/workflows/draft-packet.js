// .claude/workflows/draft-packet.js — a planning drafter: gather a five-reader packet, then draft one plan from it, pinned.
export const meta = {
  name: 'draft-packet',
  description: 'Planning agent: draft a typed plan from a spec',
  whenToUse:
    'A spec is approved and needs a draft',
  phases: [
    {
      title: 'Packet',
      detail:
        'five Sonnet readers: mechanical facts, the record, the field (incidents and the driver), the operator model, the target',
      model: 'sonnet',
    },
    {
      title: 'Draft',
      detail: 'one Fable drafter writes the plan to the scratchpad; nothing under docs/superpowers/plans yet',
      model: 'fable',
    },
  ],
}

const A = args || {}
const REPO = A.repo || '/home/dalhaka/nixos-agent-env'
const SCRATCH = A.scratch
const SINCE = A.since || '2026-09-04'
const REPLAN = A.replan || null
if (!A.date || !A.name || !SCRATCH || !A.spec) throw new Error('draft-packet: args need date, name, scratch, spec')
if (REPLAN && !A.rejection) throw new Error('draft-packet: replan needs args.rejection (the rejecting review)')

const RULES = `HARD RULES (the host is LIVE from this repo):
- Build-only. NEVER run sudo, nixos-rebuild, systemctl start/stop/restart, basket mount/teardown, or any seat launch (tools/factory/seat/* is a paid driver: read it, never run it). Two read-only exceptions: factory-dispatch with --dry-run, and factory-brief <plan> <KEY>, which reads one plan file and prints to stdout.
- Write only under ${SCRATCH}, except the three files the Ship phase names — the plan file, the judgement file and the concept file — written with the Write tool.
- Never open transcripts, seat logs, session files or store bodies (~/factory/runs/*/*.log — dispatch.log included — *.dsh-home, ~/.claude/projects, /var/lib/evidence/*.jsonl bodies). The record is verdicts, classes and counts.
- No network. No fetch of any page; the vendored catalog and the tree are the facts.
- No line beginning "### <KEY> (code|docs, XS|S|M|L) — " in any file under ${REPO}/docs/superpowers/plans until the Ship phase writes the final plan.
- Every fact about the tree is pasted from a command you ran, with the command beside it; cite anchor text, not line numbers.
- Tools: nix develop -c <cmd> from inside the repo gives python3, jq, bats; grep is ugrep.
- Your final message is machine-read: return only the requested structured output.
- The one write outside ${SCRATCH} and the Ship phase's files: a defect you find in the tree or the harness while planning is noted with BUG_NOTE_REPORTER=plan/<phase> tools/debug/bug-note "<symptom>" --evidence <path>, which appends one line to ~/factory/debug/inbox.jsonl; it never goes into the plan's tasks unless the spec names it.`

const PACKET_SCHEMA = {
  type: 'object',
  required: ['part', 'path', 'digest', 'missing', 'checkEmpty', 'headings'],
  properties: {
    part: { type: 'string', enum: ['mechanical', 'record', 'field', 'operator', 'target'] },
    path: { type: 'string' },
    digest: { type: 'string' },
    missing: { type: 'array', items: { type: 'string' } },
    // the mechanical reader sets it from tasks.py check's own output; every other reader returns null
    checkEmpty: { type: ['boolean', 'null'] },
    headings: { type: ['array', 'null'], items: { type: 'string' } },
  },
}

const DRAFT_SCHEMA = {
  type: 'object',
  required: ['path', 'words', 'tasks', 'questions', 'headings'],
  properties: {
    path: { type: 'string' },
    words: { type: 'integer' },
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['key', 'kind', 'size'],
        properties: {
          key: { type: 'string' },
          kind: { type: 'string' },
          size: { type: 'string' },
          dependsOn: { type: 'array', items: { type: 'string' } },
          touches: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    questions: {
      type: 'array',
      maxItems: 3,
      items: {
        type: 'object',
        required: ['question', 'recommendation', 'default'],
        properties: { question: { type: 'string' }, recommendation: { type: 'string' }, default: { type: 'string' } },
      },
    },
    selfScore: { type: 'array', minItems: 14, maxItems: 14, items: { type: 'integer', minimum: 0, maximum: 3 } },
    headings: { type: 'array', items: { type: 'string' } },
  },
}

const READERS = [
  {
    part: 'mechanical',
    effort: 'low',
    prompt: `Read-only. From ${REPO}, run these in order (M1–M13 of the design's §2.1) and paste each output verbatim under its command and the time it ran, into ${SCRATCH}/packet/mechanical.md:
  M1  nix develop -c python3 pkgs/evidence/tasks.py --root . check > ${SCRATCH}/packet/check.out 2> ${SCRATCH}/packet/check.err ; echo "exit=$?"      (the EXIT STATUS is the verdict and the only thing that sets checkEmpty — tasks.py check writes its findings to stderr and returns 1 if errors else 0, which is the same signal tools/factory/seat/factory-plan-brief.sh gates on. checkEmpty is true when exit=0, false when exit is non-zero. NEVER judge by whether a file has bytes in it: an unsound graph puts its findings in check.err, and nix puts its own chatter there too — an "error (ignored): SQLite database ... is busy" or "evaluation warning:" line comes from a contended eval cache and says nothing about the graph. Paste the exit line and BOTH files verbatim; never discard either, and never redirect to /dev/null. Stop after M1 only when exit is non-zero. If the command could not be run at all, name it in missing and return checkEmpty null — null means "no answer", never "unsound".)
  M2  nix develop -c python3 pkgs/evidence/tasks.py --root . brief
  M3  nix develop -c python3 pkgs/evidence/tasks.py --root . json > ${SCRATCH}/packet/graph.json      (keep it in that file; paste only its byte count)
  M4  nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --json
  M5  nix develop -c python3 pkgs/evidence/tasks.py --root . conflicts
  M6  evidence bundle --markdown
  M7  nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today ${A.date}
  M8  bash tools/ritual.sh inflight ${REPO}
  M9  bash tools/session-start.sh
  M10 grep -n '^## \\|^### ' docs/MAP.md | head -120, then the check names docs/MAP.md defines, one per line, under a heading CHECKS
  M11 cat docs/ledger/routing.toml
  M12 git log --since=${SINCE} --format='%ci%x09%s' | head -80
  M13 tools/factory/seat/factory-brief docs/superpowers/plans/2026-09-05-evidence-store.md E1      (read-only: the shape a seat sees)
Return part "mechanical", path, a five-line digest, checkEmpty, and the list of commands that were unavailable.`,
  },
  {
    part: 'record',
    effort: 'low',
    prompt: `Read-only. Write ${SCRATCH}/packet/record.md: (1) from ${REPO}/${A.spec} list the paths the spec names; (2) for each, find gate reviews in docs/reviews/*opus-review*.md whose task touched that path (grep the path), and for each rejected one give run, key, the plan-defect class (from the review's front matter if present, else from docs/ledger/plan-defects.toml if it exists, else from Appendix B of docs/superpowers/specs/2026-09-05-planning-agent-design.md) and the one sentence the plan was missing; (3) the eight questions of that document's Appendix A verbatim; (4) the rules of record: the three amendments of docs/decisions/2026-09-03-test-based-reality-amendments.md, rule A1, and the parallel-workflows ordering (deterministic first, isolated workspaces second, judgement last). Never open a transcript or a log. Return part "record", path, digest, missing, checkEmpty null.`,
  },
  {
    part: 'field',
    effort: 'low',
    prompt: `Read-only. Write ${SCRATCH}/packet/field.md — the field. (1) Every incident in ${REPO}/docs/OPERATIONS.md, docs/board/log-2026-09.md and docs/board/archive-*.md dated on or after ${SINCE} — a seat death, a dead launch, a fabricated commit, a misparsed result block, a hook loop, a guard denial of the orchestrator's or the operator's own command, a red check on main, a switch — as a dated list, one line each: what happened, what closed it (the task key or the operator's action), and the board sentence it came from. (2) The driver's contract, read in full from tools/factory/seat/factory-task, factory-wave, factory-dispatch, factory-integrate and factory-lib.sh, one sentence each with the anchor text pasted beside it (no line numbers): what FACTORY_PLAN defaults to when it is unset; the exact FACTORY-RESULT grammar the extractor accepts and what it synthesises otherwise; what factory-integrate merges, from where, and what it refuses; where dispatch.log is written and the one line it holds; what a hand launch must set. Never open a transcript or a log. Return part "field", path, digest, missing, checkEmpty null.`,
  },
  {
    part: 'operator',
    effort: 'low',
    prompt: `Read-only. Write ${SCRATCH}/packet/operator.md: brief §3 (the six invariants, verbatim), brief §7 (the phase-gate sentence) and §8 (how to work) from ${REPO}/docs/brief.md; the "Operator owns:" sentence and every pause or hold from the START HERE block of docs/OPERATIONS.md; docs/board/operator-model.md in full if it exists; the operator's verbatim words from docs/decisions/2026-09-04-parallel-agent-workflows.md, 2026-09-02-invariants-bind-agents-not-operator-apps.md, 2026-09-02-amendment-softkey.md. Then one list: decisions the spec leaves to the operator (anything under §3, an isolation grade, a name, spend, a credential's home, a widening of an agent's reach). Return part "operator", path, digest, missing, checkEmpty null.`,
  },
  {
    part: 'target',
    effort: 'low',
    prompt: `Read-only. Write ${SCRATCH}/packet/target.md: the spec ${REPO}/${A.spec} in full; its numbered items (number them if it does not); its word count and the size by the rule S ≤ 1500, M ≤ 4000, L above (an L is refused: say so); every file, option, check and command it names, each read and its anchor text pasted with the command that found it; the decisions it leaves open. In replan mode (${REPLAN || 'not set'}) also return headings: every line of ${REPO}/${REPLAN} that starts with "### ", verbatim and in order; otherwise headings null. Return part "target", path, digest, missing, checkEmpty null.`,
  },
]

function draftPrompt(packet, prior, errata) {
  const replan = REPLAN
    ? `This is a re-plan under rule A1: read the existing plan ${REPO}/${REPLAN} and the rejecting review ${REPO}/${A.rejection} in full. Write the WHOLE plan file: every existing typed heading line byte-intact and in place, the new <KEY>r section appended after the section it replaces, carrying every item of the rejection, the replacement for every deleted test, the fresh-workspace cherry-pick recipe, and the rule that replaces the enumeration the gate rejected. `
    : ''
  return `${RULES}
You are the planning agent. Inputs: the packet files ${packet.join(', ')} (read all in full first)${prior ? `, your prior draft ${prior} and the judges' errata:\n${JSON.stringify(errata, null, 1)}` : ''}.
${replan}Write ${prior ? 'the revised' : 'the'} plan to ${SCRATCH}/draft-${prior ? 'next' : '0'}.md following docs/superpowers/specs/2026-09-05-planning-agent-design.md §3 Steps 1–6 exactly: at most three operator questions each with a recommendation and a default; the spec-to-task map; typed sections (key, kind, size XS/S/M) with dependsOn, explicit touches, acceptance from docs/MAP.md's check names and a byte-exact commit subject; per section Files, Interfaces (every producer, every enum arm, the error contract), Facts pasted with their commands, Steps with the red command and its expected output and a commit step whose body is produced by a script that runs each named command and appends its output (never typed; the recipe of DF8d in docs/superpowers/plans/2026-09-11-defects.md), probes that assert the post-state only and never pin a line number, and Steps that never instruct the seat itself to merge main or to regenerate/restore the derived board block — that is the integrator's and the orchestrator's job, outside the seat's own commit, never the section's (a seat merging main inflates touches_extra and fails the fast-forward, DF13 2026-09-15; a seat's fix round told to restore the board block died mid-run on that step, HM7c 2026-09-15); Tests with one mutant per assertion and the discriminating fixture row; a Waves table from tasks.py (Step 3's scratch-copy form); a ## Global Constraints and a ## Assumptions section (the seat sees only those two plus the task's own section); a ## Operator section with one command per step, acceptance and rollback; a ## Dispatch section with the factory-dispatch --dry-run line per wave and the landing recipe of §4 A1 (branch reset to the one named commit, merge main if the base moved, review, integrate, ff); the anticipation rows of §4 whose trigger applies — a driver guard as a dependsOn on P11 or a task, not a sentence, where the field packet shows the driver still lacks it; a "Not in this plan" list. Format reference: docs/superpowers/plans/2026-09-05-evidence-store.md (header, Waves, E1). Answer Appendix A's eight questions per section in ${SCRATCH}/draft-checklist.md. Score yourself on the 14 rubric rows. Return path, words, tasks, questions, selfScore, headings (every line of the draft that starts with "### ", verbatim).`
}

function refuseDroppedHeadings(prior, d) {
  if (!REPLAN) return
  const missing = (prior || []).filter((h) => !(d.headings || []).includes(h))
  if (missing.length) throw new Error('draft-packet: replan drops heading: ' + missing.join(' | '))
}

let packetPaths = []
let priorHeadings = null

const spentBeforePacket = budget.spent()
phase('Packet')
const parts = (
  await parallel(
    READERS.map(
      (r) => () =>
        agent(`${RULES}\n${r.prompt}`, {
          label: `read-${r.part}`,
          phase: 'Packet',
          model: 'sonnet',
          effort: r.effort,
          schema: PACKET_SCHEMA,
        }),
    ),
  )
).filter(Boolean)
if (parts.length < READERS.length)
  throw new Error('draft-packet: a packet reader returned nothing; refusing to draft on a partial packet')
const mech = parts.find((p) => p.part === 'mechanical')
// Two different failures, two different sentences. `checkEmpty false` is the
// graph reporting findings; anything else — a missing reader, or `null` —
// is the reader saying it never got an answer, which is not evidence about
// the graph at all. One shared message sent an orchestrator hunting a graph
// fault that did not exist (2026-09-21, wf_e8e47844-d6a).
if (!mech || mech.checkEmpty === null || mech.checkEmpty === undefined)
  throw new Error(
    'draft-packet: could not run the soundness check (the mechanical reader did not report an exit status for tasks.py check); this says nothing about the graph — re-run the packet, and check for a concurrent nix invocation holding the eval cache',
  )
if (mech.checkEmpty !== true)
  throw new Error(
    'draft-packet: the graph is not sound (tasks.py check exited non-zero; its findings are on stderr in the packet); fix the graph first',
  )
packetPaths = parts.map((p) => p.path)
priorHeadings = (parts.find((p) => p.part === 'target') || {}).headings || null
log(`packet: ${packetPaths.length} parts; unavailable: ${parts.flatMap((p) => p.missing).join(', ') || 'none'}`)
const packetTokens = budget.spent() - spentBeforePacket

const spentBeforeDraft = budget.spent()
phase('Draft')
const d = await agent(draftPrompt(packetPaths, null, null), {
  label: 'draft',
  phase: 'Draft',
  model: 'fable',
  effort: 'max',
  schema: DRAFT_SCHEMA,
})
if (!d) throw new Error('draft-packet: the drafter returned nothing')
refuseDroppedHeadings(priorHeadings, d)
log(`draft: ${d.words} words, ${d.tasks.length} tasks, ${d.questions.length} operator questions`)
const draftTokens = budget.spent() - spentBeforeDraft

return {
  draft: d.path,
  packet: packetPaths,
  outputTokensByPhase: { packet: packetTokens, draft: draftTokens },
  spent: budget.spent(),
}
