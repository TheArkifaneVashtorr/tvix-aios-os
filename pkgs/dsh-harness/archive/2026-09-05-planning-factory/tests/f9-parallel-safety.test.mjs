import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// F9: parallel-safety annotations. Each task carries `touches` (paths/globs it will
// WRITE) and/or `parallelSafe`. Inside each wave the scheduler partitions tasks into
// serial lanes by CONNECTED COMPONENT of the touches-overlap graph (not colouring:
// colouring would run conflicting tasks in parallel and pack non-conflicting ones
// into one lane — backwards). A task with no `touches` and no `parallelSafe: true` is
// sent to a deepseekPro judge for its write paths; `args.judge === false` skips the
// judge and makes such a task serialise with everything in its wave.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner(respond = {}) {
  const state = { seq: [], overlaps: new Set(), inFlight: new Set(), logs: [], prompts: new Map(), models: new Map() }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.seq.push(label)
    state.prompts.set(label, String(prompt))
    state.models.set(label, opts.model || '')
    for (const other of state.inFlight) state.overlaps.add([label, other].sort().join('|'))
    state.inFlight.add(label)
    await Promise.resolve()
    await Promise.resolve()
    state.inFlight.delete(label)
    const r = typeof respond === 'function' ? respond(label) : respond[label]
    if (r !== undefined) return r
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    if (label.startsWith('judge:')) return { paths: [] }
    if (label.startsWith('impl:')) return 'done'
    throw new Error('unexpected label ' + label)
  }
  const parallel = async (thunks) => Promise.all(thunks.map((t) => t()))
  const pipeline = async () => []
  const log = (line) => { state.logs.push(String(line)) }
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

const T = (overrides = {}) => ({
  key: 'A',
  title: 'Task A',
  role: 'glm',
  kind: 'routine',
  spec: 'do A',
  dependsOn: [],
  ...overrides,
})

const PLAN_RESPOND = (label) => {
  if (label === 'plan:arch' || label === 'plan:product' || label === 'plan:feasibility') return 'essay'
  if (label === 'consolidate:tech' || label === 'consolidate:ux') return 'essay'
  if (label === 'consolidate:tasks') {
    return { tasks: [{ key: 'T1', title: 'Docs', role: 'glm', kind: 'routine', spec: 'do docs', dependsOn: [], touches: ['README.md'], parallelSafe: false }] }
  }
  return undefined
}

test('serialises two tasks with overlapping touches in key order and prints the note', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'B', title: 'B', touches: ['src/shared.mjs'] }), T({ key: 'A', title: 'A', touches: ['src/shared.mjs'] })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B']]], 'overlapping touches put A and B in one serial lane, key-ordered')
  assert.deepEqual(result.schedule.notes, ['serialised: A, B (touches overlap)'], 'the schedule note names the serialised pair and the reason')
  assert.equal(state.overlaps.has('impl:A|impl:B'), false, 'overlapping tasks never run concurrently')
  assert.ok(state.seq.indexOf('impl:A') < state.seq.indexOf('impl:B'), 'the lane runs in key order (A before B)')
})

test('groups by connected components, not colouring: A-B and B-C merge A,B,C into one lane', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'A', title: 'A', touches: ['a.mjs'] }),
      T({ key: 'B', title: 'B', touches: ['a.mjs', 'b.mjs'] }),
      T({ key: 'C', title: 'C', touches: ['b.mjs'] }),
    ],
  })
  // A overlaps B (a.mjs) and B overlaps C (b.mjs); A and C do not touch each other.
  // A colouring would pack A+C into one lane and run B in parallel — the opposite of
  // safe. Connected components put all three in ONE lane.
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B', 'C']]])
  assert.deepEqual(result.schedule.notes, ['serialised: A, B, C (touches overlap)'])
  assert.equal(state.overlaps.has('impl:A|impl:B'), false)
  assert.equal(state.overlaps.has('impl:B|impl:C'), false)
  assert.equal(state.overlaps.has('impl:A|impl:C'), false)
})

test('runs non-overlapping touches concurrently in separate lanes', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', title: 'A', touches: ['a.mjs'] }), T({ key: 'B', title: 'B', touches: ['b.mjs'] })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A'], ['B']]], 'disjoint touches stay in separate lanes')
  assert.deepEqual(result.schedule.notes, [], 'no serialisation note when nothing overlaps')
  assert.ok(state.overlaps.has('impl:A|impl:B'), 'disjoint touches run concurrently')
})

