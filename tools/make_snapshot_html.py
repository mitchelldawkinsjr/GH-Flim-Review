#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd
import os


def letter(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def safe_int(x) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0


def build_snapshot_html(rows: list[dict], ga_snippet: str = "") -> str:
    css = (
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n'
        '<style type="text/css">.ritz .waffle a { color: inherit; }.ritz .waffle .s2{background-color:#ffffff;text-align:right;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s4{background-color:#ebeff1;text-align:right;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s7{background-color:#ffffff;text-align:left;color:#000000;font-family:Arial;font-size:10pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s6{background-color:#fff2cc;text-align:left;font-weight:bold;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s5{background-color:#ebeff1;text-align:left;font-weight:bold;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s0{background-color:#fff2cc;text-align:center;font-weight:bold;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s1{background-color:#ffffff;text-align:left;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}.ritz .waffle .s3{background-color:#ebeff1;text-align:left;color:#000000;font-family:Arial;font-size:11pt;vertical-align:bottom;white-space:nowrap;direction:ltr;padding:0px 3px 0px 3px;}</style>'
    )

    # Header row
    header = (
        '<tr style="height: 19px">'
        '<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">1</div></th>'
        '<td class="s0">Player</td>'
        '<td class="s0">Snap count</td>'
        '<td class="s0">Drops</td>'
        '<td class="s0">Targets</td>'
        '<td class="s0">Catches</td>'
        '<td class="s0" dir="ltr">Rec Yards</td>'
        '<td class="s0" dir="ltr">Rushes</td>'
        '<td class="s0" dir="ltr">Rush Yards</td>'
        '<td class="s0">Touchdowns</td>'
        '<td class="s0">Missed Assignment</td>'
        '<td class="s0">Loaf</td>'
        '<td class="s0" dir="ltr">Key plays points</td>'
        '<td class="s0">Grade (0-100)</td>'
        '<td class="s1" dir="ltr"> </td>'
        '</tr>'
    )

    # Body rows alternate classes .s1/.s3 (left) and .s2/.s4 (right)
    body_parts = []
    zebra = 0
    total_loafs = 0
    scores = []
    for r in rows:
        zebra += 1
        lcls = 's1' if zebra % 2 == 1 else 's3'
        rcls = 's2' if zebra % 2 == 1 else 's4'
        drops_cell = '' if r['drops'] == 0 else str(r['drops'])
        ma_cell = '' if r['missed_assignments'] == 0 else str(r['missed_assignments'])
        loaf_cell = '' if r['loafs'] == 0 else str(r['loafs'])
        rushes_cell = '' if r.get('rushes', 0) == 0 else str(r.get('rushes', 0))
        key_points_cell = f"{r['key_points']:.1f}" if isinstance(r['key_points'], float) else str(r['key_points'])
        grade_cell = str(int(round(float(r['score']))))
        total_loafs += safe_int(r['loafs'])
        scores.append(float(r['score']))
        body_parts.append(
            '<tr style="height: 19px">'
            f'<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">{zebra+1}</div></th>'
            f'<td class="{lcls}">{r["player"]}</td>'
            f'<td class="{rcls}">{r["snaps"]}</td>'
            f'<td class="{lcls}">{drops_cell}</td>'
            f'<td class="{rcls}">{r["targets"]}</td>'
            f'<td class="{rcls}">{r["catches"]}</td>'
            f'<td class="{rcls}">{r["rec_yards"]}</td>'
            f'<td class="{lcls}">{rushes_cell}</td>'
            f'<td class="{lcls}">{r["rush_yards"]}</td>'
            f'<td class="{lcls}">{r["touchdowns"]}</td>'
            f'<td class="{rcls}">{ma_cell}</td>'
            f'<td class="{rcls}" dir="ltr">{loaf_cell}</td>'
            f'<td class="{rcls}" dir="ltr">{key_points_cell}</td>'
            f'<td class="{rcls}">{grade_cell}</td>'
            '<td></td>'
            '</tr>'
        )

    unit_score = sum(scores) / len(scores) if scores else 0.0
    unit_grade = letter(unit_score)

    footer = (
        '<tr style="height: 19px">'
        '<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">10</div></th>'
        '<td class="s6" dir="ltr">Total Loafs</td>'
        '<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td></td><td></td><td></td><td></td><td></td>'
        '</tr>'
        '<tr style="height: 19px">'
        '<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">11</div></th>'
        f'<td class="s2" dir="ltr">{total_loafs}</td>'
        '<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td></td><td></td><td></td><td></td><td></td>'
        '</tr>'
        '<tr style="height: 19px">'
        '<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">12</div></th>'
        '<td class="s6" dir="ltr">Unit Grade</td>'
        '<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td class="s7" dir="ltr"></td><td></td><td></td><td></td><td></td>'
        '</tr>'
        '<tr style="height: 19px">'
        '<th class="row-headers-background"><div class="row-header-wrapper" style="line-height: 19px">13</div></th>'
        f'<td class="s2" dir="ltr">{int(round(unit_score))}</td>'
        f'<td class="s1" dir="ltr">{unit_grade}</td>'
        '<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
        '<td class="s7"></td><td></td><td></td><td></td>'
        '</tr>'
    )

    html = [css, ga_snippet, '<div class="ritz grid-container" dir="ltr">', '<table class="waffle" cellspacing="0" cellpadding="0">', '<thead>']
    # Column headers (A..N) widths are cosmetic; omit for brevity
    html.append('<tr><th class="row-header freezebar-vertical-handle"></th>' + ''.join(
        f'<th class="column-headers-background">{c}</th>' for c in list('ABCDEFGHIJKLMN')
    ) + '</tr>')
    html.append('</thead><tbody>')
    html.append(header)
    html.extend(body_parts)
    html.append(footer)
    html.append('</tbody></table></div>')
    return '\n'.join(html)


def main():
    ap = argparse.ArgumentParser(description='Generate a weekly Snapshot HTML table from detailed results CSV')
    ap.add_argument('--details_csv', required=True, help='Path to weekly detailed results CSV (results_WkX_*.csv)')
    ap.add_argument('--prepared_csv', help='Optional prepared CSV to pull Rushes attempts if present')
    ap.add_argument('--out', help='Output HTML path (default: alongside details_csv as ../snapshot.html)')
    args = ap.parse_args()

    df = pd.read_csv(args.details_csv)
    # Normalize
    df['player'] = df['player'].astype(str)
    # Aggregate per player
    def sum_int(col):
        return int(pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0).sum())

    rows = []
    rushes_by_player = {}
    if args.prepared_csv and Path(args.prepared_csv).exists():
        dprep = pd.read_csv(args.prepared_csv)
        rushes_col = None
        for c in ['Rushes', 'rushes']:
            if c in dprep.columns:
                rushes_col = c
                break
        if rushes_col is not None and 'player' in dprep.columns:
            tmp = dprep.groupby(['player'])[rushes_col].sum().reset_index()
            for _, r in tmp.iterrows():
                rushes_by_player[str(r['player']).strip()] = int(r[rushes_col])

    for player, g in df.groupby('player'):
        p = str(player).strip()
        if not p or p.lower() in ('nan', 'none'):
            continue
        snaps = int(pd.to_numeric(g.get('snaps', 0), errors='coerce').fillna(0).sum())
        targets = int(pd.to_numeric(g.get('targets', 0), errors='coerce').fillna(0).sum())
        catches = int(pd.to_numeric(g.get('catches', 0), errors='coerce').fillna(0).sum())
        rec_yards = int(pd.to_numeric(g.get('rec_yards', 0), errors='coerce').fillna(0).sum())
        rush_yards = int(pd.to_numeric(g.get('rush_yards', 0), errors='coerce').fillna(0).sum())
        touchdowns = int(pd.to_numeric(g.get('touchdowns', 0), errors='coerce').fillna(0).sum())
        drops = int(pd.to_numeric(g.get('drops', 0), errors='coerce').fillna(0).sum())
        ma = int(pd.to_numeric(g.get('missed_assignments', 0), errors='coerce').fillna(0).sum())
        loafs = int(pd.to_numeric(g.get('loafs', 0), errors='coerce').fillna(0).sum())
        key_points = float(pd.to_numeric(g.get('code_points', 0.0), errors='coerce').fillna(0.0).sum())
        score = float(pd.to_numeric(g.get('score', 0.0), errors='coerce').fillna(0.0).mean())
        rows.append({
            'player': p,
            'snaps': snaps,
            'targets': targets,
            'catches': catches,
            'rec_yards': rec_yards,
            'rushes': rushes_by_player.get(p, 0),
            'rush_yards': rush_yards,
            'touchdowns': touchdowns,
            'drops': drops,
            'missed_assignments': ma,
            'loafs': loafs,
            'key_points': key_points,
            'score': score,
        })

    # Sort by score desc
    rows.sort(key=lambda r: r['score'], reverse=True)

    ga_id = os.environ.get('GA_MEASUREMENT_ID', '').strip()
    ga_snippet = ''
    if ga_id:
        ga_snippet = ("""
<script>
(function(){
  var GA_ID = '%s';
  if (navigator.doNotTrack == '1' || window.doNotTrack == '1') return;
  var s=document.createElement('script'); s.async=1;
  s.src='https://www.googletagmanager.com/gtag/js?id='+GA_ID;
  document.head.appendChild(s);
  window.dataLayer=window.dataLayer||[];
  function gtag(){dataLayer.push(arguments);} window.gtag=gtag;
  gtag('js', new Date()); gtag('config', GA_ID, { anonymize_ip: true });
})();
</script>
        """ % ga_id)
    html = build_snapshot_html(rows, ga_snippet)

    # Default out path: ../snapshot.html relative to details CSV dir
    out_path = Path(args.out) if args.out else (Path(args.details_csv).parent.parent / 'snapshot.html')
    out_path.write_text(html, encoding='utf-8')
    print(f"Wrote snapshot to {out_path}")


if __name__ == '__main__':
    main()



