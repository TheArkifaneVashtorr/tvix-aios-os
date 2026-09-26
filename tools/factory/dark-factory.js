// Dark factory — reusable Workflow script for ~/nixos-agent-env.
// Policy: docs/decisions/2026-09-02-factory-model-policy.md — but the single
// source for the per-role model assignment is the routing table
// docs/ledger/routing.toml: tools/factory/route.py derives the default
// `models` map (M below) from that table's `claude` rows, and
// tests/factory/render.test.mjs (checks.factory-unit) refuses any drift
// between the table and this file's built-in default. Leave M's default as
// the literal route.py models output; change rows in routing.toml, not here.
// Scheduling: docs/decisions/2026-09-04-parallel-agent-workflows.md — tasks run
// in deterministic dependency waves, one isolated worktree per task, each wave
// integrated (--no-ff) onto a shared integration branch before the next begins.
//
// Invoke:  Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: {...} })
// args:
//   plan      (required) path to the committed plan, e.g. docs/superpowers/plans/2026-09-03-helm.md
//   prefix    (required) commit subject prefix, e.g. 'helm'
//   tasks     (required) [{ key: 'T1', title: '...', kind: 'code'|'docs',
//                           checks: ['unit','lint'], spec: 'what to build, from the plan',
//                           dependsOn: ['T0'], touches: ['pkgs/x/*.sh'], parallelSafe: false }]
//             A code task (kind !== 'docs') must name at least one check in
//             `checks` — validateGraph refuses it before dispatch otherwise
//             (board rule A1 / research-2026-09-05-paper-2609.01481.md §6 P4
//             residue: an unnamed check is a silent degradation to the lint
//             gate). Docs tasks may omit checks.
//             dependsOn: task keys that must finish green first (waves); touches:
//             repo-relative paths/globs the task WRITES (overlapping touches
//             serialise); parallelSafe: optional bool (false serialises, true
//             runs alongside anything)
//   concurrency       (default 4) max task groups dispatched together in one wave
//   judge             (default true) ask the parallel-safety judge for any task
//                     without a `touches` annotation; false serialises it instead
//   integrationBranch (default factory/<prefix>-integration) branch each wave is
//                     merged onto; the delivery agent fast-forwards it at the end
//   repo      default /home/dalhaka/nixos-agent-env
//   host      default 'core' (nixosConfigurations.<host> for the toplevel build); null → library flake, no toplevel/closure-diff step
//   scratch   directory agents may write to besides the repo (required for commit-message files)
//   research  optional evidence digest path(s), string
//   session   optional Claude session URL for the Claude-Session trailer
//   runId     optional run identifier, echoed verbatim into the journal's
//             factory-run report (run_id; null when unset)
//   fixRounds default 2
//   models    overrides for { baseline, impl, reviewCode, reviewDocs, verify, audit }
//             (audit defaults to 'fable' — see the M assignment below for why
//             that default must be explicit)
//   invariantAudit  true → one Fable (inherited-model) audit of the diff against brief §3
//   extraRules      string appended to the hard rules
//   skills    optional { nixos: <path> } — when set, skill references are
//             injected into the impl/fix, reviewCode, reviewDocs and verify
//             prompts (see skillLines() below). tasks[].skillRefs (array of
//             reference basenames under <path>/references/) customizes the
//             impl/fix prompt's read list for that task; tasks without it
//             fall back to the router table.
//   bootstrap       true → the repo is brand new (plan committed, no flake yet): the baseline
//                   skips the lint gate; Task 1 must create flake.nix + githooks + treefmt and
//                   every later commit goes through the devShell hook as usual
// Returns: { baseline, tasks:[{ key, status, commit, fixRounds, deviations,
//   blocked_reason, findings, reviewNote, wave, branch, workspace, blockedBy }],
//   unreviewed, verify, audit, schedule, integrationBranch, integrations,
//   delivered, recorded, economics }. Every implementer/fix/review result carries
//   task_key (the task key), round (0 for the implementer, n for fix round n,
//   reviewers echo the round reviewed) and label (the agent's own spawn label);
//   the verifier additionally carries evidence_recorded, and a final recorder
//   agent persists the run report to the evidence store, setting `recorded` true
//   only when it did so. Verify is conditional: it runs only when at least
//   one wave integrated, returning { verdict:'pass'|'fail', ... }; when no
//   wave integrated there is no merged tree to check and verify is
//   { verdict:'skipped', skipped:true } instead.
export const meta = {
  name: 'dark-factory',
  description:
    'Dark factory: implement, review, and verify a committed plan task-by-task in the live-host repo (build-only, never activate); models per role per docs/decisions/2026-09-02-factory-model-policy.md',
  whenToUse:
    'Executing a docs/superpowers/plans/*.md plan in ~/nixos-agent-env — pass the plan, prefix and task list via args',
  phases: [
    { title: 'Schedule', detail: 'dependency waves, overlap groups and the parallel-safety judge', model: 'opus' },
    { title: 'Baseline', detail: 'plan committed, lint gate green on HEAD', model: 'sonnet' },
    {
      title: 'Implement',
      detail: 'one implementer per task in its own worktree, dispatched in dependency waves',
      model: 'sonnet',
    },
    {
      title: 'Review',
      detail: 'code tasks: Opus adversarial gate (max 2 fix rounds); docs tasks: one Sonnet pass',
      model: 'opus',
    },
    { title: 'Integrate', detail: 'merge each wave --no-ff onto the integration branch and re-check', model: 'sonnet' },
    {
      title: 'Verify',
      detail: 'nix flake check + toplevel build + closure diff vs the running system (skipped when no wave integrated)',
      model: 'sonnet',
    },
    { title: 'Invariant audit', detail: 'optional, Fable, only for security-critical diffs' },
    { title: 'Deliver', detail: 'fast-forward the integration branch into the current branch', model: 'sonnet' },
  ],
}

