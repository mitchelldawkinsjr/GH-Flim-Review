#!/usr/bin/env python3
from pypdf import PdfWriter
from pathlib import Path
import argparse


def main():
    ap = argparse.ArgumentParser(description='Merge PDFs into one packet')
    ap.add_argument('--summary', required=True)
    ap.add_argument('--players_dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    writer = PdfWriter()

    # Add summary first
    summary_path = Path(args.summary)
    if summary_path.exists():
        writer.append(str(summary_path))

    # Add per-player PDFs sorted by filename
    players = sorted(Path(args.players_dir).glob('*.pdf'))
    for pdf in players:
        if pdf.name == 'summary.pdf':
            continue
        writer.append(str(pdf))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        writer.write(f)


if __name__ == '__main__':
    main()


