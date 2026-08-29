#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def _csv_filenames(week: int, opponent: str) -> list[str]:
    opp_raw = opponent
    return [
        f"Wk{week}_{opp_raw}.csv",
        f"Wk{week}{opp_raw}.csv",
        f"Wk{week}_{opp_raw.replace(' ', '_')}.csv",
        f"Wk{week}{opp_raw.replace(' ', '')}.csv",
    ]


def find_csv(
    week: int,
    opponent: str,
    explicit_path: str | None,
    season: str | None = None,
    csv_root: Path | None = None,
    project_root: Path | None = None,
) -> Path:
    if explicit_path:
        p = Path(explicit_path)
        candidates = [p]
        if not p.is_absolute() and project_root is not None:
            candidates.append(project_root / p)
        for c in candidates:
            if c.exists():
                return c
        raise SystemExit(f"CSV not found at provided path: {p}")

    csv_root = csv_root if csv_root is not None else Path('csv')
    if not csv_root.exists():
        raise SystemExit(f"csv/ directory not found at {csv_root}")

    # Prefer the season folder (csv/2026-2027/), then legacy csv/ root
    search_dirs: list[Path] = []
    if season:
        search_dirs.append(csv_root / season)
    search_dirs.append(csv_root)

    for csv_dir in search_dirs:
        if not csv_dir.is_dir():
            continue
        for name in _csv_filenames(week, opponent):
            c = csv_dir / name
            if c.exists():
                return c

    week_tag = f"wk{week}".lower()

    def norm(s: str) -> str:
        return ''.join(ch.lower() for ch in s if ch.isalnum())

    opp_norm = norm(opponent)
    matches: list[Path] = []
    for csv_dir in search_dirs:
        if not csv_dir.is_dir():
            continue
        for p in csv_dir.glob('*.csv'):
            name_norm = norm(p.name)
            if week_tag in name_norm and opp_norm in name_norm:
                matches.append(p)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        pref = [m for m in matches if f"wk{week}_" in m.name.lower()]
        if pref:
            return pref[0]
        return matches[0]

    searched = ', '.join(str(d) for d in search_dirs)
    raise SystemExit(
        f"Could not locate CSV for week {week} and opponent '{opponent}'.\n"
        f"Searched in: {searched}"
    )


def pick_python_bin(user_bin: str | None, project_root: Path | None = None) -> str:
    # Prefer provided venv python if it exists, else fallback to current interpreter
    if user_bin:
        pb = Path(user_bin)
        if pb.exists():
            return str(pb)
    venv_default = (project_root / 'venv' / 'bin' / 'python') if project_root else Path('./venv/bin/python')
    if venv_default.exists():
        return str(venv_default)
    cwd_venv = Path('./venv/bin/python')
    if cwd_venv.exists():
        return str(cwd_venv)
    return sys.executable


