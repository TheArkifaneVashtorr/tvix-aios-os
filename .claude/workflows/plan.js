// .claude/workflows/plan.js — the planning agent, pinned.
// Invoke:  Workflow({ name: 'plan', args: { spec, out, name, date, since, scratch } })
//      or  Workflow({ name: 'plan', args: { judgeOnly: true, draft, spec, name, date, scratch, author, effort } })
//      or  Workflow({ name: 'plan', args: { replan, rejection, spec, out, name, date, since, scratch } })
// args:
//   spec      path of the approved spec (docs/superpowers/specs/…), relative to the repo
//   out       basename of the plan to write under docs/superpowers/plans/ (YYYY-MM-DD-<name>.md);
//             in replan mode the basename of the existing plan, rewritten whole
//   name      short plan name (labels; the judgement file name)
//   date      today, YYYY-MM-DD (a script cannot read the clock)
//   since     the date the landings-and-churn window (M12) and the field's incident list start; default '2026-09-04'
//   scratch   a directory agents may write the packet and drafts to
//   repo      default /home/dalhaka/nixos-agent-env
//   threshold default 34 (of 42); rounds default 2; run default 'plan-<name>'
//   judgeOnly, draft   judge an existing draft (a dsh seat's or a hand-written one) and stop;
//                      without `out` the panel is written beside the section panels
//                      (docs/reviews/<date>-panel-<name>-section.md), with `out` under plan-judgements/
//   author    the draft's author for the record in judgeOnly mode: 'hand' | 'dsh:<model>' (default 'hand')
//   effort    the drafter's effort for the record in judgeOnly mode (default 'unknown'); 'max' otherwise
//   replan, rejection   re-plan mode (rule A1): the existing plan's path and the rejecting review's path;
//             the drafter appends the <KEY>r section and keeps every prior typed heading byte-intact
export const meta = {
  name: 'plan',
  description:
    'Planning agent: gather the packet, draft a typed plan from a spec, judge it blind (two Sonnet, one Opus) against the 14-row rubric, revise, write the plan file, print the dispatch dry run',
  whenToUse:
    'A spec under docs/superpowers/specs/ is approved and needs an implementation plan, a rejected task needs a re-plan (replan), or a draft plan needs the judge panel (judgeOnly)',
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
    {
      title: 'Judge',
      detail: 'two blind Sonnet judges (implementer lens, reviewer lens) and one blind Opus judge score the rubric',
      model: 'opus',
    },
    { title: 'Revise', detail: 'Fable revises against the errata; at most two rounds', model: 'fable' },
    {
      title: 'Ship',
      detail: 'the plan file is written, the graph checked, the judgement filed, the dispatch dry run printed',
      model: 'sonnet',
    },
  ],
}

const A = args || {}
const REPO = A.repo || '/home/dalhaka/nixos-agent-env'
const SCRATCH = A.scratch
const SINCE = A.since || '2026-09-04'
const THRESHOLD = Number.isInteger(A.threshold) ? A.threshold : 34
const ROUNDS = Number.isInteger(A.rounds) ? A.rounds : 2
const RUN = A.run || 'plan-' + A.name
const REPLAN = A.replan || null
if (!A.date || !A.name || !SCRATCH || !A.spec) throw new Error('plan: args need date, name, scratch, spec')
if (!A.judgeOnly && !A.out) throw new Error('plan: args.out names the plan file to write')
if (A.judgeOnly && !A.draft) throw new Error('plan: judgeOnly needs args.draft')
if (REPLAN && !A.rejection) throw new Error('plan: replan needs args.rejection (the rejecting review)')
if (REPLAN && A.judgeOnly) throw new Error('plan: replan and judgeOnly are exclusive')
// The judgement file's path, computed once: a judgeOnly panel without a plan
// destination (out) lands beside the section panels, never under
// plan-judgements/ (a section panel's front matter fails test_judgements.py);
// with `out` -- a whole-plan draft -- the record stays under plan-judgements/.
const judgementPath =
  A.judgeOnly && !A.out
    ? `docs/reviews/${A.date}-panel-${A.name}-section.md`
    : `docs/reviews/plan-judgements/${A.date}-${A.name}.md`

