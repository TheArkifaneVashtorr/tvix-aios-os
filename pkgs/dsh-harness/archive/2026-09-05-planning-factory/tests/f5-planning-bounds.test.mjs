import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope. We
// reproduce that with an AsyncFunction + stubbed globals, and record the prompt
// each dispatch receives so we can assert the planning and consolidation prompts
// carry an explicit length bound. The unbounded essays were re-interpolated into
// consolidation prompts that totalled 125,476 chars (vs 9,644 for the planning
// prompts) and blew the plan-mode return past the workflow tool's 50,000-byte cap.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makePlanRunner() {
  const state = { prompts: new Map(), agentsDispatched: 0 }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.prompts.set(label, String(prompt))
    state.agentsDispatched += 1
    if (label === 'plan:arch') return 'ARCHITECTURE ESSAY'
    if (label === 'plan:product') return 'PRODUCT ESSAY'
    if (label === 'plan:feasibility') return 'FEASIBILITY ESSAY'
    if (label === 'consolidate:tech') return 'CONSOLIDATED TECHNICAL ESSAY'
    if (label === 'consolidate:ux') return 'PRODUCT/UX DECISIONS ESSAY'
    if (label === 'consolidate:tasks') {
      return { tasks: [{ key: 'T1', title: 'Docs', role: 'glm', kind: 'routine', spec: 'do docs', dependsOn: [] }] }
    }
    throw new Error('unexpected label ' + label)
  }
  const parallel = async (thunks) => Promise.all(thunks.map((t) => t()))
  const pipeline = async () => []
  const log = () => {}
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

function expectPhrase(prompts, label, phrase) {
  const prompt = prompts.get(label)
  assert.ok(prompt, label + ' must be dispatched in plan mode')
  assert.ok(
    prompt.includes(phrase),
    label + ' must state "' + phrase + '" to bound the essay length'
  )
}

test('word-caps each of the three planning-lens prompts', async () => {
  const { state, run } = makePlanRunner()
  await run({ goal: 'build a thing', mode: 'plan' })
  expectPhrase(state.prompts, 'plan:arch', 'Keep it under 800 words.')
  expectPhrase(state.prompts, 'plan:product', 'Keep it under 800 words.')
  expectPhrase(state.prompts, 'plan:feasibility', 'Keep it under 800 words.')
})

test('word-caps each of the two consolidation prompts', async () => {
  const { state, run } = makePlanRunner()
  await run({ goal: 'build a thing', mode: 'plan' })
  expectPhrase(state.prompts, 'consolidate:tech', 'Keep it under 1,200 words.')
  expectPhrase(state.prompts, 'consolidate:ux', 'Keep it under 1,200 words.')
})

test('tells the task planner to keep each spec self-contained but under a stated length', async () => {
  const { state, run } = makePlanRunner()
  await run({ goal: 'build a thing', mode: 'plan' })
  expectPhrase(state.prompts, 'consolidate:tasks', 'self-contained but under 1,500 characters')
})
