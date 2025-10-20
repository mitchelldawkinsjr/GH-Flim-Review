
#!/usr/bin/env python3
"""
film_grade.py — Grade weekly film for receivers from a CSV and emit player-facing reports.

Usage:
  python film_grade.py input.csv --out_dir OUTPUT_DIR [--out results.csv]

Input CSV required columns (case-insensitive; spaces/underscores ignored):
  player, week, snaps, targets, catches, rec_yards, rush_yards, touchdowns,
  drops, missed_assignments, loafs

Optional columns:
  key_plays (numeric)  # if absent, derived from codes
  codes                 # freeform codes string
  "key play ++", "key play --"  # if present, combined into codes

Notes:
  - If your sheet uses separate "key play ++" (positives) and "key play --" (negatives),
    the script will merge them into a single `codes` string automatically.
  - Score is clamped to 0..100 and mapped to letter A–F.
  - Player-facing review reports are written to <out_dir>/reports/<player>_<week>.txt
"""

import argparse
import sys
import pandas as pd
import re
from pathlib import Path
import math

# Required base stats; key_plays is optional since we'll derive it from codes when missing
REQUIRED_COLS_BASE = [
    "player","week","snaps","targets","catches","rec_yards","rush_yards",
    "touchdowns","drops","missed_assignments","loafs"
]

# Legend point values
LEGEND_POINTS = {
    "TD": 15,
    "E": 5,
    "ER": 7,
    "GR": 2,
    "GB": 2,
    "P": 10,
    "FD": 5,
    "MA": -10,
    "SC": 10,
    "DP": -15,
    "H": 0,
    "BR": -2,
    "L": -2,
    "NFS": -3,
    "W": -1,
}

POSITIVE_CODES_FOR_KEYPLAYS = {"TD","SC","ER","GR","GB","P","FD","E"}

# Patterns for variable-valued codes
PATTERN_CATCH_YARDS = re.compile(r'^(?:\(?\s*)?C\+(?P<n>-?\d+)(?:\s*\)?)?$', flags=re.IGNORECASE)
PATTERN_RUSH_YARDS = re.compile(r'^(?:\(?\s*)?R\+(?P<n>-?\d+)(?:\s*\)?)?$', flags=re.IGNORECASE)

def normalize_cols(df):
    def norm(c):
        return ''.join(ch for ch in c.lower() if ch.isalnum() or ch=='_')\
               .replace('__','_').strip('_')
    rename = {c: norm(c) for c in df.columns}
    df = df.rename(columns=rename)
    return df

def ensure_columns(df):
    missing = [c for c in REQUIRED_COLS_BASE if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}\n"
                         f"Found columns: {list(df.columns)}")
    return df

def safe_div(n, d):
    try:
        n = float(n)
        d = float(d)
        if d == 0:
            return 0.0
        return n / d
    except Exception:
        return 0.0

def per30(n, snaps):
    try:
        snaps = float(snaps)
        n = float(n)
        if snaps <= 0:
            return 0.0
        return n * 30.0 / snaps
    except Exception:
        return 0.0

def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def letter(score):
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"

def parse_codes_to_points(codes_str):
    """
    Parse a codes string and compute:
      - total code points
      - per-code counts (dict)
      - yards from C+N and R+N
      - derived_keyplays (count of positive-impact codes)
    Accepts formats like "(ER) (C+12) (FD)" or "ER; C+12; FD" or "ER C+12 FD"
    and can handle mixed parentheses/commas/semicolons.
    """
    total = 0
    counts = {k: 0 for k in LEGEND_POINTS.keys()}
    yards_c = 0
    yards_r = 0
    derived_keyplays = 0

    if not isinstance(codes_str, str) or not codes_str.strip():
        return total, counts, yards_c, yards_r, derived_keyplays

    tokens = re.split(r'[\s,;]+', codes_str.replace('(', ' ').replace(')', ' '))
    tokens = [t.strip() for t in tokens if t.strip()]
    for t in tokens:
        m_c = PATTERN_CATCH_YARDS.match(t)
        if m_c:
            n = int(m_c.group('n'))
            total += 0.5 * n
            yards_c += n
            continue
        m_r = PATTERN_RUSH_YARDS.match(t)
        if m_r:
            n = int(m_r.group('n'))
            total += 0.5 * n
            yards_r += n
            continue

        t_up = t.upper()
        if t_up in LEGEND_POINTS:
            total += LEGEND_POINTS[t_up]
            counts[t_up] += 1
            if t_up in POSITIVE_CODES_FOR_KEYPLAYS:
                derived_keyplays += 1

    return total, counts, yards_c, yards_r, derived_keyplays

