#!/usr/bin/env python3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from pathlib import Path
import argparse
import csv
import re
import pandas as pd


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

# Per-code point values (aligns with film_grade.py)
LEGEND_POINTS = {
    'TD': 15,
    'E': 5,
    'ER': 7,
    'GR': 2,
    'GB': 2,
    'P': 10,
    'FD': 5,
    'MA': -10,
    'SC': 10,
    'DP': -15,
    'H': 0,
    'BR': -2,
    'L': -2,
    'NFS': -3,
    'W': -1,
}


def parse_notes_to_rows(notes_text: str):
    rows = []
    if not isinstance(notes_text, str) or not notes_text.strip():
        return rows
    # Match patterns like 54(text...) possibly with spaces
    for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', notes_text):
        play = m.group(1).strip()
        note = m.group(2).strip()
        if play and note:
            rows.append([play, note])
    # Fallback: split by commas and try to parse 'NN:text'
    if not rows:
        parts = [p.strip() for p in notes_text.split(',') if p.strip()]
        for p in parts:
            m = re.match(r'^(\d+)\s*[:\-]?\s*(.*)$', p)
            if m:
                rows.append([m.group(1), m.group(2)])
    return rows


def expand_codes_in_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    # Replace standalone codes with labels, avoid touching inside words
    # Longer codes first to prevent partial overlaps
    codes_sorted = sorted(CODE_LABELS.keys(), key=lambda k: -len(k))
    for code in codes_sorted:
        label = CODE_LABELS[code]
        # word boundary or punctuation around code
        text = re.sub(rf'(?<![A-Za-z0-9+]){re.escape(code)}(?![A-Za-z0-9+])', label, text)
    # Expand C+N and R+N yardage codes (handle negatives too, e.g., C-2)
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


