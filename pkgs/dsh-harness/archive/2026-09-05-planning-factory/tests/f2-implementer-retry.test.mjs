import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope and a
// top-level `return`. We reproduce that by evaluating the file as an AsyncFunction
// body with stubbed globals. The stub routes on `opts.label`: guard labels report a
// clean tree, impl labels resolve per the test's `respond` plan, and review labels
// pass. Every label is recorded so we can assert the real dispatch sequence (e.g. a
// null implementer return produces exactly one retry, and a dependent task is never
// dispatched after a failed predecessor).
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner(respond) {
  const state = { logs: [], labels: [], prompts: new Map() }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.labels.push(label)
    state.prompts.set(label, String(prompt))
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
    if (label.startsWith('judge:')) return { paths: [] } // F9: parallel-safety judge (stubbed: writes nothing shared)
    return respond(label)
  }
  const parallel = async (thunks) => {
    const out = []
    for (const t of thunks) out.push(await t())
    return out
  }
  const pipeline = async () => []
  const log = (line) => { state.logs.push(String(line)) }
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

const T1 = { key: 'T1', title: 'One', role: 'glm', kind: 'routine', spec: 'do T1', dependsOn: [] }
const T2_DEP = { key: 'T2', title: 'Two', role: 'glm', kind: 'routine', spec: 'do T2', dependsOn: ['T1'] }
const T2_INDEP = { key: 'T2', title: 'Two', role: 'glm', kind: 'routine', spec: 'do T2', dependsOn: [] }

// A response plan that fails T1 (null on both attempts) and lets everything else
// behave: clean guard, passing reviews.
function failT1(respondOther = () => { throw new Error('unexpected label') }) {
  return (label) => {
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:T1')) return null
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    return respondOther(label)
  }
}

test('retries a null implementer return exactly once and records the retry output', async () => {
  const { state, run } = makeRunner((label) => {
    if (label.startsWith('guard:tree')) return 'clean'
    if (label === 'impl:T1') return null
    if (label === 'impl:T1:retry') return 'implemented T1'
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T1] })

  assert.deepEqual(
    state.labels.filter((l) => l === 'impl:T1' || l === 'impl:T1:retry'),
    ['impl:T1', 'impl:T1:retry'],
    'a null first attempt must be retried exactly once (no third dispatch)'
  )
  assert.equal(result.implementations.length, 1)
  assert.equal(result.implementations[0].key, 'T1')
  assert.equal(result.implementations[0].out, 'implemented T1')
  assert.equal('status' in result.implementations[0], false)
})

test('records {key, status: "failed"} and logs when both attempts return null', async () => {
  const { state, run } = makeRunner(failT1())
  const result = await run({ goal: 'g', mode: 'build', tasks: [T1] })

  assert.deepEqual(result.implementations, [{ key: 'T1', status: 'failed', wave: 1 }])
  assert.deepEqual(
    state.labels.filter((l) => l.startsWith('impl:T1')),
    ['impl:T1', 'impl:T1:retry'],
    'exactly two attempts before giving up'
  )
  assert.ok(
    state.logs.some((l) => l.startsWith('failed — T1')),
    'the failure must be logged to the durable journal'
  )
})

test('marks a dependent task blocked and never runs it when its dependency failed', async () => {
  const { state, run } = makeRunner(failT1((label) => {
    if (label.startsWith('impl:T2')) return 'must not run'
    throw new Error('unexpected label ' + label)
  }))

  const result = await run({ goal: 'g', mode: 'build', tasks: [T1, T2_DEP] })

  assert.deepEqual(result.implementations, [
    { key: 'T1', status: 'failed', wave: 1 },
    { key: 'T2', status: 'blocked', wave: 2, blockedBy: ['T1'] },
  ])
  // The scheduler blocks T2 in wave 2: no guard dispatch, no implementer dispatch
  // for the dependent task (the run continues through cross-review instead of throwing).
  assert.deepEqual(
    state.labels.filter((l) => l.startsWith('impl:T2')),
    [],
    'a blocked task is never dispatched'
  )
})

test('continues and reports when a failed task has no dependents', async () => {
  const { state, run } = makeRunner(failT1((label) => {
    if (label.startsWith('impl:T2')) return 'implemented T2'
    throw new Error('unexpected label ' + label)
  }))

  const result = await run({ goal: 'g', mode: 'build', tasks: [T1, T2_INDEP] })

  assert.equal(result.implementations.length, 2)
  assert.deepEqual(result.implementations[0], { key: 'T1', status: 'failed', wave: 1 })
  assert.equal(result.implementations[1].key, 'T2')
  assert.equal(result.implementations[1].out, 'implemented T2')
  assert.equal('status' in result.implementations[1], false)
  assert.ok(result.reviewSummary, 'the run still reaches cross-review')
})

test('the retry re-clones idempotently: rm -rf before the clone, sharing the same body', async () => {
  const { state, run } = makeRunner((label) => {
    if (label.startsWith('guard:tree')) return 'clean'
    if (label === 'impl:T1') return null
    if (label === 'impl:T1:retry') return 'implemented T1'
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T1] })

  const first = state.prompts.get('impl:T1')
  const retry = state.prompts.get('impl:T1:retry')
  assert.ok(first && retry, 'both the first attempt and the retry must carry prompts')
  assert.notEqual(first, retry, 'the retry prompt differs from the first prompt')
  assert.doesNotMatch(first, /rm -rf \$HOME\/factory\/ws\//, 'the first prompt must not remove the workspace')
  assert.ok(retry.includes('rm -rf "$HOME/factory/ws/' + result.runId + '/T1"'), 'the retry removes the quoted workspace path the died attempt may have left')
  assert.match(retry, /git clone --local \$HOME\/factory\/base\/dsh-harness/, 'the retry still clones from the base clone')
  // The difference is confined to the workspace preamble: everything after the
  // checkout line (commit convention + spec) is byte-identical.
  assert.equal(retry.split('git checkout -B T1')[1], first.split('git checkout -B T1')[1], 'only the workspace preamble differs')
})