const A = args || {}
if (!A.plan || !A.prefix || !Array.isArray(A.tasks) || A.tasks.length === 0 || !A.scratch) {
  throw new Error('dark-factory: args must include plan, prefix, scratch and a non-empty tasks array')
}
const REPO = A.repo || '/home/dalhaka/nixos-agent-env'
const HOST = A.host === null || A.host === false ? null : A.host || 'core'
const SCRATCH = A.scratch
const FIX_ROUNDS = Number.isInteger(A.fixRounds) ? A.fixRounds : 2
const M = Object.assign(
  // audit: 'fable' -- the model policy (docs/decisions/2026-09-02-factory-
  // model-policy.md) says the invariant audit runs on Fable; it's opt-in
  // via A.invariantAudit, but without a default here the spawn below would
  // omit `model` entirely and silently inherit whatever model this
  // orchestrating session happens to be running as instead.
  { baseline: 'sonnet', impl: 'sonnet', reviewCode: 'opus', reviewDocs: 'sonnet', verify: 'sonnet', audit: 'fable' },
  A.models || {},
)
const TRAILERS = ['Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>']
  .concat(A.session ? ['Claude-Session: ' + A.session] : [])
  .join('\n')

const RULES_BASE = `
HARD RULES (the host is LIVE from this repo; violating any of these is a critical failure):
- NEVER run: sudo, nixos-rebuild, systemctl start/stop/restart/reload/enable of any unit, cowork-up/cowork-down, basket mount/teardown, proton-drive, restic against /var/lib/restic. Build-only.
- NEVER write outside your worktree and ${SCRATCH}. Never touch /var/lib, /run, /etc, or the operator's home outside the repo.
- NEVER ship a certificate-error bypass or weaken the broker/netns/nftables layers. No secrets in the repo: placeholders only.
- Commit convention: subject "${A.prefix}: <summary> (test: <check names>)" (docs-only commits: "docs: <summary>"), a short body with the WHY, then EXACTLY these trailer lines last:
${TRAILERS}
- Commit via the devShell so the pre-commit lint hook has its tools: cd ${REPO} && nix develop -c git commit -F <msgfile>   (write the message to a file under ${SCRATCH}). Never bypass the hook (no --no-verify), never 2>/dev/null a gated command.${A.bootstrap ? ' BOOTSTRAP RUN: until Task 1 has landed flake.nix, githooks/ and treefmt.toml, `nix develop` does not exist — Task 1 itself commits with plain git after running its own lint tools via `nix shell nixpkgs#treefmt ...` is NOT allowed (unpinned); instead Task 1 builds the devShell first (nix develop -c true must succeed) and then commits through it like every later task.' : ''}
- git add every new/changed file BEFORE nix build / nix flake check (flakes only see tracked files).
- Nix style: nixfmt via treefmt; statix rejects "{ ... }:" module headers — use "_:"; deadnix must pass. The pre-commit hook IS the lint gate; run it early: cd ${REPO} && nix develop -c githooks/pre-commit
- Run a single check with: cd ${REPO} && nix build .#checks.x86_64-linux.<name> -L --no-link   (list names: nix develop -c bash -c 'nix flake show --json 2>/dev/null | jq -r ".checks.\\"x86_64-linux\\" | keys[]"'). VM checks take minutes; run them with a long timeout and wait.
- A new language lands WITH its formatter+linter in the same task (treefmt.toml + githooks/pre-commit + the flake's lint check).
- TDD: write/extend the failing check FIRST, show it red, then make it green. Tests must test real behavior (no tautologies).
- Tool availability: python3/jq are NOT on the default PATH; use nix develop -c for jq; grep is ugrep (use python for context greps).
- The plan is ${REPO}/${A.plan}${A.research ? '; evidence digest(s): ' + A.research : ''}. Read it before acting. Read the files you change in full first.
- Your final message is machine-read: return only the requested structured output.
`

// Implementers (and fix agents) append the single-writer worktree paragraph to
// the shared block: one branch named by the task key, never merge, never move
// another branch. Reviewers and the verifier keep RULES too — the git bans are
// harmless to a read-only role. extraRules, when set, are appended after that
// role paragraph so a caller's rule text stays the final word.
const RULES =
  RULES_BASE +
  `
- Work only in the isolated worktree you were started in (run \`git rev-parse --show-toplevel\` and report it) and in ${SCRATCH}. It is a linked worktree of ${REPO}, so it shares the object database and every branch. Create exactly ONE branch, named by your task key, and commit only there. NEVER merge, NEVER move or delete another branch, NEVER run git worktree/clone/push yourself, and NEVER write inside ${REPO}'s own checkout — a separate integrator merges your branch after your wave.
${A.extraRules || ''}`

// The orchestration roles (baseline, integrator, integfix, deliver) must
// perform the very git operations the implementer rules forbid — merging,
// moving the integration branch, and creating the fix branch. They keep every
// host-safety rule above and are permitted exactly those operations, nothing
// more.
const RULES_ORCH =
  RULES_BASE +
  `
- You are an orchestration agent, not an implementer. Do exactly the git operations your instructions below name and nothing more: checkout (including --detach and -B), merge (--no-ff / --ff-only / --abort as stated), and git branch -f to move the integration branch forward. NEVER push (this repo has no remote), NEVER delete a branch, NEVER run git worktree/clone, NEVER rebase/amend/rewrite history. Do not edit a tracked file except to resolve a merge conflict your instructions name, and commit nothing but that resolution or a file your instructions name.
${A.extraRules || ''}`

const IMPL_SCHEMA = {
  type: 'object',
  required: [
    'commit',
    'summary',
    'tests_run',
    'test_results',
    'deviations',
    'blocked',
    'workspace',
    'branch',
    'task_key',
    'round',
    'label',
  ],
  properties: {
    commit: { type: 'string', description: 'short SHA of the commit made, or empty if blocked' },
    summary: { type: 'string', description: 'what changed and why, 3-8 sentences' },
    tests_run: { type: 'array', items: { type: 'string' } },
    test_results: {
      type: 'string',
      description: 'red-then-green evidence: exact commands and the decisive output lines',
    },
    deviations: { type: 'string', description: 'any deviation from the task spec and why; empty if none' },
    blocked: { type: 'boolean' },
    blocked_reason: { type: 'string' },
    workspace: { type: 'string', description: 'the isolated worktree path the agent ran in' },
    branch: { type: 'string', description: 'the branch the agent created and committed to' },
    task_key: { type: 'string', description: 'the task key you were given, verbatim' },
    round: {
      type: 'integer',
      description: '0 for the implementer, n for fix round n; reviewers echo the round they reviewed',
    },
    label: { type: 'string', description: 'your spawn label, verbatim, as given in the prompt' },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['approved', 'findings', 'summary', 'task_key', 'round', 'label'],
  properties: {
    approved: { type: 'boolean', description: 'true only if there are no blocker/major findings' },
    task_key: { type: 'string', description: 'the task key you were given, verbatim' },
    round: {
      type: 'integer',
      description: '0 for the implementer, n for fix round n; reviewers echo the round they reviewed',
    },
    label: { type: 'string', description: 'your spawn label, verbatim, as given in the prompt' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'file', 'issue', 'fix'],
        properties: {
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          file: { type: 'string' },
          issue: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
    summary: { type: 'string' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['flake_check_green', 'toplevel_built', 'closure_diff', 'commits', 'verdict', 'notes', 'evidence_recorded'],
  properties: {
    flake_check_green: { type: 'boolean' },
    toplevel_built: { type: 'boolean' },
    closure_diff: { type: 'string', description: 'nix store diff-closures output, trimmed to the changed lines' },
    commits: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['pass', 'fail'] },
    notes: { type: 'string' },
    evidence_recorded: { type: 'boolean', description: 'true only if evidence record-check printed a JSON row' },
  },
}

let agents = 0
const spawn = (prompt, opts) => {
  agents += 1
  return agent(prompt, opts)
}

// skillLines: text injected into a prompt when args.skills.nixos is set (the
// nixos skill's install path); '' otherwise, so callers can always append it
// with no conditional at the call site. role is one of 'impl' | 'reviewCode'
// | 'reviewDocs' | 'verify'. Spec: docs/superpowers/specs/2026-09-03-nixos-skill-design.md §10.
function skillLines(role, task) {
  if (!A.skills || !A.skills.nixos) return ''
  const P = A.skills.nixos
  if (role === 'impl') {
    const refs =
      task && Array.isArray(task.skillRefs) && task.skillRefs.length
        ? `then these references: ${task.skillRefs.map((s) => `${P}/references/${s}.md`).join(', ')}.`
        : `then pick from the router's task → files table using this task's title and spec text.`
    return `\nSKILL: read ${P}/SKILL.md first, ${refs} Name the files you read in your report.`
  }
  if (role === 'reviewCode') {
    return `\nSKILL: read ${P}/references/review-checklist.md and ${P}/references/gotchas.md; apply the checklist in order.`
  }
  if (role === 'reviewDocs') {
    return `\nSKILL: read ${P}/references/nix-cli.md and ${P}/references/activation-and-switch.md before checking any command.`
  }
  if (role === 'verify') {
    return `\nSKILL: follow ${P}/references/verify.md.`
  }
  return ''
}

// ---- N10: deterministic dependency scheduler -------------------------------
// Decision: docs/decisions/2026-09-04-parallel-agent-workflows.md. Sequential
// execution is no longer the design; it is what the scheduler *chooses* when
// the graph or the file overlap says so. Everything here is a pure function of
// args.tasks: the same task list produces the same waves, the same groups and
// the same order on any machine (the cap is args.concurrency, NOT the host's
// CPU count, which the harness's own cap would otherwise leak into).
const KINDS = ['code', 'docs']
// t.key is interpolated verbatim into `git checkout -B ${t.key}`, so it must
// be a valid git branch name: alphanumerics plus . _ / -, no leading
// metacharacter, no whitespace or shell metacharacters. This is a shell/
// interpolation guard, not a full `git check-ref-format` check — git-invalid
// refs such as A..B, *.lock or a trailing / still pass here and are rejected
// by git itself later, surfacing in the agent's report rather than silently.
const KEY_RE = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/
const CONCURRENCY = Number.isInteger(A.concurrency) ? A.concurrency : 4
if (Number.isInteger(A.concurrency) && A.concurrency < 1) {
  // 0 or a negative integer would make the `i += CONCURRENCY` dispatch loop
  // never advance; refuse it here, before any agent is spawned.
  throw new Error(`dark-factory: args.concurrency must be an integer >= 1 (got ${A.concurrency})`)
}
const INT_BRANCH = A.integrationBranch || `factory/${A.prefix}-integration`
const USE_JUDGE = A.judge !== false

function validateGraph(tasks) {
  // Board rule A1 (docs/OPERATIONS.md): args.fixRounds is never raised above
  // 2 -- the "max two fix rounds" review budget is policy, not a knob. Refuse
  // it here, before any agent is dispatched, so a human typo can't silently
  // multiply review cost; the message names the cap for the caller.
  if (Number.isInteger(A.fixRounds) && A.fixRounds > 2) {
    throw new Error(`dark-factory: args.fixRounds must not exceed 2 (got ${A.fixRounds})`)
  }
  const keys = new Set()
  for (const t of tasks) {
    if (!t || typeof t.key !== 'string' || !t.key.trim())
      throw new Error('dark-factory: every task needs a non-empty key')
    if (!KEY_RE.test(t.key)) throw new Error(`dark-factory: task key ${t.key} is not a valid git branch name`)
    if (keys.has(t.key)) throw new Error(`dark-factory: duplicate task key ${t.key}`)
    keys.add(t.key)
    if (typeof t.title !== 'string' || !t.title.trim()) throw new Error(`dark-factory: task ${t.key} has no title`)
    if (typeof t.spec !== 'string' || !t.spec.trim()) throw new Error(`dark-factory: task ${t.key} has an empty spec`)
    if (t.kind !== undefined && !KINDS.includes(t.kind))
      throw new Error(`dark-factory: task ${t.key} has unknown kind ${t.kind}`)
    for (const f of ['dependsOn', 'touches', 'checks']) {
      if (t[f] !== undefined && !Array.isArray(t[f]))
        throw new Error(`dark-factory: task ${t.key} ${f} must be an array`)
    }
    // Board rule A1 / research-2026-09-05-paper-2609.01481.md §6 (P4 residue):
    // a code task (kind !== 'docs') must name at least one check — an unnamed
    // check is a silent degradation to the lint gate, so refuse it before any
    // agent is dispatched. Docs tasks keep their single-pass review and may
    // omit checks.
    if (t.kind !== 'docs' && (!Array.isArray(t.checks) || t.checks.length === 0)) {
      throw new Error(`dark-factory: task ${t.key} names no checks — a code task must name at least one check`)
    }
  }
  for (const t of tasks) {
    for (const d of t.dependsOn || []) {
      if (d === t.key) throw new Error(`dark-factory: task ${t.key} dependsOn itself`)
      if (!keys.has(d)) throw new Error(`dark-factory: task ${t.key} dependsOn unknown task ${d}`)
    }
  }
}

// Kahn's algorithm. Sorting the ready set makes the wave order reproducible.
function computeWaves(tasks) {
  const byKey = new Map(tasks.map((t) => [t.key, t]))
  const pending = new Set(tasks.map((t) => t.key))
  const done = new Set()
  const waves = []
  while (pending.size) {
    const ready = [...pending].filter((k) => (byKey.get(k).dependsOn || []).every((d) => done.has(d))).sort()
    if (!ready.length) throw new Error(`dark-factory: dependsOn cycle among ${[...pending].sort().join(', ')}`)
    waves.push(ready)
    for (const k of ready) {
      pending.delete(k)
      done.add(k)
    }
  }
  return waves
}

// Overlap is decided on the literal prefix of each `touches` entry (everything
// before the first glob metacharacter), compared at a path boundary. '*' is the
// "unknown, assume everything" sentinel an un-annotated task carries.
function literalPrefix(p) {
  const s = String(p).replace(/^\.\//, '')
  const i = s.search(/[*?[]/)
  return i === -1 ? s : s.slice(0, i)
}
function pathsOverlap(a, b) {
  const x = literalPrefix(a)
  const y = literalPrefix(b)
  const [s, l] = x.length <= y.length ? [x, y] : [y, x]
  if (s === '') return true
  return l === s || l.startsWith(s.endsWith('/') ? s : s + '/')
}
function effectiveTouches(t, judged) {
  if (Array.isArray(t.touches) && t.touches.length) return t.touches
  const j = judged.get(t.key)
  if (j && j.length) return j
  if (t.parallelSafe === true) return []
  return ['*']
}
function tasksOverlap(a, b, judged) {
  if (a.parallelSafe === false || b.parallelSafe === false) return true
  const ta = effectiveTouches(a, judged)
  const tb = effectiveTouches(b, judged)
  if (!ta.length || !tb.length) return false
  return ta.some((x) => tb.some((y) => pathsOverlap(x, y)))
}

// Connected components of the overlap graph: a component runs sequentially in
// key order, components run concurrently. Components, NOT graph colouring --
// colouring would pack non-conflicting tasks into one sequential lane, which is
// the opposite of what we want.
function groupWave(waveTasks, judged) {
  const ts = [...waveTasks].sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0))
  const parent = ts.map((_, i) => i)
  const find = (i) => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]]
      i = parent[i]
    }
    return i
  }
  for (let i = 0; i < ts.length; i++) {
    for (let j = i + 1; j < ts.length; j++) {
      if (tasksOverlap(ts[i], ts[j], judged)) {
        const a = find(i)
        const b = find(j)
        if (a !== b) parent[Math.max(a, b)] = Math.min(a, b)
      }
    }
  }
  const byRoot = new Map()
  ts.forEach((t, i) => {
    const r = find(i)
    if (!byRoot.has(r)) byRoot.set(r, [])
    byRoot.get(r).push(t)
  })
  return [...byRoot.keys()].sort((a, b) => a - b).map((r) => byRoot.get(r))
}

validateGraph(A.tasks)
const WAVES = computeWaves(A.tasks)

const judged = new Map()
const judgeRecords = []
const unannotated = A.tasks.filter((t) => !(Array.isArray(t.touches) && t.touches.length) && t.parallelSafe !== true)
if (USE_JUDGE && unannotated.length) {
  phase('Schedule')
  const answers = await parallel(
    unannotated.map(
      (t) => () =>
        spawn(
          `You are the parallel-safety judge for task ${t.key} ("${t.title}") of a dark-factory run in ${REPO}. The task carries no "touches" annotation, so the scheduler cannot tell whether it may run beside its siblings. Read ${REPO}/${A.plan} (this task's section) and the spec below, then answer ONLY with the repo-relative paths or globs this task will WRITE — not the ones it reads. Be generous: a missed path means two agents writing one file. Do not modify anything.
TASK SPEC: ${t.spec}`,
          {
            label: `judge:${t.key}`,
            phase: 'Schedule',
            model: M.reviewCode,
            effort: 'low',
            schema: {
              type: 'object',
              required: ['touches', 'reasoning'],
              properties: { touches: { type: 'array', items: { type: 'string' } }, reasoning: { type: 'string' } },
            },
          },
        ),
    ),
  )
  unannotated.forEach((t, i) => {
    const a = answers[i]
    if (!a || !Array.isArray(a.touches) || !a.touches.length) {
      log(`judge: ${t.key} gave no answer — serialising it`)
      return
    }
    judged.set(t.key, a.touches)
    judgeRecords.push({ key: t.key, touches: a.touches, reasoning: a.reasoning })
    // Recorded, printed and returned -- never silently applied.
    log(`judge: ${t.key} touches ${a.touches.join(', ')} — ${a.reasoning}`)
  })
}

const GROUPS = WAVES.map((w) =>
  groupWave(
    w.map((k) => A.tasks.find((t) => t.key === k)),
    judged,
  ),
)
log(
  `schedule: ${A.tasks.length} tasks, ${WAVES.length} wave(s), concurrency ${CONCURRENCY}, integration branch ${INT_BRANCH}`,
)
GROUPS.forEach((groups, i) => {
  log(`  wave ${i + 1}: ${groups.map((g) => g.map((t) => t.key).join('→')).join('  |  ')}`)
  for (const g of groups) if (g.length > 1) log(`    serialised: ${g.map((t) => t.key).join(', ')} (touches overlap)`)
})
const SCHEDULE = {
  waves: WAVES,
  groups: GROUPS.map((gs) => gs.map((g) => g.map((t) => t.key))),
  judged: judgeRecords,
  concurrency: CONCURRENCY,
}

phase('Baseline')
const baseline = await spawn(
  `You are the baseline agent of a dark-factory run in ${REPO}.
${RULES_ORCH}
Do, in order: 1) cd ${REPO}; confirm the working tree is clean (git status --porcelain is empty) and that ${A.plan} is tracked and committed — if not, git add it and commit it with subject "docs: plan — <plan title>" and the exact trailers${A.bootstrap ? ' (this repo is brand new and has no devShell yet: commit with plain git commit, and set lint_green=true without running any gate)' : ''}. 2) ${A.bootstrap ? 'Skip the lint gate (bootstrap run).' : 'Run the lint gate: nix develop -c githooks/pre-commit — it must exit 0.'} 3) Return HEAD (git rev-parse --short HEAD) and git log --oneline -2. 4) git branch -f ${INT_BRANCH} HEAD (do not check it out).`,
  {
    label: 'baseline',
    phase: 'Baseline',
    model: M.baseline,
    effort: 'low',
    schema: {
      type: 'object',
      required: ['head', 'lint_green', 'log'],
      properties: { head: { type: 'string' }, lint_green: { type: 'boolean' }, log: { type: 'string' } },
    },
  },
)
if (!baseline || !baseline.lint_green) throw new Error('dark-factory: baseline failed — ' + JSON.stringify(baseline))
log(`baseline ${baseline.head}, lint green`)

const INTEGRATE_SCHEMA = {
  type: 'object',
  required: ['merged', 'conflict', 'checks_green', 'head', 'output'],
  properties: {
    merged: { type: 'array', items: { type: 'string' } },
    conflict: { type: 'string', description: 'the branch whose merge conflicted, or empty' },
    checks_green: { type: 'boolean' },
    head: { type: 'string' },
    output: { type: 'string', description: 'the decisive conflict or check-failure lines, trimmed' },
  },
}
const integrations = []
const results = []
const statusOf = new Map()
const branchOf = new Map()

async function integrateWave(n, groups) {
  // Topological, then key, order: within a wave every task sits at the same
  // topological depth, so the merge order is the wave's keys sorted. The
  // groups themselves are key-sorted but concatenating them (groups.flat())
  // would interleave group membership into the order, so sort the flat list
  // by key first — that is the reproducible order this factory merges in.
  // Only approved tasks merge: a task that stayed unapproved through its fix
  // rounds (or never reported) must not ride along in its wave's merge.
  const flat = groups.flat().sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0))
  const withheld = flat.filter((t) => statusOf.get(t.key) !== 'approved').map((t) => t.key)
  const branches = flat
    .filter((t) => statusOf.get(t.key) === 'approved')
    .map((t) => branchOf.get(t.key))
    .filter(Boolean)
  if (withheld.length) log(`wave ${n}: withheld ${withheld.join(', ')} — not approved, excluded from the merge`)
  if (!branches.length) {
    log(`wave ${n}: nothing to integrate`)
    return
  }
  const checks = [...new Set(groups.flat().flatMap((t) => t.checks || []))].join(', ') || '(none named)'
  phase('Integrate')
  const merge = `In your worktree (it is a linked worktree of ${REPO}, so every task branch is already visible — this repo has no remote and nothing needs fetching): git checkout --detach ${INT_BRANCH} (detached, so ${INT_BRANCH} is never checked out anywhere and can be moved). Then merge these branches IN THIS EXACT ORDER, each with git merge --no-ff -m "factory: integrate <branch> (wave ${n})": ${branches.join(', ')}. If a merge conflicts, stop at that branch, run git merge --abort, and report it in "conflict" with the conflicting paths in "output". After all merges succeed, run these checks on the merged tree: ${checks}, each as nix build .#checks.x86_64-linux.<name> -L --no-link, then the lint gate nix develop -c githooks/pre-commit. Only if every one is green: git branch -f ${INT_BRANCH} HEAD, and report that SHA as "head".`
  let r = await spawn(
    `You are the wave-${n} integrator for a dark-factory run in ${REPO}. You do not write code; you merge and you check.
${RULES_ORCH}
${merge}`,
    {
      label: `integrate:w${n}`,
      phase: 'Integrate',
      model: M.verify,
      effort: 'medium',
      isolation: 'worktree',
      schema: INTEGRATE_SCHEMA,
    },
  )
  if (!r || r.conflict || !r.checks_green) {
    // Exactly ONE bounded fix, on the technical authority, mirroring the
    // existing retry-once rule. If it is still red the chain stops: no loop.
    log(`wave ${n}: integration ${r && r.conflict ? 'conflicted on ' + r.conflict : 'checks red'} — one bounded fix`)
    const fix = await spawn(
      `You are the integration fix agent for wave ${n} of a dark-factory run in ${REPO}. The wave's branches did not merge clean, or the merged tree is red. Fix it in ONE pass; there is no second attempt.
${RULES_ORCH}
Do: git checkout -B integfix-w${n} ${INT_BRANCH} in your worktree, then redo the merges in this order: ${branches.join(', ')}. Resolve conflicts by keeping BOTH sides' intent (read both commits with git show before deciding); never drop a task's change to make a merge easy. Then run ${checks} plus the lint gate. Only if every one is green: git branch -f ${INT_BRANCH} HEAD and report that SHA.
WHAT WENT WRONG: ${r && r.conflict ? 'conflict on branch ' + r.conflict : 'checks failed'}
OUTPUT: ${(r && r.output) || '(the integrator returned nothing)'}`,
      {
        label: `integfix:w${n}`,
        phase: 'Integrate',
        model: M.reviewCode,
        effort: 'high',
        isolation: 'worktree',
        schema: INTEGRATE_SCHEMA,
      },
    )
    if (!fix || fix.conflict || !fix.checks_green) {
      log(`wave ${n}: integration still red after one fix — this chain stops here`)
      for (const t of groups.flat()) if (statusOf.get(t.key) === 'approved') statusOf.set(t.key, 'integration-failed')
      integrations.push({ wave: n, ok: false, branches, output: (fix && fix.output) || (r && r.output) || '' })
      return
    }
    r = fix
  }
  integrations.push({ wave: n, ok: true, branches, head: r.head })
  log(`wave ${n} integrated into ${INT_BRANCH} at ${r.head}`)
}