def main():
    ap = argparse.ArgumentParser(description="Run weekly film workflow end-to-end.")
    ap.add_argument('--week', type=int, required=True, help='Week number, e.g., 8')
    ap.add_argument('--opponent', required=True, help='Opponent short name, e.g., Kville')
    ap.add_argument('--season', default='2025-2026', help='Season identifier (default: 2025-2026)')
    ap.add_argument('--csv', help='Override input CSV path')
    ap.add_argument('--out_dir', help='Output directory (default: out/{season}/Wk<week>)')
    ap.add_argument('--python', dest='python_bin', help='Python binary to use (default: ./venv/bin/python or current)')
    args = ap.parse_args()

    week = int(args.week)
    opp = str(args.opponent)
    season = str(args.season)

    project_root = Path(__file__).resolve().parents[1]
    csv_path = find_csv(
        week, opp, args.csv,
        season=season,
        csv_root=project_root / 'csv',
        project_root=project_root,
    )

    out_dir = Path(args.out_dir) if args.out_dir else project_root / 'out' / season / f"Wk{week}"
    out_dir.mkdir(parents=True, exist_ok=True)

    python_bin = pick_python_bin(args.python_bin, project_root=project_root)

    prepared_csv = out_dir / f"Wk{week}_{opp}_prepared.csv"
    results_csv_name = f"results_Wk{week}_{opp}.csv"
    results_csv = out_dir / results_csv_name
    summary_csv = out_dir / f"results_Wk{week}_{opp}_summary.csv"

    # Step 1: prep
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'prep_wk7.py'),
        str(csv_path), '--out', str(prepared_csv), '--week', str(week)
    ], check=True)

    # Step 2: grade
    subprocess.run([
        python_bin, str(project_root / 'film_grade.py'),
        str(prepared_csv), '--out_dir', str(out_dir), '--out', results_csv_name
    ], check=True)

    # Step 3: PDFs
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_pdfs.py'),
        '--reports_dir', str(out_dir / 'reports'),
        '--out_dir', str(out_dir / 'pdfs'),
        '--summary_csv', str(summary_csv),
        '--details_csv', str(results_csv),
        '--title', f"Week {week} Summary"
    ], check=True)

    # Step 4: Group film study PDF from raw CSV
    group_pdf = out_dir / 'pdfs' / 'group_film_study.pdf'
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_group_film_pdf.py'),
        '--csv', str(csv_path),
        '--out', str(group_pdf),
        '--week', str(week),
        '--opponent', opp,
    ], check=True)

    print("\nDone. Outputs:")
    print(f"  Prepared CSV: {prepared_csv}")
    print(f"  Results CSV:  {results_csv}")
    print(f"  Summary CSV:  {summary_csv}")
    print(f"  Reports dir:  {out_dir / 'reports'}")
    print(f"  PDFs dir:     {out_dir / 'pdfs'}")
    print(f"  Group Film PDF: {group_pdf}")
    # Step 5: Per-player dashboards
    dashboards_pdf = out_dir / 'pdfs' / 'dashboards.pdf'
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_dashboard.py'),
        '--details_csv', str(results_csv),
        '--out_pdf', str(dashboards_pdf),
        '--title', f"Week {week} Player Dashboards"
    ], check=True)
    print(f"  Dashboards PDF: {dashboards_pdf}")
    # HTML dashboards
    dashboards_html_dir = out_dir / 'dashboards'
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_dashboard_html.py'),
        '--details_csv', str(results_csv),
        '--out_dir', str(dashboards_html_dir),
        '--title', f"Week {week} Player Dashboards",
        '--pdfs_dir', str(out_dir / 'pdfs'),
        '--week', str(week)
    ], check=True)
    print(f"  Dashboards HTML: {dashboards_html_dir}/index.html")

    # Weekly Snapshot HTML (spreadsheet-like table)
    snapshot_html = out_dir / 'snapshot.html'
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_snapshot_html.py'),
        '--details_csv', str(results_csv),
        '--prepared_csv', str(prepared_csv),
        '--out', str(snapshot_html)
    ], check=True)

    # Season dashboards (aggregate across out/{season}/Wk*/results_*.csv)
    season_dir = project_root / 'out' / season / 'Season' / 'dashboards'
    season_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_season_dashboard_html.py'),
        '--weekly_glob', str(project_root / 'out' / season / 'Wk*' / 'results_*.csv'),
        '--out_dir', str(season_dir),
        '--title', 'Season Player Dashboards'
    ], check=True)
    print(f"  Season Dashboards HTML: {season_dir}/index.html")

    # Update site landing index for this season
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_site_index.py'),
        '--out_root', str(project_root / 'out'),
        '--season', season
    ], check=True)
    print(f"  Site Index: {project_root / 'out' / season / 'index.html'}")
    
    # Update root season selector
    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_season_selector.py'),
        '--out_root', str(project_root / 'out')
    ], check=True)
    print(f"  Season Selector: {project_root / 'out' / 'index.html'}")

    subprocess.run([
        python_bin, str(project_root / 'tools' / 'make_upload_html.py'),
        '--out_root', str(project_root / 'out'),
        '--csv_root', str(project_root / 'csv'),
    ], check=True)
    print(f"  Upload page: {project_root / 'out' / 'upload.html'}")


if __name__ == '__main__':
    main()


