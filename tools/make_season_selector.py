#!/usr/bin/env python3
"""
Generate season selector landing page with top 5 WRs for each season.
"""
import argparse
from pathlib import Path
import pandas as pd
import html
import os
import sys

# Import letter function from film_grade
sys.path.insert(0, str(Path(__file__).parent.parent))
from film_grade import letter


def calculate_top_wrs(season_path: Path, top_n: int = 5, excluded_players: list = None) -> list[dict]:
    """Calculate top N WRs by season average grade, excluding specified players"""
    if excluded_players is None:
        excluded_players = []
    
    # Normalize excluded player names for comparison
    excluded_normalized = {p.strip().lower() for p in excluded_players}
    
    # Aggregate from weekly summary CSVs
    weekly_summaries = list(season_path.glob('Wk*/results_*_summary.csv'))
    
    if not weekly_summaries:
        return []
    
    # Aggregate scores per player
    player_scores = {}  # {player: [scores]}
    for csv_path in weekly_summaries:
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                player = str(row['player']).strip()
                # Skip excluded players
                if player.lower() in excluded_normalized:
                    continue
                score = float(pd.to_numeric(row.get('score', 0), errors='coerce') or 0)
                if player and not pd.isna(score):
                    if player not in player_scores:
                        player_scores[player] = []
                    player_scores[player].append(score)
        except Exception as e:
            # Skip invalid CSVs
            continue
    
    # Calculate averages and sort
    player_avgs = []
    for player, scores in player_scores.items():
        if scores:
            avg = sum(scores) / len(scores)
            letter_grade = letter(avg)
            player_avgs.append({
                'player': player,
                'avg_score': avg,
                'letter_grade': letter_grade,
                'games': len(scores)
            })
    
    # Sort by avg_score descending, take top N
    player_avgs.sort(key=lambda x: x['avg_score'], reverse=True)
    return player_avgs[:top_n]


def main():
    ap = argparse.ArgumentParser(description='Generate season selector landing page')
    ap.add_argument('--out_root', default='out', help='Root output directory (default: out)')
    args = ap.parse_args()
    
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    
    # Discover available seasons
    seasons = []
    for season_dir in sorted(out_root.glob('[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]')):
        if season_dir.is_dir():
            seasons.append(season_dir.name)
    seasons.sort(reverse=True)  # Most recent first
    
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
    
    css = """
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --primary: #2563eb;
      --border: #e5e7eb;
      --gold: #fbbf24;
      --silver: #9ca3af;
      --bronze: #cd7f32;
    }
    body { 
      font-family: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; 
      margin: 0;
      padding: 20px;
      background: var(--bg); 
      color: var(--text); 
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    h1 { 
      margin-bottom: 24px; 
      font-weight: 700; 
      letter-spacing: -0.01em; 
      font-size: 32px;
    }
    .seasons-grid { 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
      gap: 20px; 
      margin-top: 24px;
    }
    .season-card { 
      background: var(--card); 
      border: 1px solid var(--border); 
      border-radius: 16px; 
      padding: 20px; 
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .season-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    .season-title {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 16px;
      color: var(--primary);
    }
    .season-title a {
      color: var(--primary);
      text-decoration: none;
    }
    .season-title a:hover {
      text-decoration: underline;
    }
    .top-wrs {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
    }
    .top-wrs-title {
      font-size: 14px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 12px;
    }
    .wr-item {
      display: flex;
      align-items: center;
      padding: 8px 0;
      font-size: 15px;
    }
    .wr-rank {
      font-weight: 700;
      min-width: 40px;
      font-size: 16px;
    }
    .wr-rank.rank-1 { color: var(--gold); }
    .wr-rank.rank-2 { color: var(--silver); }
    .wr-rank.rank-3 { color: var(--bronze); }
    .wr-rank.rank-4, .wr-rank.rank-5 { color: var(--muted); }
    .wr-name {
      flex: 1;
      color: var(--text);
      font-weight: 500;
    }
    .wr-grade {
      color: var(--muted);
      font-size: 14px;
      margin-left: 8px;
    }
    .wr-score {
      color: var(--text);
      font-weight: 600;
      margin-left: auto;
    }
    .no-data {
      color: var(--muted);
      font-style: italic;
      font-size: 14px;
    }
    @media (max-width: 640px) { 
      body { margin: 14px; }
      .seasons-grid {
        grid-template-columns: 1fr;
      }
      h1 {
        font-size: 28px;
      }
    }
    """
    
    season_cards_html = []
    for season in seasons:
        season_path = out_root / season
        # Exclude Res and Ju for 2025-2026 season
        excluded_players = []
        if season == '2025-2026':
            excluded_players = ['Res', 'Ju']
        top_wrs = calculate_top_wrs(season_path, top_n=5, excluded_players=excluded_players)
        
        # Build top WRs HTML
        wr_items_html = []
        if top_wrs:
            for idx, wr in enumerate(top_wrs, 1):
                rank_class = f"rank-{idx}"
                wr_items_html.append(
                    f'<div class="wr-item">'
                    f'<span class="wr-rank {rank_class}">#{idx}</span>'
                    f'<span class="wr-name">{html.escape(wr["player"])}</span>'
                    f'<span class="wr-score">{wr["avg_score"]:.1f}</span>'
                    f'<span class="wr-grade">({wr["letter_grade"]})</span>'
                    f'</div>'
                )
        else:
            wr_items_html.append('<div class="no-data">No data available</div>')
        
        top_wrs_html = ''.join(wr_items_html)
        
        season_cards_html.append(f"""
    <div class="season-card">
      <div class="season-title">
        <a href="{html.escape(season)}/index.html" onclick="if(window.gtag){{gtag('event','select_season',{{event_category:'navigation',season:'{html.escape(season)}'}});}}">
          {html.escape(season)} Season
        </a>
      </div>
      <div class="top-wrs">
        <div class="top-wrs-title">Top 5 Wide Receivers</div>
        {top_wrs_html}
      </div>
    </div>
        """)
    
    if not season_cards_html:
        season_cards_html.append("""
    <div class="season-card">
      <div class="season-title">No Seasons Available</div>
      <div class="no-data">No season data found. Please run the workflow to generate season content.</div>
    </div>
        """)
    
    html_str = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Film Review Hub - Select Season</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  {ga_snippet}
  <style>{css}</style>
</head>
<body>
  <div class="container">
    <h1>Film Review Hub</h1>
    <p style="color: var(--muted); margin-bottom: 8px;">Select a season to view player dashboards, weekly reports, and statistics.</p>
    
    <div class="seasons-grid">
      {''.join(season_cards_html)}
    </div>
    
    <p style="margin-top: 32px; color: var(--muted); font-size: 12px;">Generated by make_season_selector.py</p>
  </div>
</body>
</html>
"""
    
    (out_root / 'index.html').write_text(html_str, encoding='utf-8')
    print(f"Wrote season selector to {out_root/'index.html'}")


if __name__ == '__main__':
    main()

