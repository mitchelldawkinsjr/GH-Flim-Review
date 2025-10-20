#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import re


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    norm = lambda c: ''.join(ch for ch in c.lower() if ch.isalnum() or ch=='_').replace('__','_').strip('_')
    return df.rename(columns={c: norm(c) for c in df.columns})


def count_list(x) -> int:
    if isinstance(x, (int, float)) and not pd.isna(x):
        return int(x)
    if isinstance(x, str) and x.strip():
        items = [t for t in (s.strip() for s in x.split(',')) if t and any(ch.isalnum() for ch in t)]
        return len(items)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('in_csv')
    ap.add_argument('--out', required=True)
    ap.add_argument('--week', type=int, required=True)
    args = ap.parse_args()

    df_raw = pd.read_csv(args.in_csv)

    # Build output DataFrame from exact original headers
    get_num = lambda col: pd.to_numeric(df_raw.get(col, 0), errors='coerce').fillna(0).astype(int)
    get_txt = lambda col: df_raw.get(col, '').astype(str) if col in df_raw.columns else pd.Series('', index=df_raw.index)

    out = pd.DataFrame({
        'player': get_txt('Player'),
        'week': int(args.week),
        'snaps': get_num('Snap count'),
        'targets': get_num('Targets'),
        'catches': get_num('Catches'),
        'rec_yards': get_num('Rec Yards'),
        'rush_yards': get_num('Rush Yards'),
        'touchdowns': get_num('Touchdowns'),
        'drops': get_num('Drops'),
        'missed_assignments': get_txt('Missed Assignment').apply(count_list).astype(int),
        'loafs': get_txt('Loaf').apply(count_list).astype(int),
        'notes': get_txt('Notes'),
    })

    # Merge key play ++/-- into codes
    pos_vals = get_txt('Key play ++')
    neg_vals = get_txt('Key play --')
    out['codes'] = (pos_vals + ' ' + neg_vals).str.strip()

    # If codes present, derive MA and Loaf directly from codes to avoid sheet mismatches
    def derive_ma_loaf(codes_str: str) -> tuple[int, int] | None:
        if not isinstance(codes_str, str) or not codes_str.strip():
            return None
        ma_cnt = 0
        loaf_cnt = 0
        for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', codes_str):
            inside = m.group(2).upper()
            tokens = [t.strip() for t in inside.split(',') if t.strip()]
            for t in tokens:
                if t == 'MA':
                    ma_cnt += 1
                elif t == 'L':
                    loaf_cnt += 1
        return ma_cnt, loaf_cnt

    derived = out['codes'].apply(derive_ma_loaf)
    mask_has_codes = derived.notna()
    out.loc[mask_has_codes, 'missed_assignments'] = derived[mask_has_codes].apply(lambda x: x[0]).astype(int)
    out.loc[mask_has_codes, 'loafs'] = derived[mask_has_codes].apply(lambda x: x[1]).astype(int)

    # Finally, zero discipline stats when snaps == 0 to avoid false positives
    try:
        out.loc[out['snaps'] <= 0, ['missed_assignments', 'loafs']] = 0
    except Exception:
        pass

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)


if __name__ == '__main__':
    main()


