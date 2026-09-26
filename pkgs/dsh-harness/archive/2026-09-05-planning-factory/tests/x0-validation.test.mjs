import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope, and a
// top-level `return` to yield the result. We reproduce that here by evaluating the
// file as an AsyncFunction body with stubbed globals, and count agent dispatches so
// we can prove the entry guard throws *before* any agent is dispatched.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner() {
  const state = { agentsDispatched: 0 }
  const agent = async () => {
    state.agentsDispatched += 1
    return { text: 'stubbed' }
  }
  const parallel = async (thunks) => {
    const out = []
    for (const t of thunks) out.push(await t())
    return out
  }
  const pipeline = async () => []
  const log = () => {}
  const phase = () => {}
  const run = (args) => {
    const fn = new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)
    return fn(agent, parallel, pipeline, log, phase, args)
  }
  return { state, run }
}

const TASK = (overrides = {}) => ({
  key: 'T1',
  title: 'A task',
  role: 'glm',
  kind: 'routine',
  spec: 'do the thing',
  ...overrides,
})

// Assert a supplied task list is rejected by the entry guard with a plain Error
// matching `pattern`, and that no agent was dispatched before the throw.
async function assertRejectedOnEntry(tasks, pattern) {
  const { state, run } = makeRunner()
  await assert.rejects(
    run({ goal: 'test goal', mode: 'build', tasks }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error, got: ' + err)
      assert.match(err.message, pattern)
      return true
    }
  )
  assert.equal(state.agentsDispatched, 0, 'no agent may be dispatched before the entry guard throws')
}

test('rejects an unknown role before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ role: 'hacker' })], /unknown role/)
})

test('defaults a missing role and kind instead of rejecting them', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'test goal',
    mode: 'plan',
    tasks: [{ key: 'T1', title: 'One', spec: 'do it', dependsOn: [] }],
  })
  assert.equal(state.agentsDispatched, 0)
  assert.equal(result.tasks.length, 1)
  assert.equal(result.tasks[0].role, 'glm', 'a missing role takes the norm() default (glm)')
  assert.equal(result.tasks[0].kind, 'backend', 'a missing kind takes the norm() default (backend)')
})

test('rejects a missing title before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ title: undefined })], /missing a title/)
  await assertRejectedOnEntry([TASK({ title: '' })], /missing a title/)
})

test('rejects a dangling dependsOn before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ dependsOn: ['T2'] })], /depends on unknown task/)
})

test('rejects a missing/empty key before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ key: '' })], /non-empty key/)
  await assertRejectedOnEntry([TASK({ key: undefined })], /non-empty key/)
})

test('rejects a task key with a space or dot-dot before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ key: 'has space' })], /invalid task key/)
  await assertRejectedOnEntry([TASK({ key: '../escape' })], /invalid task key/)
})

test('rejects the all-dot keys "." and ".." before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ key: '..' })], /invalid task key/)
  await assertRejectedOnEntry([TASK({ key: '.' })], /invalid task key/)
})

test('rejects the reserved key "integration" before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ key: 'integration' })], /reserved/)
})

test('rejects task keys matching /^fix-w\\d+$/ (the per-wave fix clone names) before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ key: 'fix-w1' })], /reserved/)
  await assertRejectedOnEntry([TASK({ key: 'fix-w12' })], /reserved/)
})

test('rejects an empty spec before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ spec: '' })], /missing a spec/)
})

test('rejects an unknown kind before any agent is dispatched', async () => {
  await assertRejectedOnEntry([TASK({ kind: 'magic' })], /unknown kind/)
})

test('accepts unknown extra fields such as touches and parallelSafe', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'test goal',
    mode: 'plan',
    tasks: [
      {
        key: 'T1',
        title: 'One',
        role: 'deepseekPro',
        kind: 'backend',
        spec: 'build the API',
        dependsOn: [],
        touches: ['src/api.mjs'],
        parallelSafe: true,
      },
    ],
  })
  assert.equal(state.agentsDispatched, 0)
  assert.equal(result.tasks.length, 1)
  assert.equal(result.tasks[0].key, 'T1')
})

test('plan-mode return projects spec onto every task', async () => {
  const { state, run } = makeRunner()
  const result = await run({
    goal: 'test goal',
    mode: 'plan',
    tasks: [
      { key: 'T1', title: 'Build the API', role: 'deepseekPro', kind: 'backend', spec: 'implement GET /health', dependsOn: [] },
      { key: 'T2', title: 'Write docs', role: 'glm', kind: 'routine', spec: 'README + runbook', dependsOn: ['T1'] },
    ],
  })
  assert.equal(state.agentsDispatched, 0)
  assert.equal(result.mode, 'plan')
  assert.equal(result.tasks.length, 2)
  for (const t of result.tasks) {
    assert.ok('spec' in t, 'every returned task must carry its spec')
    assert.equal(typeof t.spec, 'string')
    assert.ok(t.spec.length > 0)
  }
  assert.equal(result.tasks[0].spec, 'implement GET /health')
  assert.equal(result.tasks[1].spec, 'README + runbook')
})

test('refuses build mode when args.tasks is missing, non-array, or empty', async () => {
  for (const bad of [undefined, 'not-a-list', {}, []]) {
    const { state, run } = makeRunner()
    await assert.rejects(
      run({ goal: 'g', mode: 'build', tasks: bad }),
      (err) => {
        assert.ok(err instanceof Error, 'must throw a plain Error')
        assert.match(err.message, /args\.tasks/)
        return true
      }
    )
    assert.equal(state.agentsDispatched, 0, 'no agent may be dispatched on the refusal: ' + JSON.stringify(bad))
  }
})

// The planner (consolidate:tasks) bypasses the args.tasks entry guard, so its graph
// is only checked by validateGraph + computeWaves. Reuse the workflow-tool contract
// with a planner stub that returns a task list with a dangling dependsOn.
function makePlanRunner(taskList) {
  const state = { agentsDispatched: 0 }
  const agent = async (_prompt, opts = {}) => {
    state.agentsDispatched += 1
    const label = opts.label || ''
    if (label.startsWith('plan:')) return 'essay'
    if (label === 'consolidate:tech' || label === 'consolidate:ux') return 'essay'
    if (label === 'consolidate:tasks') return { tasks: taskList }
    throw new Error('unexpected label ' + label)
  }
  const parallel = async (thunks) => {
    const out = []
    for (const t of thunks) out.push(await t())
    return out
  }
  const pipeline = async () => []
  const log = () => {}
  const phase = () => {}
  const run = (args) => new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
    agent, parallel, pipeline, log, phase, args
  )
  return { state, run }
}

test('reports a planner-emitted dangling dependsOn as "dangling dependsOn", not a cycle', async () => {
  const { run } = makePlanRunner([
    { key: 'T1', title: 'One', role: 'glm', kind: 'routine', spec: 'do the thing', dependsOn: ['T2'] },
  ])
  await assert.rejects(
    run({ goal: 'g', mode: 'plan' }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error')
      assert.match(err.message, /dangling dependsOn/)
      assert.doesNotMatch(err.message, /cycle among/)
      return true
    }
  )
})
