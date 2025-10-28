#!/usr/bin/env python3
import argparse
from pathlib import Path
import os
from datetime import datetime
import pandas as pd
import html
import glob as _glob
import re as _re

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


def build_coach_review(player: str, totals: dict, rates: dict, code_counts: dict) -> str:
    catches = int(totals.get('catches', 0))
    targets = int(totals.get('targets', 0))
    rec_yards = int(totals.get('rec_yards', 0))
    tds = int(totals.get('touchdowns', 0))
    drops = int(totals.get('drops', 0))
    ma = int(totals.get('ma', 0))
    loafs = int(totals.get('loafs', 0))
    letter = rates.get('grade', '')
    score = float(rates.get('score', 0.0))
    catch_rate_pct = f"{rates.get('catch_rate', 0.0)*100:.1f}%"
    ypt = f"{rates.get('ypt', 0.0):.2f}"

    e_cnt = int(code_counts.get('E', 0))
    fd_cnt = int(code_counts.get('FD', 0))
    p_cnt = int(code_counts.get('P', 0))
    gb_cnt = int(code_counts.get('GB', 0))
    sc_cnt = int(code_counts.get('SC', 0))
    td_cnt = int(code_counts.get('TD', 0))

    stood_out_parts = []
    if e_cnt > 0:
        stood_out_parts.append(f"{e_cnt} effort plays")
    if fd_cnt > 0:
        stood_out_parts.append(f"{fd_cnt} first downs")
    if td_cnt > 0:
        stood_out_parts.append(f"{td_cnt} TD{'s' if td_cnt>1 else ''}")
    if p_cnt > 0:
        stood_out_parts.append(f"{p_cnt} pancakes")
    if gb_cnt > 0:
        stood_out_parts.append(f"{gb_cnt} good blocks")
    if sc_cnt > 0:
        stood_out_parts.append(f"{sc_cnt} spectacular catch{'es' if sc_cnt>1 else ''}")
    if not stood_out_parts:
        stood_out_parts.append("created positive plays and executed assignments")
    stood_out = ", ".join(stood_out_parts)

    improve_parts = []
    if loafs > 0:
        improve_parts.append("Eliminate loafs — sprint off-screen and finish every rep.")
    if drops > 0:
        improve_parts.append("Secure the ball — reduce drops with eyes-to-hands and late hands.")
    if ma > 0:
        improve_parts.append("Tighten assignments — clear pre-snap plan and alignment.")
    if not improve_parts:
        improve_parts.append("Keep assignments clean and finish blocks through the whistle.")

    goals = ["0 loafs", "75%+ catch rate"]
    goals.append("0 drops" if drops > 0 else "maintain 0 drops")
    goals.append("stack effort plays and first downs")

    return (
        "<h2>Coach Review</h2>"
        "<table><tr><th>Review</th></tr><tr><td>"
        f"<ul><li><strong>Summary</strong>: {letter} ({score:.1f}). {catches} catches on {targets} targets for {rec_yards} yards and {tds} TD{'s' if tds!=1 else ''}. {drops} drops, {ma} MA, {loafs} loafs.</li>"
        f"<li><strong>What stood out</strong>: {html.escape(stood_out)}</li>"
        f"<li><strong>Efficiency</strong>: {catch_rate_pct} catch rate and {ypt} yards per target.</li>"
        f"<li><strong>Improve</strong>: {' '.join(html.escape(s) for s in improve_parts)}</li>"
        f"<li><strong>Next week focus</strong>: {', '.join(html.escape(g) for g in goals)}.</li></ul>"
        "Keep the same intent and finish habits on every snap—your impact is elite when the motor runs hot."
        "</td></tr></table>"
    )