test('parallelSafe: true runs concurrently and is never sent to the judge', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', title: 'A', parallelSafe: true }), T({ key: 'B', title: 'B', parallelSafe: true })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A'], ['B']]])
  assert.equal(state.seq.filter((l) => l.startsWith('judge:')).length, 0, 'parallelSafe tasks are never judged')
  assert.ok(state.overlaps.has('impl:A|impl:B'), 'parallelSafe tasks still run concurrently')
})

test('the overlap check respects path boundaries: a directory overlaps its contents, siblings do not', async () => {
  const { run } = makeRunner()
  const dir = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['src/'] }), T({ key: 'B', title: 'B', touches: ['src/api.mjs'] })],
  })
  assert.deepEqual(dir.schedule.serialLanes, [[['A', 'B']]], 'writing src/ conflicts with writing src/api.mjs')

  const siblings = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['src/api.mjs'] }), T({ key: 'B', title: 'B', touches: ['src/app.mjs'] })],
  })
  assert.deepEqual(siblings.schedule.serialLanes, [[['A'], ['B']]], 'sibling files do not conflict')
})

test('a glob compares its literal prefix (everything before the first glob metacharacter)', async () => {
  const { run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['src/**/*.mjs'] }), T({ key: 'B', title: 'B', touches: ['src/api.mjs'] })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B']]], 'src/**/*.mjs and src/api.mjs share the literal prefix src/')
})

test('a leading-glob touches entry overlaps everything (its literal prefix is empty)', async () => {
  const { run } = makeRunner()
  const starStar = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['**'] }), T({ key: 'B', title: 'B', touches: ['src/a.mjs'] })],
  })
  assert.deepEqual(starStar.schedule.serialLanes, [[['A', 'B']]], "'**' writes everything, so it conflicts with any specific path")

  const markdown = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['*.md'] }), T({ key: 'B', title: 'B', touches: ['README.md'] })],
  })
  assert.deepEqual(markdown.schedule.serialLanes, [[['A', 'B']]], "'*.md' overlaps README.md, not nothing")
})

test('a leading-glob touches entry serialises against a parallelSafe peer and notes "writes everything"', async () => {
  const s1 = makeRunner()
  const starStar = await s1.run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'B', title: 'B', touches: ['**'] }), T({ key: 'A', title: 'A', parallelSafe: true })],
  })
  assert.deepEqual(starStar.schedule.serialLanes, [[['A', 'B']]], "'**' writes everything, so it serialises even against a parallelSafe peer")
  assert.deepEqual(starStar.schedule.notes, ['serialised: A, B (writes everything)'], 'the note names the leading-glob reason, not "unannotated"')
  assert.equal(s1.state.overlaps.has('impl:A|impl:B'), false, "'**' never runs concurrently with the parallelSafe peer")

  const s2 = makeRunner()
  const markdown = await s2.run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'B', title: 'B', touches: ['*.md'] }), T({ key: 'A', title: 'A', parallelSafe: true })],
  })
  assert.deepEqual(markdown.schedule.serialLanes, [[['A', 'B']]], "'*.md' writes every markdown file, so it serialises against a parallelSafe peer")
  assert.deepEqual(markdown.schedule.notes, ['serialised: A, B (writes everything)'])
  assert.equal(s2.state.overlaps.has('impl:A|impl:B'), false, "'*.md' never runs concurrently with the parallelSafe peer")
})

test('the path-boundary rule separates a directory name from a sibling directory prefix (src/api vs src/apiv2)', async () => {
  const { run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [T({ key: 'A', title: 'A', touches: ['src/api'] }), T({ key: 'B', title: 'B', touches: ['src/apiv2/x.mjs'] })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A'], ['B']]], "'src/api' is not a prefix of 'src/apiv2/...' at a path boundary, so they stay separate")
})

test('judge is consulted only for unannotated tasks, and its answer is recorded and logged', async () => {
  const { state, run } = makeRunner({ 'judge:Z': { paths: ['shared.mjs'] } })
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'X', title: 'X', touches: ['x.mjs'] }), // explicit touches — never judged
      T({ key: 'Y', title: 'Y', parallelSafe: true }), // parallelSafe — never judged
      T({ key: 'Z', title: 'Z' }), // unannotated — judged
    ],
  })
  assert.deepEqual(state.seq.filter((l) => l.startsWith('judge:')), ['judge:Z'], 'only the unannotated task is judged')
  assert.equal(state.models.get('judge:Z'), 'deepseek/deepseek-v4-pro-0813', 'the judge is deepseekPro')
  assert.deepEqual(result.schedule.judge.consulted, ['Z'])
  assert.deepEqual(result.schedule.judge.answers, { Z: ['shared.mjs'] }, 'the answer is recorded in the schedule output')
  assert.equal(result.schedule.judge.disabled, false)
  assert.ok(state.logs.some((l) => l.includes('judge: Z -> ["shared.mjs"]')), 'the answer is logged')
})

