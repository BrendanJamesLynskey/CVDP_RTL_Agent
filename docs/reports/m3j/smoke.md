# M3j smoke runs (plumbing, not results)

2026-11-03, after PR #50 merged (agent image from 2b1c327), `split=m3g_smoke` (3 problems), 1 seed, Claude Haiku 5.5,
`ubuntu-24.04-arm`. Rows from each run's `results.csv`; none of them is a result.

| Arm | Run | Passed | Stop reasons | `cc_tools` | `cc_api_key_source` | Input tokens (incl. cache) | Estimate charged to the guard |
|---|---|---|---|---|---|---|---|
| PA (`cc_profile=plain`, `claude_endpoint=api`) | 41652673442 | 2/3 | submit ×3 | Bash;Edit;Read;Write | ANTHROPIC_API_KEY ×3 | 31,790 / 38,933 / 16,400 | $0.0105 (Claude Code's own figure) |
| B (`cc_profile=bare`, `claude_endpoint=api`) | 41652680449 | 2/3 | submit ×3 | Bash;Edit;Read | ANTHROPIC_API_KEY ×3 | 22,873 / 37,167 / 10,343 | $0.0096 (Claude Code's own figure) |
| R (`harness=apiloop`) | 41652686350 | 2/3 | submit ×3 | Read;Write;Edit;Bash | (no Claude Code) | 43,540 / 14,807 / 8,088 | $0.0614 (upper bound) |

Checked:

- Every PA and B row's init event reported `apiKeySource` `ANTHROPIC_API_KEY`: billed to the key, not the plan.
- B's init event lists three tools, as the local capture showed (`--bare` drops Write).
- R's prompt caching works: cache reads 32,698 / 8,636 / 4,392 tokens, cache writes 10,826 / 6,161 / 3,688.
- R's tool log (`api_tools.jsonl`) holds tool, path or command head, exit code and output size; its Bash guard
  refused one `git log` (the same programs the Claude Code arms deny). No network flags in any arm.
- No key- or token-shaped string in any downloaded artifact.