def compute_row(r):
    snaps = r.get('snaps', 0)
    targets = r.get('targets', 0)
    catches = r.get('catches', 0)
    rec_yards = r.get('recyards', r.get('rec_yards', 0))
    rush_yards = r.get('rushyards', r.get('rush_yards', 0))
    touchdowns = r.get('touchdowns', 0)
    drops = r.get('drops', 0)
    ma = r.get('missedassignments', r.get('missed_assignments', 0))
    loafs = r.get('loafs', 0)
    keyplays_in = r.get('key_plays', r.get('keyplays', 0))
    codes_str = r.get('codes', '')

    # Guard against bogus discipline stats when no snaps were recorded
    try:
        snaps_val = int(snaps)
    except Exception:
        snaps_val = 0
    if snaps_val <= 0:
        ma = 0
        loafs = 0

    # Parse codes for points and a derived key play count
    code_points, code_counts, code_catch_yards, code_rush_yards, derived_kp = parse_codes_to_points(codes_str)
    # If codes are provided, set discipline tallies exactly from code counts to avoid mismatches
    if isinstance(codes_str, str) and codes_str.strip():
        try:
            ma = int(code_counts.get('MA', 0))
            loafs = int(code_counts.get('L', 0))
        except Exception:
            pass

    # Use provided key_plays if present and >0, else fallback to derived
    keyplays = keyplays_in if (isinstance(keyplays_in, (int,float)) and keyplays_in > 0) else derived_kp

    # Core rates
    catch_rate = safe_div(catches, targets)
    yards_per_target = safe_div((rec_yards + rush_yards), targets)
    tds_per30 = per30(touchdowns, snaps)
    keyplays_per30 = per30(keyplays, snaps)
    targets_per30 = per30(targets, snaps)
    drops_rate = safe_div(drops, targets)
    loafs_per30 = per30(loafs, snaps)
    ma_per30 = per30(ma, snaps)

    base = 73.0
    # Excel-equivalent terms
    yards_term = 1.5 * min(safe_div(yards_per_target, 8.0), 1.0)
    tds_term = 12.0 * min(tds_per30, 1.0)
    # sqrt of key plays per 30, capped at 1.33, scaled by 6
    kp_sqrt_capped = min(math.sqrt(keyplays_per30) if keyplays_per30 > 0 else 0.0, 1.33)
    keyplays_term = 6.0 * kp_sqrt_capped
    targets_term = 4.0 * min(targets_per30, 1.0)
    synergy_term = 1.0 * min(catch_rate * safe_div(yards_per_target, 8.0), 1.0)

    pos = (
        15.0 * catch_rate +
        yards_term +
        tds_term +
        keyplays_term +
        targets_term +
        synergy_term
    )
    neg = (
        12.0 * drops_rate +
        4.0  * loafs_per30 +
        9.0  * min(ma_per30, 1.0)
    )

    score = clamp(base + pos - neg, 0.0, 100.0)
    grade = letter(score)

    flat_counts = {f'cnt_{k.lower()}': v for k, v in code_counts.items()}

    return {
        'catch_rate': catch_rate,
        'yards_per_target': yards_per_target,
        'tds_per30': tds_per30,
        'keyplays_per30': keyplays_per30,
        'targets_per30': targets_per30,
        'drops_rate': drops_rate,
        'loafs_per30': loafs_per30,
        'ma_per30': ma_per30,
        'score': score,
        'grade': grade,
        'code_points': code_points,
        'code_catch_yards': code_catch_yards,
        'code_rush_yards': code_rush_yards,
        'derived_keyplays': derived_kp,
        **flat_counts
    }

