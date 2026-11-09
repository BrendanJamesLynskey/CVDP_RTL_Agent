#!/usr/bin/env python3
"""M4: pass rate and failure labels by task category, from the committed run CSVs. Stdlib only.

Run from the repo root:  python3 docs/reports/m4/categories.py
Writes docs/reports/m4/categories_data.json (read by the site), docs/reports/m4/categories_groups.csv and
docs/reports/m4/categories.md (hand-written text in HEAD and TAIL below, tables generated).

Rules:
- A "group" is one milestone's arm on one problem set with one model/harness; seeds of the same arm are pooled.
  Groups are never pooled with each other, and a pass rate is never compared across problem sets.
- Sets: dev86 (tools/m3b_eval_ids.txt), heldout100 (tools/m3g_heldout_ids.txt), m2_92 (the 92 agentic problems
  of M2/M3). Rows of a CSV whose id is not in the group's set are dropped.
- Pilots (M1's 10, reasoning_pick, M2a), smoke runs, M3b's excluded-problem runs and M3l's 13-problem subset are
  not groups. Fable's wall-cap reruns are a 30-problem top-up of the Claude Code run and are left out.
- Categories: cid002 RTL completion, cid003 spec to RTL, cid004 RTL modification, cid005 spec to RTL with module
  reuse, cid016 bug fixing. These are the only ones in the free split.
"""
import csv, glob, json, math, os, sys, collections

R = 'docs/reports'
CATS = {'cid002': 'RTL completion', 'cid003': 'spec to RTL', 'cid004': 'RTL modification',
        'cid005': 'spec to RTL, module reuse', 'cid016': 'bug fixing'}
LABELS = {
    'llm_error': 'provider error or missed call deadline',
    'agent_error': 'agent crashed',
    'killed': 'agent killed, no summary',
    'no_edit': 'finished without editing rtl/',
    'stopped_by_cap': 'stopped by a turn, budget or time cap',
    'gave_up': 'agent gave up',
    'sim_incomplete': 'hidden simulation never finished',
    'compile_fail_own': 'hidden build failed, own compile failed too',
    'compile_fail_hidden': 'hidden build failed (port or interface mismatch), own compile passed',
    'signal_missing_hidden': 'hidden test reads a signal or parameter name the design lacks',
    'tests_failed_selfcheck_passed': 'hidden tests failed, own testbench passed',
    'tests_failed_selfcheck_failed': 'hidden tests failed, own testbench failed, submitted anyway',
    'tests_failed_no_selfcheck': 'hidden tests failed, agent never ran a testbench',
    'harness_error': 'harness fault',
    'needs_artifacts': 'no evidence columns',
    'unclassified': 'no rule held',
}


def ids(path):
    return {l.strip() for l in open(path) if l.strip() and not l.startswith('#')}


SETS = {'dev86': ids('tools/m3b_eval_ids.txt'), 'heldout100': ids('tools/m3g_heldout_ids.txt')}
LIMITED = ids('tools/benchmark_limited_ids.txt')


def g(*pats):
    out = []
    for p in pats:
        out += sorted(glob.glob(os.path.join(R, p)))
    return out


