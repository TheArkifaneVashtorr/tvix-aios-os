import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope. We
// reproduce that with an AsyncFunction + stubbed globals. `parallel` runs its
// thunks concurrently (Promise.all), and the stub `agent` yields twice between
// recording "in flight" and returning, so we can observe which agents actually
// overlap — the only honest way to prove two dispatches were concurrent rather
// than sequential awaits.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

const defaultRespond = (label) => {
  if (label.startsWith('guard:tree')) return 'clean'
  if (label.startsWith('impl:')) return 'done'
  if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
  throw new Error('unexpected label ' + label)
}

function makeRunner(respond = defaultRespond) {
  const state = { seq: [], overlaps: new Set(), inFlight: new Set(), logs: [], agentsDispatched: 0 }
  const agent = async (_prompt, opts = {}) => {
    const label = opts.label || ''
    state.seq.push(label)
    for (const other of state.inFlight) state.overlaps.add([label, other].sort().join('|'))
    state.inFlight.add(label)
    state.agentsDispatched += 1
    await Promise.resolve()
    await Promise.resolve()
    state.inFlight.delete(label)
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
    if (label.startsWith('judge:')) return { paths: [] } // F9: parallel-safety judge (stubbed: writes nothing shared)
    return respond(label)
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

test('rejects a dependsOn cycle before any agent is dispatched, naming the keys', async () => {
  const { state, run } = makeRunner()
  const tasks = [
    T({ key: 'A', title: 'A', dependsOn: ['B'] }),
    T({ key: 'B', title: 'B', dependsOn: ['A'] }),
  ]
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error, got: ' + err)
      assert.match(err.message, /cycle among A, B/)
      return true
    }
  )
  assert.equal(state.agentsDispatched, 0, 'no agent may be dispatched before the cycle is named')
})

test('rejects duplicate task keys before any agent is dispatched (validateGraph)', async () => {
  const { state, run } = makeRunner()
  const tasks = [T({ key: 'A' }), T({ key: 'A' })]
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error, got: ' + err)
      assert.match(err.message, /duplicate task key/)
      return true
    }
  )
  assert.equal(state.agentsDispatched, 0, 'no agent may be dispatched before the duplicate key is named')
})

test('rejects a task depending on itself before any agent is dispatched', async () => {
  const { state, run } = makeRunner()
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A', dependsOn: ['A'] })] }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error, got: ' + err)
      assert.match(err.message, /depends on itself/)
      return true
    }
  )
  assert.equal(state.agentsDispatched, 0, 'no agent may be dispatched before the self-dependency is named')
})

test('computes sorted Kahn waves and logs the whole schedule in plan mode', async () => {
  const { state, run } = makeRunner()
  // Deliberately listed out of key order: T2 before T10. A sorted ready set puts
  // "T10" before "T2" (string order), so the schedule is reproducible from the
  // task list alone and never depends on the array's order.
  const result = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [
      T({ key: 'T2', title: 'Two', dependsOn: [] }),
      T({ key: 'T10', title: 'Ten', dependsOn: [] }),
      T({ key: 'T1', title: 'One', dependsOn: ['T2'] }),
    ],
  })

  assert.deepEqual(result.schedule.waves, [['T10', 'T2'], ['T1']])
  assert.equal(result.schedule.concurrency, 4, 'default concurrency is 4')
  assert.equal(result.schedule.integrationBranch, 'factory/integration')
  assert.ok(
    state.logs.includes('schedule: 3 task(s), 2 wave(s), concurrency 4, integration branch factory/integration'),
    'the schedule summary line must name tasks, waves, concurrency and the integration branch'
  )
  assert.ok(state.logs.includes('  wave 1: T10 | T2'), 'wave 1 is logged with its groups')
  assert.ok(state.logs.includes('  wave 2: T1'), 'wave 2 is logged with its groups')
  assert.equal(state.agentsDispatched, 0, 'plan mode dispatches nothing')
})