// The single source of truth for a task's result record (the per-task shape
// returned in `tasks`). runTask fills in its live values; the unreported path
// builds the empty version from this same helper so the two can never drift.
function taskResult(t, overrides) {
  return Object.assign(
    {
      key: t.key,
      title: t.title,
      kind: t.kind === 'docs' ? 'docs' : 'code',
      status: 'unreported',
      commit: '',
      fixRounds: 0,
      review: null,
      impl: null,
      reviewNote: undefined,
      wave: 0,
      branch: undefined,
      workspace: undefined,
      blockedBy: [],
    },
    overrides,
  )
}

async function runTask(t, wave) {
  const kind = t.kind === 'docs' ? 'docs' : 'code'
  const checks = (t.checks || []).join(', ') || '(none named — the lint gate still applies)'
  // The implementer prompt names this task's checks. A single-element list of
  // the literal word "none" must not render as the bare "none": that is
  // byte-identical to the empty-case sentence and hides the fact that "none"
  // is itself a (nonexistent) check name the integrator will fail on. Print
  // the array literally (["none"]) instead; the reviewer/fix prompts keep the
  // joined `${checks}` form because those are the names handed to
  // `nix build .#checks.x86_64-linux.<name>`.
  const checksLiteral = t.checks && t.checks.length ? JSON.stringify(t.checks) : checks
  let impl = await spawn(
    `You are the implementer for task ${t.key} (${t.title}) of a dark-factory run in ${REPO}. A separate reviewer checks your commit afterwards, so be precise and honest.
${RULES}
WORKSPACE: run \`git checkout -B ${t.key} ${INT_BRANCH}\` first — that puts you on your own branch at the integration branch's current tip, which already contains every dependency's merged work. Report the worktree path in \`workspace\` and the branch in \`branch\`.
TASK SPEC: ${t.spec}${skillLines('impl', t)}
Named checks for this task: ${checksLiteral}.
Process: read the plan; read every file you will touch in full; write the failing test first and run it (show red); implement; run the named checks (show green); run the lint gate; git add; commit with the exact convention. If something in the spec is impossible or wrong, do the rest, do NOT invent a workaround that violates the hard rules, and report it in deviations/blocked. Set task_key to "${t.key}", round to 0 and label to "impl:${t.key}" in your output.`,
    {
      label: `impl:${t.key}`,
      phase: 'Implement',
      model: M.impl,
      effort: 'high',
      schema: IMPL_SCHEMA,
      isolation: 'worktree',
    },
  )

  let review = null
  let rounds = 0
  // reviewErrored: the review agent returned null twice in a row (initial
  // spawn + one retry) — an infrastructure failure, not a rejection. The
  // task must never read as "approved" when this happens (defect found
  // 2026-09-03: four Opus reviews died with API 529 and were logged
  // "approved" because `review` was null and the old blocking-findings
  // filter treated null the same as "no findings").
  let reviewErrored = false
  const maxRounds = kind === 'docs' ? 1 : FIX_ROUNDS
  for (let round = 0; round <= maxRounds; round++) {
    if (!impl || impl.blocked) break
    const reviewPrompt =
      kind === 'docs'
        ? `You are the single-pass reviewer for docs task ${t.key} (${t.title}) in ${REPO}. Check ONLY: every command in the changed docs actually exists and runs from the stated directory (dry-run what is safe, e.g. --help); paths referenced exist in the tree; the text matches what the code does; no secrets. Style, tone and commit-subject nits are 'minor' and never block. Do: git checkout --detach ${impl.branch}; git show ${impl.commit || 'HEAD'}. Do not modify files. Set task_key to "${t.key}", round to ${round} and label to "review:${t.key}:r${round + 1}" in your output.${skillLines('reviewDocs', t)}`
        : `You are the adversarial review gate for task ${t.key} (${t.title}) in ${REPO}. Assume the implementer got something wrong and try to prove it.
Do: git checkout --detach ${impl.branch}; git show ${impl.commit || 'HEAD'} (full diff); read the touched files in full at HEAD. Independently RE-RUN the named checks (${checks}) with nix build .#checks.x86_64-linux.<name> -L --no-link and the lint gate (nix develop -c githooks/pre-commit). Verify: every spec item done; tests are real (reason from the test code whether it would fail without the change); no hard-rule violation (no bypass flags, no sudo/switch/service starts, commit trailers exact, Nix style); no regression in existing checks; comments state WHY. Severity: blocker = wrong/unsafe/violates rules or a named check is red; major = spec item missing or test tautological; minor = style/comment. approved=true only with zero blocker/major findings. Do not modify files.
${RULES}
TASK SPEC: ${t.spec}${skillLines('reviewCode', t)}
Set task_key to "${t.key}", round to ${round} and label to "review:${t.key}:r${round + 1}" in your output.`
    const reviewOpts = {
      label: `review:${t.key}:r${round + 1}`,
      phase: 'Review',
      model: kind === 'docs' ? M.reviewDocs : M.reviewCode,
      effort: kind === 'docs' ? 'medium' : 'high',
      schema: REVIEW_SCHEMA,
      isolation: 'worktree',
    }
    review = await spawn(reviewPrompt, reviewOpts)
    if (!review) {
      log(`${t.key}: review agent returned no result — retrying once`)
      review = await spawn(reviewPrompt, { ...reviewOpts, label: `${reviewOpts.label}:retry` })
    }
    if (!review) {
      reviewErrored = true
      break
    }
    const blocking = (review.findings || []).filter(
      (f) => f.severity === 'blocker' || (kind === 'code' && f.severity === 'major'),
    )
    if ((review.approved && blocking.length === 0) || blocking.length === 0) break
    if (round === maxRounds) {
      log(`${t.key}: review still not approved after ${maxRounds} fix round(s) — reporting blocked`)
      break
    }
    rounds += 1
    impl = await spawn(
      `You are the fix agent for task ${t.key} (${t.title}) in ${REPO}. The review gate rejected the previous commit with these findings (fix every blocker/major; minors only if trivial):
${JSON.stringify(blocking, null, 2)}
WORKSPACE: run \`git checkout -B ${t.key}-fix${round + 1} ${impl.branch}\` first — that branches a fix from the branch the implementer reported; a fix branch is a descendant, so the integrator merging it subsumes the original. Report the worktree path in \`workspace\` and the branch in \`branch\`.
Fix in a NEW commit on top (do not amend, do not rewrite history), subject "${A.prefix}: address review — ${t.title} (test: ...)" with the WHY in the body and the exact trailers. Re-run the named checks (${checks}) + lint gate. Report the new commit SHA. Set task_key to "${t.key}", round to ${round + 1} and label to "fix:${t.key}:r${round + 1}" in your output.
${RULES}
TASK SPEC: ${t.spec}${skillLines('impl', t)}`,
      {
        label: `fix:${t.key}:r${round + 1}`,
        phase: 'Implement',
        model: M.impl,
        effort: 'high',
        schema: IMPL_SCHEMA,
        isolation: 'worktree',
      },
    )
  }
  const blocking = ((review && review.findings) || []).filter(
    (f) => f.severity === 'blocker' || (kind === 'code' && f.severity === 'major'),
  )
  const status = !impl
    ? 'no-result'
    : impl.blocked
      ? 'blocked'
      : reviewErrored
        ? 'unreviewed'
        : blocking.length
          ? 'unapproved'
          : 'approved'
  // F32: a reviewer that returns approved=false but cites no blocker/major
  // finding is a mismatch worth a human's attention (status still derives
  // only from blocking findings, per policy -- this does not change it).
  let reviewNote
  if (review && review.approved === false && blocking.length === 0) {
    reviewNote = 'reviewer returned approved=false without blocking findings'
    log(`${t.key}: WARNING — ${reviewNote}`)
  }
  const r = taskResult(t, {
    status,
    commit: impl && impl.commit,
    fixRounds: rounds,
    review,
    impl,
    reviewNote,
    wave,
    branch: impl && impl.branch,
    workspace: impl && impl.workspace,
  })
  log(`${t.key} ${status} (${rounds} fix round(s)) ${impl && impl.commit ? impl.commit : ''}`)
  return r
}

