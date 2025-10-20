#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors


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


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = list(df.columns)
    normalized = { ''.join(ch.lower() for ch in c if ch.isalnum()): c for c in cols }
    for cand in candidates:
        key = ''.join(ch.lower() for ch in cand if ch.isalnum())
        if key in normalized:
            return normalized[key]
    # try startswith/contains loose matching
    for c in cols:
        lc = c.lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None


def cell_text(val) -> str:
    """Return a clean string for a CSV cell: '' for NaN/None/blank, else stripped text."""
    try:
        if pd.isna(val):
            return ''
    except Exception:
        pass
    if isinstance(val, str):
        s = val.strip()
        return '' if s.lower() == 'nan' or s == '' else s
    return str(val).strip()


def extract_play_numbers(show_val: str) -> list[str]:
    if not isinstance(show_val, str):
        return []
    # Accept formats like "12", "12, 13", "12 13", "12;13", "12-13" (split by non-digits)
    nums = re.findall(r'\d+', show_val)
    return [n for n in nums]


def parse_numbered_segments(text: str) -> list[tuple[str, str]]:
    """
    Parse patterns like "28(MA)" or "102(ER, C+12)" possibly with commas/spaces between entries
    and return a list of (play_number, inside_text) pairs. Inside text is trimmed and can contain
    multiple comma-separated tokens; we keep as a single string, codes expanded later.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    out: list[tuple[str, str]] = []
    # find all occurrences of <num>(...)
    for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', text):
        pn = m.group(1).strip()
        inside = m.group(2).strip()
        if pn and inside:
            out.append((pn, inside))
    return out


def split_numbered_and_remainder(text: str) -> tuple[list[tuple[str, str]], str]:
    """
    Return (segments, remainder) where segments is [(play, inside), ...] and remainder is
    whatever text remains after removing all <num>(...) patterns. Remainder is cleaned
    of extra punctuation and whitespace.
    """
    if not isinstance(text, str) or not text.strip():
        return [], ''
    segs = parse_numbered_segments(text)
    # Remove all numbered segments to get remainder
    remainder = re.sub(r'\d+\s*\([^)]*\)', ' ', text)
    remainder = re.sub(r'[;|]+', ' ', remainder)
    remainder = re.sub(r'\s+', ' ', remainder).strip(' ,;|')
    return segs, remainder


def main():
    ap = argparse.ArgumentParser(description='Create a group film study PDF from the raw CSV.')
    ap.add_argument('--csv', required=True, help='Path to raw CSV source data')
    ap.add_argument('--out', required=True, help='Output PDF path')
    ap.add_argument('--week', type=int, help='Week number (for title)')
    ap.add_argument('--opponent', help='Opponent (for title)')
    args = ap.parse_args()

    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)

    show_col = find_column(df, ['Show in flim', 'Show in film', 'Show in Flim'])
    plus_col = find_column(df, ['Key play ++', 'Key Play ++'])
    minus_col = find_column(df, ['Key play --', 'Key Play --'])
    notes_col = find_column(df, ['Notes', 'Note'])
    player_col = find_column(df, ['Player', 'player'])

    # if not show_col:
    #     raise SystemExit("Could not find 'Show in film/flim' column in CSV.")

    # Build index: play_number -> list of entries {player, plus, minus, notes}
    by_play: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        show_val = cell_text(row.get(show_col, ''))
        plays_to_show = extract_play_numbers(show_val)
        if not plays_to_show:
            continue

        # Parse numbered segments inside the detail columns
        plus_raw = cell_text(row.get(plus_col, '')) if plus_col else ''
        minus_raw = cell_text(row.get(minus_col, '')) if minus_col else ''
        notes_raw = cell_text(row.get(notes_col, '')) if notes_col else ''

        plus_segments, plus_rem = split_numbered_and_remainder(plus_raw)
        minus_segments, minus_rem = split_numbered_and_remainder(minus_raw)
        notes_segments, notes_rem = split_numbered_and_remainder(notes_raw)

        player_name = cell_text(row.get(player_col, '')) if player_col else ''

        # For each play listed to show, collect only matching numbered segments
        for pn in plays_to_show:
            plus_texts = [expand_codes_in_text(seg) for pseg, seg in plus_segments if pseg == pn]
            minus_texts = [expand_codes_in_text(seg) for pseg, seg in minus_segments if pseg == pn]
            notes_texts = [seg for pseg, seg in notes_segments if pseg == pn]

            # Also include unnumbered remainder text for each column (applies to all listed plays)
            if plus_rem:
                plus_texts.append(expand_codes_in_text(plus_rem))
            if minus_rem:
                minus_texts.append(expand_codes_in_text(minus_rem))
            if notes_rem:
                notes_texts.append(notes_rem)

            plus_combined = '; '.join(t for t in plus_texts if t)
            minus_combined = '; '.join(t for t in minus_texts if t)
            notes_combined = '; '.join(t for t in notes_texts if t)

            # If all three are empty, skip
            if not (plus_combined or minus_combined or notes_combined):
                continue

            entry = {
                'player': player_name,
                'plus': plus_combined,
                'minus': minus_combined,
                'notes': notes_combined,
            }
            by_play.setdefault(pn, []).append(entry)

    # Sort plays numeric
    def _key_num(s: str) -> int:
        try:
            return int(s)
        except Exception:
            return 0
    plays_sorted = sorted(by_play.keys(), key=_key_num)

    out_pdf = Path(args.out)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    story = []

    # Title
    title_bits = ["Group Film Study"]
    if args.week:
        title_bits.append(f"Week {args.week}")
    if args.opponent:
        title_bits.append(str(args.opponent))
    story.append(Paragraph(' — '.join(title_bits), styles['Title']))
    story.append(Spacer(1, 0.2*inch))

    # Aggregate per-play details by player (combine multiple rows for same player/play)
    rows = [["Play", "Player", "Detail"]]
    for pn in plays_sorted:
        entries = by_play[pn]
        by_player: dict[str, dict[str, list[str]]] = {}
        for e in entries:
            player = e['player'] or '-'
            acc = by_player.setdefault(player, {'plus': [], 'minus': [], 'notes': []})
            if e['plus']:
                acc['plus'].append(e['plus'])
            if e['minus']:
                acc['minus'].append(e['minus'])
            if e['notes']:
                acc['notes'].append(e['notes'])

        # Stable order by player name
        for player in sorted(by_player.keys(), key=lambda s: s.lower()):
            acc = by_player[player]
            # Deduplicate while preserving order
            def uniq(seq: list[str]) -> list[str]:
                seen = set()
                out = []
                for item in seq:
                    if item and item not in seen:
                        seen.add(item)
                        out.append(item)
                return out
            plus_combined = '; '.join(uniq(acc['plus']))
            minus_combined = '; '.join(uniq(acc['minus']))
            notes_combined = '; '.join(uniq(acc['notes']))

            parts = []
            if plus_combined:
                parts.append(f"<b>Key play ++</b>: {plus_combined}")
            if minus_combined:
                parts.append(f"<b>Key play --</b>: {minus_combined}")
            if notes_combined:
                parts.append(f"<b>Notes</b>: {notes_combined}")
            detail_html = ' | '.join(parts) if parts else '-'
            rows.append([str(pn), player, Paragraph(detail_html, styles['BodyText'])])

    tbl = Table(rows, hAlign='LEFT', colWidths=[0.8*inch, 1.8*inch, 4.9*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),  # Play column centered
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(tbl)

    if not plays_sorted:
        story.append(Paragraph("No plays found in 'Show in film' column.", styles['BodyText']))

    doc = SimpleDocTemplate(str(out_pdf), pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    doc.build(story)


if __name__ == '__main__':
    main()


