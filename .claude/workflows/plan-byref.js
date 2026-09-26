// .claude/workflows/plan-byref.js — a planning drafter that queries the tree and evidence store directly, pinned.

export const meta = {
  name: 'plan-byref',
  description:
    'Planning agent: draft a typed plan from a spec',
  whenToUse:
    'A spec is approved and needs a draft',
  phases: [
    {
      title: 'Draft',
      detail:
        'one Fable drafter queries the spec, the tree and the evidence store directly (tasks.py, duckdb/JSONL, grep, git log) and writes the plan to the scratchpad; no packet phase',
      model: 'fable',
    },
    {
      title: 'Judge',
      detail: 'two blind Sonnet judges (implementer lens, reviewer lens) and one blind Opus judge score the rubric',
      model: 'opus',
    },
    {
      title: 'Revise',
      detail: 'Fable revises against the errata, querying again as needed; at most two rounds',
      model: 'fable',
    },
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
const STORE = A.store || '/var/lib/evidence'
const THRESHOLD = Number.isInteger(A.threshold) ? A.threshold : 34
const ROUNDS = Number.isInteger(A.rounds) ? A.rounds : 2
const RUN = A.run || 'plan-' + A.name
if (!A.date || !A.name || !SCRATCH || !A.spec || !A.out)
  throw new Error('plan-byref: args need date, name, scratch, spec, out')
const judgementPath = `docs/reviews/plan-judgements/${A.date}-${A.name}.md`

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

function draftPrompt(prior, errata) {
  return `${RULES}
You are the planning agent. There is no packet and no fixed reading order: query the spec, the tree and the evidence store yourself, as you draft, and verify every fact you write by a command you ran, pasted beside it — never invent a path, a command's output or a defect class.
Inputs: the spec ${REPO}/${A.spec} (read it in full first), the repo root ${REPO}, and EVIDENCE_STORE=${STORE}${prior ? `; also your prior draft ${prior} and the judges' errata:\n${JSON.stringify(errata, null, 1)}` : ''}.
Query recipes — run these yourself, on demand, as the draft needs them; none needs a packet file or a prior read. Append every command you run, with its exit code, to ${SCRATCH}/queries.log as you go (one line per command); a Facts line in the plan with no matching entry in that log is a defect.
  - The task graph: plain python3 ${REPO}/pkgs/evidence/tasks.py --root ${REPO} <check|brief|json|waves --repo nixos-agent-env --json|conflicts> — tasks.py is stdlib-only, so this runs without nix develop.
  - The evidence store: duckdb over the JSONL streams under ${STORE} via python3 -c "import duckdb; ..." if duckdb is importable in this environment; otherwise read the .jsonl files line by line with the json module.
  - The tree: grep -n / rg over ${REPO} for facts, defect and gate reviews (docs/reviews/*opus-review*.md), decisions (docs/decisions/), the operator model (docs/brief.md, docs/OPERATIONS.md), the field record (docs/OPERATIONS.md, docs/board/log-*.md, docs/board/archive-*.md).
  - History: git -C ${REPO} log --format='%ci%x09%s' <path or --since date>.
You MAY spawn sub-agents for sub-questions that would cost you the same context to chase yourself (for example, "what does the field record say happened to this driver since the spec's date?" or "what does this rejected review's front matter give as its defect class?"). Hand each sub-agent one path (or a small set) and the question, never a summary of what you already found; that sub-agent writes its raw output to ${SCRATCH}/q/<n>.md (pick the next free n) and returns only that path — read the file yourself before writing anything that depends on it, since there is no persistent REPL here and a subagent receives only the prompt string you give it.
Write ${prior ? 'the revised' : 'the'} plan to ${SCRATCH}/draft-${prior ? 'next' : '0'}.md following docs/superpowers/specs/2026-09-05-planning-agent-design.md §3 Steps 1–6 exactly: at most three operator questions each with a recommendation and a default; the spec-to-task map; typed sections (key, kind, size XS/S/M) with dependsOn, explicit touches, acceptance from docs/MAP.md's check names and a byte-exact commit subject; per section Files, Interfaces (every producer, every enum arm, the error contract), Facts pasted with their commands, Steps with the red command and its expected output and a commit step whose body is produced by a script that runs each named command and appends its output (never typed; the recipe of DF8d in docs/superpowers/plans/2026-09-11-defects.md), probes that assert the post-state only and never pin a line number, and Steps that never instruct the seat itself to merge main or to regenerate/restore the derived board block — that is the integrator's and the orchestrator's job, outside the seat's own commit, never the section's (a seat merging main inflates touches_extra and fails the fast-forward, DF13 2026-09-15; a seat's fix round told to restore the board block died mid-run on that step, HM7c 2026-09-15); Tests with one mutant per assertion and the discriminating fixture row; a Waves table from tasks.py (Step 3's scratch-copy form); a ## Global Constraints and a ## Assumptions section (the seat sees only those two plus the task's own section); a ## Operator section with one command per step, acceptance and rollback; a ## Dispatch section with the factory-dispatch --dry-run line per wave and the landing recipe of §4 A1 (branch reset to the one named commit, merge main if the base moved, review, integrate, ff); the anticipation rows of §4 whose trigger applies — a driver guard as a dependsOn on P11 or a task, not a sentence, where your own query of the field (docs/OPERATIONS.md, docs/board/*, the driver scripts under tools/factory/seat/) shows the driver still lacks it; a "Not in this plan" list. Format reference: docs/superpowers/plans/2026-09-05-evidence-store.md (header, Waves, E1). Answer Appendix A's eight questions per section in ${SCRATCH}/draft-checklist.md. Score yourself on the 14 rubric rows. Return path, words, tasks, questions, selfScore, headings (every line of the draft that starts with "### ", verbatim).`
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

let draft = null
let questions = []
let selfScore = null

const spentBeforeDraft = budget.spent()
phase('Draft')
const d0 = await agent(draftPrompt(null, null), {
  label: 'draft',
  phase: 'Draft',
  model: 'fable',
  effort: 'max',
  schema: DRAFT_SCHEMA,
})
if (!d0) throw new Error('plan-byref: the drafter returned nothing')
draft = d0.path
questions = d0.questions
selfScore = d0.selfScore || null
log(`draft: ${d0.words} words, ${d0.tasks.length} tasks, ${d0.questions.length} operator questions`)
const draftTokens = budget.spent() - spentBeforeDraft

let round = 0
let verdict
let judgements = []
let judgeTokens = 0
let reviseTokens = 0
while (true) {
  const spentBeforeJudge = budget.spent()
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
  judgeTokens += budget.spent() - spentBeforeJudge
  verdict = tally(judgements)
  log(
    `judge round ${round}: ${verdict.total}/42 from ${verdict.judges.length} judges${verdict.dropped.length ? ` (silent: ${verdict.dropped.join(', ')})` : ''}, floor ${verdict.floorOk ? 'ok' : 'FAILED'} → ${verdict.panelShort ? 'panel-short' : verdict.pass ? 'dispatchable' : 'revise'}`,
  )
  if (verdict.pass || verdict.panelShort || round >= ROUNDS) break
  round++
  const spentBeforeRevise = budget.spent()
  phase('Revise')
  const errata = judgements.filter(Boolean).flatMap((j) => j.errata)
  const d = await agent(draftPrompt(draft, errata), {
    label: `revise-${round}`,
    phase: 'Revise',
    model: 'fable',
    effort: 'max',
    schema: DRAFT_SCHEMA,
  })
  reviseTokens += budget.spent() - spentBeforeRevise
  if (!d) break
  draft = d.path
  questions = d.questions
  selfScore = d.selfScore || selfScore
}

phase('Ship')
const spentBeforeShip = budget.spent()
const decision = verdict.panelShort ? 'panel-short' : verdict.pass ? 'dispatch' : 'revise-exhausted'
const record = {
  plan: `docs/superpowers/plans/${A.out}`,
  spec: A.spec,
  author: 'fable',
  effort: 'max',
  date: A.date,
  judges: verdict.judges,
  judges_dropped: verdict.dropped,
  scores: verdict.per,
  total: verdict.total,
  selfScore,
  threshold: THRESHOLD,
  decision,
  revision: round,
  replan: null,
  rejection: null,
  questions,
  errata: judgements.filter(Boolean).flatMap((j) => j.errata),
  reasons: judgements.filter(Boolean).map((j) => j.reasons || []),
}
const writePlan = `Copy the draft verbatim to ${REPO}/docs/superpowers/plans/${A.out} with the Write tool (a new file has no heading to lose).`
const ship = await agent(
  `${RULES}
Ship phase. Decision: ${decision}. Draft: ${draft}. Record (JSON): ${JSON.stringify(record)}.
1. Write ${REPO}/${judgementPath}: a front-matter block between two --- lines with ${RECORD_FIELDS.join(', ')}; then the errata table and each judge's reasons. Use the Write tool.
${
  decision === 'dispatch'
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
const shipTokens = budget.spent() - spentBeforeShip

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
  // OUTPUT TOKENS ONLY (budget.spent() counts output tokens): a delta sampled at each phase boundary.
  outputTokensByPhase: { draft: draftTokens, judge: judgeTokens, revise: reviseTokens, ship: shipTokens },
}
