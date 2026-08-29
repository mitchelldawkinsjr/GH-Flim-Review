#!/usr/bin/env python3
"""Download a Google Sheets 'publish to web' CSV into csv/{season}/Wk{N}_{Opponent}.csv."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / 'sheets' / 'published.json'
USER_AGENT = 'flim-review-fetch/1.0 (+https://github.com/mitchelldawkinsjr/GH-Flim-Review)'


def load_published_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    return {}


def apply_gid(url: str, gid: str | None) -> str:
    if not gid:
        return url
    if re.search(r'[?&]gid=', url):
        return re.sub(r'([?&]gid=)[^&]*', rf'\g<1>{gid}', url, count=1)
    sep = '&' if '?' in url else '?'
    return f'{url}{sep}gid={gid}&single=true&output=csv'


def fetch_csv(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to download published CSV: {exc}") from exc
    text = raw.decode('utf-8-sig')
    head = text.lstrip()[:200].lower()
    if head.startswith('<!doctype') or head.startswith('<html'):
        raise SystemExit(
            "Published CSV URL returned HTML, not CSV. "
            "Confirm File → Share → Publish to web is still enabled for that tab."
        )
    if ',' not in text.split('\n', 1)[0]:
        raise SystemExit(f"Downloaded file does not look like a CSV header: {text.splitlines()[:1]!r}")
    return text


def dest_path(csv_root: Path, season: str, week: int, opponent: str) -> Path:
    opp = re.sub(r'[\s_]+', '', opponent.strip())
    return csv_root / season / f'Wk{week}_{opp}.csv'


def main() -> None:
    cfg = load_published_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--season', required=True)
    ap.add_argument('--week', type=int, required=True)
    ap.add_argument('--opponent', required=True)
    ap.add_argument('--url', default=cfg.get('csv_url', ''), help='Published CSV URL')
    ap.add_argument('--gid', default='', help='Override gid= in the published URL (per-tab)')
    ap.add_argument('--csv_root', default='csv')
    ap.add_argument('--github-output', action='store_true')
    args = ap.parse_args()

    url = (args.url or '').strip()
    if not url:
        raise SystemExit('No published CSV URL. Pass --url or set tools/sheets/published.json')
    gid = (args.gid or '').strip()
    url = apply_gid(url, gid or None)

    text = fetch_csv(url)
    out = dest_path(Path(args.csv_root), args.season, args.week, args.opponent)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith('\n'):
        text += '\n'
    out.write_text(text, encoding='utf-8')
    print(f"Wrote {out} from {url}", file=sys.stderr)

    if args.github_output:
        opp = re.sub(r'[\s_]+', '', args.opponent.strip())
        print(f"csv_path={out.as_posix()}")
        print(f"season={args.season}")
        print(f"week={args.week}")
        print(f"opponent={opp}")


if __name__ == '__main__':
    main()