for (let w = 0; w < GROUPS.length; w++) {
  phase('Implement')
  const groups = GROUPS[w]
  // Chunking by CONCURRENCY is a barrier per chunk: simple, deterministic, and
  // the harness caps concurrent agents anyway (min(16, CPUs-2)). A group runs
  // sequentially inside itself because its members write the same paths.
  for (let i = 0; i < groups.length; i += CONCURRENCY) {
    const slice = groups.slice(i, i + CONCURRENCY)
    const done = await parallel(
      slice.map((g) => async () => {
        const out = []
        for (const t of g) {
          const failed = (t.dependsOn || []).filter((d) => statusOf.get(d) !== 'approved')
          if (failed.length) {
            log(`${t.key} blocked — dependency ${failed.join(', ')} did not finish green`)
            out.push({
              key: t.key,
              title: t.title,
              kind: t.kind === 'docs' ? 'docs' : 'code',
              status: 'blocked',
              wave: w + 1,
              blockedBy: failed,
            })
          } else {
            out.push(await runTask(t, w + 1))
          }
        }
        return out
      }),
    )
    // parallel() swallows a thrown thunk to null; runTask never throws, so a
    // null here is an infrastructure failure and must not vanish.
    done.forEach((rs, k) => {
      if (!rs) {
        log(`wave ${w + 1}: a task group returned null — ${slice[k].map((t) => t.key).join(',')} unreported`)
        for (const t of slice[k]) {
          const r = taskResult(t, { wave: w + 1 })
          results.push(r)
          statusOf.set(r.key, r.status)
        }
        return
      }
      for (const r of rs) {
        results.push(r)
        statusOf.set(r.key, r.status)
        if (r.branch) branchOf.set(r.key, r.branch)
      }
    })
  }
  await integrateWave(w + 1, GROUPS[w])
}

