#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List, Dict
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart


POSITIVE_CODES = {"TD","SC","ER","GR","GB","P","FD","E"}
NEGATIVE_CODES = {"MA","DP","L","NFS","W","BR","H"}


def cell_text(val) -> str:
    try:
        if pd.isna(val):
            return ''
    except Exception:
        pass
    s = str(val)
    return '' if s.lower() == 'nan' else s


def collect_code_counts(row_dict: Dict) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for k, v in row_dict.items():
        if isinstance(k, str) and k.startswith('cnt_'):
            code = k.replace('cnt_', '').upper()
            try:
                out[code] = out.get(code, 0) + int(v)
            except Exception:
                pass
    return out


def make_bar_chart(categories: List[str], values: List[float], width=6.0*inch, height=2.0*inch,
                   value_color=colors.darkblue) -> Drawing:
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 20
    chart.height = height - 40
    chart.width = width - 60
    chart.data = [values]
    chart.strokeColor = colors.black
    chart.valueAxis.valueMin = 0
    try:
        vmax = max(values) if values else 1
        chart.valueAxis.valueMax = max(1, vmax * 1.15)
    except Exception:
        chart.valueAxis.valueMax = 1
    chart.valueAxis.valueStep = max(1, int(round(chart.valueAxis.valueMax / 4)))
    chart.categoryAxis.categoryNames = categories
    chart.categoryAxis.labels.boxAnchor = 'ne'
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -10
    chart.barLabels.nudge = 5
    chart.barLabels.fontSize = 7
    chart.barLabelFormat = '%0.0f'
    chart.bars[0].fillColor = value_color
    drawing.add(chart)
    return drawing


def main():
    ap = argparse.ArgumentParser(description='Generate per-player dashboard PDF with charts.')
    ap.add_argument('--details_csv', required=True, help='Detailed results CSV produced by film_grade.py')
    ap.add_argument('--out_pdf', required=True, help='Output PDF path')
    ap.add_argument('--title', default='Player Dashboards')
    args = ap.parse_args()

    df = pd.read_csv(args.details_csv)

    # Aggregate per player
    # Sum counts; average score; sum code_points
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    agg_dict = {c: 'sum' for c in numeric_cols}
    if 'score' in df.columns:
        agg_dict['score'] = 'mean'
    if 'grade' in df.columns:
        agg_dict['grade'] = 'first'
    grouped = df.groupby('player', dropna=False).agg(agg_dict).reset_index()

    styles = getSampleStyleSheet()
    out_pdf = Path(args.out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_pdf), pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = [Paragraph(args.title, styles['Title']), Spacer(1, 0.15*inch)]

    # Build per-player pages
    for _, r in grouped.iterrows():
        player = cell_text(r.get('player', '')) or '(Unknown)'
        score = float(r.get('score', 0.0)) if 'score' in r else 0.0
        grade = cell_text(r.get('grade', ''))

        # Collect code counts by summing original rows for the player
        sub = df[df['player'].astype(str) == player]
        code_counts: Dict[str, int] = {}
        for _, rr in sub.iterrows():
            code_counts_row = collect_code_counts(rr.to_dict())
            for k, v in code_counts_row.items():
                code_counts[k] = code_counts.get(k, 0) + v

        # Key metrics
        metrics_rows = []
        def geti(name, default=0):
            try:
                return int(r.get(name, default))
            except Exception:
                try:
                    return int(float(r.get(name, default)))
                except Exception:
                    return default

        snaps = geti('snaps')
        targets = geti('targets')
        catches = geti('catches')
        rec_yards = geti('rec_yards')
        rush_yards = geti('rush_yards')
        touchdowns = geti('touchdowns')
        drops = geti('drops')
        ma = geti('missed_assignments')
        loafs = geti('loafs')
        code_points = r.get('code_points', 0)

        metrics_rows.append(['Grade', f"{grade} ({score:.1f})" if grade else f"{score:.1f}"])
        metrics_rows.append(['Snaps', snaps])
        metrics_rows.append(['Targets', targets])
        metrics_rows.append(['Catches', catches])
        metrics_rows.append(['Rec Yards', rec_yards])
        metrics_rows.append(['Rush Yards', rush_yards])
        metrics_rows.append(['Touchdowns', touchdowns])
        metrics_rows.append(['Drops', drops])
        metrics_rows.append(['Missed Assignments', ma])
        metrics_rows.append(['Loafs', loafs])
        metrics_rows.append(['Key Plays Points', f"{float(code_points):.1f}" if isinstance(code_points, float) else str(code_points)])

        story.append(Paragraph(player, styles['Heading2']))
        tbl = Table(metrics_rows, hAlign='LEFT', colWidths=[2.2*inch, 3.8*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.1*inch))

        # Rates chart
        rate_cats = []
        rate_vals = []
        def add_rate(label, val):
            try:
                v = float(val)
            except Exception:
                v = 0.0
            rate_cats.append(label)
            rate_vals.append(max(0.0, v))

        for label in ['catch_rate','yards_per_target','targets_per30','keyplays_per30','tds_per30','drops_rate','ma_per30','loafs_per30']:
            if label in df.columns:
                add_rate(label, sub[label].mean())

        if rate_cats:
            story.append(Paragraph('Rates (avg)', styles['Heading4']))
            story.append(make_bar_chart(rate_cats, rate_vals, width=6.0*inch, height=2.0*inch, value_color=colors.darkolivegreen))
            story.append(Spacer(1, 0.1*inch))

        # Code counts chart (top 10)
        if code_counts:
            items = sorted(code_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
            cats = [k for k, _ in items]
            vals = [v for _, v in items]
            story.append(Paragraph('Code Counts', styles['Heading4']))
            story.append(make_bar_chart(cats, vals, width=6.0*inch, height=2.2*inch, value_color=colors.steelblue))

        story.append(PageBreak())

    doc.build(story)
    print(f"Wrote dashboards to {out_pdf}")


if __name__ == '__main__':
    main()


