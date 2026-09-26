# M2b — reasoning effort off vs medium (n=1 per arm)

| effort | input | output | reasoning chunks | s | verdict | notable |
|---|---|---|---|---|---|---|
| off | 176,196 | 3,478 | 0 (0 blocks, 0 B) | 86 | approve | 8 lines; all four required facts; one 80-char line breaks the README's 76-col wrap |
| medium | 205,958 | 7,757 | 1,290 (17 blocks, 17,435 B) | 124 | approve | 12 lines; adds `off`→wire `none` and `env > saved > route default`; commit body name-drops "the M2 measurement task" |

## Wire and reasoning (transcripts)

`request/header.data.header.config.reasoningEffort` is literally `"off"` and
`"medium"` in the two sessions — the env var reached the wire in both. Medium
streamed 166 `reasoning-chunks` records = 1,290 text chunks = 17,435 bytes
across 17 blocks (steps 1–18); off streamed none. So yes, the provider is
visibly reasoning at medium.

**No usage record carries reasoning tokens.** The key union over every
`assistant/message.data.usage` is `{inputTokens, outputTokens, cacheReadTokens,
totalTokens}` in both arms — no `reasoningTokens` field exists anywhere in
either transcript, which is why the `.result` line reads `"reasoning": 0` even
for the medium run. The output delta (+4,279) is close to 17,435 B ÷ ~4 B/tok
≈ 4,360, consistent with reasoning being billed inside `outputTokens` but never
itemised. Not proven — medium also wrote a longer hunk and commit body.

## Review

Both are accurate against `pkgs/dsh-openrouter/dsh-openrouter.sh` @ `task/N21b`
(picker levels lines 150/403; default medium line 79; the pre-boot selection
write lines 237–320; `off: none` line 420) and against the real fake upstream
(`tests/unit/70-dsh-openrouter.bats` + `tests/mocks/openai-fake.py`, which
capture only the request). Both are under the 15-line cap, fit the README's
prose-and-backticks style, carry the `docs: … (test: lint)` subject and both
trailers, and pass lint. Neither needs rework.

## Conclusion

Medium bought two extra true facts — the `none` wire spelling and the
precedence chain — for +17% input, +123% output, +44% wall clock. Real but
small: the off arm already satisfied the brief. **Recommend `off` as the seat
default for XS docs tasks and for factory implementers**, reserving medium for
tasks with a real decision in them. n=1 per arm; treat as a signal, not a
result.
