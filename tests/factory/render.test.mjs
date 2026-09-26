// Loads the real tools/factory/dark-factory.js text (no imports available in
// the Workflow sandbox, so this is the only way to test what it renders),
// strips the `export const meta = {...}` literal, wraps the remainder as the
// body of an async IIFE via `new Function`, and runs it with stub globals
// standing in for the Workflow harness (agent, parallel, pipeline, phase,
// log, workflow, budget, args). Asserts:
//  - args.skills + tasks[].skillRefs are injected, byte-exact, into all five
//    prompt sites (implementer, fix agent, Opus code reviewer, docs
//    reviewer, verifier) exactly as skillLines() specifies, and not at all
//    when args.skills is absent.
//  - a review spawn() that returns null is retried once with the same
//    prompt; if still null the task's status is "unreviewed" (review stays
//    null, never "approved"), and the run's final log + return list it.
//  - a first review that rejects with a blocker spawns the fix agent, whose
//    prompt carries the same skill-injection site as the implementer's.
//  - the F32 case (approved=false, no blocking findings) produces a
//    reviewNote that reaches the run's returned task list, not just the
//    internal results array.
//  - a code task with an empty or absent checks array is refused in
//    validateGraph before any agent dispatch (a docs task may omit checks).
//  - a reviewer that returns rework forever is capped at two fix rounds
//    (fixRounds === 2), the task is recorded not-approved, and the run is
//    not delivered.
//  - the header comment documents the models.audit override and the
//    skills/skillRefs args.
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const scriptPath = path.join(__dirname, '..', '..', 'tools', 'factory', 'dark-factory.js')
const src = fs.readFileSync(scriptPath, 'utf8')

// Strip the leading `export const meta = { ... }` literal: from the line
// starting `export const meta` to the first line that is EXACTLY "}".
function stripMeta(text) {
  const lines = text.split('\n')
  const startIdx = lines.findIndex((l) => l.startsWith('export const meta'))
  if (startIdx === -1) {
    throw new Error('render.test.mjs: could not find "export const meta" in dark-factory.js')
  }
  let endIdx = -1
  for (let i = startIdx; i < lines.length; i++) {
    if (lines[i] === '}') {
      endIdx = i
      break
    }
  }
  if (endIdx === -1) {
    throw new Error('render.test.mjs: could not find the closing "}" line of the meta literal')
  }
  return lines
    .slice(0, startIdx)
    .concat(lines.slice(endIdx + 1))
    .join('\n')
}

const body = stripMeta(src)

function makeRunner(body) {
  return new Function(
    'agent',
    'parallel',
    'pipeline',
    'phase',
    'log',
    'workflow',
    'budget',
    'args',
    `return (async () => {\n${body}\n})()`,
  )
}

const runScript = makeRunner(body)

const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-skills.json'), 'utf8'))

// The exact strings skillLines() in dark-factory.js emits, reproduced here
// so the assertions below are byte-exact rather than substring matches.
function expectedSkillLine(P, role, task) {
  if (role === 'impl') {
    const refs =
      task && Array.isArray(task.skillRefs) && task.skillRefs.length
        ? `then these references: ${task.skillRefs.map((s) => `${P}/references/${s}.md`).join(', ')}.`
        : `then pick from the router's task → files table using this task's title and spec text.`
    return `SKILL: read ${P}/SKILL.md first, ${refs} Name the files you read in your report.`
  }
  if (role === 'reviewCode') {
    return `SKILL: read ${P}/references/review-checklist.md and ${P}/references/gotchas.md; apply the checklist in order.`
  }
  if (role === 'reviewDocs') {
    return `SKILL: read ${P}/references/nix-cli.md and ${P}/references/activation-and-switch.md before checking any command.`
  }
  if (role === 'verify') {
    return `SKILL: follow ${P}/references/verify.md.`
  }
  throw new Error(`expectedSkillLine: unknown role ${role}`)
}

// Extracts the single "SKILL: ..." line from a prompt (skillLines() always
// emits it as one line, preceded by a bare "\n" that is not part of the
// line's own content).
function skillLineOf(prompt) {
  const m = prompt.match(/^SKILL:.*$/m)
  return m ? m[0] : null
}