test('the judge answer drives serialisation against an explicitly-touched peer', async () => {
  const { state, run } = makeRunner({ 'judge:A': { paths: ['shared.mjs'] } })
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', title: 'A' }), T({ key: 'B', title: 'B', touches: ['shared.mjs'] })],
  })
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B']]], 'the judged paths make A overlap B')
  assert.deepEqual(result.schedule.notes, ['serialised: A, B (touches overlap)'])
  assert.equal(state.overlaps.has('impl:A|impl:B'), false, 'A and B no longer run concurrently once the judge reports a shared path')
})

test('a judge-supplied leading glob serialises against a parallelSafe peer and notes "writes everything"', async () => {
  const s1 = makeRunner({ 'judge:B': { paths: ['**'] } })
  const starStar = await s1.run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', title: 'A', parallelSafe: true }), T({ key: 'B', title: 'B' })],
  })
  assert.deepEqual(starStar.schedule.serialLanes, [[['A', 'B']]], "a judge-supplied '**' writes everything, so it serialises against a parallelSafe peer")
  assert.deepEqual(starStar.schedule.notes, ['serialised: A, B (writes everything)'], 'the note names the leading-glob reason, not "unannotated"')
  assert.equal(s1.state.overlaps.has('impl:A|impl:B'), false, "a judge-supplied '**' never runs concurrently with the parallelSafe peer")

  const s2 = makeRunner({ 'judge:B': { paths: ['*.md'] } })
  const markdown = await s2.run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', title: 'A', parallelSafe: true }), T({ key: 'B', title: 'B' })],
  })
  assert.deepEqual(markdown.schedule.serialLanes, [[['A', 'B']]], "a judge-supplied '*.md' writes every markdown file, so it serialises against a parallelSafe peer")
  assert.deepEqual(markdown.schedule.notes, ['serialised: A, B (writes everything)'])
  assert.equal(s2.state.overlaps.has('impl:A|impl:B'), false, "a judge-supplied '*.md' never runs concurrently with the parallelSafe peer")
})

test('args.judge === false disables the judge and an unannotated task serialises with everything', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    judge: false,
    tasks: [T({ key: 'A', title: 'A' }), T({ key: 'B', title: 'B' })],
  })
  assert.deepEqual(state.seq.filter((l) => l.startsWith('judge:')), [], 'no judge is dispatched when args.judge is false')
  assert.equal(result.schedule.judge.disabled, true)
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B']]], 'two unannotated tasks serialise together')
  assert.deepEqual(result.schedule.notes, ['serialised: A, B (unannotated — serialises with everything)'])
  assert.equal(state.overlaps.has('impl:A|impl:B'), false)
})

test('plan mode never consults the judge and treats unannotated tasks conservatively', async () => {
  const { state, run } = makeRunner()
  const result = await run({ goal: 'g', mode: 'plan', tasks: [T({ key: 'A', title: 'A' }), T({ key: 'B', title: 'B' })] })
  assert.equal(state.seq.length, 0, 'plan mode dispatches nothing at all')
  assert.equal(result.schedule.judge.disabled, true, 'the judge is disabled in plan mode')
  assert.deepEqual(result.schedule.serialLanes, [[['A', 'B']]], 'unannotated tasks serialise conservatively in plan mode')
})

test('the task planner is told to emit touches for every task, with the reason', async () => {
  const { state, run } = makeRunner(PLAN_RESPOND)
  await run({ goal: 'build a thing', mode: 'plan' })
  const prompt = state.prompts.get('consolidate:tasks')
  assert.ok(prompt, 'the task planner must be dispatched')
  assert.match(prompt, /`touches`/, 'the planner is told to emit touches')
  assert.ok(prompt.includes('two agents writing one file'), 'the planner is told WHY (a missed path = two agents writing one file)')
})

test('planner-emitted touches and parallelSafe survive normalisation into the return', async () => {
  const { run } = makeRunner(PLAN_RESPOND)
  const result = await run({ goal: 'build a thing', mode: 'plan' })
  assert.equal(result.tasks.length, 1)
  assert.deepEqual(result.tasks[0].touches, ['README.md'], 'touches carry through to the returned task')
  assert.equal(result.tasks[0].parallelSafe, false, 'parallelSafe carries through to the returned task')
})