# (key, set, milestone, model and harness, arm, files)
LUNA = 'OpenAI gpt-6-luna, LangGraph agent'
HAIKU_CC = 'Anthropic claude-haiku-5-5, Claude Code harness'
GROUPS = [
    ('m2x86_haiku', 'm2_92', 'M2', 'Anthropic claude-haiku-5.5 (low), LangGraph agent, x86', 'base', g('m2/x86/results_claude-haiku-5.5_low.csv')),
    ('m2x86_ds', 'm2_92', 'M2', 'DeepSeek deepseek-v4.1-flash-1017 (off), LangGraph agent, x86', 'base', g('m2/x86/results_deepseek*.csv')),
    ('m2x86_luna', 'm2_92', 'M2', 'OpenAI gpt-6-luna, LangGraph agent, x86', 'base', g('m2/x86/results_gpt-6-luna*.csv')),
    ('m2a64_haiku', 'm2_92', 'M2', 'Anthropic claude-haiku-5.5 (low), LangGraph agent, Arm64', 'base', g('m2/arm64/results_claude*.csv')),
    ('m2a64_ds', 'm2_92', 'M2', 'DeepSeek deepseek-v4.1-flash-1017 (off), LangGraph agent, Arm64', 'base', g('m2/arm64/results_deepseek*.csv')),
    ('m2a64_luna', 'm2_92', 'M2', 'OpenAI gpt-6-luna, LangGraph agent, Arm64', 'base', g('m2/arm64/results_gpt*.csv')),
    ('m3_A', 'm2_92', 'M3', LUNA, 'A base', g('m3/runs/A?_*.csv')),
    ('m3_B', 'm2_92', 'M3', LUNA, 'B self-check off', g('m3/runs/B?_*.csv')),
    ('m3_C', 'm2_92', 'M3', LUNA, 'C lint off', g('m3/runs/C?_*.csv')),
    ('m3_D', 'm2_92', 'M3', LUNA, 'D self-check and lint off', g('m3/runs/D?_*.csv')),
    ('m3_E', 'm2_92', 'M3', LUNA, 'E 5 turns', g('m3/runs/E?_*.csv')),
    ('m3_F', 'm2_92', 'M3', LUNA, 'F 20 turns', g('m3/runs/F?_*.csv')),
    ('m3_G', 'm2_92', 'M3', LUNA, 'G $0.02 budget', g('m3/runs/G?_*.csv')),
    ('m3b_A', 'dev86', 'M3b', LUNA, 'A LangGraph, no memory', g('m3b/runs/A?_*.csv', 'm3b/confirm_runs/A?_*.csv')),
    ('m3b_B', 'dev86', 'M3b', 'OpenAI gpt-6-luna, Deep Agents harness', 'B Deep Agents, no memory', g('m3b/runs/B?_*.csv', 'm3b/confirm_runs/B?_*.csv')),
    ('m3b_C', 'dev86', 'M3b', LUNA, 'C LangGraph, lessons memory', g('m3b/runs/C?_*.csv')),
    ('m3b_D', 'dev86', 'M3b', 'OpenAI gpt-6-luna, Deep Agents harness', 'D Deep Agents, lessons memory', g('m3b/runs/D?_*.csv')),
    ('m3c_A', 'dev86', 'M3c', LUNA, 'A base', g('m3c/runs/A?_*.csv')),
    ('m3c_I', 'dev86', 'M3c', LUNA, 'I interface check', g('m3c/runs/I?_*.csv')),
    ('m3c_M', 'dev86', 'M3c', LUNA, 'M mutation gate', g('m3c/runs/M?_*.csv')),
    ('m3d_A', 'dev86', 'M3d', LUNA, 'A base', g('m3d/runs/A?_*.csv')),
    ('m3d_V', 'dev86', 'M3d', LUNA, 'V verify before submit', g('m3d/runs/V?_*.csv')),
    ('m3d_S', 'dev86', 'M3d', LUNA, 'S verify plus spec cases', g('m3d/runs/S?_*.csv')),
    ('m3e_opus', 'dev86', 'M3e', 'Anthropic claude-opus-5.5 (low), LangGraph agent', 'LG, run refused by guard counted as fail', g('m3e/full86/*.csv')),
    ('cc_haiku', 'dev86', 'Claude Code ladder', 'Anthropic claude-haiku-5-5 (low), Claude Code', 'plan-signed-in', g('claude_code/runs/claude-haiku-5-5.csv')),
    ('cc_sonnet', 'dev86', 'Claude Code ladder', 'Anthropic claude-sonnet-5-5 (low), Claude Code', 'plan-signed-in', g('claude_code/runs/claude-sonnet-5-5.csv')),
    ('cc_opus', 'dev86', 'Claude Code ladder', 'Anthropic claude-opus-5-5 (low), Claude Code', 'plan-signed-in', g('claude_code/runs/claude-opus-5-5.csv')),
    ('cc_fable', 'dev86', 'Claude Code ladder', 'Anthropic claude-fable-5-1 (low), Claude Code', 'plan-signed-in', g('claude_code/runs/claude-fable-5-1.csv')),
    ('m3g_dev_K', 'dev86', 'M3g', LUNA, 'K knowledge pack', g('m3g/runs/dev_K?_*.csv')),
    ('m3g_ho_A', 'heldout100', 'M3g', LUNA, 'A base', g('m3g/runs/heldout_A?_*.csv')),
    ('m3g_ho_K', 'heldout100', 'M3g', LUNA, 'K knowledge pack', g('m3g/runs/heldout_K?_*.csv')),
    ('m3h_dev_A', 'dev86', 'M3h', HAIKU_CC, 'A base', g('m3h/runs/dev86_A_*.csv')),
    ('m3h_dev_S1c', 'dev86', 'M3h', HAIKU_CC, 'S1c skills v1.0 + hint', g('m3h/runs/dev86_S1c_*.csv')),
    ('m3h_dev_S2c', 'dev86', 'M3h', HAIKU_CC, 'S2c skills v2.0 + hint', g('m3h/runs/dev86_S2c_*.csv')),
    ('m3h_ho_A', 'heldout100', 'M3h', HAIKU_CC, 'A base', g('m3h/runs/heldout_A?_*.csv')),
    ('m3h_ho_S1c', 'heldout100', 'M3h', HAIKU_CC, 'S1c skills v1.0 + hint', g('m3h/runs/heldout_S1c?_*.csv')),
    ('m3h_ho_S2c', 'heldout100', 'M3h', HAIKU_CC, 'S2c skills v2.0 + hint', g('m3h/runs/heldout_S2c?_*.csv')),
    ('m3h_ho_S2', 'heldout100', 'M3h', HAIKU_CC, 'S2 skills v2.0, no hint (1 run)', g('m3h/runs/heldout_S2_*.csv')),
    ('m3i_dev_P', 'dev86', 'M3i', HAIKU_CC, 'P plain profile', g('m3i/runs/dev86_P_*.csv')),
    ('m3i_ho_P', 'heldout100', 'M3i', HAIKU_CC, 'P plain profile', g('m3i/runs/heldout_P?_*.csv')),
    ('m3j_dev_B', 'dev86', 'M3j', HAIKU_CC, 'B', g('m3j/runs/dev86_B_*.csv')),
    ('m3j_dev_PA', 'dev86', 'M3j', HAIKU_CC, 'PA', g('m3j/runs/dev86_PA_*.csv')),
    ('m3j_dev_R', 'dev86', 'M3j', HAIKU_CC, 'R (first run plus rerun of not-run problems)', g('m3j/runs/dev86_R_merged.csv')),
    ('m3j_ho_B', 'heldout100', 'M3j', HAIKU_CC, 'B', g('m3j/runs/heldout_B*.csv')),
    ('m3j_ho_PA', 'heldout100', 'M3j', HAIKU_CC, 'PA', g('m3j/runs/heldout_PA*.csv')),
    ('m3j_ho_R', 'heldout100', 'M3j', HAIKU_CC, 'R', g('m3j/runs/heldout_R*.csv')),
    ('m3k_dev_T', 'dev86', 'M3k', HAIKU_CC, 'T', g('m3k/runs/dev86_T_*.csv')),
    ('m3k_dev_K', 'dev86', 'M3k', HAIKU_CC, 'K', g('m3k/runs/dev86_K_*.csv')),
    ('m3k_ho_T', 'heldout100', 'M3k', HAIKU_CC, 'T', g('m3k/runs/heldout_T?_*.csv')),
    ('m3k_ho_K', 'heldout100', 'M3k', HAIKU_CC, 'K', g('m3k/runs/heldout_K?_*.csv')),
]
# M2's 92 problems = the ids M2 scored; dev86 is a subset of them.
SETS['m2_92'] = {r['id'] for f in g('m2/x86/results_gpt-6-luna_default.csv') for r in csv.DictReader(open(f))}
SETNAME = {'dev86': 'dev 86', 'heldout100': 'held-out 100', 'm2_92': 'M2 92'}
# Reference group per model for the failure-label tables.
REFS = ['m3b_A', 'm3b_B', 'm3e_opus', 'cc_haiku', 'cc_sonnet', 'cc_opus', 'cc_fable', 'm3h_dev_A', 'm3h_ho_A', 'm3g_ho_A']


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load():
    out = {}
    for key, st, ms, model, arm, files in GROUPS:
        rows = []
        for f in files:
            for r in csv.DictReader(open(f)):
                if r['id'] in SETS[st]:
                    rows.append(r)
        out[key] = dict(key=key, set=st, ms=ms, model=model, arm=arm, files=len(files), rows=rows)
    return out