def make_reports(out_df, reports_dir='reports', by_player='player', by_week='week'):
    p = Path(reports_dir)
    p.mkdir(parents=True, exist_ok=True)

    for (player, week), g in out_df.groupby([by_player, by_week]):
        snaps = int(g['snaps'].sum())
        targets = int(g['targets'].sum())
        catches = int(g['catches'].sum())
        rec_yards = int(g['rec_yards'].sum())
        rush_yards = int(g['rush_yards'].sum())
        touchdowns = int(g['touchdowns'].sum())
        drops = int(g['drops'].sum())
        ma = int(g['missed_assignments'].sum())
        loafs = int(g['loafs'].sum())
        # Prefer input key_plays if present, else derived
        keyplays = int(g['key_plays'].sum()) if 'key_plays' in g.columns else int(g['derived_keyplays'].sum())

        avg_score = float(g['score'].mean())
        letter_grade = letter(avg_score)

        code_cols = [c for c in g.columns if c.startswith('cnt_')]
        total_code_points = round(float(g['code_points'].sum()), 1)
        code_counts_sum = g[code_cols].sum().to_dict()

        lines = []
        lines.append(f"PLAYER REVIEW — {player} — Week {week}")
        lines.append("=" * 60)
        lines.append(f"Summary: Grade {letter_grade} ({avg_score:.1f})  |  Snaps {snaps}  |  Tgts {targets}  |  Rec {catches} for {rec_yards} yds  |  Rush {rush_yards} yds  |  TD {touchdowns}")
        lines.append(f"Discipline: Drops {drops}  |  MAs {ma}  |  Loafs {loafs} ")
        lines.append(f"Key Plays Points (sum): {total_code_points}")
        lines.append("")

        inv = {}
        for k,v in code_counts_sum.items():
            code = k.replace('cnt_', '').upper()
            inv[code] = int(v)

        def pick_top(d, keys, topn=5):
            items = [(k, d.get(k,0)) for k in keys]
            items.sort(key=lambda x: x[1], reverse=True)
            return [(k,v) for k,v in items if v>0][:topn]

        positive_keys = ["TD","SC","ER","GR","GB","P","FD","E"]
        negative_keys = ["MA","DP","L","NFS","W","BR","H"]

        pos_top = pick_top(inv, positive_keys, topn=7)
        neg_top = pick_top(inv, negative_keys, topn=7)

        if pos_top:
            lines.append("WHAT YOU DID WELL")
            for code, cnt in pos_top:
                pts = LEGEND_POINTS.get(code, 0) * cnt
                lines.append(f"  • {code}: x{cnt}  ({'+' if pts>=0 else ''}{pts})")
            lines.append("")
        if neg_top:
            lines.append("WHERE TO IMPROVE")
            for code, cnt in neg_top:
                pts = LEGEND_POINTS.get(code, 0) * cnt
                lines.append(f"  • {code}: x{cnt}  ({'+' if pts>=0 else ''}{pts})")
            lines.append("")

        coaching = []
        if inv.get("DP",0) > 0:
            coaching.append("Jugs work: 50 high-speed catches, 20 contested — focus eyes to tuck.")
        if inv.get("MA",0) > 0:
            coaching.append("Walk-through: alignment, split, and route depth for your assignments.")
        if inv.get("L",0) + inv.get("NFS",0) > 0:
            coaching.append("Finish every rep on film — sprint off screen, block through whistle.")
        if inv.get("W",0) > 0:
            coaching.append("Strike timing on stalk block — inside hand fit, under control into contact.")
        if not coaching:
            coaching.append("Keep stacking habits — practice full speed reps.")

        lines.append("COACHING POINTS")
        for c in coaching:
            lines.append(f"  • {c}")
        lines.append("")

        fname = p / f"{str(player).strip().replace(' ', '_')}_{str(week).strip()}.txt"
        with open(fname, 'w') as f:
            f.write("\n".join(lines))

