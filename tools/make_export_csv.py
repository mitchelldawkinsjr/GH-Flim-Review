#!/usr/bin/env python3
import argparse
from pathlib import Path
import csv
import math
import pandas as pd
import re


def letter(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


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
}


def expand_codes_in_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    codes_sorted = sorted(CODE_LABELS.keys(), key=lambda k: -len(k))
    for code in codes_sorted:
        label = CODE_LABELS[code]
        text = re.sub(rf'(?<![A-Za-z0-9+]){re.escape(code)}(?![A-Za-z0-9+])', label, text)
    # Expand yardage codes
    def _repl_c(m):
        n = m.group('n')
        sign = '+' if not n.startswith('-') else ''
        return f"Catch {sign}{n} yards"
    def _repl_r(m):
        n = m.group('n')
        sign = '+' if not n.startswith('-') else ''
        return f"Rush {sign}{n} yards"
    text = re.sub(r'(?<![A-Za-z0-9])C\+(?P<n>-?\d+)(?![A-Za-z0-9])', _repl_c, text, flags=re.IGNORECASE)
    text = re.sub(r'(?<![A-Za-z0-9])C-(?P<n>\d+)(?![A-Za-z0-9])', lambda m: f"Catch -{m.group('n')} yards", text, flags=re.IGNORECASE)
    text = re.sub(r'(?<![A-Za-z0-9])R\+(?P<n>-?\d+)(?![A-Za-z0-9])', _repl_r, text, flags=re.IGNORECASE)
    text = re.sub(r'(?<![A-Za-z0-9])R-(?P<n>\d+)(?![A-Za-z0-9])', lambda m: f"Rush -{m.group('n')} yards", text, flags=re.IGNORECASE)
    return text


def parse_notes_to_rows(notes_text: str):
    rows = []
    if not isinstance(notes_text, str) or not notes_text.strip():
        return rows
    for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', notes_text):
        play = m.group(1).strip()
        note = m.group(2).strip()
        if play and note:
            rows.append((play, note))
    if not rows:
        parts = [p.strip() for p in str(notes_text).split(',') if p.strip()]
        for p in parts:
            m = re.match(r'^(\d+)\s*[:\-]?\s*(.*)$', p)
            if m:
                rows.append((m.group(1), m.group(2)))
    return rows


def main():
    ap = argparse.ArgumentParser(description='Export results to an example-file style CSV')
    ap.add_argument('--details_csv', required=True, help='Path to detailed results CSV (from film_grade)')
    ap.add_argument('--prepared_csv', help='Path to prepared input CSV (optional, to pull Rushes attempts)')
    ap.add_argument('--out', required=True, help='Output CSV path')
    args = ap.parse_args()

    df = pd.read_csv(args.details_csv)

    rushes_by_player = {}
    if args.prepared_csv and Path(args.prepared_csv).exists():
        df_prep = pd.read_csv(args.prepared_csv)
        rushes_col = None
        for c in ['Rushes', 'rushes']:
            if c in df_prep.columns:
                rushes_col = c
                break
        if rushes_col is not None:
            tmp = df_prep.groupby(['player','week'])[rushes_col].sum().reset_index()
            for _, r in tmp.iterrows():
                rushes_by_player[(str(r['player']).strip(), str(r['week']).strip())] = int(r[rushes_col])

    groups = []
    for (player, week), g in df.groupby(['player','week']):
        player = str(player)
        week = str(week)
        snaps = int(g['snaps'].sum())
        targets = int(g['targets'].sum())
        catches = int(g['catches'].sum())
        rec_yards = int(g['rec_yards'].sum())
        rush_yards = int(g['rush_yards'].sum())
        touchdowns = int(g['touchdowns'].sum())
        drops = int(g['drops'].sum())
        ma = int(g['missed_assignments'].sum())
        loafs = int(g['loafs'].sum())
        key_points = round(float(g['code_points'].sum()), 1) if 'code_points' in g.columns else 0.0
        avg_score = float(g['score'].mean()) if 'score' in g.columns else 0.0
        letter_grade = letter(avg_score)
        rushes = rushes_by_player.get((player.strip(), week.strip()), 0)

        notes_text = ' '.join([str(x) for x in g.get('notes', []) if isinstance(x, str)])
        notes_text = expand_codes_in_text(notes_text)
        notes_rows = parse_notes_to_rows(notes_text)

        groups.append({
            'player': player,
            'snaps': snaps,
            'targets': targets,
            'catches': catches,
            'rec_yards': rec_yards,
            'rushes': rushes,
            'rush_yards': rush_yards,
            'touchdowns': touchdowns,
            'drops': drops,
            'missed_assignments': ma,
            'loafs': loafs,
            'key_points': key_points,
            'score': avg_score,
            'grade': letter_grade,
            'notes_rows': notes_rows,
        })

    groups.sort(key=lambda r: r['score'], reverse=True)

    total_loafs = sum(g['loafs'] for g in groups)
    unit_score = sum(g['score'] for g in groups) / len(groups) if groups else 0.0
    unit_grade = letter(unit_score)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'Player','Snap count','Drops','Targets','Catches','Rec Yards','Rushes','Rush Yards','Touchdowns',
            'Missed Assignment','Loaf','Key plays points','Grade (0-100)', ''
        ])
        for g in groups:
            w.writerow([
                g['player'], g['snaps'], '' if g['drops'] == 0 else g['drops'], g['targets'], g['catches'],
                g['rec_yards'], g['rushes'], g['rush_yards'], g['touchdowns'],
                '' if g['missed_assignments'] == 0 else g['missed_assignments'],
                '' if g['loafs'] == 0 else g['loafs'],
                g['key_points'], round(g['score']), g['grade']
            ])

        w.writerow([])
        w.writerow(['Total Loafs'])
        w.writerow([total_loafs])
        w.writerow(['Unit Grade'])
        w.writerow([round(unit_score), unit_grade])
        w.writerow([])

        for g in groups:
            w.writerow([f"{g['player']}: "])
            for play, note in g['notes_rows']:
                w.writerow([f"{play}: {note}"])
            w.writerow([])

    print(f"Wrote export CSV to {out_path}")


if __name__ == '__main__':
    main()