const CRITERIA = [
  'spec coverage',
  'correct facts',
  'self-contained sections',
  'TDD discipline',
  'mutant per assertion and discriminating fixtures',
  'interfaces and error contracts',
  'rules not enumerations',
  'waves, touches, conflicts',
  'invariant awareness',
  'operator steps and rollback',
  'anticipation',
  'economy',
  'format and graph compliance',
  'judgement calls',
]
const FLOOR_ROWS = [1, 2, 4, 5, 6, 12] // rows 2, 3, 5, 6, 7, 13 (0-based)
const RECORD_FIELDS = [
  'plan',
  'spec',
  'author',
  'effort',
  'words',
  'tasks',
  'judges',
  'judges_dropped',
  'scores',
  'total',
  'self_score',
  'threshold',
  'decision',
  'revision',
]

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
const SCORE_SCHEMA = {
  type: 'object',
  required: ['scores', 'errata', 'dispatchable'],
  properties: {
    scores: { type: 'array', minItems: 14, maxItems: 14, items: { type: 'integer', minimum: 0, maximum: 3 } },
    reasons: { type: 'array', minItems: 14, maxItems: 14, items: { type: 'string' } },
    errata: {
      type: 'array',
      items: {
        type: 'object',
        required: ['criterion', 'task', 'finding', 'fix'],
        properties: {
          criterion: { type: 'integer', minimum: 1, maximum: 14 },
          task: { type: 'string' },
          finding: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
    wrongFacts: { type: 'integer' },
    dispatchable: { type: 'boolean' },
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

const LENSES = [
  {
    name: 'implementer',
    model: 'sonnet',
    effort: 'high',
    lens: `You are a blind implementer with no session context. For three sections chosen at random, run tools/factory/seat/factory-brief <draft> <KEY> from the repo (read-only; it reads any plan path and prints to stdout — the rules name it as allowed) and try to land the task from that text alone: list every path, signature, command or fact you would have had to invent. Score row 3 from that list first; then the rest.`,
  },
  {
    name: 'reviewer',
    model: 'sonnet',
    effort: 'high',
    lens: `You are the Opus gate rehearsing its mutation table. For every assertion the draft names, write the one-line mutant the draft names and one it does not; mark each survivor. For every rule, write one spelling outside it. A proof shape the draft names ("a fixture listing, or an assertion over the layout") is not a mutant: write the mutant that shape would need, and if the draft did not name it, mark it a survivor. Score rows 5, 6 and 7 from the survivors first; then the rest.`,
  },
  {
    name: 'whole',
    model: 'opus',
    effort: 'high',
    lens: `Judge the whole plan against the spec and the tree: re-run three cited commands and count wrong facts (row 2). For row 13, copy the tree with its .git to ${SCRATCH}/tree (cp -a ${REPO} ${SCRATCH}/tree), place the draft under ${SCRATCH}/tree/docs/superpowers/plans/, write a one-repo file — printf '[[repo]]\\nname = "nixos-agent-env"\\npath = "%s"\\n' ${SCRATCH}/tree > ${SCRATCH}/repos.toml — and run, from ${REPO}: nix develop -c python3 pkgs/evidence/tasks.py --root ${SCRATCH}/tree --repos ${SCRATCH}/repos.toml --runs-dir /nonexistent --store /nonexistent check, then conflicts and waves --repo nixos-agent-env --json the same way (the --root-only form re-reads the live tree through docs/ledger/repos.toml and cannot see the draft; after P1, tasks.py check --draft replaces this). Read the Waves, Operator and Dispatch sections against §4 and §5 of the design (rows 8, 10, 11); the invariants (row 9); the decisions (row 14).`,
  },
]
function judgePrompt(l, draft) {
  return `${RULES}
Blind judge, ${l.name} lens. Read only: the spec ${REPO}/${A.spec}, the draft ${draft}, the rubric ${REPO}/tools/factory/plan/rubric.md and the judge instructions ${REPO}/tools/factory/plan/judge-prompt.md and the tree. Do not read any other draft, packet, transcript or judgement. ${l.lens}`
}

function tally(judgements) {
  const js = judgements.filter(Boolean)
  const per = CRITERIA.map((_, i) => {
    const v = js.map((j) => j.scores[i]).sort((a, b) => a - b)
    return v.length === 3 ? v[1] : v.length ? v[0] : 0 // median of three; fewer than three never dispatches (panelShort)
  })
  const total = per.reduce((s, x) => s + x, 0)
  const floorOk = FLOOR_ROWS.every((i) => per[i] >= 2)
  const answered = LENSES.filter((_, i) => judgements[i]).map((l) => l.model)
  const dropped = LENSES.filter((_, i) => !judgements[i]).map((l) => l.name)
  const panelShort = js.length < 3
  return {
    per,
    total,
    floorOk,
    judges: answered,
    dropped,
    panelShort,
    pass: !panelShort && total >= THRESHOLD && floorOk,
  }
}
function refuseDroppedHeadings(prior, d) {
  if (!REPLAN) return
  const missing = (prior || []).filter((h) => !(d.headings || []).includes(h))
  if (missing.length) throw new Error('plan: replan drops heading: ' + missing.join(' | '))
}

let packetPaths = []
let priorHeadings = null
let draft = A.draft || null
let questions = []
let selfScore = null

if (!A.judgeOnly) {
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
    throw new Error('plan: a packet reader returned nothing; refusing to draft on a partial packet')
  const mech = parts.find((p) => p.part === 'mechanical')
  // Two different failures, two different sentences. `checkEmpty false` is the
  // graph reporting findings; anything else — a missing reader, or `null` —
  // is the reader saying it never got an answer, which is not evidence about
  // the graph at all. One shared message sent an orchestrator hunting a graph
  // fault that did not exist (2026-09-21, wf_e8e47844-d6a).
  if (!mech || mech.checkEmpty === null || mech.checkEmpty === undefined)
    throw new Error(
      'plan: could not run the soundness check (the mechanical reader did not report an exit status for tasks.py check); this says nothing about the graph — re-run the packet, and check for a concurrent nix invocation holding the eval cache',
    )
  if (mech.checkEmpty !== true)
    throw new Error(
      'plan: the graph is not sound (tasks.py check exited non-zero; its findings are on stderr in the packet); fix the graph first',
    )
  packetPaths = parts.map((p) => p.path)
  priorHeadings = (parts.find((p) => p.part === 'target') || {}).headings || null
  log(`packet: ${packetPaths.length} parts; unavailable: ${parts.flatMap((p) => p.missing).join(', ') || 'none'}`)

  phase('Draft')
  const d = await agent(draftPrompt(packetPaths, null, null), {
    label: 'draft',
    phase: 'Draft',
    model: 'fable',
    effort: 'max',
    schema: DRAFT_SCHEMA,
  })
  if (!d) throw new Error('plan: the drafter returned nothing')
  draft = d.path
  questions = d.questions
  selfScore = d.selfScore || null
  refuseDroppedHeadings(priorHeadings, d)
  log(`draft: ${d.words} words, ${d.tasks.length} tasks, ${d.questions.length} operator questions`)
}

let round = 0
let verdict
let judgements = []
while (true) {
  phase('Judge')
  judgements = await parallel(
    LENSES.map(
      (l) => () =>
        agent(judgePrompt(l, draft), {
          label: `judge-${l.name}-${round}`,
          phase: 'Judge',
          model: l.model,
          effort: l.effort,
          schema: SCORE_SCHEMA,
        }),
    ),
  )
  for (let i = 0; i < LENSES.length; i++) {
    // one re-ask for a silent lens; a lens still silent leaves the panel short, and a short panel never dispatches
    if (!judgements[i])
      judgements[i] = await agent(judgePrompt(LENSES[i], draft), {
        label: `judge-${LENSES[i].name}-${round}-retry`,
        phase: 'Judge',
        model: LENSES[i].model,
        effort: LENSES[i].effort,
        schema: SCORE_SCHEMA,
      })
  }
  verdict = tally(judgements)
  log(
    `judge round ${round}: ${verdict.total}/42 from ${verdict.judges.length} judges${verdict.dropped.length ? ` (silent: ${verdict.dropped.join(', ')})` : ''}, floor ${verdict.floorOk ? 'ok' : 'FAILED'} → ${verdict.panelShort ? 'panel-short' : verdict.pass ? 'dispatchable' : 'revise'}`,
  )
  if (verdict.pass || verdict.panelShort || A.judgeOnly || round >= ROUNDS) break
  round++
  phase('Revise')
  const errata = judgements.filter(Boolean).flatMap((j) => j.errata)
  const d = await agent(draftPrompt(packetPaths, draft, errata), {
    label: `revise-${round}`,
    phase: 'Revise',
    model: 'fable',
    effort: 'max',
    schema: DRAFT_SCHEMA,
  })
  if (!d) break
  refuseDroppedHeadings(priorHeadings, d)
  draft = d.path
  questions = d.questions
  selfScore = d.selfScore || selfScore
}

phase('Ship')
const decision = verdict.panelShort
  ? 'panel-short'
  : verdict.pass
    ? 'dispatch'
    : A.judgeOnly
      ? 'revise'
      : 'revise-exhausted'
const record = {
  plan: A.judgeOnly ? draft : `docs/superpowers/plans/${A.out}`,
  spec: A.spec,
  author: A.judgeOnly ? A.author || 'hand' : 'fable',
  effort: A.judgeOnly ? A.effort || 'unknown' : 'max',
  date: A.date,
  judges: verdict.judges,
  judges_dropped: verdict.dropped,
  scores: verdict.per,
  total: verdict.total,
  selfScore,
  threshold: THRESHOLD,
  decision,
  revision: round,
  replan: REPLAN,
  rejection: A.rejection || null,
  questions,
  errata: judgements.filter(Boolean).flatMap((j) => j.errata),
  reasons: judgements.filter(Boolean).map((j) => j.reasons || []),
}
const writePlan = REPLAN
  ? `Re-plan: before writing, list the "### " heading lines of ${REPO}/${REPLAN} and check every one of them appears byte-identical in ${draft} (comm -23 <(grep '^### ' ${REPO}/${REPLAN} | sort -u) <(grep '^### ' ${draft} | sort -u) must print nothing — a superset of the orchestrator guard's typed-heading rule, which refuses a write that loses one). If it prints a line, stop and return plan: null with that line. Otherwise write the draft whole over ${REPO}/docs/superpowers/plans/${A.out} with the Write tool.`
  : `Copy the draft verbatim to ${REPO}/docs/superpowers/plans/${A.out} with the Write tool (a new file has no heading to lose).`
const ship = await agent(
  `${RULES}
Ship phase. Decision: ${decision}. Draft: ${draft}. Record (JSON): ${JSON.stringify(record)}.
1. Write ${REPO}/${judgementPath}: a front-matter block between two --- lines with ${RECORD_FIELDS.join(', ')}; then the errata table and each judge's reasons. Use the Write tool.
${
  decision === 'dispatch' && !A.judgeOnly
    ? `2. ${writePlan}
3. From ${REPO} run and paste: nix develop -c python3 pkgs/evidence/tasks.py --root . check (must be empty); … conflicts; … waves --repo nixos-agent-env --plan ${A.out} --next; tools/factory/seat/factory-dispatch ${RUN} ${REPO} docs/superpowers/plans/${A.out} --dry-run. Never run factory-dispatch without --dry-run.
4. Write the concept file ${REPO}/docs/concepts/${A.date}-<letter>-<slug>.md in the house format (Class / Status / Origin / Idea / Payoff / Dependencies / Earliest landing) — pick the next free letter for the date.`
    : `2. Do not write under docs/superpowers/plans. Return the errata${decision === 'panel-short' ? ' and the silent lens' : ''} for the operator.`
}
Return JSON: { judgement, plan, check, conflicts, nextWave, dryRun, concept } with null for anything not done.`,
  {
    label: 'ship',
    phase: 'Ship',
    model: 'sonnet',
    effort: 'medium',
    schema: {
      type: 'object',
      required: ['judgement'],
      properties: {
        judgement: { type: 'string' },
        plan: { type: ['string', 'null'] },
        check: { type: ['string', 'null'] },
        conflicts: { type: ['string', 'null'] },
        nextWave: { type: ['string', 'null'] },
        dryRun: { type: ['string', 'null'] },
        concept: { type: ['string', 'null'] },
      },
    },
  },
)

return {
  decision,
  total: verdict.total,
  scores: verdict.per,
  floorOk: verdict.floorOk,
  judges: verdict.judges,
  judgesDropped: verdict.dropped,
  rounds: round,
  questions,
  draft,
  ship,
  spent: budget.spent(),
}
