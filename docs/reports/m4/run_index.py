#!/usr/bin/env python3
"""M4: build docs/reports/m4/run_index.csv from the committed reports and the GitHub artifact list. Stdlib + gh.

Run from the repo root:  python3 docs/reports/m4/run_index.py
A run is "scored" if its 11-digit Actions run id appears in a committed run CSV file name or in a milestone report.
It is packed only if it has a public upload: an artifact named sweep-<split>-<run id> (the sweep workflow uploads
only after the secret check and the leak guard pass). Smoke artifacts, the pack-building 'lessons' artifact, M0
checks and pages artifacts are not in the public upload list and are never packed.
"""
import collections, csv, glob, json, os, re, subprocess

ORDER = ['m2', 'm3', 'm3b', 'm3c', 'm3d', 'm3e', 'claude_code', 'fable_wallcap', 'm3g', 'm3h', 'm3i', 'm3j', 'm3k', 'm3l']
REPORT = {'M2_report.md': 'm2', 'unsolved_analysis.md': 'claude_code', 'M3_report.md': 'm3', 'M3b_report.md': 'm3b', 'M3c_report.md': 'm3c', 'M3d_report.md': 'm3d',
          'M3e_report.md': 'm3e', 'claude_code_ladder.md': 'claude_code', 'fable_wallcap.md': 'fable_wallcap',
          'M3g_report.md': 'm3g', 'M3h_report.md': 'm3h', 'M3i_report.md': 'm3i', 'M3j_report.md': 'm3j',
          'M3k_report.md': 'm3k', 'M3l_report.md': 'm3l'}
RID = re.compile(r'(?<!\d)(\d{11})(?!\d)')
REPO = 'BrendanJamesLynskey/CVDP_RTL_Agent'


def main():
    out = subprocess.run(['gh', 'api', 'repos/%s/actions/artifacts' % REPO, '--paginate', '-q',
                          '.artifacts[]|[.id,.name,.size_in_bytes,.expired,.expires_at,.workflow_run.id]|@tsv'],
                         capture_output=True, text=True, check=True).stdout
    arts = collections.defaultdict(list)
    for l in out.splitlines():
        i, n, sz, ex, exp, run = l.split('\t')
        arts[run].append(dict(id=i, name=n, size=int(sz), expired=ex, expires=exp))
    ms, arm, scored = {}, {}, set()
    for f in sorted(glob.glob('docs/reports/*/**/*.csv', recursive=True)):
        parts = f.split('/')
        if parts[2] not in ORDER or 'smoke' in parts or 'runs_excluded' in parts or 'learning' in parts:
            continue
        for m in RID.findall(parts[-1]):
            ms[m] = parts[2]; arm[m] = os.path.splitext(parts[-1])[0]; scored.add(m)
    for f, k in REPORT.items():
        txt = open('docs/reports/' + f).read()
        for line in txt.splitlines():
            for m in RID.findall(line):
                scored.add(m)
                if m not in ms or ORDER.index(k) < ORDER.index(ms[m]):
                    if m not in ms:
                        ms[m] = k
                if m not in arm:
                    cells = [c.strip(' `') for c in line.split('|') if c.strip()]
                    arm[m] = ' '.join(cells[:2])[:60] if line.startswith('|') else 'see %s' % f
                    if f == 'unsolved_analysis.md':
                        arm[m] = 'Claude Code ladder row (listed in unsolved_analysis.md)'
    pub = lambda n: n.startswith('sweep-') and 'smoke' not in n
    rows = []
    for m in sorted(scored, key=lambda r: (ORDER.index(ms[r]), r)):
        a = [x for x in arts.get(m, []) if pub(x['name'])]
        if a:
            x = a[0]
            rows.append([ms[m], arm[m], m, x['name'], x['size'], x['expires'][:10], 'yes' if x['expired'] == 'false' else 'no', ''])
        else:
            rows.append([ms[m], arm[m], m, '', 0, '', 'no', 'no public upload artifact (expired, or never uploaded)'])
    with open('docs/reports/m4/run_index.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['milestone', 'arm', 'run_id', 'artifact', 'size_bytes', 'expires', 'packed', 'reason_not_packed'])
        w.writerows(rows)
    print(len(rows), 'runs;', sum(1 for r in rows if r[6] == 'yes'), 'with artifact;', sum(r[4] for r in rows), 'bytes')


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
    main()
