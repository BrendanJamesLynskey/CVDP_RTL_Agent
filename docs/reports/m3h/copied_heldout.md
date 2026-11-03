#### Problem-runs whose own files reproduce pack text (descriptive; added in the second amendment)

Made locally by `tools/m3h_copied.py` with the private `v2.0` checkout, the same public set (the dataset) for every arm, and without the v1.0 allowance, so the arms are comparable. It scans the model files left in each sweep's artifacts (patch, agent_out, agent_tb, report logs) and adds each sweep's `withheld.csv` (files the guard removed before upload). A is a control for chance matches: no pack was installed. Names and counts only.

| Arm | Problem-runs | Reproducing pack text (≥ 80 bytes) | Skills (problem-runs) |
|---|---|---|---|
| S1c | 300 | 0 (0.0%) | none |
| S2c | 300 | 1 (0.3%) | `valid-ready-handshake` 1 |
| S2 (no hint) | 100 | 0 (0.0%) | none |
| A (no pack installed; control for chance matches) | 300 | 0 (0.0%) | none |
