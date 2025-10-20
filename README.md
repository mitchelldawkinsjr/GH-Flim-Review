
# Film Grade CLI

A single-file Python script that grades weekly receiver film from a CSV using your weights:
- Base 73
- +15 × catch rate
- +1.5 × min(yards per target ÷ 8, 1)
- +12 × min(TDs per 30 snaps, 1)
- +6 × min(sqrt(key plays per 30), 1.33)
- +4 × min(targets per 30 snaps, 1)
- +1 × min(catch rate × (yards per target ÷ 8), 1)
- −12 × drop rate (biggest penalty)
- −4 × loafs per 30 snaps
- −9 × min(missed assignments per 30 snaps, 1) (second‑worst penalty)
- Clamped 0..100, with letter grade A–F

## Required columns (case‑insensitive)
player, week, snaps, targets, catches, rec_yards, rush_yards, touchdowns, drops, missed_assignments, loafs, key_plays

## How to run
1. Ensure Python 3.9+ and packages are installed (from the project root):
   ```bash
   /Users/mitchelldawkins/Projects/scripts/venv/bin/pip install -U pandas reportlab pypdf
   ```
2. Save your data as CSV (see examples in `csv/`).
3. Run grading and send everything to a folder you name (e.g., `Wk7_Out`):
   ```bash
   /Users/mitchelldawkins/Projects/scripts/venv/bin/python /Users/mitchelldawkins/Projects/scripts/film_grade.py \
     /Users/mitchelldawkins/Projects/scripts/csv/Wk7_Fruitport.csv \
     --out_dir /Users/mitchelldawkins/Projects/scripts/Wk7_Out \
     --out results_Wk7_Fruitport.csv
   ```
4. Outputs inside your folder:
   - `<out_dir>/results_Wk7_Fruitport.csv` — detailed per‑row grades and metrics
   - `<out_dir>/results_Wk7_Fruitport_summary.csv` — averages grouped by `--by` (default: player)
   - `<out_dir>/reports/*.txt` — player review text reports (`<Player>_<Week>.txt`)
5. Optional: generate PDFs (player reports + a summary PDF) into a `pdfs/` subfolder:
   ```bash
   /Users/mitchelldawkins/Projects/scripts/venv/bin/python /Users/mitchelldawkins/Projects/scripts/tools/make_pdfs.py \
     --reports_dir /Users/mitchelldawkins/Projects/scripts/Wk7_Out/reports \
     --out_dir /Users/mitchelldawkins/Projects/scripts/Wk7_Out/pdfs \
     --summary_csv /Users/mitchelldawkins/Projects/scripts/Wk7_Out/results_Wk7_Fruitport_summary.csv \
     --details_csv /Users/mitchelldawkins/Projects/scripts/Wk7_Out/results_Wk7_Fruitport.csv \
     --title "Week 7 Summary"
   ```

## Tips
- Column names are normalized, so `Missed Assignments`, `missed_assignments`, or `MissedAssignments` all work.
- Use `--by week` to summarize weekly league view, or `--by player` for season view.
\n\n
# Film Grade CLI — Codes Support

Now supports your film codes (with Whiffed = -2) via a "codes" column. Enter per-play codes like:
- "(ER) (C+12) (FD)"
- "ER; C+12; FD"
- "ER C+12 FD"

**Legend (points):**
TD +10, E +3, ER +5, GR +2, C+n +n, GB +2, P +5, FD +2, R+N +N, MA -5, SC +5, DP -3, H 0, BR 0, L -1, NFS -1, W -2

The script computes:
- `code_points` per play (row), summed in summaries.
- Per-code counts (columns prefixed with `cnt_`).
- Player-facing review reports saved to `<out_dir>/reports/<player>_<week>.txt` with:
  - Summary line (grade, snaps, targets, catches, yards, TDs)
  - What You Did Well (top positive codes)
  - Where To Improve (top negative codes)
  - Coaching Points (auto-generated)

Run:
```bash
/Users/mitchelldawkins/Projects/scripts/venv/bin/python /Users/mitchelldawkins/Projects/scripts/film_grade.py input.csv --out_dir /absolute/path/to/MyWeekOut --out results.csv
```

## All-in-one command (prep → grade → PDFs)

```bash
cd /Users/mitchelldawkins/Projects/scripts && \
WEEK=7 OUT=out/Wk$WEEK && \
./venv/bin/python tools/prep_wk7.py csv/Wk7_Fruitport.csv --out $OUT/Wk${WEEK}_Fruitport_prepared.csv --week $WEEK && \
./venv/bin/python film_grade.py $OUT/Wk${WEEK}_Fruitport_prepared.csv --out_dir $OUT --out results_Wk${WEEK}_Fruitport.csv && \
./venv/bin/python tools/make_pdfs.py --reports_dir $OUT/reports --out_dir $OUT/pdfs --summary_csv $OUT/results_Wk${WEEK}_Fruitport_summary.csv --details_csv $OUT/results_Wk${WEEK}_Fruitport.csv --title "Week $WEEK Summary"
```

What each part does:
- **WEEK**: sets the week number used in file names and the prep step.
- **OUT**: where all outputs go (e.g., `out/Wk7`).
- **prep_wk7.py**: normalizes spreadsheet headers, merges key‑play columns, adds `week`, writes a prepared CSV.
- **film_grade.py**: computes grades, writes `<OUT>/results_*.csv`, `<OUT>/results_*_summary.csv`, and `<OUT>/reports/*.txt`.
- **make_pdfs.py**: creates player PDFs to `<OUT>/pdfs/` and a `summary.pdf` from the summary CSV.