def cell(rows):
    k = sum(1 for r in rows if r['pass'] == '1')
    n = len(rows)
    lo, hi = wilson(k, n)
    return dict(k=k, n=n, lo=lo, hi=hi)


def fmt(c):
    if c['n'] == 0:
        return 'n/a'
    return '%d/%d = %.1f%% [%.1f, %.1f]' % (c['k'], c['n'], 100 * c['k'] / c['n'], 100 * c['lo'], 100 * c['hi'])


HEAD = """# M4: failures by task category

**Status: done (2026-11-09).** Analysis only: no sweep, no model call. Every number is computed by
`docs/reports/m4/categories.py` from the committed run CSVs (rerun it from the repo root). Raw cells are in
`categories_groups.csv`; the site chart reads `categories_data.json`.

## In short

- **No category is uniformly hard for our agents.** On the 86 development problems, every model and agent we ran
  solves between about half and nine in ten of each category. The weakest category changes with the model: bug
  fixing (cid016) for `gpt-6-luna` in the LangGraph agent (50.5%, n = 99) and for Fable in Claude Code (64%),
  RTL modification (cid004) for Haiku and Sonnet in Claude Code (58% each), module reuse (cid005) for Opus in
  Claude Code (61%). Single-run cells hold 11 to 33 problems, so most gaps between categories are inside the
  intervals.
- **On the held-out 100, RTL completion (cid002) is the weakest category** for every arm we ran: 40% to 50%
  against 60% to 72% for spec to RTL (cid003). It also holds the most problems no run solved: 13 of 42.
- **Where the failures are depends on the category.** Bug fixing fails differently: for `gpt-6-luna` in the
  LangGraph agent, the agent's own testbench had passed in 22 of 49 failed bug-fixing rows. In spec to RTL, the
  hidden build failed on an interface mismatch in 28 of 119 failed rows. Everywhere else the biggest label is
  that the agent never ran a testbench.
- **This split cannot test the paper's central category finding.** It has no verification-writing categories
  (testbench stimulus, checkers, assertions: cid012 to cid014). See "What is missing".

## Method

- **Groups.** One group is one milestone's arm, on one problem set, with one model and harness. Seeds of the same
  arm are pooled. Groups are not pooled with each other, because arms differ on purpose. The pass-rate table
  shows every group.
- **Sets stay apart.** dev 86 (`tools/m3b_eval_ids.txt`), held-out 100 (`tools/m3g_heldout_ids.txt`) and the M2 92
  (the 92 agentic problems of M2 and M3). A pass rate is never compared across sets. Rows whose problem is not in
  the group's set are dropped (some M3h and M3i dev files carry the 6 problems outside the 86).
- **Left out.** Pilots (M1's 10, the reasoning pick, M2a), smoke runs, M3b's runs on excluded problems, M3l's
  13-problem and 3-problem subsets, and Fable's wall-cap reruns (a 30-problem top-up of the Claude Code run).
  M3e's Opus run is the merged 86 where the problems the cost guard refused count as failures.
- **Cells.** passed/n = rate [Wilson 95% interval]. n counts problem-runs, so a three-seed group has three times
  the problems. Seeds of one problem are not independent, so the interval for a pooled cell is narrower than the
  truth.
- **Categories in the free split.** cid002 RTL completion (held-out only), cid003 spec to RTL, cid004 RTL
  modification, cid005 spec to RTL with module reuse (agentic only), cid016 bug fixing (agentic only). The
  paper writes these as cid02, cid03 and so on.
- **Labels.** `failure_label` from `tools/taxonomy.py`: deterministic rules on the logs, no model reads anything.
  M2 CSVs predate the labels, so label tables use the groups from M3 on.

## Results

"""
TAIL = """
## What is missing

The free split of the benchmark contains **no verification-writing categories**: testbench stimulus generation
(cid012), testbench checker generation (cid013) and assertion generation (cid014) are not in it, nor are code
improvement (cid007), the correspondence tasks or question answering. Our five categories are RTL completion,
spec to RTL, RTL modification, module reuse and bug fixing. So nothing here can confirm or contradict the paper's
finding that verification categories are harder than RTL categories.

## The paper, beside ours

Paper: "Comprehensive Verilog Design Problems: A Next-Generation Benchmark Dataset for Evaluating Large Language
Models and Agents on RTL Design and Verification", arXiv 2506.14074 (v1, 17 June 2025), read through
export.arxiv.org.

- **Verification is harder than RTL, in the paper.** Section 4: "Design verification categories ... exhibit
  substantially lower pass rates compared to other code generation categories." Table 2 (non-agentic, pass@1,
  n = 5): cid12 13% to 25%, cid13 3% to 11%, cid14 5% to 23%, against cid02 to cid04 of 18% to 48%. Table 3 (agentic, converted to single-turn) shows the same split. Section 5
  and Table 5 say the same of the failure clusters. The abstract adds that agentic tasks "involving RTL reuse
  and verification" are particularly difficult. The recollection that verification and testbench categories
  are harder than RTL categories is confirmed by the paper.
- **Where our categories match the paper's** (cid003, cid004, cid005, cid016; cid002 for the held-out set), the paper
  tested older models with single-turn prompts on all of the benchmark's problems for each category: the models
  were Claude 3.7 Sonnet, Claude 3.5 Haiku, GPT 4.1, o1, o4-mini and Llama 3.1. Our models, our agent loop and
  our problem subsets differ, so we do not compare levels. Table 3 gives bug fixing (cid16) the highest
  agentic pass rate for most models (36% to 56%) and module reuse (cid05) among the lowest of the RTL categories
  (18% to 25%). We do not see that order: for gpt-6-luna in the LangGraph agent, bug fixing is the lowest of
  the four (50.5%) and module reuse the highest (64.2%); for the Claude Code models bug fixing is higher
  (64% to 82%) and module reuse mixed (61% to 78%). We read the order as not stable across models and harnesses.
- **Section 5 failure entities** (Table 5) are LLM-clustered text such as "data misalignment" or "bit-slicing
  errors". Ours are rule-based labels from logs. The two sets are not comparable label by label.

## Limits

- Cell sizes are small (11 to 33 problems per category on one run), and the intervals say so.
- Every dev-set result is on problems we developed against. The held-out 100 is the cleaner read, but it has no
  cid005 or cid016.
- "Never solved" counts a problem as solved if any run of any arm passed it. It is a floor on difficulty for these
  agents, not a property of the benchmark; the 11 benchmark-limited problems (`unsolved_analysis.md`) are
  marked.
- Held-out problems are counted here, never named.
"""