def text_report_to_pdf(txt_path: Path, pdf_path: Path, player_notes_index=None, ma_plays_index=None, loaf_plays_index=None, key_entries_index=None):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch
    )
    styles = getSampleStyleSheet()
    story = []

    with open(txt_path, 'r') as f:
        raw_lines = [ln.rstrip('\n') for ln in f]

    # Parse known sections
    title_line = next((ln for ln in raw_lines if ln.startswith('PLAYER REVIEW')), None)
    summary_line = next((ln for ln in raw_lines if ln.startswith('Summary:')), '')
    discipline_line = next((ln for ln in raw_lines if ln.startswith('Discipline:')), '')
    code_points_line = next((ln for ln in raw_lines if ln.startswith('Key Plays Points (sum):') or ln.startswith('Code Points (sum):')), '')

    # Extract positives/negatives/coaching blocks
    def collect_block(header):
        items = []
        try:
            start = raw_lines.index(header)
        except ValueError:
            return items
        for ln in raw_lines[start+1:]:
            if not ln.strip():
                break
            if ln.strip().isupper():
                break
            if ln.strip().startswith('•') or ln.strip().startswith('-') or ln.strip().startswith('*'):
                items.append(ln.strip().lstrip('•-* ').strip())
            else:
                items.append(ln.strip())
        return items

    pos_items = collect_block('WHAT YOU DID WELL')
    neg_items = collect_block('WHERE TO IMPROVE')
    coach_items = collect_block('COACHING POINTS')

    # Identify player and week from title or filename for notes lookup
    player_name = None
    week_val = None
    mtitle = None
    # Try from title line
    if title_line:
        mtitle = re.search(r'PLAYER REVIEW \u2014\s*(.*?)\s*\u2014\s*Week\s*(\S+)', title_line)
        if not mtitle:
            mtitle = re.search(r'PLAYER REVIEW \—\s*(.*?)\s*\—\s*Week\s*(\S+)', title_line)
        if not mtitle:
            mtitle = re.search(r'PLAYER REVIEW\s*—\s*(.*?)\s*—\s*Week\s*(\S+)', title_line)
    if mtitle:
        player_name = mtitle.group(1).strip()
        week_val = str(mtitle.group(2)).strip()
    else:
        # Fallback from filename: <player>_<week>.txt with spaces replaced by underscores
        stem = txt_path.stem
        if '_' in stem:
            week_val = stem.split('_')[-1]
            player_name = stem[:-(len(week_val)+1)].replace('_', ' ').strip()

    # Title
    if title_line:
        story.append(Paragraph(title_line, styles['Title']))
        story.append(Spacer(1, 0.15*inch))

    # Summary parsing
    summary_vals = {}
    # Summary: Grade B (83.2)  |  Snaps 60  |  Tgts 8  |  Rec 5 for 58 yds  |  Rush 23 yds  |  TD 0
    m = re.search(r'Grade\s+(?P<grade>[A-F])\s*\((?P<score>[0-9]+\.?[0-9]*)\)', summary_line)
    # We intentionally omit Grade and numeric score from PDFs
    m = re.search(r'Snaps\s+(?P<n>\d+)', summary_line)
    if m: summary_vals['Snaps'] = m.group('n')
    m = re.search(r'Tgts\s+(?P<n>\d+)', summary_line)
    if m: summary_vals['Targets'] = m.group('n')
    m = re.search(r'Rec\s+(?P<c>\d+)\s+for\s+(?P<y>\d+)\s+yds', summary_line)
    if m:
        summary_vals['Catches'] = m.group('c')
        summary_vals['Rec Yards'] = m.group('y')
    m = re.search(r'Rush\s+(?P<y>\d+)\s+yds', summary_line)
    if m: summary_vals['Rush Yards'] = m.group('y')
    m = re.search(r'TD\s+(?P<n>\d+)', summary_line)
    if m: summary_vals['Touchdowns'] = m.group('n')

    # Discipline parsing
    disc_vals = {}
    # Discipline: Drops 1  |  MAs 0  |  Loafs 0  |  Key Plays 3
    m = re.search(r'Drops\s+(?P<n>\d+)', discipline_line)
    if m: disc_vals['Drops'] = m.group('n')
    m = re.search(r'MAs\s+(?P<n>\d+)', discipline_line)
    if m: disc_vals['Missed Assignments'] = m.group('n')
    m = re.search(r'Loafs\s+(?P<n>\d+)', discipline_line)
    if m: disc_vals['Loafs'] = m.group('n')
    m = re.search(r'Key Plays\s+(?P<n>\d+)', discipline_line)
    if m: disc_vals['Key Plays'] = m.group('n')

    # Code points
    m = re.search(r'(?:Key Plays Points|Code Points) \(sum\):\s*(?P<n>-?\d+(?:\.\d+)?)', code_points_line)
    if m: summary_vals['Key Plays Points'] = m.group('n')

    # Build summary table
    if summary_vals:
        story.append(Paragraph('SUMMARY', styles['Heading3']))
        rows = []
        order = ['Snaps','Targets','Catches','Rec Yards','Rush Yards','Touchdowns','Key Plays Points']
        for k in order:
            if k in summary_vals:
                rows.append([k, str(summary_vals[k])])
        tbl = Table(rows, hAlign='LEFT', colWidths=[1.8*inch, 4.2*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.15*inch))

    # DISCIPLINE section removed as redundant

    # KEY PLAYS detailed list (from 'codes' per play)
    if key_entries_index is not None and player_name and week_val:
        key = (player_name.strip().lower(), str(week_val).strip())
        kp_entries = key_entries_index.get(key, [])
        if kp_entries:
            story.append(Paragraph('KEY PLAYS', styles['Heading3']))
            rows = [['Play', 'Action', 'Points']]
            for play_no, action_label, pts in kp_entries:
                # Stringify with explicit sign for clarity (support decimals)
                pts_str = f"{pts:+.1f}" if isinstance(pts, float) else (f"{pts:+d}" if isinstance(pts, int) else str(pts))
                rows.append([str(play_no), action_label, pts_str])
            tbl = Table(rows, hAlign='LEFT', colWidths=[0.9*inch, 4.4*inch, 0.7*inch])
            tbl.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.15*inch))

    # Positives table
    def parse_code_items(items):
        rows = []
        for it in items:
            # Example: "TD: x3 (+30)" or with decimals "C+8: x1 (+4.0)"
            m = re.search(r'^(?P<code>[A-Z]+):\s*x(?P<cnt>\d+)\s*\((?P<pts>[+\-]?[0-9]+(?:\.[0-9]+)?)\)', it)
            if m:
                rows.append([m.group('code'), m.group('cnt'), m.group('pts')])
        return rows

    pos_rows = parse_code_items(pos_items)
    if pos_rows:
        story.append(Paragraph('WHAT YOU DID WELL', styles['Heading3']))
        # Map code abbreviations to labels
        pos_rows_labeled = [[CODE_LABELS.get(code, code), cnt, pts] for code, cnt, pts in pos_rows]
        tbl = Table([['Action','Count','Points']] + pos_rows_labeled, hAlign='LEFT', colWidths=[2.3*inch, 1.0*inch, 1.2*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.15*inch))

    neg_rows = parse_code_items(neg_items)
    if neg_rows:
        story.append(Paragraph('WHERE TO IMPROVE', styles['Heading3']))
        neg_rows_labeled = [[CODE_LABELS.get(code, code), cnt, pts] for code, cnt, pts in neg_rows]
        tbl = Table([['Action','Count','Points']] + neg_rows_labeled, hAlign='LEFT', colWidths=[2.3*inch, 1.0*inch, 1.2*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.15*inch))

    if coach_items:
        story.append(Paragraph('COACHING POINTS', styles['Heading3']))
        # Render as single-column table for consistent wrapping
        rows = [[Paragraph(f"• {c}", styles['BodyText'])] for c in coach_items]
        tbl = Table(rows, hAlign='LEFT', colWidths=[6.0*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.0, colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(tbl)

    # NOTES section (from detailed CSV), formatted as: play number : note
    if player_notes_index and player_name and week_val:
        key = (player_name.strip().lower(), str(week_val).strip())
        notes_text = player_notes_index.get(key, '')
        # Expand codes inside notes for readability
        notes_text = expand_codes_in_text(notes_text)
        note_rows = parse_notes_to_rows(notes_text)
        if note_rows:
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph('NOTES', styles['Heading3']))
            # Wrap long notes using Paragraphs to avoid overflow
            note_rows_wrapped = [[play, Paragraph(note, styles['BodyText'])] for play, note in note_rows]
            tbl = Table([['Play', 'Note']] + note_rows_wrapped, hAlign='LEFT', colWidths=[0.8*inch, 5.2*inch])
            tbl.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ]))
            story.append(tbl)

    doc.build(story)