phase('Verify')
let verify
if (integrations.some((i) => i.ok)) {
  verify = await spawn(
    `You are the whole-run verifier for a dark-factory run in ${REPO}. Nothing you do may change the live system.
${RULES}
Do, in order: 0) git checkout --detach ${INT_BRANCH}. 1) git log --oneline ${baseline.head}..HEAD. 2) nix flake check -L (full; wait for VM checks). ${HOST ? `3) nix build .#nixosConfigurations.${HOST}.config.system.build.toplevel -o ${SCRATCH}/result-toplevel. 4) nix store diff-closures /run/current-system ${SCRATCH}/result-toplevel — report only changed lines. 5) verdict = pass only if flake check is green and the toplevel builds; list anything in the closure diff that the plan does not explain.` : `3) This repo has no nixosConfigurations: set toplevel_built=true and closure_diff="n/a (library flake)". 4) verdict = pass only if flake check is green.`} 6) Record the observation so Helm and the board can reuse it: cd ${REPO} && nix develop -c python3 pkgs/evidence/evidence.py record-check --name flake-check --rev $(git rev-parse HEAD) --ok --class nix-check --src dark-factory-verify --duration <seconds the flake check took> (use --fail instead of --ok when the flake check was red). If the store directory does not exist yet (pre-switch), report evidence_recorded=false and say so in notes — that is NOT a verify failure. evidence_recorded = true only if that printed a JSON row.${skillLines('verify', null)}`,
    {
      label: 'verify',
      phase: 'Verify',
      model: M.verify,
      effort: 'medium',
      isolation: 'worktree',
      schema: VERIFY_SCHEMA,
    },
  )
} else {
  verify = { verdict: 'skipped', skipped: true }
  log('verify=skipped — nothing was integrated, so there is no merged tree to verify')
}

