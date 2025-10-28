
# Film Review Pipeline

A data pipeline and static site generator for weekly and season-long player evaluations from CSV film logs. Outputs per-player PDFs, weekly and season HTML dashboards, a snapshot table per week, and a main site index suitable for GitHub Pages.

## Quick Start

1) Create and activate venv (first time):

```bash
python3 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install pandas reportlab pypdf pillow openpyxl numpy
```

2) Prepare weekly CSV (example: Week 7):

```bash
./venv/bin/python tools/prep_wk7.py csv/Wk7_Fruitport.csv --out out/Wk7/Wk7_Fruitport_prepared.csv --week 7
```

3) Grade and generate all artifacts for that week:

```bash
./venv/bin/python film_grade.py out/Wk7/Wk7_Fruitport_prepared.csv --out_dir out/Wk7 --out results_Wk7_Fruitport.csv
./venv/bin/python tools/make_pdfs.py \
  --reports_dir out/Wk7/reports \
  --out_dir out/Wk7/pdfs \
  --summary_csv out/Wk7/results_Wk7_Fruitport_summary.csv \
  --details_csv out/Wk7/results_Wk7_Fruitport.csv \
  --title "Week 7 Summary"
./venv/bin/python tools/make_dashboard_html.py \
  --details_csv out/Wk7/results_Wk7_Fruitport.csv \
  --out_dir out/Wk7/dashboards \
  --title "Week 7 Player Dashboards" \
  --pdfs_dir out/Wk7/pdfs \
  --week 7
./venv/bin/python tools/make_snapshot_html.py \
  --details_csv out/Wk7/results_Wk7_Fruitport.csv \
  --prepared_csv out/Wk7/Wk7_Fruitport_prepared.csv \
  --out out/Wk7/snapshot.html
```

4) Rebuild Season dashboards and Site index:

```bash
./venv/bin/python tools/make_season_dashboard_html.py \
  --weekly_glob "out/Wk*/results_*.csv" \
  --out_dir out/Season/dashboards \
  --title "Season Player Dashboards"
./venv/bin/python tools/make_site_index.py --out_root out
```

## Rubric (Key Play Points)
- Positive: TD +15, Relentless Effort +5, Elite Route +7, Good Route +2, Catch/Rush yardage +0.5/yd, Broken Tackle(s) +1.0/bt, Good Block +2, Pancake +10, First Down +5, Spectacular Catch +10
- Negative: Missed Assignment -10, Dropped Pass -15, Bad Route -2, Loaf -2, Not Full Speed -3, Whiffed -1, Holding 0

## Metrics (definitions)
- Catch Rate = catches / (catches + drops)
- Drop Rate = drops / (catches + drops)
- Yards per Target = (rec_yards + rush_yards) / targets
- TDs per 30, Targets per 30, Key Plays per 30 = per-30 snap-normalized rates

## Outputs
- out/WkX/reports: per-player text reports
- out/WkX/pdfs: per-player PDF + weekly summary and group film PDFs
- out/WkX/dashboards: per-player weekly dashboards (HTML)
- out/WkX/snapshot.html: weekly snapshot table
- out/Season/dashboards: season dashboards (index + per-player)
- out/index.html: site landing page with links to all weeks and season

## Google Analytics (GA4)
Set GA_MEASUREMENT_ID in your environment (locally or GitHub Actions) to inject the gtag snippet and enable event tracking (PDF opens, navigation clicks).

Example local run:
```bash
export GA_MEASUREMENT_ID=G-XXXXXXXXXX
./venv/bin/python tools/make_site_index.py --out_root out
```

## CI/CD (GitHub Pages)
- GitHub Actions workflow publishes the `out/` directory to the `gh-pages` branch on every push to `main`.
- Ensure Pages is set to build from `gh-pages` branch (root).

## Batch Rebuild Script (all weeks)
Use this one-liner to rebuild weekly outputs, season dashboards, and site index:

```bash
for d in out/Wk*; do \
  wk="${d##*/Wk}"; \
  prep=$(ls "$d"/Wk*_*_prepared.csv 2>/dev/null | head -n1 || true); \
  details=$(ls "$d"/results_*.csv 2>/dev/null | grep -v summary | head -n1 || true); \
  [ -f "$prep" ] && [ -f "$details" ] || continue; \
  ./venv/bin/python film_grade.py "$prep" --out_dir "$d" --out "$(basename "$details")"; \
  ./venv/bin/python tools/make_pdfs.py --reports_dir "$d/reports" --out_dir "$d/pdfs" --summary_csv "${details%.csv}_summary.csv" --details_csv "$details" --title "Week $wk Summary"; \
  ./venv/bin/python tools/make_dashboard_html.py --details_csv "$details" --out_dir "$d/dashboards" --title "Week $wk Player Dashboards" --pdfs_dir "$d/pdfs" --week "$wk"; \
  ./venv/bin/python tools/make_snapshot_html.py --details_csv "$details" --prepared_csv "$prep" --out "$d/snapshot.html"; \
 done; \
 ./venv/bin/python tools/make_season_dashboard_html.py --weekly_glob "out/Wk*/results_*.csv" --out_dir out/Season/dashboards --title "Season Player Dashboards"; \
 ./venv/bin/python tools/make_site_index.py --out_root out
```

## Notes
- Discipline (MA/Loaf) is derived from codes when provided and zeroed when snaps=0.
- Group film PDF aggregates per-play details and code expansions.
- All HTML is mobile-optimized (responsive tables, sparkline, embedded PDF height).
