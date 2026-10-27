# Compiled paths the agent cannot reach

Made by `tools/reachable.py --paths-md-out` from the dataset's hidden harness files (the revision pinned in `sweep.yml`; all 92 problems of the agentic split) and M3's 14 runs. It adds the check brief 09 found missing (`unsolved_analysis.md`, `sync_serial_communication_0001`): every source file the hidden harness compiles (`VERILOG_SOURCES` in its `.env` files) must be a file the task gives, a path or file name the prompt or a document writes, or a module name the task gives with the extension of the stated language. Otherwise the path is unreachable:

- `unnamed_file`: the file's stem is no name the task gives;
- `extension_mismatch`: the stem is a given module name, but the extension belongs to the other language (`.sv` while the prompt says only "Verilog", or `.v` while it says only "SystemVerilog"), and no given `rtl/` file has that extension.

**The M3b evaluation set is not changed.** `tools/m3b_eval_ids.txt` is frozen, because every scored result since M3b depends on it. This report says what the check would have excluded.

## Summary

- **4 of 92 problems** compile a path the agent cannot reach; 4 of them are in the 86-problem evaluation set.
- **3 evaluation problem(s) would have been excluded** under M3b's rule (unreachable name or path, and M3 labels the problem `signal_missing_hidden` or `compile_fail_hidden` in at least half of its 14 runs): `cache_controller_0001`, `sigma_delta_audio_0001`, `sync_serial_communication_0001`.
- Against `tools/benchmark_limited_ids.txt` (7 problems): the path check flags `cache_controller_0001`, `sync_serial_communication_0001`; it does not flag `dynamic_equalizer_0008`, `elevator_control_0004`, `rc5_0001`, `secure_apb_history_shift_register_0001`, `traffic_light_controller_0001`, whose causes are behaviour or values, not file paths (except where the given-RTL note below applies). Flagged and not in that list: `sigma_delta_audio_0001`, `spi_complex_mult_0002`.
- A flagged path with few interface or compile failures in M3 is one the agent happened to guess (for example the `.sv` extension when the prompt says "Verilog"): it is kept under M3b's rule, but it is still a gap in the task.

## Unreachable compiled paths

| Problem | In eval set | Path | Reason | Interface/compile failures in M3 | Excluded under M3b's rule with paths |
|---|---|---|---|---|---|
| `cache_controller_0001` | yes | `rtl/cache_controller.sv` | `extension_mismatch` | 13/14 | yes |
| `sigma_delta_audio_0001` | yes | `rtl/sigma_delta_audio.sv` | `extension_mismatch` | 14/14 | yes |
| `spi_complex_mult_0002` | yes | `rtl/spi_complex_mult.sv` | `extension_mismatch` | 0/14 | no |
| `sync_serial_communication_0001` | yes | `rtl/sync_serial_communication_top.sv` | `unnamed_file` | 13/14 | yes |

## Note: given RTL that no `.env` compiles

Not an unreachable reason by itself: it matters only when the design instantiates the given file from its own file, as the task invites in `rc5_0001` ("choose the appropriate CA design"). A design that does fails to compile; one that copies the module into a compiled file does not.

| Problem | In eval set | Given `rtl/` files not compiled |
|---|---|---|
| `DES_0003` | yes | `rtl/des_enc.sv` |
| `binary_search_tree_algorithms_0014` | yes | `rtl/binary_search_tree_sort_construct.sv` |
| `rc5_0001` | yes | `rtl/CA_1.sv`, `rtl/CA_2.sv`, `rtl/CA_3.sv`, `rtl/CA_4.sv` |
