#!/usr/bin/env python3
import argparse
from pathlib import Path
import glob
import os
import pandas as pd
import html

CODE_LABELS = {
    'TD': 'Touchdown',
    'E': 'Relentless Effort',
    'ER': 'Elite Route',
    'GR': 'Good Route',
    'GB': 'Good Block',
    'P': 'Pancake',
    'FD': 'First Down',
    'MA': 'Missed Assignment',
    'SC': 'Spectacular Catch',
    'DP': 'Dropped Pass',
    'H': 'Holding',
    'BR': 'Bad Route',
    'L': 'Loaf (Laziness)',
    'NFS': 'Not Full Speed',
    'W': 'Whiffed',
    'BT': 'Broken Tackle',
}


def safe_div(n, d) -> float:
    try:
        n = float(n)
        d = float(d)
        if d == 0:
            return 0.0
        return n / d
    except Exception:
        return 0.0


def per30(n, snaps) -> float:
    try:
        snaps = float(snaps)
        n = float(n)
        if snaps <= 0:
            return 0.0
        return n * 30.0 / snaps
    except Exception:
        return 0.0


def letter(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def cell_text(val) -> str:
    try:
        if pd.isna(val):
            return ''
    except Exception:
        pass
    s = str(val)
    return '' if s.lower() == 'nan' else s


def collect_code_counts(df_sub: pd.DataFrame) -> dict:
    counts = {}
    for _, r in df_sub.iterrows():
        for k, v in r.to_dict().items():
            if isinstance(k, str) and k.startswith('cnt_'):
                code = k.replace('cnt_', '').upper()
                try:
                    counts[code] = counts.get(code, 0) + int(v)
                except Exception:
                    pass
    return counts


def render_player_html(player: str, totals: dict, rates: dict, code_counts: dict, title: str, breadcrumbs_html: str = "", weekly_links_html: str = "", ga_snippet: str = "", nav_html: str = "") -> str:
    css = """
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --primary: #2563eb;
      --row: #ffffff;
      --row-alt: #f9fafb;
      --thead: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
      --border: #e5e7eb;
    }
    body { font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: var(--bg); color: var(--text); }
    h1 { margin: 0 0 6px 0; font-weight: 700; letter-spacing: -0.01em; }
    h2 { margin-top: 24px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .small { color: var(--muted); font-size: 12px; }
    .breadcrumbs { font-size: 12px; color: #666; margin-bottom: 8px; }
    .breadcrumbs a { color: var(--primary); text-decoration: none; }
    .breadcrumbs a:hover { text-decoration: underline; }
    table { width: 100%; border-collapse: separate; border-spacing: 0; background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }
    thead th { background: var(--thead); color: #111827; text-transform: uppercase; font-size: 11px; letter-spacing: .05em; padding: 12px 14px; text-align: left; }
    tbody td, td { padding: 12px 14px; border-top: 1px solid var(--border); }
    tbody tr:nth-child(odd) { background: var(--row); }
    tbody tr:nth-child(even) { background: var(--row-alt); }
    tbody tr:hover { background: #eef2ff; }
    a { color: var(--primary); text-decoration: none; }
    a:hover { text-decoration: underline; }
    """

    metrics_rows = [
        ("Season Grade (avg)", f"{rates['grade']} ({rates['score']:.1f})"),
        ("Snaps", totals['snaps']),
        ("Targets", totals['targets']),
        ("Catches", totals['catches']),
        ("Rec Yards", totals['rec_yards']),
        ("Rush Yards", totals['rush_yards']),
        ("Touchdowns", totals['touchdowns']),
        ("Drops", totals['drops']),
        ("Missed Assignments", totals['ma']),
        ("Loafs", totals['loafs']),
        ("Key Plays Points", f"{totals['code_points']:.1f}"),
        ("Games", totals['games']),
    ]
    if 'rushes' in totals:
        metrics_rows.insert(6, ("Rush Attempts", totals['rushes']))

    rate_rows = [
        ("Catch Rate", f"{rates['catch_rate']*100:.1f}%"),
        ("Yards per Target", f"{rates['ypt']:.2f}"),
        ("Targets per 30", f"{rates['targets_per30']:.2f}"),
        ("Key Plays per 30", f"{rates['keyplays_per30']:.2f}"),
        ("TDs per 30", f"{rates['tds_per30']:.2f}"),
        ("Drops Rate", f"{rates['drops_rate']*100:.1f}%"),
        ("Missed Assignments per 30", f"{rates['ma_per30']:.2f}"),
        ("Loafs per 30", f"{rates['loafs_per30']:.2f}"),
    ]

    codes_rows = sorted(code_counts.items(), key=lambda kv: kv[1], reverse=True)
    def table(rows):
        html_rows = ["<table>", "<tr><th>Metric</th><th>Value</th></tr>"]
        for k, v in rows:
            html_rows.append(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>")
        html_rows.append("</table>")
        return "\n".join(html_rows)

    codes_table_rows = []
    codes_table_rows.append("<table><tr><th>Code</th><th>Meaning</th><th>Count</th></tr>")
    for k, v in codes_rows:
        meaning = CODE_LABELS.get(k, k)
        codes_table_rows.append(
            f"<tr><td>{html.escape(k)}</td><td>{html.escape(meaning)}</td><td>{v}</td></tr>"
        )
    codes_table_rows.append("</table>")
    codes_table = "".join(codes_table_rows)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{html.escape(title)} — {html.escape(player)}</title>
  {ga_snippet}
  <style>{css}</style>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <link rel=\"icon\" href=\"data:,\" />
  </head>
<body>
  {nav_html}
  <h1>{html.escape(player)}</h1>
  {breadcrumbs_html}
  <div class=\"small\">{html.escape(title)}</div>
  <div class=\"grid\">\n    <div>\n      <h2>Season Totals</h2>\n      {table(metrics_rows)}\n    </div>\n    <div>\n      <h2>Rates (from totals)</h2>\n      {table(rate_rows)}\n    </div>\n  </div>
  <h2>Season Code Counts</h2>
  {codes_table}
  {('<h2>Weekly Pages</h2>' + weekly_links_html) if weekly_links_html else ''}
  <p class=\"small\">Generated by make_season_dashboard_html.py</p>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description='Generate season HTML dashboards (totals per player) from weekly detailed CSVs')
    ap.add_argument('--weekly_glob', default='out/Wk*/results_*.csv', help='Glob pattern to weekly detailed CSV files')
    ap.add_argument('--out_dir', required=True)
    ap.add_argument('--title', default='Season Player Dashboards')
    args = ap.parse_args()
    ga_id = os.environ.get('GA_MEASUREMENT_ID', '').strip()
    ga_snippet = ''
    if ga_id:
        ga_snippet = f"""
  <script>
  (function(){{
    var GA_ID = '{html.escape(ga_id)}';
    if (navigator.doNotTrack == '1' || window.doNotTrack == '1') return;
    var s=document.createElement('script'); s.async=1;
    s.src='https://www.googletagmanager.com/gtag/js?id='+GA_ID;
    document.head.appendChild(s);
    window.dataLayer=window.dataLayer||[];
    function gtag(){{dataLayer.push(arguments);}}
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', GA_ID, {{ anonymize_ip: true }});
  }})();
  </script>
        """

    csv_paths = sorted(glob.glob(args.weekly_glob))
    if not csv_paths:
        raise SystemExit(f"No weekly CSVs found for pattern: {args.weekly_glob}")

    dfs = []
    for p in csv_paths:
        try:
            dfs.append(pd.read_csv(p))
        except Exception:
            pass
    if not dfs:
        raise SystemExit("No data could be loaded from weekly CSVs")

    df = pd.concat(dfs, ignore_index=True)

    # Optionally collect rush attempt counts from prepared CSVs if available
    rushes_by_player_week: dict[tuple[str, str], int] = {}
    try:
        prep_paths = sorted(glob.glob(str(Path('out') / 'Wk*' / 'Wk*_*_prepared.csv')))
        for pp in prep_paths:
            try:
                dprep = pd.read_csv(pp)
            except Exception:
                continue
            rushes_col = None
            for c in ['Rushes', 'rushes']:
                if c in dprep.columns:
                    rushes_col = c
                    break
            if rushes_col is None:
                continue
            if 'player' not in dprep.columns or 'week' not in dprep.columns:
                continue
            tmp = dprep.groupby(['player','week'])[rushes_col].sum().reset_index()
            for _, r2 in tmp.iterrows():
                key = (str(r2['player']).strip(), str(r2['week']).strip())
                rushes_by_player_week[key] = rushes_by_player_week.get(key, 0) + int(r2[rushes_col])
    except Exception:
        rushes_by_player_week = {}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    players = sorted([cell_text(p) for p in df['player'].astype(str).unique()])
    index_items = []
    for player in players:
        if not player:
            continue
        sub = df[df['player'].astype(str) == player]
        if sub.empty:
            continue

        def sum_int(col):
            return int(pd.to_numeric(sub.get(col, 0), errors='coerce').fillna(0).sum())

        snaps = sum_int('snaps')
        targets = sum_int('targets')
        catches = sum_int('catches')
        rec_yards = sum_int('rec_yards')
        rush_yards = sum_int('rush_yards')
        touchdowns = sum_int('touchdowns')
        drops = sum_int('drops')
        ma = sum_int('missed_assignments')
        loafs = sum_int('loafs')
        code_points = float(pd.to_numeric(sub.get('code_points', 0.0), errors='coerce').fillna(0.0).sum())
        games = int(sub['week'].nunique()) if 'week' in sub.columns else len(sub.index)
        rushes_total = 0
        if 'week' in sub.columns and rushes_by_player_week:
            for w in sub['week'].astype(str).tolist():
                rushes_total += int(rushes_by_player_week.get((player.strip(), str(w).strip()), 0))

        catch_rate = safe_div(catches, targets)
        ypt = safe_div((rec_yards + rush_yards), targets)
        tds_per30 = per30(touchdowns, snaps)
        keyplays_total = int(pd.to_numeric(sub.get('derived_keyplays', 0), errors='coerce').fillna(0).sum())
        keyplays_per30 = per30(keyplays_total, snaps)
        targets_per30 = per30(targets, snaps)
        drops_rate = safe_div(drops, targets)
        loafs_per30 = per30(loafs, snaps)
        ma_per30 = per30(ma, snaps)

        score = float(pd.to_numeric(sub.get('score', 0.0), errors='coerce').fillna(0.0).mean())
        letter_grade = letter(score)

        totals = {
            'snaps': snaps,
            'targets': targets,
            'catches': catches,
            'rec_yards': rec_yards,
            'rush_yards': rush_yards,
            'touchdowns': touchdowns,
            'drops': drops,
            'ma': ma,
            'loafs': loafs,
            'code_points': code_points,
            'games': games,
        }
        rates = {
            'catch_rate': catch_rate,
            'ypt': ypt,
            'targets_per30': targets_per30,
            'keyplays_per30': keyplays_per30,
            'tds_per30': tds_per30,
            'drops_rate': drops_rate,
            'ma_per30': ma_per30,
            'loafs_per30': loafs_per30,
            'score': score,
            'grade': letter_grade,
        }

        codes = collect_code_counts(sub)

        player_file = f"{player.strip().replace(' ', '_')}.html"
        if rushes_total:
            totals['rushes'] = rushes_total
        root_index = Path(out_dir).parent.parent / 'index.html'
        season_index = Path(out_dir) / 'index.html'
        try:
            home_rel = os.path.relpath(root_index, out_dir)
            season_rel = os.path.relpath(season_index, out_dir)
        except Exception:
            home_rel = '../index.html'
            season_rel = 'index.html'
        breadcrumbs = f"<div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel)}\">Home</a> &rsaquo; <a href=\"{html.escape(season_rel)}\">Season</a> &rsaquo; <span>{html.escape(player)}</span></div>"

        weekly_rows = []
        if 'week' in sub.columns:
            raw_weeks = sub['week'].tolist()
            week_ints = sorted({int(float(w)) for w in raw_weeks if (not pd.isna(w)) and str(w).strip() != ''})
            player_file_name = f"{player.strip().replace(' ', '_')}.html"
            for w_int in week_ints:
                try:
                    root = Path(out_dir).parent.parent
                    wk_dir = root / f"Wk{w_int}"
                    dash_player = wk_dir / 'dashboards' / player_file_name
                    dash_index = wk_dir / 'dashboards' / 'index.html'
                    if dash_player.exists():
                        dash_target = dash_player
                    else:
                        dash_target = dash_index
                    pdf_path = wk_dir / 'pdfs' / f"{player.strip().replace(' ', '_')}_{w_int}.pdf"
                    dash_rel = os.path.relpath(dash_target, out_dir)
                    pdf_rel = os.path.relpath(pdf_path, out_dir) if pdf_path.exists() else ''
                except Exception:
                    dash_rel = f"../../Wk{w_int}/dashboards/{player_file_name}"
                    pdf_rel = f"../../Wk{w_int}/pdfs/{player.strip().replace(' ', '_')}_{w_int}.pdf"
                pdf_cell = f"<a href=\"{html.escape(pdf_rel)}\">PDF</a>" if pdf_rel else '-'
                weekly_rows.append(f"<tr><td>Wk{w_int}</td><td><a href=\"{html.escape(dash_rel)}\">Dashboards</a></td><td>{pdf_cell}</td></tr>")
        weekly_links_html = "<table><tr><th>Week</th><th>Dashboards</th><th>PDF</th></tr>" + ''.join(weekly_rows) + "</table>" if weekly_rows else ''

        try:
            home_rel_nav = os.path.relpath(Path(out_dir).parent.parent / 'index.html', out_dir)
        except Exception:
            home_rel_nav = '../index.html'
        nav_html = f"<div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel_nav)}\">Home</a> · <a href=\"{html.escape(season_rel)}\">Season</a></div>"

        html_str = render_player_html(player, totals, rates, codes, args.title, breadcrumbs, weekly_links_html, ga_snippet, nav_html)
        (out_dir / player_file).write_text(html_str, encoding='utf-8')
        total_yards = rec_yards + rush_yards
        index_items.append((player, player_file, score, catches, total_yards, drops, touchdowns))

    index_items.sort(key=lambda t: t[2], reverse=True)
    rows = "".join(
        f"<tr>"
        f"<td><a href=\"{html.escape(f)}\">{html.escape(p)}</a></td>"
        f"<td>{c}</td>"
        f"<td>{y}</td>"
        f"<td>{d}</td>"
        f"<td>{td}</td>"
        f"<td>{s:.1f}</td>"
        f"</tr>"
        for p, f, s, c, y, d, td in index_items
    )
    try:
        home_rel_idx = os.path.relpath(Path(out_dir).parent.parent / 'index.html', out_dir)
    except Exception:
        home_rel_idx = '../../index.html'
    sort_script = """
  <script>
    (function(){
      function makeSortable(table){
        const ths = table.querySelectorAll('thead th');
        ths.forEach((th, idx) => {
          th.addEventListener('click', () => {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const asc = th.getAttribute('data-sort') !== 'asc';
            rows.sort((a,b) => {
              const ta = a.children[idx].innerText.trim();
              const tb = b.children[idx].innerText.trim();
              const na = parseFloat(ta.replace(/[^0-9.-]/g,''));
              const nb = parseFloat(tb.replace(/[^0-9.-]/g,''));
              const bothNum = !isNaN(na) && !isNaN(nb);
              let cmp = 0;
              if(bothNum){ cmp = na - nb; } else { cmp = ta.localeCompare(tb); }
              return asc ? cmp : -cmp;
            });
            ths.forEach(h=>h.removeAttribute('data-sort'));
            th.setAttribute('data-sort', asc ? 'asc':'desc');
            rows.forEach(r=>tbody.appendChild(r));
          });
        });
      }
      const t = document.querySelector('table'); if(t) makeSortable(t);
    })();
  </script>
    """
    index_html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{html.escape(args.title)}</title>
  {ga_snippet}
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --border: #e5e7eb;
      --thead: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
      --primary: #2563eb;
    }}
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: var(--bg); color: var(--text); }}
    .breadcrumbs {{ font-size: 12px; color: #666; margin-bottom: 8px; }}
    .breadcrumbs a {{ color: var(--primary); text-decoration: none; }}
    .breadcrumbs a:hover {{ text-decoration: underline; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }}
    thead th {{ background: var(--thead); color: #111827; text-transform: uppercase; font-size: 11px; letter-spacing: .05em; padding: 12px 14px; text-align: left; position: sticky; top: 0; z-index: 2; cursor: pointer; }}
    tbody td {{ padding: 12px 14px; border-top: 1px solid var(--border); }}
    tbody tr:nth-child(even) {{ background: #f9fafb; }}
  </style>
</head>
<body>
  <h1>{html.escape(args.title)}</h1>
  <div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel_idx)}\">Home</a> &rsaquo; <span>Season</span></div>
  <table>
    <thead><tr><th>Player</th><th>Catches</th><th>Yards</th><th>Drops</th><th>TDs</th><th>Avg Score</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {sort_script}
</body>
</html>
"""
    (out_dir / 'index.html').write_text(index_html, encoding='utf-8')
    print(f"Wrote season HTML dashboards to {out_dir}")


if __name__ == '__main__':
    main()