test('trims a task key once in norm() so a trimmed dependsOn matches in the graph', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'plan',
    tasks: [
      T({ key: ' A ', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: ['A'] }),
    ],
  })
  assert.deepEqual(result.schedule.waves, [['A'], ['B']], 'the trimmed key drives the dependency graph, not a spurious cycle')
  assert.equal(state.agentsDispatched, 0, 'plan mode dispatches nothing')
})

test('carries a wave number on every build result', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'A', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: [] }),
      T({ key: 'C', title: 'C', dependsOn: ['A'] }),
    ],
  })
  const byKey = Object.fromEntries(result.implementations.map((r) => [r.key, r.wave]))
  assert.deepEqual(byKey, { A: 1, B: 1, C: 2 }, 'every implementation result carries its wave')
})

test('marks a task blocked and never runs it when a dependency failed', async () => {
  const { state, run } = makeRunner((label) => {
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:A')) return null // A dies on both attempts
    if (label.startsWith('impl:B')) return 'must not run'
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  })
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'A', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: ['A'] }),
    ],
  })

  const b = result.implementations.find((r) => r.key === 'B')
  assert.equal(b.status, 'blocked', 'a task whose dependency failed is marked blocked')
  assert.deepEqual(b.blockedBy, ['A'], 'the blocking dependency is named')
  assert.equal(b.wave, 2, 'the blocked task still carries its wave')
  assert.deepEqual(
    state.seq.filter((l) => l.startsWith('impl:B')),
    [],
    'a blocked task is never dispatched an implementer'
  )
})

test('a blocked dependency blocks its dependents transitively (A fails -> B blocked -> C blocked, C never dispatched)', async () => {
  const { state, run } = makeRunner((label) => {
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:A')) return null // A dies on both attempts
    if (label.startsWith('impl:B')) return 'must not run'
    if (label.startsWith('impl:C')) return 'must not run'
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  })
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'A', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: ['A'] }),
      T({ key: 'C', title: 'C', dependsOn: ['B'] }),
    ],
  })
  const byKey = Object.fromEntries(result.implementations.map((r) => [r.key, r]))
  assert.equal(byKey.B.status, 'blocked', 'B is blocked because A failed')
  assert.equal(byKey.C.status, 'blocked', 'C is blocked because B was blocked (transitive)')
  assert.deepEqual(byKey.C.blockedBy, ['B'], 'C names its direct blocking dependency')
  assert.deepEqual(
    state.seq.filter((l) => l.startsWith('impl:C')),
    [],
    'C is never dispatched an implementer'
  )
})

test('runs same-wave tasks concurrently and later waves only after earlier ones finish', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [
      T({ key: 'A', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: [] }),
      T({ key: 'C', title: 'C', dependsOn: ['A'] }),
    ],
  })
  assert.deepEqual(result.schedule.waves, [['A', 'B'], ['C']])
  assert.ok(state.overlaps.has('impl:A|impl:B'), 'independent tasks in one wave overlap in flight')
  assert.equal(state.overlaps.has('impl:A|impl:C'), false, 'a dependent task never overlaps its dependency')
  assert.equal(state.overlaps.has('impl:B|impl:C'), false, 'a dependent task never overlaps a wave-1 peer')
})

test('honours args.concurrency by chunking the wave (1 serialises it)', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    concurrency: 1,
    tasks: [
      T({ key: 'A', title: 'A', dependsOn: [] }),
      T({ key: 'B', title: 'B', dependsOn: [] }),
    ],
  })
  assert.equal(result.schedule.concurrency, 1)
  assert.equal(state.overlaps.has('impl:A|impl:B'), false, 'concurrency 1 never overlaps two tasks')
})

test('runs the three read-only cross-reviewers concurrently under parallel()', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A', title: 'A', dependsOn: [] })] })
  assert.deepEqual(
    state.seq.filter((l) => l.startsWith('review:')).sort(),
    ['review:completeness', 'review:technical', 'review:visual'],
    'all three reviewers run'
  )
  assert.ok(state.overlaps.has('review:technical|review:visual'), 'reviewers overlap in flight — they run in parallel, not sequentially')
})
