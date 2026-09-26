import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope, and a
// top-level `return` to yield the result. We reproduce that by evaluating the file
// as an AsyncFunction body with stubbed globals. `agent` returns canned review
// verdicts keyed by the review label suffix (technical / visual / completeness);
// every log() line is captured so we can assert on the durable journal output.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeBuildRunner(reviewsByLabel) {
  const state = { logs: [], agentsDispatched: 0 }
  const agent = async (_prompt, opts = {}) => {
    state.agentsDispatched += 1
    const label = opts.label || ''
    if (label.startsWith('review:')) {
      const key = label.slice('review:'.length)
      return reviewsByLabel[key] || { verdict: 'pass', findings: [] }
    }
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
    return { text: 'stubbed implementation' }
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

const TASK = { key: 'T1', title: 'One task', role: 'glm', kind: 'routine', spec: 'do the thing', dependsOn: [] }

// Run a build with one implementer + three reviewers returning the given verdicts,
// and return the captured logs plus the result object.
async function runBuild(reviewsByLabel) {
  const { state, run } = makeBuildRunner(reviewsByLabel)
  const result = await run({ goal: 'test goal', mode: 'build', tasks: [TASK] })
  return { state, result }
}

const MIXED = {
  technical: {
    verdict: 'pass',
    findings: [
      { severity: 'blocker', where: 'src/api.mjs', issue: 'auth bypass' },
      { severity: 'minor', where: 'src/api.mjs', issue: 'naming nit' },
    ],
  },
  visual: {
    verdict: 'pass',
    findings: [{ severity: 'major', where: 'src/layout.mjs', issue: 'breaks at 320px' }],
  },
  completeness: {
    verdict: 'rework',
    findings: [{ severity: 'major', where: 'factory/tests', issue: 'no test for X' }],
  },
}

test('logs one line per blocker/major finding as "severity — where — issue"', async () => {
  const { state, result } = await runBuild(MIXED)

  assert.ok(state.logs.includes('blocker — src/api.mjs — auth bypass'), 'blocker finding must be logged')
  assert.ok(state.logs.includes('major — src/layout.mjs — breaks at 320px'), 'major finding must be logged')
  assert.ok(state.logs.includes('major — factory/tests — no test for X'), 'rework reviewer findings must be logged too')

  assert.equal(
    state.logs.some((l) => l.includes('naming nit')),
    false,
    'minor findings must not be logged (only blocker/major)'
  )
  assert.ok('reviews' in result, 'the reviews object is still returned')
})

test('logs one line per rework verdict', async () => {
  const { state } = await runBuild(MIXED)
  assert.ok(state.logs.includes('rework — completeness'), 'the completeness reviewer rework verdict must be logged')
  assert.equal(
    state.logs.filter((l) => l.startsWith('rework —')).length,
    1,
    'exactly one rework line for exactly one rework verdict'
  )
})

test('adds reviewSummary to the return with per-severity counts and rework labels', async () => {
  const { result } = await runBuild(MIXED)
  assert.deepEqual(result.reviewSummary, {
    blockers: 1,
    majors: 2,
    minors: 1,
    rework: ['completeness'],
  })
})

test('returns a zeroed reviewSummary when every reviewer passes', async () => {
  const { result } = await runBuild({
    technical: { verdict: 'pass', findings: [] },
    visual: { verdict: 'pass', findings: [] },
    completeness: { verdict: 'pass', findings: [] },
  })
  assert.deepEqual(result.reviewSummary, { blockers: 0, majors: 0, minors: 0, rework: [] })
})

test('logs one line per rework verdict when multiple reviewers rework', async () => {
  const { state, result } = await runBuild({
    technical: { verdict: 'rework', findings: [{ severity: 'blocker', where: 'x', issue: 'y' }] },
    visual: { verdict: 'pass', findings: [] },
    completeness: { verdict: 'rework', findings: [] },
  })
  assert.ok(state.logs.includes('rework — technical'))
  assert.ok(state.logs.includes('rework — completeness'))
  assert.deepEqual(result.reviewSummary.rework, ['technical', 'completeness'])
})
