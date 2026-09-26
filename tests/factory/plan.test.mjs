// Loads the real .claude/workflows/plan.js text (a Workflow script, so it has
// no import support), strips the `export const meta = {...}` literal, wraps the
// remainder as the body of an async IIFE via `new Function`, and runs it with
// stub globals standing in for the Workflow harness (agent, parallel, pipeline,
// phase, log, workflow, budget, args). The agent stub answers from
// fixtures/plan-judgements.json keyed by the opts.label prefix. Nothing here is
// a framework: node's assert/strict, one t() group per assertion the plan names,
// and a count of failures at the end (so a single red run shows every gap).
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.join(__dirname, '..', '..')
const scriptPath = path.join(repoRoot, '.claude', 'workflows', 'plan.js')
const fixturePath = path.join(__dirname, 'fixtures', 'plan-judgements.json')
const rubricPath = path.join(repoRoot, 'tools', 'factory', 'plan', 'rubric.md')
const judgementsPy = path.join(repoRoot, 'pkgs', 'evidence', 'judgements.py')

const src = fs.readFileSync(scriptPath, 'utf8')
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'))

// Strip the leading `export const meta = { ... }` literal the same way
// render.test.mjs does: from the line starting `export const meta` to the
// first line that is EXACTLY "}". Returns the body and the meta object text.
function splitScript(text) {
  const lines = text.split('\n')
  const startIdx = lines.findIndex((l) => l.startsWith('export const meta'))
  if (startIdx === -1) {
    throw new Error('plan.test.mjs: could not find "export const meta" in plan.js')
  }
  let endIdx = -1
  for (let i = startIdx; i < lines.length; i++) {
    if (lines[i] === '}') {
      endIdx = i
      break
    }
  }
  if (endIdx === -1) {
    throw new Error('plan.test.mjs: could not find the closing "}" of the meta literal')
  }
  const metaText = lines.slice(startIdx, endIdx + 1).join('\n')
  const objText = metaText.replace(/^export const meta = /, '')
  const body = lines
    .slice(0, startIdx)
    .concat(lines.slice(endIdx + 1))
    .join('\n')
  return { body, metaText, objText }
}

const { body, metaText, objText } = splitScript(src)

function makeRunner(bodyText) {
  return new Function(
    'agent',
    'parallel',
    'pipeline',
    'phase',
    'log',
    'workflow',
    'budget',
    'args',
    `return (async () => {\n${bodyText}\n})()`,
  )
}

const runScript = makeRunner(body)

const all = (v) => Array(14).fill(v)
const all0 = all(0)
const all2 = all(2)
const all3 = all(3)

// The base non-judgeOnly invocation args. `scratch` is only ever interpolated
// into prompts by plan.js (the stub agents never write), so a constant path is
// fine; test 13 proves the script never touches the filesystem.
const baseArgs = {
  spec: 'docs/superpowers/specs/2026-09-05-planning-agent-design.md',
  out: '2026-09-06-test.md',
  name: 'test',
  date: '2026-09-06',
  scratch: '/tmp/plan-test/scratch',
}

function baseKey(label) {
  if (label.startsWith('read-')) return label
  const judge = label.match(/^(judge-(?:implementer|reviewer|whole))/)
  if (judge) return judge[1]
  if (label.startsWith('revise-')) return 'revise'
  return label // draft, ship
}

function makeStubs(override) {
  const calls = []
  const agent = async (prompt, opts) => {
    const label = (opts && opts.label) || ''
    calls.push({ prompt, opts })
    if (override) {
      const v = override(label, calls)
      if (v !== undefined) return v
    }
    const key = baseKey(label)
    if (!(key in fixture)) {
      throw new Error(`plan.test.mjs: no fixture answer for label "${label}" (key "${key}")`)
    }
    return fixture[key]
  }
  agent.calls = calls
  const logs = []
  const phases = []
  const stubs = {
    agent,
    parallel: async (fns) => Promise.all(fns.map((f) => f())),
    pipeline: async () => [],
    phase: (t) => phases.push(t),
    log: (m) => logs.push(m),
    workflow: {},
    budget: { spent: () => 0 },
    logs,
    phases,
  }
  return stubs
}

async function run(args, override) {
  const stubs = makeStubs(override)
  const result = await runScript(
    stubs.agent,
    stubs.parallel,
    stubs.pipeline,
    stubs.phase,
    stubs.log,
    stubs.workflow,
    stubs.budget,
    args,
  )
  return { result, stubs }
}

