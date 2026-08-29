#!/usr/bin/env python3
"""Prepare a raw weekly film CSV for grading.

Builds a normalized intermediate CSV with a single `codes` column merged from
the sheet's key-play columns, derives discipline tallies from the codes, and
drops the legend/total/group-notes footer rows that aren't player data.
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

# Allow importing rubric.py from the project root when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rubric import loaf_units, parse_codes_to_points


def count_list(x) -> int:
    if isinstance(x, (int, float)) and not pd.isna(x):
        return int(x)
    if isinstance(x, str) and x.strip():
        items = [t for t in (s.strip() for s in x.split(',')) if t and any(ch.isalnum() for ch in t)]
        return len(items)
    return 0


def strip_headers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_column(df: pd.DataFrame, *names: str) -> str | None:
    by_lower = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        key = name.strip().lower()
        if key in by_lower:
            return by_lower[key]
    return None


def is_player_row(player_val) -> bool:
    """True when a row represents a real player, not a legend/total/footer row."""
    if player_val is None:
        return False
    s = str(player_val).strip()
    if not s or s.lower() in ('nan', 'none'):
        return False
    # Footer markers that appear in the Player column of legend/total rows.
    if s.lower() in ('total snaps', 'code', 'totals'):
        return False
    # Legend rows start the code table: ",(TD),Touchdown,15,..." -> player cell
    # is empty or a bare code like "(TD)". Skip rows whose player cell is a
    # parenthesized code or a known legend keyword.
    if re.fullmatch(r'\(?[A-Za-z]{2,}\)?', s) and s.lower() in {
        'td', 'e', 'er', 'gr', 'gb', 'p', 'fd', 'ma', 'sc', 'dp', 'h', 'br',
        'l', 'nfs', 'w', 'bt', 'lf', 'bbl', 'ep',
    }:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('in_csv')
    ap.add_argument('--out', required=True)
    ap.add_argument('--week', type=int, required=True)
    args = ap.parse_args()

    df_raw = strip_headers(pd.read_csv(args.in_csv, encoding='utf-8-sig'))
    player_col = find_column(df_raw, 'Player', 'Name')
    if not player_col:
        raise SystemExit(
            f"Missing Player/Name column. Found: {list(df_raw.columns)}"
        )

    # Keep only real player rows; drop legend/total/group-notes footer.
    df_raw = df_raw[df_raw[player_col].apply(is_player_row)].reset_index(drop=True)

    get_num = lambda col: pd.to_numeric(df_raw.get(col, 0), errors='coerce').fillna(0).astype(int)

    def get_txt(col):
        if col not in df_raw.columns:
            return pd.Series('', index=df_raw.index)
        return df_raw[col].astype(object).where(df_raw[col].notna(), '').astype(str)

    out = pd.DataFrame({
        'player': get_txt(player_col) if player_col else pd.Series('', index=df_raw.index),
        'week': int(args.week),
        'snaps': get_num('Snap count'),
        'targets': get_num('Targets'),
        'catches': get_num('Catches'),
        'rec_yards': get_num('Rec Yards'),
        'rush_yards': get_num('Rush Yards'),
        'touchdowns': get_num('Touchdowns'),
        'drops': get_num('Drops'),
        'missed_assignments': get_txt('Missed Assignment').apply(count_list).astype(int),
        'loafs': get_txt('Loaf').apply(count_list).astype(float),
        'notes': get_txt('Notes'),
    })

    # Merge key play ++/-- into codes; support the legacy singular "key play" column.
    pos_col = find_column(df_raw, 'Key play ++')
    neg_col = find_column(df_raw, 'Key play --')
    single_col = find_column(df_raw, 'Key play')
    if pos_col or neg_col:
        out['codes'] = (get_txt(pos_col) + ' ' + get_txt(neg_col)).str.strip()
    elif single_col:
        out['codes'] = get_txt(single_col).str.strip()
    else:
        out['codes'] = ''

    # When codes are present, derive MA and Loaf from the codes so the sheet's
    # mixed-bag "Missed Assignment"/"Loaf" columns don't miscount. LF counts as
    # half a loaf for discipline (matching the grader).
    def derive_ma_loaf(codes_str):
        if not isinstance(codes_str, str) or not codes_str.strip():
            return None
        _, counts, _, _, _ = parse_codes_to_points(codes_str)
        return int(counts.get('MA', 0)), loaf_units(counts)

    derived = out['codes'].apply(derive_ma_loaf)
    mask_has_codes = derived.notna()
    out.loc[mask_has_codes, 'missed_assignments'] = derived[mask_has_codes].apply(lambda x: x[0]).astype(int)
    out.loc[mask_has_codes, 'loafs'] = derived[mask_has_codes].apply(lambda x: x[1]).astype(float)

    # Zero discipline stats when snaps == 0 to avoid false positives.
    try:
        out.loc[out['snaps'] <= 0, ['missed_assignments', 'loafs']] = 0
    except Exception:
        pass

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)


if __name__ == '__main__':
    main()