def main():
    G = load()
    data = {'cats': CATS, 'groups': [], 'never': {}}
    csvrows = []
    for key, gr in G.items():
        cats = sorted({r['cid'] for r in gr['rows']})
        d = dict(key=key, set=gr['set'], ms=gr['ms'], model=gr['model'], arm=gr['arm'], cells={}, labels={})
        d['all'] = cell(gr['rows'])
        for c in cats:
            rs = [r for r in gr['rows'] if r['cid'] == c]
            d['cells'][c] = cell(rs)
            cnt = collections.Counter(r.get('failure_label', '') for r in rs if r['pass'] != '1')
            d['labels'][c] = dict(cnt)
            csvrows.append([key, gr['set'], gr['ms'], gr['model'], gr['arm'], c, d['cells'][c]['k'], d['cells'][c]['n'],
                            '%.4f' % d['cells'][c]['lo'], '%.4f' % d['cells'][c]['hi']])
        data['groups'].append(d)
    # problems that no run solved, per set and category
    for st, idset in SETS.items():
        solved, seen, cid = set(), set(), {}
        for gr in G.values():
            if gr['set'] != st:
                continue
            for r in gr['rows']:
                seen.add(r['id']); cid[r['id']] = r['cid']
                if r['pass'] == '1':
                    solved.add(r['id'])
        per = {}
        for c in sorted(set(cid.values())):
            tot = [i for i in seen if cid[i] == c]
            nev = sorted(i for i in tot if i not in solved)
            per[c] = dict(problems=len(tot), never=len(nev), limited=sum(1 for i in nev if i in LIMITED),
                          never_ids=nev if st != 'heldout100' else [])
        data['never'][st] = per
    json.dump(data, open('docs/reports/m4/categories_data.json', 'w'), indent=1)
    with open('docs/reports/m4/categories_groups.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['group', 'set', 'milestone', 'model_and_harness', 'arm', 'cid', 'passed', 'n', 'wilson_lo', 'wilson_hi'])
        w.writerows(csvrows)
    # markdown
    o = []
    for st in ('dev86', 'heldout100', 'm2_92'):
        o.append('### Pass rate by category: %s\n' % SETNAME[st])
        cats = sorted({c for d in data['groups'] if d['set'] == st for c in d['cells']})
        o.append('| Milestone | Model and harness | Arm | ' + ' | '.join('%s %s' % (c, CATS[c]) for c in cats) + ' | All |')
        o.append('|---|---|---|' + '---|' * (len(cats) + 1))
        for d in data['groups']:
            if d['set'] != st:
                continue
            o.append('| %s | %s | %s | ' % (d['ms'], d['model'], d['arm']) + ' | '.join(fmt(d['cells'].get(c, dict(n=0))) for c in cats) + ' | ' + fmt(d['all']) + ' |')
        o.append('')
    o.append('### Failed rows by label and category (reference groups)\n')
    for key in REFS:
        d = next(x for x in data['groups'] if x['key'] == key)
        used = sorted({l for c in d['labels'].values() for l in c})
        o.append('**%s, %s, %s (%s)**\n' % (d['ms'], d['model'], d['arm'], SETNAME[d['set']]))
        cats = sorted(d['cells'])
        o.append('| Label | In plain words | ' + ' | '.join('%s (%d failed of %d)' % (c, d['cells'][c]['n'] - d['cells'][c]['k'], d['cells'][c]['n']) for c in cats) + ' |')
        o.append('|---|---|' + '---|' * len(cats))
        for l in sorted(used, key=lambda l: -sum(d['labels'][c].get(l, 0) for c in cats)):
            o.append('| `%s` | %s | ' % (l or '(none)', LABELS.get(l, '')) + ' | '.join(str(d['labels'][c].get(l, 0)) for c in cats) + ' |')
        o.append('')
    o.append('### Problems that no run solved\n')
    for st in ('dev86', 'heldout100', 'm2_92'):
        o.append('**%s** (every group on this set counted)\n' % SETNAME[st])
        o.append('| Category | Problems | Never solved | Of those, benchmark-limited |')
        o.append('|---|---|---|---|')
        tp = tn = tl = 0
        for c, v in data['never'][st].items():
            o.append('| %s %s | %d | %d | %d |' % (c, CATS[c], v['problems'], v['never'], v['limited']))
            tp += v['problems']; tn += v['never']; tl += v['limited']
        o.append('| **All** | %d | %d | %d |' % (tp, tn, tl))
        o.append('')
    open('docs/reports/m4/categories.md', 'w').write(HEAD + '\n'.join(o) + TAIL)


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    main()