// A rejected run; asserts the rejection carries `fragment` and returns the
// stubs so a caller can inspect which agents ran before the throw.
async function runReject(args, override, fragment) {
  const stubs = makeStubs(override)
  try {
    await runScript(
      stubs.agent,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.log,
      stubs.workflow,
      stubs.budget,
      args,
    )
  } catch (err) {
    assert.ok(
      typeof (err && err.message) === 'string' && err.message.includes(fragment),
      `expected a rejection containing "${fragment}", got: ${err && err.message}`,
    )
    return stubs
  }
  throw new Error(`expected a rejection containing "${fragment}", but the run resolved`)
}

function judgeOverride(map) {
  return (label) => {
    let lens = null
    if (label.startsWith('judge-implementer')) lens = 'implementer'
    else if (label.startsWith('judge-reviewer')) lens = 'reviewer'
    else if (label.startsWith('judge-whole')) lens = 'whole'
    if (!lens) return undefined
    const v = map[lens]
    if (v === null || v === undefined) return null
    return { scores: v, errata: [], dispatchable: true }
  }
}

function shipPrompt(stubs) {
  const call = stubs.agent.calls.find((c) => c.opts && c.opts.label === 'ship')
  assert.ok(call, 'the ship agent ran')
  return call.prompt
}

const tests = []

function t(name, fn) {
  tests.push({ name, fn })
}

const replay = (name) => (label) => {
  // replan target reader: two typed headings in the prior plan.
  if (label === 'read-target') {
    return {
      part: 'target',
      path: 'scratch/packet/target.md',
      digest: 'replan target',
      missing: [],
      checkEmpty: null,
      headings: ['### A1 (code, S) — a', '### A2 (code, S) — b'],
    }
  }
  if (label === 'draft' || label.startsWith('revise-')) {
    return {
      path: 'scratch/draft-0.md',
      words: 100,
      tasks: [],
      questions: [],
      selfScore: all3,
      headings: name, // the draft's headings for this scenario
    }
  }
  return undefined
}

t('(1) the text parses in the harness shape', () => {
  const wrapped = `async function __plan_check() {\n${body}\n}\n`
  const dir = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'plan-check-'))
  const f = path.join(dir, 'plan-check.js')
  fs.writeFileSync(f, wrapped)
  try {
    execFileSync(process.execPath, ['--check', f], { stdio: 'pipe' })
  } finally {
    fs.rmSync(dir, { recursive: true, force: true })
  }
})

