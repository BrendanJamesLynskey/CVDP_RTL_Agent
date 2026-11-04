#### Pack skill use per arm

| Arm | Problem-runs | Pack skills offered (mean `skills_listed`) | Loading any pack skill | Distinct pack skills per loading run (mean) | First-load turn: median [min–max] | Pass rate, loading / not |
|---|---|---|---|---|---|---|
| R | 86 | — | — | — | — | — |
| T | 86 | — | — | — | — | — |
| K | 86 | — | — | — | — | — |

#### Bundled (Claude Code's own) skills loaded

| Arm | Problem-runs | Bundled skill calls |
|---|---|---|

#### Effort per arm (Claude Code's own counts; nothing billed per call)

| Arm | Problem-runs | Turns: median (mean) | Wall s: median | Wall-cap stops | Prompt tokens incl. cache, per run (mean) | Completion tokens per run (mean) |
|---|---|---|---|---|---|---|
| R | 86 | 7 (7.6) | 37 | 0 | 119,011 | 10,425 |
| T | 86 | 8 (9.8) | 60 | 0 | 180,380 | 15,524 |
| K | 86 | 7 (8.1) | 38 | 0 | 127,425 | 10,812 |

#### Stop reasons per arm

| Arm | Stop reasons |
|---|---|
| R | submit 86 |
| T | llm_error 2, submit 84 |
| K | llm_error 1, submit 85 |
