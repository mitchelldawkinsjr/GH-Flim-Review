#!/usr/bin/env python3
"""Parse csv/{season}/Wk{N}_{Opponent}.csv into season, week, opponent."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILENAME_RE = re.compile(r'^Wk(\d+)\s*_?\s*(.+)\.csv$', re.IGNORECASE)
SEASON_RE = re.compile(r'^\d{4}-\d{4}$')


def parse_week_csv_path(path: str | Path) -> dict[str, str | int]:
    p = Path(path)
    match = FILENAME_RE.match(p.name)
    if not match:
        raise ValueError(
            f"CSV filename must look like Wk8_Kville.csv (got {p.name!r})"
        )
    week = int(match.group(1))
    raw_opp = match.group(2).strip().strip('_').strip()
    opponent = re.sub(r'[\s_]+', '', raw_opp)
    if not opponent:
        raise ValueError(f"Could not parse opponent from filename {p.name!r}")

    season = None
    parts = list(p.parts)
    if 'csv' in parts:
        idx = parts.index('csv')
        if idx + 1 < len(parts) - 1:
            candidate = parts[idx + 1]
            if SEASON_RE.match(candidate):
                season = candidate
    if season is None and len(p.parts) >= 2:
        candidate = p.parts[-2]
        if SEASON_RE.match(candidate):
            season = candidate
    if season is None:
        raise ValueError(
            f"Could not determine season from path {path!r}. "
            "Expected csv/YYYY-YYYY/WkN_Opponent.csv"
        )

    return {
        'season': season,
        'week': week,
        'opponent': opponent,
        'path': str(p),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('csv_path', help='Path like csv/2026-2027/Wk1_Holland.csv')
    ap.add_argument(
        '--github-output',
        action='store_true',
        help='Print GITHUB_OUTPUT assignments (season/week/opponent/csv_path)',
    )
    args = ap.parse_args()
    try:
        parsed = parse_week_csv_path(args.csv_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.github_output:
        print(f"season={parsed['season']}")
        print(f"week={parsed['week']}")
        print(f"opponent={parsed['opponent']}")
        print(f"csv_path={parsed['path']}")
        return

    print(f"{parsed['season']} Wk{parsed['week']} {parsed['opponent']}")


if __name__ == '__main__':
    main()