t('(2) meta is a pure literal; every agent() carries model and effort', () => {
  assert.ok(!/\w\(/.test(metaText), 'meta must not call anything (no identifier-followed-by-paren)')
  assert.ok(!/Date|Math|require|import/.test(metaText), 'meta must be a pure literal')
  assert.ok(!metaText.includes('`'), 'meta must have no template literal')
  const meta = new Function(`return ${objText}`)()
  assert.equal(meta.name, 'plan')
  assert.equal(meta.phases.length, 5, 'five phases')
  for (const ph of meta.phases) {
    assert.ok(ph.model, `phase ${ph.title} names a model`)
  }
  // change (4): every agent() call site must name model: and effort:. Splitting
  // on "agent(" isolates each call's remainder; each must contain both keys.
  const parts = body.split('agent(')
  assert.equal(parts.length, 7, 'expected 6 agent() call sites')
  for (let i = 1; i < parts.length; i++) {
    assert.ok(parts[i].includes('model:'), `agent() call ${i} must carry model:`)
    assert.ok(parts[i].includes('effort:'), `agent() call ${i} must carry effort:`)
  }
})

t('(3) medians: [3,3,0] per row totals 42 and passes', async () => {
  const { result } = await run(baseArgs, judgeOverride({ implementer: all3, reviewer: all3, whole: all0 }))
  assert.equal(result.total, 42, 'median of [3,3,0] is 3 on every row')
  assert.equal(result.decision, 'dispatch', '42/42 with the floor met dispatches')
})

t('(4) the six-row floor gates a passing total', async () => {
  // median total 35, criterion #5 (0-based 4, a floor row) at 1.
  const floorFail = [3, 3, 3, 3, 1, 3, 3, 3, 3, 3, 3, 2, 1, 1]
  const { result: a } = await run(
    baseArgs,
    judgeOverride({ implementer: floorFail, reviewer: floorFail, whole: floorFail }),
  )
  assert.equal(a.floorOk, false, 'a floor row below 2 fails the floor')
  assert.notEqual(a.decision, 'dispatch', 'a floor failure never dispatches')

  // same total with criterion #1 (0-based 0, not a floor row) at 1.
  const floorOk = [1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 1, 3, 1]
  const { result: b } = await run(baseArgs, judgeOverride({ implementer: floorOk, reviewer: floorOk, whole: floorOk }))
  assert.equal(b.floorOk, true, 'total 35 with the floor met passes the floor')
  assert.equal(b.decision, 'dispatch', 'the discriminating pair dispatches')
})

t('(5) judgeOnly skips the readers and the drafter', async () => {
  const args = {
    spec: baseArgs.spec,
    name: baseArgs.name,
    date: baseArgs.date,
    scratch: baseArgs.scratch,
    judgeOnly: true,
    draft: 'docs/superpowers/plans/existing.md',
  }
  const { stubs } = await run(args)
  const labels = stubs.agent.calls.map((c) => c.opts.label)
  assert.ok(
    !labels.some((l) => l.startsWith('read-') || l === 'draft'),
    'no reader or drafter agent runs in judgeOnly mode',
  )
})

t('(6) the mechanical checkEmpty gate and the partial-packet refusal', async () => {
  const notSound = (label) => {
    if (label === 'read-mechanical') {
      return {
        part: 'mechanical',
        path: 'scratch/packet/mechanical.md',
        digest: 'graph prints something',
        missing: [],
        checkEmpty: false,
      }
    }
    return undefined
  }
  const stubs = await runReject(baseArgs, notSound, 'not sound')
  assert.ok(!stubs.agent.calls.some((c) => c.opts.label === 'draft'), 'no drafter runs while the graph is unsound')

  const silentReader = (label) => (label === 'read-field' ? null : undefined)
  await runReject(baseArgs, silentReader, 'partial packet')
})

t('(7) a silent lens shortens the panel and never dispatches', async () => {
  const { result, stubs } = await run(baseArgs, judgeOverride({ implementer: all3, reviewer: null, whole: all3 }))
  assert.equal(result.decision, 'panel-short')
  assert.deepEqual(result.judges, ['sonnet', 'opus'])
  assert.deepEqual(result.judgesDropped, ['reviewer'])
  assert.equal(
    stubs.agent.calls.filter((c) => c.opts.label.includes('-retry')).length,
    1,
    'exactly one re-ask for the silent lens',
  )
  const prompt = shipPrompt(stubs)
  assert.ok(prompt.includes('Do not write under docs/superpowers/plans'))
  assert.ok(!prompt.includes('Copy the draft'), 'no plan-write instruction on a short panel')
})

t('(8) the replan guard refuses a dropped or renamed heading', async () => {
  const replanArgs = {
    ...baseArgs,
    replan: 'docs/superpowers/plans/2026-09-05-original.md',
    rejection: 'docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md',
  }

  // the drafter returns only the first heading: the second is dropped.
  const stubs = await runReject(
    replanArgs,
    replay(['### A1 (code, S) — a']),
    'replan drops heading: ### A2 (code, S) — b',
  )
  assert.ok(
    !stubs.agent.calls.some((c) => c.opts.label.startsWith('judge-')),
    'no judge runs on a draft that lost a heading',
  )

  // same count but a renamed second heading: membership, not length, catches it.
  await runReject(
    replanArgs,
    replay(['### A1 (code, S) — a', '### A2 (code, S) — renamed']),
    'replan drops heading: ### A2 (code, S) — b',
  )

  // both headings intact: the judges run, no throw.
  const { result, stubs: okStubs } = await run(replanArgs, replay(['### A1 (code, S) — a', '### A2 (code, S) — b']))
  assert.ok(
    okStubs.agent.calls.some((c) => c.opts.label.startsWith('judge-')),
    'the judges run on an intact replan draft',
  )
  assert.ok('decision' in result)
})

t('(9) args validation refuses the four bad shapes', async () => {
  await runReject({ ...baseArgs, date: undefined }, undefined, 'args need date, name, scratch, spec')
  await runReject(
    { spec: baseArgs.spec, name: baseArgs.name, date: baseArgs.date, scratch: baseArgs.scratch, judgeOnly: true },
    undefined,
    'judgeOnly needs args.draft',
  )
  await runReject(
    {
      ...baseArgs,
      judgeOnly: true,
      draft: 'docs/superpowers/plans/existing.md',
      replan: 'docs/superpowers/plans/2026-09-05-original.md',
      rejection: 'docs/reviews/r.md',
    },
    undefined,
    'replan and judgeOnly are exclusive',
  )
  await runReject(
    { spec: baseArgs.spec, name: baseArgs.name, date: baseArgs.date, scratch: baseArgs.scratch },
    undefined,
    'args.out names the plan file to write',
  )
})

t('(10) a never-passing panel stops after exactly two revisions', async () => {
  const { result, stubs } = await run(baseArgs, judgeOverride({ implementer: all2, reviewer: all2, whole: all2 }))
  assert.equal(result.decision, 'revise-exhausted')
  assert.equal(
    stubs.agent.calls.filter((c) => c.opts.label.startsWith('revise-')).length,
    2,
    'exactly two revise- agents ran',
  )
})

t('(11) the ship prompt names the plan, judgement and RECORD_FIELDS', async () => {
  const recordMatch = body.match(/const RECORD_FIELDS = \[([^\]]*)\]/)
  assert.ok(recordMatch, 'RECORD_FIELDS is not defined in plan.js')
  const recordFields = recordMatch[1].match(/'([^']*)'/g).map((s) => s.slice(1, -1))

  const allowList = execFileSync('python3', [judgementsPy, '--fields'], { encoding: 'utf8' }).trim().split('\n')
  assert.deepEqual(recordFields, allowList, 'RECORD_FIELDS equals judgements.py --fields')

  const { stubs } = await run(baseArgs)
  const prompt = shipPrompt(stubs)
  assert.ok(prompt.includes('docs/superpowers/plans/2026-09-06-test.md'))
  assert.ok(prompt.includes('docs/reviews/plan-judgements/2026-09-06-test.md'))
  for (const name of recordFields) {
    assert.ok(prompt.includes(name), `the ship prompt lists ${name}`)
  }
})

