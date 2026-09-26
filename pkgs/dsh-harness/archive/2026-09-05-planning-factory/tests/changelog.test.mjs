import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..')

// T2 — CHANGELOG.md (task T1) is the record of the 2026-09-04 factory chain,
// one bullet per integrated commit "grouped by task". That grouping is only
// trustworthy if the changelog NAMES every landed task key. F7 is the one
// chain task that never landed (only its retry F7B did), so the landed set is
// X0, F1–F6, F8–F10. A key counts as named only as a whole word, so the
// "F10" heading cannot satisfy the "F1" assertion.

const LANDED_KEYS = ['X0', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F8', 'F9', 'F10']

test('the changelog names every landed task key', () => {
  const changelog = readFileSync(join(REPO_ROOT, 'CHANGELOG.md'), 'utf8')
  const missing = LANDED_KEYS.filter((key) => !new RegExp(`\\b${key}\\b`).test(changelog))
  assert.deepEqual(
    missing,
    [],
    `CHANGELOG.md must mention every landed task key; missing: ${missing.join(', ')}`
  )
})