// reviewMode: 'ok' -> every review approves with no findings; 'null' ->
// every review spawn returns null (the defect this task fixes);
// 'rejectThenApprove' -> the first review round (":r1") returns a blocker,
// every later round approves; 'approvedFalseNoBlocking' -> every review
// returns approved=false with zero findings (the F32 mismatch).
function makeStubs(reviewMode) {
  const calls = []
  const logs = []
  // --- concurrency instrumentation (N10) ---------------------------------
  const seq = [] // labels in dispatch order
  const overlaps = new Set() // "L1|L2" for every pair in flight together
  const inFlight = new Set()
  let logsBeforeFirstAgent = 0
  const track = async (label, body) => {
    if (!seq.length) logsBeforeFirstAgent = logs.length
    seq.push(label)
    for (const other of inFlight) overlaps.add([label, other].sort().join('|'))
    inFlight.add(label)
    await Promise.resolve()
    await Promise.resolve() // yield twice
    inFlight.delete(label)
    return body()
  }
  const agentFn = async (prompt, opts) =>
    track((opts && opts.label) || '', () => {
      calls.push({ prompt, opts })
      const label = (opts && opts.label) || ''
      if (label === 'baseline') {
        return { head: 'abc1234', lint_green: true, log: 'ok' }
      }
      if (label.startsWith('review:')) {
        if (reviewMode === 'null') return null
        if (reviewMode === 'rejectThenApprove') {
          if (label.endsWith(':r1')) {
            return {
              approved: false,
              findings: [{ severity: 'blocker', file: 'tools/factory/dark-factory.js', issue: 'bad', fix: 'do y' }],
              summary: 'blocked',
            }
          }
          return { approved: true, findings: [], summary: 'ok now' }
        }
        if (reviewMode === 'approvedFalseNoBlocking') {
          return { approved: false, findings: [], summary: 'weird' }
        }
        if (reviewMode === 'rejectAAlways') {
          if (label.startsWith('review:A:')) {
            return {
              approved: false,
              findings: [
                { severity: 'blocker', file: 'tools/factory/dark-factory.js', issue: 'still bad', fix: 'do z' },
              ],
              summary: 'blocked every round',
            }
          }
          return { approved: true, findings: [], summary: 'ok' }
        }
        if (reviewMode === 'rejectAlways') {
          return {
            approved: false,
            findings: [{ severity: 'blocker', file: 'tools/factory/dark-factory.js', issue: 'bad', fix: 'do y' }],
            summary: 'blocked',
          }
        }
        return { approved: true, findings: [], summary: 'ok' }
      }
      if (label.startsWith('impl:') || label.startsWith('fix:')) {
        return {
          commit: 'abc1234',
          summary: 'did it',
          tests_run: [],
          test_results: 'ok',
          deviations: '',
          blocked: false,
          branch: label.split(':')[1] || 'taskbranch',
          workspace: '/tmp/wt-' + (label.split(':')[1] || 'x'),
        }
      }
      if (label.startsWith('integrate:') || label.startsWith('integfix:')) {
        return { merged: ['A'], conflict: '', checks_green: true, head: 'def5678', output: 'ok' }
      }
      if (label.startsWith('judge:')) {
        return { touches: ['pkgs/guessed'], reasoning: 'guessed from the spec text' }
      }
      if (label === 'deliver') {
        return { ok: true, head: 'fff1111' }
      }
      if (label === 'recorder') {
        return { ok: true, ts: '2026-09-05T12:00:00Z' }
      }
      if (label === 'verify') {
        return {
          flake_check_green: true,
          toplevel_built: true,
          closure_diff: '',
          commits: [],
          verdict: 'pass',
          notes: '',
        }
      }
      if (label === 'invariant-audit') {
        return { ok: true, concerns: [], summary: 'ok' }
      }
      return {}
    })
  const parallel = async (thunks) => Promise.all(thunks.map((t) => t()))
  const pipeline = async (thunks) => {
    let r
    for (const t of thunks) r = await t(r)
    return r
  }
  const phase = () => {}
  const logFn = (...a) => logs.push(a.join(' '))
  const workflow = {}
  const budget = { total: null, spent: () => 0, remaining: () => Infinity }
  return {
    agentFn,
    parallel,
    pipeline,
    phase,
    logFn,
    workflow,
    budget,
    calls,
    logs,
    seq,
    overlaps,
    logsBeforeFirstAgent: () => logsBeforeFirstAgent,
  }
}

function byLabel(calls, label) {
  return calls.find((c) => c.opts && c.opts.label === label)
}
function byLabelPrefix(calls, prefix) {
  return calls.find((c) => c.opts && c.opts.label && c.opts.label.startsWith(prefix))
}