def summary_csv_to_pdf(csv_path: Path, pdf_path: Path, title="Wk Summary"):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles['Title']), Spacer(1, 0.2*inch)]

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        story.append(Paragraph("No data", styles['BodyText']))
        doc.build(story)
        return

    header, data = rows[0], rows[1:]
    # Limit columns for readability if too many
    keep_cols = [c for c in header if c in (
        'player','catch_rate','yards_per_target','targets_per30','keyplays_per30','tds_per30','drops_rate','code_points')]
    idxs = [header.index(c) for c in keep_cols]
    # Rename header for code_points if present
    header_row = keep_cols.copy()
    header_row = ['Key Plays Points' if h == 'code_points' else h for h in header_row]
    table_rows = [header_row] + [[r[i] for i in idxs] for r in data]

    table = Table(table_rows, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightyellow])
    ]))
    story.append(table)
    doc.build(story)


def main():
    ap = argparse.ArgumentParser(description='Make per-player PDFs from text reports and a group summary PDF from CSV')
    ap.add_argument('--reports_dir', default='reports')
    ap.add_argument('--out_dir', default='pdfs')
    ap.add_argument('--summary_csv', required=True)
    ap.add_argument('--details_csv', help='Detailed results CSV (for notes)')
    ap.add_argument('--title', default='Week Summary')
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build (player,week)->notes index and MA/Loaf play indices from detailed CSV if provided
    player_notes_index = {}
    ma_plays_index = {}
    loaf_plays_index = {}
    key_entries_index = {}
    if args.details_csv and Path(args.details_csv).exists():
        try:
            df = pd.read_csv(args.details_csv)
            # Normalize keys: player lower, week str
            for _, r in df.iterrows():
                player = str(r.get('player','')).strip()
                week = str(r.get('week','')).strip()
                notes = str(r.get('notes','')).strip()
                codes_str = str(r.get('codes',''))
                if player and week:
                    key = (player.lower(), week)
                    # Notes aggregation
                    if notes:
                        prev = player_notes_index.get(key, '')
                        player_notes_index[key] = (prev + ('; ' if prev else '') + notes).strip()
                    # Extract MA and L play numbers from codes like "54(MA)" or "69(L)"
                    if isinstance(codes_str, str) and codes_str.strip():
                        plays_ma = ma_plays_index.get(key, set())
                        plays_loaf = loaf_plays_index.get(key, set())
                        # Collect per-play key entries (play, action label, point value)
                        kp_list = key_entries_index.get(key, [])
                        for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', codes_str):
                            play_no = m.group(1).strip()
                            inside = m.group(2).upper()
                            # split by commas
                            tokens = [t.strip() for t in inside.split(',') if t.strip()]
                            # classify tokens and build entries
                            for tok in tokens:
                                # Variable yardage codes
                                m_c = re.match(r'^C\+(?P<n>-?\d+)$', tok, flags=re.IGNORECASE)
                                m_cm = re.match(r'^C-(?P<n>\d+)$', tok, flags=re.IGNORECASE)
                                m_r = re.match(r'^R\+(?P<n>-?\d+)$', tok, flags=re.IGNORECASE)
                                m_rm = re.match(r'^R-(?P<n>\d+)$', tok, flags=re.IGNORECASE)
                                label = None
                                points = 0
                                if m_c:
                                    n = int(m_c.group('n'))
                                    label = f"Catch {'+' if n>=0 else ''}{n} yards"
                                    points = 0.5 * n
                                elif m_cm:
                                    n = -int(m_cm.group('n'))
                                    label = f"Catch {n} yards"
                                    points = n
                                elif m_r:
                                    n = int(m_r.group('n'))
                                    label = f"Rush {'+' if n>=0 else ''}{n} yards"
                                    points = 0.5 * n
                                elif m_rm:
                                    n = -int(m_rm.group('n'))
                                    label = f"Rush {n} yards"
                                    points = n
                                else:
                                    code = tok.upper()
                                    label = CODE_LABELS.get(code, code)
                                    points = LEGEND_POINTS.get(code, 0)
                                kp_list.append((play_no, label, float(points)))
                            if any(tok == 'MA' for tok in tokens):
                                plays_ma.add(play_no)
                            if any(tok == 'L' for tok in tokens):
                                plays_loaf.add(play_no)
                        if kp_list:
                            # sort entries by play number numeric
                            kp_list.sort(key=lambda t: int(re.sub(r'\D','', t[0]) or '0'))
                            key_entries_index[key] = kp_list
                        if plays_ma:
                            ma_plays_index[key] = plays_ma
                        if plays_loaf:
                            loaf_plays_index[key] = plays_loaf
            # Convert sets to sorted lists
            ma_plays_index = {k: sorted(list(v), key=lambda x: int(re.sub(r'\D', '', x) or '0')) for k,v in ma_plays_index.items()}
            loaf_plays_index = {k: sorted(list(v), key=lambda x: int(re.sub(r'\D', '', x) or '0')) for k,v in loaf_plays_index.items()}
        except Exception:
            player_notes_index = {}
            ma_plays_index = {}
            loaf_plays_index = {}
            key_entries_index = {}

    # Per-player PDFs
    for txt in reports_dir.glob('*.txt'):
        pdf = out_dir / (txt.stem + '.pdf')
        text_report_to_pdf(txt, pdf, player_notes_index=player_notes_index, ma_plays_index=ma_plays_index, loaf_plays_index=loaf_plays_index, key_entries_index=key_entries_index)

    # Group summary
    group_pdf = out_dir / 'summary.pdf'
    summary_csv_to_pdf(Path(args.summary_csv), group_pdf, title=args.title)


if __name__ == '__main__':
    main()


