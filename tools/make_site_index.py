#!/usr/bin/env python3
import argparse
from pathlib import Path
import glob
import html
import re
import os


def main():
    ap = argparse.ArgumentParser(description='Generate a landing index at out/index.html')
    ap.add_argument('--out_root', default='out', help='Root output directory (default: out)')
    args = ap.parse_args()

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Season dashboard
    season_index = out_root / 'Season' / 'dashboards' / 'index.html'

    # Weeks discovered
    week_dirs = sorted([p for p in out_root.glob('Wk*') if p.is_dir()])

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(out_root))
        except Exception:
            return str(p)

    # GA from env
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

    weeks_rows = []
    for wd in week_dirs:
        week_name = wd.name
        dashboards = wd / 'dashboards' / 'index.html'
        pdfs_dir = wd / 'pdfs'
        summary_pdf = pdfs_dir / 'summary.pdf'
        group_pdf = pdfs_dir / 'group_film_study.pdf'
        # Find weekly results/summary CSVs
        csvs = sorted(glob.glob(str(wd / 'results_*.csv')))
        # Derive opponent from results or prepared filenames
        opponent = ''
        if csvs:
            stem = Path(csvs[0]).stem  # e.g., results_Wk8_Kville
            m = re.search(r'results_Wk\d+_(.+)$', stem)
            if m:
                opponent = m.group(1)
        if not opponent:
            prep_files = sorted(glob.glob(str(wd / 'Wk*_*_prepared.csv')))
            if prep_files:
                stem = Path(prep_files[0]).stem  # e.g., Wk8_Kville_prepared
                m = re.search(r'Wk\d+_(.+)_prepared$', stem)
                if m:
                    opponent = m.group(1)
        csv_links = ' '.join(f"<a href=\"{html.escape(rel(Path(c)))}\" onclick=\"if(window.gtag){{gtag('event','open_csv',{{event_category:'navigation',week:'{html.escape(week_name)}'}});}}\">{html.escape(Path(c).name)}</a>" for c in csvs)
        # Snapshot link: always render (file exists for generated weeks)
        snapshot_rel = rel(wd / 'snapshot.html')
        snapshot_link = f"<a href=\"{html.escape(snapshot_rel)}\" onclick=\"if(window.gtag){{gtag('event','open_snapshot',{{event_category:'navigation',week:'{html.escape(week_name)}'}});}}\">Snapshot</a>"
        weeks_rows.append(
            f"<tr><td>{html.escape(week_name)}</td><td>{html.escape(opponent) if opponent else '-'}</td>"
            f"<td><a href=\"{html.escape(rel(dashboards))}\" onclick=\"if(window.gtag){{gtag('event','open_week_dash',{{event_category:'navigation',week:'{html.escape(week_name)}'}});}}\">Dashboards</a></td>"
            f"<td><a href=\"{html.escape(rel(summary_pdf))}\" onclick=\"if(window.gtag){{gtag('event','open_summary_pdf',{{event_category:'navigation',week:'{html.escape(week_name)}'}});}}\">Summary PDF</a></td>"
            f"<td><a href=\"{html.escape(rel(group_pdf))}\" onclick=\"if(window.gtag){{gtag('event','open_group_pdf',{{event_category:'navigation',week:'{html.escape(week_name)}'}});}}\">Group Film PDF</a></td>"
            f"<td>{snapshot_link}</td>"
            f"<td>{csv_links}</td>"
            f"</tr>"
        )

    html_str = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Film Review Hub</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  {ga_snippet}
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --primary: #2563eb;
      --row: #ffffff;
      --row-alt: #f9fafb;
      --thead: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
      --border: #e5e7eb;
    }}
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: var(--bg); color: var(--text); }}
    h1 {{ margin-bottom: 12px; font-weight: 700; letter-spacing: -0.01em; }}
    .section {{ margin-top: 24px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .muted {{ color: var(--muted); font-size: 12px; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }}
    thead th {{ background: var(--thead); color: #111827; text-transform: uppercase; font-size: 11px; letter-spacing: .05em; padding: 12px 14px; text-align: left; }}
    tbody td {{ padding: 12px 14px; border-top: 1px solid var(--border); }}
    tbody tr:nth-child(odd) {{ background: var(--row); }}
    tbody tr:nth-child(even) {{ background: var(--row-alt); }}
    tbody tr:hover {{ background: #eef2ff; }}
    a {{ color: var(--primary); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    details summary {{ cursor: pointer; }}
  </style>
</head>
<body>
  <h1>Film Review Hub</h1>

  <div class=\"cards\">
    <div class=\"card\">
      <div><b>Season Dashboards</b></div>
      <div class=\"muted\">Totals & rates per player</div>
      <div style=\"margin-top:8px\"><a href=\"{html.escape(rel(season_index))}\" onclick=\"if(window.gtag){{gtag('event','open_season_dash',{{event_category:'navigation'}});}}\">Open</a></div>
    </div>
  </div>

  <div class=\"section\" style=\"margin-top:18px\">
    <details>
      <summary><b>How to score well</b></summary>
      <ul>
        <li><b>Relentless effort every rep</b>: finish full speed, strain on blocks (earn Relentless Effort, avoid Loaf/Not Full Speed).</li>
        <li><b>Master your assignment</b>: split, depth, route landmark, adjust vs coverage (avoid Missed Assignment).</li>
        <li><b>Elite, crisp routes</b>: full depth, explode out, hold leverage (earn Elite Route/Good Route, avoid Bad Route).</li>
        <li><b>Win the ball</b>: eyes-to-tuck, high-point, squeeze through contact (earn Spectacular Catch, avoid Dropped Pass).</li>
        <li><b>Add yards and chains</b>: fight through contact; Catch/Rush yardage = +0.5 per yard; Broken Tackle(s) +1.0/bt; First Downs +5.</li>
        <li><b>Dominate run game</b>: position + hand fit + run feet (Good Block +2, Pancake +10).</li>
        <li><b>Finish drives</b>: Touchdowns are +15; red-zone detail matters.</li>
      </ul>
      <div class=\"muted\">Key Play Points Rubric: Touchdown +15, Relentless Effort +5, Elite Route +7, Good Route +2, Catch/Rush yardage +0.5/yd, Broken Tackle(s) +1.0/bt, Good Block +2, Pancake +10, First Down +5, Spectacular Catch +10; Missed Assignment -10, Dropped Pass -15, Bad Route -2, Loaf (Laziness) -2, Not Full Speed -3, Whiffed -1, Holding 0.</div>
    </details>
  </div>
  <div class=\"section\">
    <h2>Weeks</h2>
    <table>
      <thead><tr><th>Week</th><th>Opponent</th><th>Weekly Dashboards</th><th>Summary</th><th>Group Film</th><th>Snapshot</th><th>CSVs</th></tr></thead>
      <tbody>{''.join(weeks_rows)}</tbody>
    </table>
  </div>

  <p class=\"muted\">Generated by make_site_index.py</p>
</body>
</html>
"""

    (out_root / 'index.html').write_text(html_str, encoding='utf-8')
    print(f"Wrote landing index to {out_root/'index.html'}")


if __name__ == '__main__':
    main()