t('(12) the rubric.md rows equal CRITERIA in order', () => {
  const criteriaMatch = body.match(/const CRITERIA = \[([^\]]*)\]/)
  assert.ok(criteriaMatch, 'CRITERIA is not defined in plan.js')
  const criteria = criteriaMatch[1].match(/'([^']*)'/g).map((s) => s.slice(1, -1))
  assert.equal(criteria.length, 14, 'CRITERIA has 14 rows')

  const rubric = fs.readFileSync(rubricPath, 'utf8')
  const rowNames = []
  for (const line of rubric.split('\n')) {
    const m = line.match(/^\|\s*\d+\s*\|\s*([^|]+?)\s*\|/)
    if (m) rowNames.push(m[1].trim())
  }
  assert.equal(rowNames.length, 14, 'rubric.md has a 14-row table')

  // The rubric table renders the connective differently (";"/"," vs "and"),
  // so compare the significant words ignoring the connector "and" and case.
  const norm = (s) =>
    s
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((w) => w && w !== 'and')
      .join(' ')
  rowNames.forEach((name, i) => {
    assert.equal(norm(name), norm(criteria[i]), `rubric row ${i + 1} matches CRITERIA[${i}]`)
  })
})

t('(13) the script never touches the filesystem and never writes the plan unless it dispatches', async () => {
  const dir = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'plan-run-'))
  const cwd = process.cwd()
  try {
    process.chdir(dir)
    const { stubs } = await run(baseArgs, judgeOverride({ implementer: all0, reviewer: all0, whole: all0 }))
    assert.deepEqual(fs.readdirSync(dir), [], 'no file was written')
    for (const call of stubs.agent.calls) {
      assert.ok(
        !call.prompt.includes('Copy the draft verbatim to'),
        'a non-dispatch prompt must not instruct writing the plan',
      )
    }
  } finally {
    process.chdir(cwd)
    fs.rmSync(dir, { recursive: true, force: true })
  }
})

async function main() {
  let failures = 0
  for (const { name, fn } of tests) {
    try {
      await fn()
      console.log(`ok - ${name}`)
    } catch (err) {
      failures++
      console.error(`FAIL - ${name}`)
      console.error(err && err.message ? err.message : err)
    }
  }
  if (failures) {
    console.error(`plan.test.mjs: ${failures} assertion group(s) failed`)
    process.exit(1)
  }
  console.log('plan.test.mjs: all assertions passed')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
