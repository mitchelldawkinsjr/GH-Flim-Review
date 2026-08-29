#!/usr/bin/env python3
"""Generate the Film Review Hub CSV upload helper page (out/upload.html)."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.ghfb_hub_link import HUB_LINK_CSS, HUB_LINK_HTML, HUB_LINK_SCRIPT

DEFAULT_REPO = "mitchelldawkinsjr/GH-Flim-Review"
SEASON_RE = re.compile(r'^\d{4}-\d{4}$')


def discover_seasons(out_root: Path, csv_root: Path) -> list[str]:
    found: set[str] = set()
    for root in (out_root, csv_root):
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if p.is_dir() and SEASON_RE.match(p.name):
                found.add(p.name)
    return sorted(found, reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out_root', default='out', help='Root output directory (default: out)')
    ap.add_argument('--csv_root', default='csv', help='CSV root (default: csv)')
    args = ap.parse_args()

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    csv_root = Path(args.csv_root)
    seasons = discover_seasons(out_root, csv_root)
    if not seasons:
        seasons = ['2026-2027']
    default_season = seasons[0]
    repo = os.environ.get('GITHUB_REPOSITORY', DEFAULT_REPO).strip() or DEFAULT_REPO
    actions_url = f"https://github.com/{repo}/actions/workflows/process-week.yml"

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

    seasons_json = json.dumps(seasons)
    css = """
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --primary: #2563eb;
      --border: #e5e7eb;
    }
    body {
      font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 20px;
      background: var(--bg);
      color: var(--text);
    }
    .container { max-width: 720px; margin: 0 auto; }
    h1 { margin-bottom: 8px; font-weight: 700; letter-spacing: -0.01em; font-size: 32px; }
    .lede { color: var(--muted); margin-bottom: 24px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    label { display: block; font-weight: 600; font-size: 14px; margin: 14px 0 6px; }
    input, select {
      width: 100%;
      box-sizing: border-box;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 16px;
    }
    .filename {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      background: #f3f4f6;
      padding: 10px 12px;
      border-radius: 8px;
      word-break: break-all;
    }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
    .btn {
      display: inline-block;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      font-weight: 600;
      padding: 10px 16px;
      border-radius: 8px;
    }
    .btn.secondary { background: #fff; color: var(--primary); border: 1px solid var(--primary); }
    .note { color: var(--muted); font-size: 14px; margin-top: 16px; line-height: 1.5; }
    @media (max-width: 640px) { body { margin: 14px; } h1 { font-size: 28px; } }
    """ + HUB_LINK_CSS

    html_str = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Upload week CSV — Film Review Hub</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  {ga_snippet}
  <style>{css}</style>
</head>
<body>
  <div class="container">
    {HUB_LINK_HTML}
    <p class="hub-back"><a href="index.html">← Seasons</a></p>
    <h1>Upload week CSV</h1>
    <p class="lede">Name the file, then upload it on GitHub (or git push). The process-week Action grades it and publishes pages.</p>
    <div class="card">
      <label for="season">Season</label>
      <select id="season"></select>
      <label for="week">Week</label>
      <input id="week" type="number" min="1" max="20" value="1" />
      <label for="opponent">Opponent (short name)</label>
      <input id="opponent" type="text" placeholder="Holland" autocomplete="off" />
      <label>Required filename</label>
      <div class="filename" id="filename">Wk1_Holland.csv</div>
      <div class="actions">
        <a class="btn" id="upload" href="#" target="_blank" rel="noopener">Upload on GitHub</a>
        <a class="btn secondary" href="{html.escape(actions_url)}" target="_blank" rel="noopener">View Actions</a>
      </div>
      <p class="note">
        You need write access to <code>{html.escape(repo)}</code>.
        After the file lands in <code>csv/{{season}}/</code>, pages appear on this hub in a few minutes.
        Same result via <code>git add csv/… &amp;&amp; git push</code>,
        or <strong>Actions → Process week CSV</strong> with source <code>published_sheet</code> (pulls the Google Sheet published CSV).
      </p>
    </div>
  </div>
  {HUB_LINK_SCRIPT}
  <script>
  (function () {{
    var seasons = {seasons_json};
    var repo = {json.dumps(repo)};
    var seasonEl = document.getElementById('season');
    var weekEl = document.getElementById('week');
    var oppEl = document.getElementById('opponent');
    var fileEl = document.getElementById('filename');
    var uploadEl = document.getElementById('upload');
    seasons.forEach(function (s, i) {{
      var o = document.createElement('option');
      o.value = s; o.textContent = s;
      if (i === 0) o.selected = true;
      seasonEl.appendChild(o);
    }});
    function filename() {{
      var week = String(weekEl.value || '1').trim();
      var opp = (oppEl.value || 'Opponent').replace(/\\s+/g, '');
      return 'Wk' + week + '_' + opp + '.csv';
    }}
    function refresh() {{
      var season = seasonEl.value || {json.dumps(default_season)};
      var name = filename();
      fileEl.textContent = 'csv/' + season + '/' + name;
      uploadEl.href = 'https://github.com/' + repo + '/upload/main/csv/' + encodeURIComponent(season);
      uploadEl.onclick = function () {{
        if (window.gtag) gtag('event', 'upload_csv', {{ event_category: 'ingest', season: season }});
      }};
    }}
    ['change', 'input'].forEach(function (ev) {{
      seasonEl.addEventListener(ev, refresh);
      weekEl.addEventListener(ev, refresh);
      oppEl.addEventListener(ev, refresh);
    }});
    refresh();
  }})();
  </script>
</body>
</html>
"""
    out_path = out_root / 'upload.html'
    out_path.write_text(html_str, encoding='utf-8')
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
