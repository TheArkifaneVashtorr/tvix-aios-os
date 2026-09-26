// .claude/workflows/draft-byref.js — a planning drafter that queries the tree and evidence store directly as it drafts, pinned.
export const meta = {
  name: 'draft-byref',
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
  ],
}

const A = args || {}
const REPO = A.repo || '/home/dalhaka/nixos-agent-env'
const SCRATCH = A.scratch
const STORE = A.store || '/var/lib/evidence'
if (!A.date || !A.name || !SCRATCH || !A.spec) throw new Error('draft-byref: args need date, name, scratch, spec')

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

const spentBeforeDraft = budget.spent()
phase('Draft')
const d0 = await agent(draftPrompt(null, null), {
  label: 'draft',
  phase: 'Draft',
  model: 'fable',
  effort: 'max',
  schema: DRAFT_SCHEMA,
})
if (!d0) throw new Error('draft-byref: the drafter returned nothing')
log(`draft: ${d0.words} words, ${d0.tasks.length} tasks, ${d0.questions.length} operator questions`)
const draftTokens = budget.spent() - spentBeforeDraft

return {
  draft: d0.path,
  queriesLog: `${SCRATCH}/queries.log`,
  outputTokensByPhase: { draft: draftTokens },
  spent: budget.spent(),
}