async function main() {
  const P = '/skills/nixos'

  // Scenario 1: args.skills set, reviews approve — byte-exact assertion on
  // every injection site that fires without a review rejection (impl x2,
  // both reviewers, verify). No reviewNote: the run went cleanly.
  {
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      fixture,
    )

    const implA = byLabel(stubs.calls, 'impl:A')
    assert.ok(implA, 'impl:A prompt was recorded')
    assert.equal(
      skillLineOf(implA.prompt),
      expectedSkillLine(P, 'impl', fixture.tasks[0]),
      'impl:A SKILL line is byte-exact (has skillRefs)',
    )

    const implB = byLabel(stubs.calls, 'impl:B')
    assert.ok(implB, 'impl:B prompt was recorded')
    assert.equal(
      skillLineOf(implB.prompt),
      expectedSkillLine(P, 'impl', fixture.tasks[1]),
      'impl:B SKILL line is byte-exact (no skillRefs, falls back to the router sentence)',
    )

    const reviewA = byLabelPrefix(stubs.calls, 'review:A:')
    assert.ok(reviewA, 'review:A prompt was recorded')
    assert.equal(
      skillLineOf(reviewA.prompt),
      expectedSkillLine(P, 'reviewCode'),
      'code reviewer SKILL line is byte-exact',
    )

    const reviewB = byLabelPrefix(stubs.calls, 'review:B:')
    assert.ok(reviewB, 'review:B prompt was recorded')
    assert.equal(
      skillLineOf(reviewB.prompt),
      expectedSkillLine(P, 'reviewDocs'),
      'docs reviewer SKILL line is byte-exact',
    )

    const verify = byLabel(stubs.calls, 'verify')
    assert.ok(verify, 'verify prompt was recorded')
    assert.equal(skillLineOf(verify.prompt), expectedSkillLine(P, 'verify'), 'verifier SKILL line is byte-exact')

    const taskA = result.tasks.find((t) => t.key === 'A')
    const taskB = result.tasks.find((t) => t.key === 'B')
    assert.equal(taskA.status, 'approved')
    assert.equal(taskB.status, 'approved')
    assert.equal(taskA.reviewNote, undefined, 'no reviewNote on a clean approval')
    assert.equal(taskB.reviewNote, undefined, 'no reviewNote on a clean approval')
  }

  // Scenario 2: args.skills absent — no prompt anywhere contains "SKILL:",
  // and every other prompt site is otherwise unchanged.
  {
    const noSkillsArgs = JSON.parse(JSON.stringify(fixture))
    delete noSkillsArgs.skills
    const stubs = makeStubs('ok')
    await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      noSkillsArgs,
    )
    assert.ok(stubs.calls.length > 0, 'at least one prompt was recorded')
    for (const c of stubs.calls) {
      assert.ok(
        !c.prompt.includes('SKILL:'),
        `prompt for ${(c.opts && c.opts.label) || '?'} must not contain "SKILL:" when args.skills is absent`,
      )
    }
  }

  // Scenario 3: every review spawn() returns null — retried once, then the
  // task is "unreviewed" (never "approved"), and the run reports it.
  {
    const stubs = makeStubs('null')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      fixture,
    )
    assert.equal(result.tasks.find((t) => t.key === 'A').status, 'unreviewed')
    assert.equal(result.tasks.find((t) => t.key === 'B').status, 'unreviewed')
    assert.ok(
      stubs.logs.some((l) => l.includes('retrying once')),
      'log records the retry',
    )
    assert.deepEqual([...result.unreviewed].sort(), ['A', 'B'], 'the run return value lists both keys under unreviewed')
    // exactly one retry per task: two review: calls each, no fix: calls
    // (an errored review is not a rejection — nothing to fix).
    const reviewCallsA = stubs.calls.filter((c) => c.opts && c.opts.label && c.opts.label.startsWith('review:A:'))
    assert.equal(reviewCallsA.length, 2, 'task A: initial review + exactly one retry')
    const fixCalls = stubs.calls.filter((c) => c.opts && c.opts.label && c.opts.label.startsWith('fix:'))
    assert.equal(fixCalls.length, 0, 'no fix agent is spawned for an errored review')
    // W2-N10c / Opus major 2: "unreviewed" is excluded from the merge list,
    // not only "unapproved" — mutating the branch filter to !== 'unapproved'
    // would let an unreviewed (review-errored) task carry its branch into the
    // wave merge. Nothing may integrate and nothing may deliver.
    assert.equal(
      byLabel(stubs.calls, 'integrate:w1'),
      undefined,
      'an unreviewed task is excluded from the merge — no integrate spawn',
    )
    assert.equal(result.delivered, false, 'the run is not delivered while a task is unreviewed')
  }

  // Scenario 4: the first review round rejects with a blocker — the fix
  // agent runs, and its prompt carries the same SKILL injection site
  // (skillLines('impl', t)) as the original implementer's, byte-exact.
  {
    const oneTaskArgs = JSON.parse(JSON.stringify(fixture))
    oneTaskArgs.tasks = [fixture.tasks[0]] // task A: kind 'code', has skillRefs
    const stubs = makeStubs('rejectThenApprove')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      oneTaskArgs,
    )

    const fixCall = byLabelPrefix(stubs.calls, 'fix:A:')
    assert.ok(fixCall, 'fix:A prompt was recorded (the rejecting review spawned the fix agent)')
    assert.equal(
      skillLineOf(fixCall.prompt),
      expectedSkillLine(P, 'impl', oneTaskArgs.tasks[0]),
      'fix-agent SKILL line is byte-exact, same site as the implementer prompt',
    )
    assert.match(fixCall.prompt, /"issue":\s*"bad"/, 'fix-agent prompt carries the blocking finding')

    const taskA = result.tasks.find((t) => t.key === 'A')
    assert.equal(taskA.status, 'approved', 'task approved after the fix round')
    assert.equal(taskA.fixRounds, 1, 'exactly one fix round ran')
    assert.equal(taskA.reviewNote, undefined, 'no F32 mismatch here: the rejecting review did cite a blocker')
  }

  // Scenario 5 (F32): a review returns approved=false with zero blocking
  // findings — the mismatch produces a reviewNote, and it reaches the run's
  // returned task list (not just the internal results array).
  {
    const oneTaskArgs = JSON.parse(JSON.stringify(fixture))
    oneTaskArgs.tasks = [fixture.tasks[0]]
    const stubs = makeStubs('approvedFalseNoBlocking')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      oneTaskArgs,
    )
    const taskA = result.tasks.find((t) => t.key === 'A')
    assert.equal(taskA.status, 'approved', 'zero blocking findings still counts as approved')
    assert.equal(
      taskA.reviewNote,
      'reviewer returned approved=false without blocking findings',
      'reviewNote reaches the returned task, not just the internal results array',
    )
    assert.ok(
      stubs.logs.some((l) => l.includes('WARNING') && l.includes('reviewer returned approved=false')),
      'the mismatch is logged',
    )
  }

  // Scenario 6: the header comment (above `export const meta`) documents
  // the models.audit override and the skills/skillRefs args.
  {
    const metaIdx = src.indexOf('export const meta')
    assert.ok(metaIdx > 0, 'sanity: "export const meta" found in dark-factory.js')
    const header = src.slice(0, metaIdx)
    assert.match(header, /^\/\/\s+models\b[^\n]*\baudit\b/m, 'header documents the models.audit override')
    assert.match(header, /\bskills\b/, 'header documents the skills arg')
    assert.match(header, /skillRefs/, 'header documents tasks[].skillRefs')
  }

  // Scenario 7: a malformed graph refuses before any agent is spawned.
  {
    for (const [mutate, needle] of [
      [
        (a) => {
          a.tasks[0].dependsOn = ['ZZ']
        },
        /unknown task ZZ/,
      ],
      [
        (a) => {
          a.tasks[0].dependsOn = ['B']
          a.tasks[1].dependsOn = ['A']
        },
        /cycle/,
      ],
      [
        (a) => {
          a.tasks.push({ ...a.tasks[0] })
        },
        /duplicate task key A/,
      ],
      [
        (a) => {
          a.tasks[0].kind = 'prose'
        },
        /unknown kind prose/,
      ],
      [
        (a) => {
          a.tasks[0].spec = ''
        },
        /empty spec/,
      ],
      [
        (a) => {
          a.tasks[1].key = 'B C'
        },
        /not a valid git branch name/,
      ],
      [
        (a) => {
          a.tasks[1].key = '-lead'
        },
        /not a valid git branch name/,
      ],
    ]) {
      const bad = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      mutate(bad)
      const stubs = makeStubs('ok')
      await assert.rejects(
        () =>
          runScript(
            stubs.agentFn,
            stubs.parallel,
            stubs.pipeline,
            stubs.phase,
            stubs.logFn,
            stubs.workflow,
            stubs.budget,
            bad,
          ),
        needle,
      )
      assert.equal(stubs.calls.length, 0, 'no agent is spawned when the task graph is malformed')
    }
  }

  // Scenario 8: waves, groups, and real concurrency.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.deepEqual(result.schedule.waves, [['A', 'B', 'C'], ['D']], 'Kahn waves, keys sorted')
    assert.deepEqual(
      result.schedule.groups[0],
      [['A', 'C'], ['B']],
      'A and C share pkgs/a and serialise; B runs alongside them',
    )
    assert.ok(stubs.overlaps.has('impl:A|impl:B'), 'A and B are in flight at the same time')
    assert.ok(!stubs.overlaps.has('impl:A|impl:C'), 'A and C never overlap — their touches collide')
    assert.equal(
      stubs.seq.indexOf('impl:C') > stubs.seq.indexOf('impl:A'),
      true,
      'C follows A inside the group, in key order',
    )
    assert.ok(
      stubs.seq.indexOf('impl:D') > stubs.seq.indexOf('integrate:w1'),
      'wave 2 starts only after wave 1 is integrated',
    )
    // sorted: results are pushed in group-completion order (A,C then B), not key order
    assert.deepEqual(result.tasks.map((t) => [t.key, t.wave]).sort(), [
      ['A', 1],
      ['B', 1],
      ['C', 1],
      ['D', 2],
    ])
    assert.ok(stubs.logsBeforeFirstAgent() > 0, 'the schedule is logged before the first agent is dispatched')
    assert.ok(
      stubs.logs.some((l) => l.includes('serialised: A, C (touches overlap)')),
      'the overlap note is printed',
    )
  }

  // Scenario 9: isolation, branches and integration.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    for (const c of stubs.calls) {
      const l = (c.opts && c.opts.label) || ''
      if (/^(impl|fix|review|integrate|integfix):/.test(l) || l === 'verify') {
        assert.equal(c.opts.isolation, 'worktree', `${l} runs in an isolated worktree`)
      }
      if (l === 'baseline' || l === 'deliver' || l.startsWith('judge:')) {
        assert.equal(c.opts.isolation, undefined, `${l} needs no worktree of its own`)
      }
    }
    const implA = byLabel(stubs.calls, 'impl:A')
    assert.match(
      implA.prompt,
      /git checkout -B A factory\/sched-integration/,
      'the implementer starts from the integration tip on its own branch',
    )
    assert.ok(!implA.prompt.includes('Do not create branches or worktrees'), 'the old single-writer rule is gone')
    assert.match(implA.prompt, /work only in the isolated worktree you were started in/i)
    const integ = byLabel(stubs.calls, 'integrate:w1')
    assert.match(integ.prompt, /git merge --no-ff/, 'integration merges are --no-ff')
    assert.match(integ.prompt, /A, B, C/, 'branches are merged in topological, then key, order')
    assert.equal(result.integrationBranch, 'factory/sched-integration')
    assert.equal(
      result.delivered,
      true,
      'verify passed, so the integration branch was fast-forwarded into the current branch',
    )
    assert.match(byLabel(stubs.calls, 'deliver').prompt, /git merge --ff-only factory\/sched-integration/)
  }

  // Scenario 10: a failed dependency blocks, never runs; and a red integration stops one chain after exactly one fix.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      // The overrides below short-circuit before inner (the track-wrapped
      // dispatch that records calls), so record these three explicitly or the
      // assertions below would see a missing integfix call.
      if (l === 'impl:A' || l === 'integrate:w1' || l === 'integfix:w1') stubs.calls.push({ prompt: p, opts: o })
      if (l === 'impl:A')
        return {
          commit: '',
          summary: '',
          tests_run: [],
          test_results: '',
          deviations: '',
          blocked: true,
          blocked_reason: 'spec impossible',
        }
      if (l === 'integrate:w1')
        return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'unit FAILED' }
      if (l === 'integfix:w1') return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'still red' }
      return inner(p, o)
    }
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const d = result.tasks.find((t) => t.key === 'D')
    assert.equal(d.status, 'blocked')
    assert.deepEqual(d.blockedBy, ['A'])
    assert.equal(byLabel(stubs.calls, 'impl:D'), undefined, 'a blocked task is never dispatched')
    assert.equal(
      stubs.calls.filter((c) => c.opts.label === 'integfix:w1').length,
      1,
      'exactly one bounded integration fix, no loop',
    )
    assert.equal(
      byLabel(stubs.calls, 'integfix:w1').opts.model,
      'opus',
      'the integration fix runs on the technical authority',
    )
    assert.match(byLabel(stubs.calls, 'integfix:w1').prompt, /unit FAILED/, 'the fix agent is given the check output')
    assert.equal(result.delivered, false, 'nothing is delivered while the merged tree is red')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined)
  }

  // Scenario 11: the judge is consulted only for un-annotated tasks, is recorded, and is switchable.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    delete args.tasks[1].touches // B is now un-annotated
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.ok(byLabel(stubs.calls, 'judge:B'), 'the un-annotated task is judged')
    assert.equal(byLabel(stubs.calls, 'judge:A'), undefined, 'an annotated task is never judged')
    assert.deepEqual(result.schedule.judged, [
      { key: 'B', touches: ['pkgs/guessed'], reasoning: 'guessed from the spec text' },
    ])
    assert.ok(
      stubs.logs.some((l) => l.includes('judge: B touches pkgs/guessed')),
      'the judge answer is printed, never silent',
    )

    const off = JSON.parse(JSON.stringify(args))
    off.judge = false
    const s2 = makeStubs('ok')
    const r2 = await runScript(s2.agentFn, s2.parallel, s2.pipeline, s2.phase, s2.logFn, s2.workflow, s2.budget, off)
    assert.equal(byLabel(s2.calls, 'judge:B'), undefined, 'args.judge=false consults no judge')
    assert.deepEqual(
      r2.schedule.groups[0],
      [['A', 'B', 'C']],
      'with no annotation and no judge, B serialises with everything',
    )
  }

  // Scenario 12 (N10FIX finding 1 + W2-N10b): the implementer block keeps the
  // single-writer git bans; the orchestration roles (baseline, integrator,
  // integfix, deliver) get a block that permits their exact git operations,
  // so their prompts must NOT carry the three implementer-only clauses, and
  // the integfix prompt must NOT forbid the hand-edits its own conflict
  // resolution demands.
  {
    const forbidden = ['NEVER merge', 'NEVER move or delete another branch', 'NEVER write inside']

    // Clean run: baseline, integrator and deliver all render; no integfix.
    {
      const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      const stubs = makeStubs('ok')
      await runScript(
        stubs.agentFn,
        stubs.parallel,
        stubs.pipeline,
        stubs.phase,
        stubs.logFn,
        stubs.workflow,
        stubs.budget,
        args,
      )
      const implA = byLabel(stubs.calls, 'impl:A')
      assert.ok(implA, 'impl:A prompt recorded')
      for (const s of forbidden) assert.ok(implA.prompt.includes(s), `implementer prompt still forbids "${s}"`)
      for (const label of ['baseline', 'integrate:w1', 'deliver']) {
        const c = byLabel(stubs.calls, label)
        assert.ok(c, `${label} prompt recorded`)
        for (const s of forbidden) assert.ok(!c.prompt.includes(s), `${label} prompt must not contain "${s}"`)
      }
      assert.equal(byLabel(stubs.calls, 'integfix:w1'), undefined, 'no integfix in a clean run')
    }

    // Conflict run: the integfix prompt also gets the orchestration block.
    {
      const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      const stubs = makeStubs('ok')
      const inner = stubs.agentFn
      stubs.agentFn = async (p, o) => {
        const l = (o && o.label) || ''
        if (l === 'integrate:w1') {
          stubs.calls.push({ prompt: p, opts: o })
          return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'unit FAILED' }
        }
        if (l === 'integfix:w1') {
          stubs.calls.push({ prompt: p, opts: o })
          return { merged: [], conflict: '', checks_green: true, head: 'def5678', output: 'ok' }
        }
        return inner(p, o)
      }
      await runScript(
        stubs.agentFn,
        stubs.parallel,
        stubs.pipeline,
        stubs.phase,
        stubs.logFn,
        stubs.workflow,
        stubs.budget,
        args,
      )
      const integfix = byLabel(stubs.calls, 'integfix:w1')
      assert.ok(integfix, 'integfix prompt recorded')
      for (const s of forbidden) assert.ok(!integfix.prompt.includes(s), `integfix prompt must not contain "${s}"`)
      // W2-N10b: the orchestration block must not forbid the hand-edits its
      // own conflict-resolution instruction demands — assert it positively,
      // not only via the removed strings above.
      assert.ok(
        !integfix.prompt.includes('never edit tracked files by hand'),
        'integfix prompt no longer forbids editing tracked files by hand',
      )
      // W2-N10c / Opus major 3: match the whole permissive sentence, not a
      // fragment — a contradictory clause like "NEVER edit a tracked file,
      // not even to resolve a merge conflict your instructions name" still
      // contains the fragment and would slip past a fragment match.
      assert.match(
        integfix.prompt,
        /Do not edit a tracked file except to resolve a merge conflict your instructions name, and commit nothing but that resolution or a file your instructions name\./,
        'integfix prompt permits exactly the conflict resolution it names (whole permissive sentence)',
      )
      assert.doesNotMatch(
        integfix.prompt,
        /NEVER edit a tracked file/i,
        'integfix prompt never forbids editing a tracked file',
      )
    }
  }

  // Scenario 13 (N10FIX finding 2): a wave whose integration fails twice
  // marks its approved tasks 'integration-failed' in the RETURNED tasks[]
  // (not only the internal statusOf map).
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      if (l === 'integrate:w1' || l === 'integfix:w1') stubs.calls.push({ prompt: p, opts: o })
      if (l === 'integrate:w1')
        return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'unit FAILED' }
      if (l === 'integfix:w1') return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'still red' }
      return inner(p, o)
    }
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const status = Object.fromEntries(result.tasks.map((t) => [t.key, t.status]))
    assert.equal(status.A, 'integration-failed', 'A approved pre-integration but its wave failed to integrate')
    assert.equal(status.B, 'integration-failed', 'B approved pre-integration but its wave failed to integrate')
    assert.equal(status.C, 'integration-failed', 'C approved pre-integration but its wave failed to integrate')
    assert.equal(status.D, 'blocked', 'D is blocked because A is no longer approved')
    assert.equal(result.delivered, false, 'nothing is delivered while the merged tree is red')
    // W2-N10c / Opus major 4 (two-wave case): the not-delivered line names
    // A/B/C's integration failure, not just "D not approved" — the summary
    // derives from statusOf, which the integration-failure downgrade writes.
    assert.equal(
      stubs.logs.find((l) => l.startsWith('NOT delivered — ')),
      'NOT delivered — A (integration-failed), B (integration-failed), C (integration-failed), D (blocked); factory/sched-integration holds the work (fast-forward by hand: cd /home/dalhaka/nixos-agent-env && git merge --ff-only factory/sched-integration)',
      'the not-delivered line names every non-approved task with its statusOf status',
    )
  }

  // Scenario 14 (W2-N10c / Opus major 4, single-wave case): a single wave
  // whose tasks were all approved pre-integration but whose integration is
  // red twice must read as "integration-failed", not "no tasks approved".
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    args.tasks = args.tasks.slice(0, 2) // A, B — a single wave, no dependsOn
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      if (l === 'integrate:w1' || l === 'integfix:w1') stubs.calls.push({ prompt: p, opts: o })
      if (l === 'integrate:w1')
        return { merged: [], conflict: '', checks_green: false, head: '', output: 'unit FAILED' }
      if (l === 'integfix:w1') return { merged: [], conflict: '', checks_green: false, head: '', output: 'still red' }
      return inner(p, o)
    }
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.equal(result.delivered, false, 'nothing is delivered while the merged tree is red')
    assert.equal(
      stubs.logs.find((l) => l.startsWith('NOT delivered — ')),
      'NOT delivered — A (integration-failed), B (integration-failed); factory/sched-integration holds the work (fast-forward by hand: cd /home/dalhaka/nixos-agent-env && git merge --ff-only factory/sched-integration)',
      'the not-delivered line names the integration failure, not "no tasks approved"',
    )
  }

  // Scenario 15 (W2-N10c / Opus major 4, verify-failed case): every task
  // approved and integrated, but the whole-run verifier returns verdict
  // 'fail' — the not-delivered line says verify failed, not "no tasks approved".
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      if (l === 'verify')
        return {
          flake_check_green: false,
          toplevel_built: false,
          closure_diff: '',
          commits: [],
          verdict: 'fail',
          notes: 'flake check red',
        }
      return inner(p, o)
    }
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.equal(result.delivered, false, 'nothing is delivered when verify fails')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined, 'no deliver agent is spawned when verify fails')
    assert.equal(
      stubs.logs.find((l) => l.startsWith('NOT delivered — ')),
      'NOT delivered — verify failed; factory/sched-integration holds the work (fast-forward by hand: cd /home/dalhaka/nixos-agent-env && git merge --ff-only factory/sched-integration)',
      'the not-delivered line names verify failure, not "no tasks approved"',
    )
  }

  // Scenario 16 (N10FIX finding 3): args.concurrency of 0 or a negative
  // integer is refused before any agent is spawned.
  {
    for (const bad of [0, -1, -2]) {
      const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      args.concurrency = bad
      const stubs = makeStubs('ok')
      await assert.rejects(
        () =>
          runScript(
            stubs.agentFn,
            stubs.parallel,
            stubs.pipeline,
            stubs.phase,
            stubs.logFn,
            stubs.workflow,
            stubs.budget,
            args,
          ),
        /concurrency must be an integer >= 1/,
      )
      assert.equal(stubs.calls.length, 0, 'no agent is spawned for an invalid concurrency')
    }
  }

  // Scenario 17 (W2-N10a): a task that stays unapproved through every fix
  // round is withheld from its wave's merge list, and the run is not
  // delivered.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('rejectAAlways')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const integ = byLabel(stubs.calls, 'integrate:w1')
    assert.match(
      integ.prompt,
      /\)": B, C\. /,
      'wave-1 merge list is exactly B, C — unapproved A is withheld, not merged',
    )
    assert.ok(
      stubs.logs.some((l) => l.includes('withheld') && l.includes('A')),
      'a log line names A as withheld from the merge',
    )
    assert.equal(result.delivered, false, 'the run is not delivered while A is unapproved')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined, 'no deliver agent is spawned')
    assert.equal(
      stubs.logs.find((l) => l.startsWith('NOT delivered — ')),
      'NOT delivered — A (unapproved), D (blocked); factory/sched-integration holds the work (fast-forward by hand: cd /home/dalhaka/nixos-agent-env && git merge --ff-only factory/sched-integration)',
      'the not-delivered line names every non-approved key with its status',
    )
  }

  // Scenario 18 (W2-N10a): a task group that vanishes (its thunk throws and
  // the harness's parallel() swallows it to null) is recorded as 'unreported',
  // every task still appears in the returned list, and the run is not
  // delivered.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      if (l === 'impl:B') throw new Error('impl:B infrastructure failure')
      return inner(p, o)
    }
    const swallow = async (thunks) => Promise.all(thunks.map((t) => t().catch(() => null)))
    const result = await runScript(
      stubs.agentFn,
      swallow,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.equal(result.tasks.length, 4, 'every task still appears in the returned tasks[]')
    const b = result.tasks.find((t) => t.key === 'B')
    assert.ok(b, 'task B is present in the returned list')
    assert.equal(b.status, 'unreported', 'B is reported as unreported, not silently dropped')
    assert.equal(result.delivered, false, 'the run is not delivered while B is unreported')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined, 'no deliver agent is spawned')
  }

  // Scenario 19 (W2-N10c / Opus major 1): a harness parallel() that DROPS a
  // group's results (returns a shorter array than it was given) must not
  // deliver — the results.length === args.tasks.length delivery-gate term is
  // what catches a short tasks[] that would otherwise read as "everything
  // approved". Deleting that term flips delivered false → true here.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const dropLastGroup = async (thunks) => {
      const r = await Promise.all(thunks.map((t) => t()))
      r.pop()
      return r
    }
    const result = await runScript(
      stubs.agentFn,
      dropLastGroup,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.ok(result.tasks.length < args.tasks.length, 'a dropped group leaves tasks[] short of args.tasks')
    assert.equal(result.delivered, false, 'the run is not delivered while tasks are missing')
  }

  // Scenario 20 (W2-N10a): when no task is approved (nothing to integrate),
  // the whole-run verifier is skipped and reported as verify=skipped.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('rejectAlways')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    assert.equal(byLabel(stubs.calls, 'verify'), undefined, 'no verifier is spawned when nothing was integrated')
    assert.equal(result.verify.verdict, 'skipped', 'the run reports verify=skipped')
    assert.equal(result.delivered, false, 'nothing is delivered when nothing was integrated')
    assert.ok(
      stubs.logs.some((l) => l.includes('verify=skipped')),
      'the skip is logged',
    )
  }

  // Scenario 21 (W2-N10b): args.extraRules is appended LAST in the rules
  // block — after the role paragraph (the implementer's single-writer clause
  // or the orchestrator's operation clause), so a caller's rule text is the
  // final word rather than buried mid-block.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    args.extraRules = 'EXTRA-RULES-SENTINEL'
    const stubs = makeStubs('ok')
    await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const implA = byLabel(stubs.calls, 'impl:A')
    const integ = byLabel(stubs.calls, 'integrate:w1')
    assert.ok(implA.prompt.includes('EXTRA-RULES-SENTINEL'), 'extraRules reach the implementer prompt')
    assert.ok(integ.prompt.includes('EXTRA-RULES-SENTINEL'), 'extraRules reach the orchestrator prompt')
    assert.ok(
      implA.prompt.indexOf('EXTRA-RULES-SENTINEL') > implA.prompt.indexOf('Work only in the isolated worktree'),
      'extraRules are appended after the single-writer paragraph (last in the implementer block)',
    )
    assert.ok(
      integ.prompt.indexOf('EXTRA-RULES-SENTINEL') > integ.prompt.indexOf('You are an orchestration agent'),
      'extraRules are appended after the orchestration paragraph (last in the orchestration block)',
    )
  }

  // Scenario 22 (N12 / board rule A1): a stubbed reviewer returning rework
  // forever is capped at exactly two fix rounds (the FIX_ROUNDS default). The
  // task is recorded not-approved with its fixRounds in the run summary, the
  // bounded fix logic spawns exactly two fix agents (no unbounded loop), and
  // the run is not delivered.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    args.tasks = [
      {
        key: 'A',
        title: 'A rework forever',
        kind: 'code',
        checks: ['unit'],
        spec: 'A spec.',
        touches: ['pkgs/a/a.sh'],
        dependsOn: [],
      },
    ]
    const stubs = makeStubs('rejectAlways')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const taskA = result.tasks.find((t) => t.key === 'A')
    assert.equal(taskA.status, 'unapproved', 'a rework-forever code task is marked not-approved')
    assert.equal(taskA.fixRounds, 2, 'a rework-forever reviewer is capped at exactly two fix rounds')
    const fixCalls = stubs.calls.filter((c) => c.opts && c.opts.label && c.opts.label.startsWith('fix:A:'))
    assert.equal(fixCalls.length, 2, 'the bounded fix logic stops after FIX_ROUNDS: exactly two fix agents spawn')
    assert.equal(result.delivered, false, 'the run is not delivered while a task is unapproved')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined, 'no deliver agent is spawned')
    // A1: no chain in a run may report more than two fix rounds.
    for (const t of result.tasks) {
      assert.ok(t.fixRounds <= 2, `task ${t.key} reports fixRounds ${t.fixRounds} > 2`)
    }
  }

  // Scenario 23 (N12 / board rule A1): validateGraph refuses, before any
  // agent dispatch, a code task whose checks array is empty or absent — the
  // message names the task key — while a docs task may still omit checks
  // (docs behaviour is unchanged).
  {
    const base = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    for (const mutate of [
      (a) => {
        a.tasks[0].checks = []
      },
      (a) => {
        delete a.tasks[0].checks
      },
    ]) {
      const bad = JSON.parse(JSON.stringify(base))
      mutate(bad)
      const stubs = makeStubs('ok')
      await assert.rejects(
        () =>
          runScript(
            stubs.agentFn,
            stubs.parallel,
            stubs.pipeline,
            stubs.phase,
            stubs.logFn,
            stubs.workflow,
            stubs.budget,
            bad,
          ),
        /task A names no checks/,
      )
      assert.equal(stubs.calls.length, 0, 'no agent is spawned when a code task names no checks')
    }

    // A docs task without checks still runs and approves — behaviour unchanged.
    const docsArgs = JSON.parse(JSON.stringify(base))
    docsArgs.tasks = [
      { key: 'D', title: 'docs only', kind: 'docs', spec: 'D spec.', touches: ['docs/d.md'], dependsOn: [] },
    ]
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      docsArgs,
    )
    assert.equal(
      result.tasks.find((t) => t.key === 'D').status,
      'approved',
      'a docs task without checks still runs and approves',
    )
  }

  // Scenario 24 (N18 / board rule A1): args.fixRounds above 2 is refused in
  // validateGraph before any agent is dispatched, and the message names the
  // cap (2) — so a human typo can't silently multiply the review budget.
  {
    for (const bad of [3, 5, 99]) {
      const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      args.fixRounds = bad
      const stubs = makeStubs('ok')
      await assert.rejects(
        () =>
          runScript(
            stubs.agentFn,
            stubs.parallel,
            stubs.pipeline,
            stubs.phase,
            stubs.logFn,
            stubs.workflow,
            stubs.budget,
            args,
          ),
        /fixRounds must not exceed 2/,
        `args.fixRounds=${bad} is refused with a message naming the cap`,
      )
      assert.equal(stubs.calls.length, 0, `no agent is spawned for args.fixRounds=${bad}`)
    }
  }

  // Scenario 26 (E3): attribution in every structured result, an observation
  // from the verifier, and a recorder that persists the run report.
  {
    const stubs = makeStubs('ok')
    const out = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      { ...fixture, tasks: [{ key: 'A', title: 'a', kind: 'code', checks: ['unit'], spec: 's' }] },
    )
    const impl = byLabel(stubs.calls, 'impl:A')
    for (const k of ['task_key', 'round', 'label'])
      assert.ok(impl.opts.schema.required.includes(k), `IMPL_SCHEMA requires ${k}`)
    assert.match(impl.prompt, /set task_key to "A", round to 0 and label to "impl:A"/i)
    const review = byLabel(stubs.calls, 'review:A:r1')
    for (const k of ['task_key', 'round', 'label'])
      assert.ok(review.opts.schema.required.includes(k), `REVIEW_SCHEMA requires ${k}`)
    assert.match(review.prompt, /set task_key to "A", round to 0 and label to "review:A:r1"/i)
    const verify = byLabel(stubs.calls, 'verify')
    assert.ok(verify.opts.schema.required.includes('evidence_recorded'), 'VERIFY_SCHEMA requires evidence_recorded')
    assert.match(
      verify.prompt,
      /pkgs\/evidence\/evidence\.py --store "\$\{EVIDENCE_STORE:-\/var\/lib\/evidence\}" record-check --name flake-check --rev \$\(git rev-parse HEAD\)/,
    )
    assert.match(verify.prompt, /--class nix-check --src dark-factory-verify/)
    const recorder = byLabel(stubs.calls, 'recorder')
    assert.ok(recorder, 'a recorder agent is spawned at the end of the run')
    assert.match(recorder.prompt, /"kind":"factory-run"/)
    assert.match(recorder.prompt, /"delivered":true/)
    assert.match(recorder.prompt, /"key":"A","status":"approved"/)
    assert.match(
      recorder.prompt,
      /pkgs\/evidence\/evidence\.py --store "\$\{EVIDENCE_STORE:-\/var\/lib\/evidence\}" record runs --json/,
    )
    assert.equal(recorder.opts.model, 'sonnet')
    assert.equal(out.recorded, true, 'the run reports that it was recorded')
    // the docs single-pass reviewer carries the same attribution sentence
    const stubsD = makeStubs('ok')
    await runScript(
      stubsD.agentFn,
      stubsD.parallel,
      stubsD.pipeline,
      stubsD.phase,
      stubsD.logFn,
      stubsD.workflow,
      stubsD.budget,
      { ...fixture, tasks: [{ key: 'B', title: 'b', kind: 'docs', spec: 's' }] },
    )
    assert.match(
      byLabel(stubsD.calls, 'review:B:r1').prompt,
      /set task_key to "B", round to 0 and label to "review:B:r1"/i,
    )
  }

  // Scenario 25 (N18): a task whose checks array is exactly ["none"] must not
  // have its implementer prompt read "Named checks for this task: none."
  // (the degraded empty-case sentence) — print the literal list instead so a
  // caller who writes ["none"] to get past the guard can see the actual list.
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    args.tasks = [
      {
        key: 'A',
        title: 'A literal none',
        kind: 'code',
        checks: ['none'],
        spec: 'A spec.',
        touches: ['pkgs/a/a.sh'],
        dependsOn: [],
      },
    ]
    const stubs = makeStubs('ok')
    const result = await runScript(
      stubs.agentFn,
      stubs.parallel,
      stubs.pipeline,
      stubs.phase,
      stubs.logFn,
      stubs.workflow,
      stubs.budget,
      args,
    )
    const implA = byLabel(stubs.calls, 'impl:A')
    assert.ok(implA, 'impl:A prompt recorded')
    assert.ok(
      !implA.prompt.includes('Named checks for this task: none.'),
      'checks ["none"] must not collapse into the empty-case "none" sentence',
    )
    assert.ok(implA.prompt.includes('["none"]'), 'the literal ["none"] list is printed')
    assert.equal(
      result.tasks.find((t) => t.key === 'A').status,
      'approved',
      'a ["none"] task still dispatches and approves against stubs',
    )
  }

  // Scenario 27 (RT2): dark-factory.js's built-in default `models` map must
  // equal `route.py models` for the committed docs/ledger/routing.toml. The
  // table is the single source: the default map is the harness-readable copy
  // of route.py's derivation and must not drift from it. This sandbox and the
  // lint gate both copy route.py + the table (checks.factory-unit, flake.nix),
  // so the comparison always runs the live derivation — a table-only drift
  // fails here, not only in the pre-commit hook.
  {
    // The default map is the object literal assigned as the first argument of
    // Object.assign (flat: no nested braces), so a regex over the source is a
    // reliable extraction that does not depend on the model values.
    const m = src.match(/const M = Object\.assign\(\s*(?:\/\/[^\n]*\n\s*)*(\{[^}]*\}),\s*A\.models/)
    assert.ok(m, 'could not find the default models literal in dark-factory.js')
    const jsDefault = new Function(`return (${m[1]})`)()
    assert.deepEqual(
      Object.keys(jsDefault).sort(),
      ['audit', 'baseline', 'impl', 'reviewCode', 'reviewDocs', 'verify'].sort(),
    )
    const routePy = path.join(__dirname, '..', '..', 'tools', 'factory', 'route.py')
    const table = path.join(__dirname, '..', '..', 'docs', 'ledger', 'routing.toml')
    const routeModels = JSON.parse(
      execFileSync('python3', [routePy, '--file', table, 'models'], { encoding: 'utf8' }).trim(),
    )
    assert.deepEqual(
      jsDefault,
      routeModels,
      'dark-factory.js default models must equal route.py models for the committed table',
    )
  }

  console.log('render.test.mjs: all assertions passed')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