def main():
    ap = argparse.ArgumentParser(description="Compute weekly film grades from CSV and emit player reports.")
    ap.add_argument('csv', help='Input CSV path')
    ap.add_argument('--out', default='results.csv', help='Output CSV filename or path (default: results.csv)')
    ap.add_argument('--out_dir', default='out', help='Directory where all outputs are written (default: out)')
    ap.add_argument('--by', default='player', help='Column to aggregate by for summary (default: player)')
    args = ap.parse_args()

    # Read raw to inspect original column names for key play ++/--
    df_raw = pd.read_csv(args.csv)

    # Merge "key play ++" and "key play --" into a single 'codes' column if present
    pos_col = next((c for c in df_raw.columns if c.strip().lower() == 'key play ++'), None)
    neg_col = next((c for c in df_raw.columns if c.strip().lower() == 'key play --'), None)
    if pos_col or neg_col:
        pos_vals = df_raw[pos_col].fillna('') if pos_col else ''
        neg_vals = df_raw[neg_col].fillna('') if neg_col else ''
        combined = (pos_vals.astype(str) + ' ' + neg_vals.astype(str)).str.strip()
        # If a pre-existing "codes" col exists, append to it
        if 'codes' in df_raw.columns:
            df_raw['codes'] = (df_raw['codes'].fillna('') + ' ' + combined).str.strip()
        else:
            df_raw['codes'] = combined

    # Normalize after we've built the codes column
    df = normalize_cols(df_raw)

    # Ensure required base columns exist
    df = ensure_columns(df)

    # Compute row-wise metrics
    calc_rows = df.apply(compute_row, axis=1, result_type='expand')
    out = pd.concat([df, calc_rows], axis=1)

    # Order columns
    preferred_order = [
        'player','week','snaps','targets','catches','rec_yards','rush_yards',
        'touchdowns','drops','missed_assignments','loafs','key_plays','codes',
        'code_points','derived_keyplays',
        'catch_rate','yards_per_target','targets_per30','keyplays_per30',
        'tds_per30','drops_rate','ma_per30','loafs_per30','score','grade'
    ]
    ordered = [c for c in preferred_order if c in out.columns] + \
              [c for c in out.columns if c not in preferred_order]
    out = out[ordered]

    # Resolve output locations
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = out_dir / out_path.name

    # Write detailed results
    out.to_csv(out_path, index=False)

    # Summary
    by = args.by if args.by in out.columns else 'player'
    summary = out.groupby([by]).agg({
        'score':'mean',
        'catch_rate':'mean',
        'yards_per_target':'mean',
        'targets_per30':'mean',
        'keyplays_per30':'mean',
        'tds_per30':'mean',
        'drops_rate':'mean',
        'ma_per30':'mean',
        'loafs_per30':'mean',
        'code_points':'sum'
    }).round(3).reset_index().sort_values('score', ascending=False)
    summary_out = out_path.with_name(out_path.stem + '_summary.csv')
    summary.to_csv(summary_out, index=False)

    # Emit player-facing reports into out_dir/reports
    make_reports(out, reports_dir=str(out_dir / 'reports'))

    print(f"Wrote detailed results to {out_path}")
    print(f"Wrote summary by {by} to {summary_out}")
    print(f"Wrote player reports to {out_dir / 'reports'}")

if __name__ == '__main__':
    main()