const allOk =
  integrations.every((i) => i.ok) && results.length === A.tasks.length && results.every((r) => r.status === 'approved')
let delivered = false
if (verify && verify.verdict === 'pass' && allOk) {
  phase('Deliver')
  const d = await spawn(
    `You are the delivery agent for a dark-factory run in ${REPO}. Every task is approved, every wave integrated, and the whole-run verify passed on ${INT_BRANCH}.
${RULES_ORCH}
Do exactly this and nothing else: cd ${REPO}; git status --porcelain must be empty (if it is not, STOP and report ok=false with the output); git merge --ff-only ${INT_BRANCH}; git log --oneline -1. Report ok and the new HEAD. Do not delete any branch or worktree — the operator reads them for the post-mortem.`,
    {
      label: 'deliver',
      phase: 'Deliver',
      model: M.verify,
      effort: 'low',
      schema: {
        type: 'object',
        required: ['ok', 'head'],
        properties: { ok: { type: 'boolean' }, head: { type: 'string' } },
      },
    },
  )
  delivered = !!(d && d.ok)
  log(
    delivered
      ? `delivered: ${INT_BRANCH} fast-forwarded into the current branch at ${d.head}`
      : `NOT delivered — ${INT_BRANCH} is left for the operator`,
  )
} else {
  // The summary reads statusOf, not results[].status: the integration-failure
  // downgrade above writes only statusOf, so a task that was approved and then
  // failed to integrate would otherwise read as plain "approved" here and the
  // line would misstate the reason (e.g. "no tasks approved" on the commonest
  // failure path). Name every non-approved task with its status; when nothing
  // is non-approved the only remaining failure is a verify that did not pass.
  const nonApproved = A.tasks
    .map((t) => ({ key: t.key, status: statusOf.get(t.key) || 'unreported' }))
    .filter((t) => t.status !== 'approved')
    .map((t) => `${t.key} (${t.status})`)
    .sort()
  const reason = nonApproved.length ? nonApproved.join(', ') : 'verify failed'
  log(
    `NOT delivered — ${reason}; ${INT_BRANCH} holds the work (fast-forward by hand: cd ${REPO} && git merge --ff-only ${INT_BRANCH})`,
  )
}