def render_player_html(player: str, totals: dict, rates: dict, code_counts: dict, title: str, pdf_rel: str | None = None, breadcrumbs_html: str = "", ga_snippet: str = "", week_val: str | None = None, nav_html: str = "") -> str:
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
    table h2 { margin: 0; }
    thead th { background: var(--thead); color: #111827; text-transform: uppercase; font-size: 11px; letter-spacing: .05em; padding: 12px 14px; text-align: left; }
    tbody td, td { padding: 12px 14px; border-top: 1px solid var(--border); }
    tbody tr:nth-child(odd) { background: var(--row); }
    tbody tr:nth-child(even) { background: var(--row-alt); }
    tbody tr:hover { background: #eef2ff; }
    a { color: var(--primary); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .table-wrap { overflow-x: auto; }
    @media (max-width: 640px) {
      .grid { grid-template-columns: 1fr; }
      thead th, tbody td, td { padding: 10px 12px; }
      body { margin: 14px; }
    }
    """

    metrics_rows = [
        ("Grade", f"{rates['grade']} ({rates['score']:.1f})"),
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
    ]

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

    codes_table_rows = ["<table><tr><th>Code</th><th>Meaning</th><th>Count</th></tr>"]
    for k, v in codes_rows:
        meaning = CODE_LABELS.get(k, k)
        codes_table_rows.append(
            f"<tr><td title=\"{html.escape(meaning)}\">{html.escape(k)}</td><td>{html.escape(meaning)}</td><td>{v}</td></tr>"
        )
    codes_table_rows.append("</table>")
    codes_table = "".join(codes_table_rows)

    # Optional PDF embed section
    pdf_html = ""
    if pdf_rel:
        player_esc = html.escape(player)
        week_esc = html.escape(str(week_val) if week_val else "")
        pdf_url = html.escape(pdf_rel)
        pdf_html = (
            f"<h2>Player PDF</h2>"
            f"<p><a href=\"{pdf_url}\" target=\"_blank\" onclick=\"if(window.gtag){{gtag('event','pdf_open', {{event_category: 'engagement', player: '{player_esc}', week: '{week_esc}'}});}}\">Open PDF</a></p>"
            f"<object data=\"{pdf_url}\" type=\"application/pdf\" width=\"100%\" height=\"640px\">"
            f"<p>PDF preview not available. <a href=\"{pdf_url}\" onclick=\"if(window.gtag){{gtag('event','pdf_download', {{event_category: 'engagement', player: '{player_esc}', week: '{week_esc}'}});}}\">Download</a></p>"
            f"</object>"
        )

    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
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
  <div class=\"grid\"> 
    <div>
      <h2>Totals</h2>
      <div class=\"table-wrap\">{table(metrics_rows)}</div>
    </div>
    <div>
      <h2>Rates (from totals)</h2>
      <div class=\"table-wrap\">{table(rate_rows)}</div>
    </div>
  </div>
  <h2>Code Counts</h2>
  <div class=\"table-wrap\">{codes_table}</div>
  {build_coach_review(player, totals, rates, code_counts)}
  {pdf_html}
  <p class=\"small\">Updated at {updated_at} · Generated by make_dashboard_html.py</p>
</body>
</html>
"""


def render_week(details_csv: str, out_dir: str, title: str, pdfs_dir: str | None, week: str | None, ga_snippet: str):
    df = pd.read_csv(details_csv)
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    players = sorted([cell_text(p) for p in df['player'].astype(str).unique()])
    index_items = []
    for player in players:
        if not player:
            continue
        sub = df[df['player'].astype(str) == player]
        if sub.empty:
            continue
        def sum_int(col):
            val = sub.get(col)
            if val is None:
                return 0
            ser = pd.to_numeric(val, errors='coerce')
            try:
                return int(ser.fillna(0).sum())
            except Exception:
                try:
                    return int(float(ser))
                except Exception:
                    return 0
        def sum_float(col):
            val = sub.get(col)
            if val is None:
                return 0.0
            ser = pd.to_numeric(val, errors='coerce')
            try:
                return float(ser.fillna(0.0).sum())
            except Exception:
                try:
                    return float(ser)
                except Exception:
                    return 0.0
        snaps = sum_int('snaps'); targets = sum_int('targets'); catches = sum_int('catches')
        rec_yards = sum_int('rec_yards'); rush_yards = sum_int('rush_yards'); touchdowns = sum_int('touchdowns')
        drops = sum_int('drops'); ma = sum_int('missed_assignments'); loafs = sum_int('loafs')
        code_points = sum_float('code_points')
        catch_rate = safe_div(catches, targets)
        ypt = safe_div((rec_yards + rush_yards), targets)
        tds_per30 = per30(touchdowns, snaps)
        keyplays_total = sum_int('derived_keyplays')
        keyplays_per30 = per30(keyplays_total, snaps)
        targets_per30 = per30(targets, snaps)
        drops_rate = safe_div(drops, targets)
        loafs_per30 = per30(loafs, snaps)
        ma_per30 = per30(ma, snaps)
        try:
            score_series = pd.to_numeric(sub.get('score'), errors='coerce') if sub.get('score') is not None else None
            score = float(score_series.fillna(0.0).mean()) if score_series is not None else 0.0
        except Exception:
            score = 0.0
        letter_grade = letter(score)
        totals = {'snaps': snaps,'targets': targets,'catches': catches,'rec_yards': rec_yards,'rush_yards': rush_yards,'touchdowns': touchdowns,'drops': drops,'ma': ma,'loafs': loafs,'code_points': code_points}
        rates = {'catch_rate': catch_rate,'ypt': ypt,'targets_per30': targets_per30,'keyplays_per30': keyplays_per30,'tds_per30': tds_per30,'drops_rate': drops_rate,'ma_per30': ma_per30,'loafs_per30': loafs_per30,'score': score,'grade': letter_grade}
        codes = collect_code_counts(sub)
        player_file = f"{player.strip().replace(' ', '_')}.html"
        pdf_rel = None
        if pdfs_dir and week:
            pdf_name = f"{player.strip().replace(' ', '_')}_{str(week).strip()}.pdf"
            pdf_path = Path(pdfs_dir) / pdf_name
            try:
                pdf_rel = os.path.relpath(pdf_path, out_dir_p)
            except Exception:
                pdf_rel = str(pdf_path)
        root_index = Path(out_dir_p).parent.parent / 'index.html'
        week_index = Path(out_dir_p) / 'index.html'
        try:
            home_rel = os.path.relpath(root_index, out_dir_p)
        except Exception:
            home_rel = '../../index.html'
        try:
            week_rel = os.path.relpath(week_index, out_dir_p)
        except Exception:
            week_rel = 'index.html'
        season_index = Path(out_dir_p).parent.parent / 'Season' / 'dashboards' / 'index.html'
        try:
            season_rel = os.path.relpath(season_index, out_dir_p)
        except Exception:
            season_rel = '../../Season/dashboards/index.html'
        snapshot_path = Path(out_dir_p).parent / 'snapshot.html'
        try:
            snapshot_rel = os.path.relpath(snapshot_path, out_dir_p)
        except Exception:
            snapshot_rel = '../snapshot.html'
        nav_html = f"<div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel)}\">Home</a> · <a href=\"{html.escape(week_rel)}\">Week</a> · <a href=\"{html.escape(season_rel)}\">Season</a> · <a href=\"{html.escape(snapshot_rel)}\">Snapshot</a></div>"
        breadcrumbs = f"<div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel)}\">Home</a> &rsaquo; <a href=\"{html.escape(week_rel)}\">Week</a> &rsaquo; <span>{html.escape(player)}</span></div>"
        html_str = render_player_html(player, totals, rates, codes, title, pdf_rel, breadcrumbs, ga_snippet, week, nav_html)
        (out_dir_p / player_file).write_text(html_str, encoding='utf-8')
        total_yards = rec_yards + rush_yards
        index_items.append((player, player_file, score, letter_grade, catches, total_yards, drops, touchdowns, (pdf_rel or '')))
    index_items.sort(key=lambda t: t[2], reverse=True)
    rows = "".join(
        f"<tr>"
        f"<td><a href=\"{html.escape(f)}\" onclick=\"if(window.gtag){{gtag('event','open_week_player',{{event_category:'navigation',player:'{html.escape(p)}',week:'{html.escape(str(week))}'}});}}\">{html.escape(p)}</a></td>"
        f"<td>{html.escape(l)}</td>"
        f"<td class=\"num\">{s:.1f}</td>"
        f"<td class=\"num\">{c}</td>"
        f"<td class=\"num\">{y}</td>"
        f"<td class=\"num\">{d}</td>"
        f"<td class=\"num\">{td}</td>"
        f"<td>{('<a href=\\\"' + html.escape(pdf) + '\\\">PDF</a>') if pdf else '-'}</td>"
        f"</tr>"
        for p, f, s, l, c, y, d, td, pdf in index_items
    )
    totals_row = ""
    if index_items:
        try:
            avg_score = sum(it[2] for it in index_items) / len(index_items)
        except Exception:
            avg_score = 0.0
        total_catches = sum(it[4] for it in index_items)
        total_yards = sum(it[5] for it in index_items)
        total_drops = sum(it[6] for it in index_items)
        total_tds = sum(it[7] for it in index_items)
        totals_row = (
            f"<tr>"
            f"<td><strong>Totals</strong></td>"
            f"<td>-</td>"
            f"<td class=\"num\"><strong>{avg_score:.1f}</strong></td>"
            f"<td class=\"num\"><strong>{total_catches}</strong></td>"
            f"<td class=\"num\"><strong>{total_yards}</strong></td>"
            f"<td class=\"num\"><strong>{total_drops}</strong></td>"
            f"<td class=\"num\"><strong>{total_tds}</strong></td>"
            f"<td>-</td>"
            f"</tr>"
        )
    try:
        home_rel_idx = os.path.relpath(Path(out_dir_p).parent.parent / 'index.html', out_dir_p)
    except Exception:
        home_rel_idx = '../index.html'
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
    filter_script = """
  <script>
    (function(){
      const input = document.getElementById('playerFilter');
      if(!input) return;
      input.addEventListener('input', function(){
        const q = this.value.trim().toLowerCase();
        const rows = Array.from(document.querySelectorAll('tbody tr'));
        rows.forEach(function(r){
          const name = (r.children[0] && r.children[0].innerText ? r.children[0].innerText : '').toLowerCase();
          r.style.display = name.indexOf(q) !== -1 ? '' : 'none';
        });
      });
    })();
  </script>
    """
    try:
        csv_rel = os.path.relpath(details_csv, out_dir_p)
    except Exception:
        csv_rel = details_csv
    updated_at_idx = datetime.now().strftime('%Y-%m-%d %H:%M')
    index_html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{html.escape(title)}</title>
  {ga_snippet}
  <style>
    :root {{ --bg:#f5f7fb; --card:#ffffff; --text:#111827; --muted:#6b7280; --primary:#2563eb; --row:#ffffff; --row-alt:#f9fafb; --thead:linear-gradient(135deg,#eef2ff 0%,#e0e7ff 100%); --border:#e5e7eb; }}
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: var(--bg); color: var(--text); }}
    h1 {{ margin-bottom: 12px; font-weight: 700; letter-spacing: -0.01em; }}
    .breadcrumbs {{ font-size: 12px; color: #666; margin-bottom: 8px; }}
    .breadcrumbs a {{ color: var(--primary); text-decoration: none; }}
    .breadcrumbs a:hover {{ text-decoration: underline; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }}
    thead th {{ background: var(--thead); color: #111827; text-transform: uppercase; font-size: 11px; letter-spacing: .05em; padding: 12px 14px; text-align: left; position: sticky; top: 0; z-index: 2; cursor: pointer; }}
    thead th[data-sort=\"asc\"]::after {{ content: " \25B2"; font-size: 10px; color: #6b7280; }}
    thead th[data-sort=\"desc\"]::after {{ content: " \25BC"; font-size: 10px; color: #6b7280; }}
    tbody td {{ padding: 12px 14px; border-top: 1px solid var(--border); }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    tbody tr:nth-child(odd) {{ background: var(--row); }}
    tbody tr:nth-child(even) {{ background: var(--row-alt); }}
    tbody tr:hover {{ background: #eef2ff; }}
  </style>
  {sort_script}
  {filter_script}
</head>
<body>
  <div class=\"breadcrumbs\"><a href=\"{html.escape(home_rel_idx)}\">Home</a> · <a href=\"../../Season/dashboards/index.html\">Season</a></div>
  <h1>{html.escape(title)}</h1>
  <div class=\"small\"><a href=\"{html.escape(csv_rel)}\">Download details CSV</a></div>
  <div style=\"margin:8px 0 12px\"><input id=\"playerFilter\" type=\"search\" placeholder=\"Filter players...\" style=\"padding:8px 10px;border:1px solid var(--border);border-radius:8px;width:240px;\"></div>
  <div class=\"table-wrap\">
    <table>
      <thead><tr><th>Player</th><th>Letter</th><th>Avg Score</th><th>Catches</th><th>Yards</th><th>Drops</th><th>TDs</th><th>PDF</th></tr></thead>
      <tbody>{rows}{totals_row}</tbody>
    </table>
  </div>
  <p class=\"small\" style=\"margin-top:8px\">Updated at {updated_at_idx}</p>
</body>
</html>
"""
    (out_dir_p / 'index.html').write_text(index_html, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description='Generate per-player HTML dashboards from detailed CSV or batch via glob')
    ap.add_argument('--details_csv', help='Weekly detailed results CSV')
    ap.add_argument('--out_dir', help='Output dashboards dir for weekly mode')
    ap.add_argument('--title', default='Player Dashboards')
    ap.add_argument('--pdfs_dir', help='Directory containing per-player PDFs (weekly mode)')
    ap.add_argument('--week', help='Week number for PDF filenames like Player_8.pdf (weekly mode)')
    ap.add_argument('--weekly_glob', help='Glob of weekly detailed results CSVs to batch-generate dashboards (CI mode)')
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

    if args.weekly_glob and not args.details_csv:
        paths = sorted(_glob.glob(args.weekly_glob))
        for p in paths:
            out_dir = str(Path(p).parent / 'dashboards')
            m = _re.search(r"Wk(\d+)", p)
            week = m.group(1) if m else None
            pdfs_dir = str((Path(p).parent / 'pdfs'))
            render_week(p, out_dir, f"Week {week} Player Dashboards" if week else "Player Dashboards", pdfs_dir, week, ga_snippet)
        print("Batch dashboards generated.")
        return

    if not (args.details_csv and args.out_dir):
        ap.error("In weekly mode, --details_csv and --out_dir are required")
    render_week(args.details_csv, args.out_dir, args.title, args.pdfs_dir, args.week, ga_snippet)
    print(f"Wrote HTML dashboards to {args.out_dir}")


if __name__ == '__main__':
    main()