let audit = null
if (A.invariantAudit) {
  phase('Invariant audit')
  audit = await spawn(
    `You are the invariant auditor for a dark-factory run in ${REPO}. Read docs/brief.md §3 (the six non-negotiable invariants) and the commit list ${baseline.head}..HEAD (git log --stat, and git show for any commit touching nixosModules/, pkgs/basket, pkgs/broker, hosts/). Judge ONLY whether any change could weaken an invariant (data classification routing, egress chokepoint, no secrets in repo, declarative-only, basket encryption, build-time assertions). Return: { ok: boolean, concerns: [{invariant, commit, why}], summary }. Do not modify files.`,
    {
      label: 'invariant-audit',
      phase: 'Invariant audit',
      model: M.audit,
      effort: 'high',
      schema: {
        type: 'object',
        required: ['ok', 'concerns', 'summary'],
        properties: {
          ok: { type: 'boolean' },
          concerns: { type: 'array', items: { type: 'object' } },
          summary: { type: 'string' },
        },
      },
    },
  )
}

const spent = budget.spent()
// E3: persist the run report (the paper's evidence bundle crossing the loop
// boundary). The Workflow sandbox has no filesystem, so one cheap agent
// writes the JSON and appends it to the store.
const report = {
  kind: 'factory-run',
  run_id: A.runId || null,
  plan: A.plan,
  prefix: A.prefix,
  baseline: baseline.head,
  integration_branch: INT_BRANCH,
  tasks: results.map((r) => ({
    key: r.key,
    status: statusOf.get(r.key),
    commit: r.commit || null,
    fixRounds: r.fixRounds,
  })),
  verify: verify ? verify.verdict : 'none',
  delivered,
  agents,
  output_tokens: spent,
}
const reportJson = JSON.stringify(report)
const rec = await spawn(
  `You are the recorder for a dark-factory run in ${REPO}. Do exactly this: write the following JSON verbatim to ${SCRATCH}/run-report.json, then run: cd ${REPO} && nix develop -c python3 pkgs/evidence/evidence.py record runs --json "$(cat ${SCRATCH}/run-report.json)". Report ok=true and the ts the command printed; if the store directory does not exist yet, report ok=false with the error (the orchestrator records it after the switch).
JSON: ${reportJson}`,
  {
    label: 'recorder',
    phase: 'Deliver',
    model: M.verify,
    effort: 'low',
    schema: { type: 'object', required: ['ok', 'ts'], properties: { ok: { type: 'boolean' }, ts: { type: 'string' } } },
  },
)
const recorded = !!(rec && rec.ok)
if (!recorded)
  log('run report NOT recorded — append it by hand: evidence record runs --json <the JSON in the transcript>')
const unreviewed = results.filter((r) => r.status === 'unreviewed').map((r) => r.key)
log(
  `factory closed: ${agents} agents, ~${Math.round(spent / 1000)}k output tokens, verify=${verify ? verify.verdict : 'none'}, unreviewed=${unreviewed.length ? unreviewed.join(',') : 'none'}`,
)
return {
  baseline: baseline.head,
  tasks: results.map((r) => ({
    key: r.key,
    status: statusOf.get(r.key),
    commit: r.commit,
    fixRounds: r.fixRounds,
    deviations: r.impl && r.impl.deviations,
    blocked_reason: r.impl && r.impl.blocked_reason,
    findings: r.review && r.review.findings,
    reviewNote: r.reviewNote,
    wave: r.wave,
    branch: r.branch,
    workspace: r.workspace,
    blockedBy: r.blockedBy,
  })),
  unreviewed,
  verify,
  audit,
  schedule: SCHEDULE,
  integrationBranch: INT_BRANCH,
  integrations,
  delivered,
  recorded,
  economics: { agents, outputTokens: spent },
}
