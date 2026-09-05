#!/usr/bin/env python3
"""Download a Google Sheets 'publish to web' CSV into csv/{season}/Wk{N}_{Opponent}.csv.

The tab is chosen by position: week N maps to the Nth tab (sheet) in the
workbook. The per-tab gid is discovered by fetching the published HTML
index (pub?output=html), which embeds every tab's gid in tab order. This
works with the existing "publish to web" link and needs no API key and no
extra sharing. A --gid override is still supported.
"""
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
GID_RE = re.compile(r'gid:\s*"(\d+)"')


def load_published_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    return {}


def apply_gid(url: str, gid: str | None) -> str:
    if not gid:
        return url
    # Drop any existing gid/single/output query params so we rebuild cleanly.
    url = re.sub(r'[?&](gid|single|output)=[^&]*', '', url)
    url = url.rstrip('?&')
    sep = '?' if '?' not in url else '&'
    return f'{url}{sep}gid={gid}&single=true&output=csv'


def _strip_query(url: str) -> str:
    return url.split('?', 1)[0].rstrip('/')


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode('utf-8', 'replace')
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc


def fetch_published_gids(csv_url: str) -> list[str]:
    """Return the workbook's tab gids in tab order, from the published HTML index."""
    html_url = f'{_strip_query(csv_url)}?output=html'
    html = fetch_text(html_url)
    gids = GID_RE.findall(html)
    # Preserve first-seen order, drop duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for g in gids:
        if g not in seen:
            seen.add(g)
            ordered.append(g)
    if not ordered:
        raise SystemExit(
            f"No tab gids found in published HTML index at {html_url}. "
            f"Confirm File -> Share -> Publish to web is enabled for the document."
        )
    return ordered


def resolve_gid_by_position(week: int, csv_url: str) -> str:
    gids = fetch_published_gids(csv_url)
    if week < 1 or week > len(gids):
        raise SystemExit(
            f"Week {week} is out of range: published workbook has {len(gids)} tab(s)."
        )
    gid = gids[week - 1]
    print(f"Resolved week {week} -> tab {week} gid={gid}", file=sys.stderr)
    return gid


def fetch_csv(url: str) -> str:
    text = fetch_text(url)
    head = text.lstrip()[:200].lower()
    if head.startswith('<!doctype') or head.startswith('<html'):
        raise SystemExit(
            "Published CSV URL returned HTML, not CSV. "
            "Confirm File -> Share -> Publish to web is still enabled for that tab."
        )
    if ',' not in text.split('\n', 1)[0]:
        raise SystemExit(f"Downloaded file does not look like a CSV header: {text.splitlines()[:1]!r}")
    return text


def dest_path(csv_root: Path, season: str, week: int, opponent: str) -> Path:
    opp = re.sub(r'[\s_]+', '', opponent.strip())
    return csv_root / season / f'Wk{week}_{opp}.csv'


def resolve_gid(week: int, cfg: dict, override: str | None) -> str:
    """Pick the published-tab gid for a given week.

    Priority: explicit --gid flag > Nth tab by position from the published HTML index.
    """
    if override:
        return override
    csv_url = cfg.get('csv_url') or ''
    if not csv_url:
        raise SystemExit('No csv_url in tools/sheets/published.json.')
    return resolve_gid_by_position(week, csv_url)


def main() -> None:
    cfg = load_published_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--season', required=True)
    ap.add_argument('--week', type=int, required=True)
    ap.add_argument('--opponent', required=True)
    ap.add_argument('--url', default=cfg.get('csv_url', ''), help='Published CSV URL (without gid)')
    ap.add_argument('--gid', default='', help='Override gid= in the published URL (per-tab)')
    ap.add_argument('--csv_root', default='csv')
    ap.add_argument('--github-output', action='store_true')
    args = ap.parse_args()

    url = (args.url or '').strip()
    if not url:
        raise SystemExit('No published CSV URL. Pass --url or set tools/sheets/published.json')
    # If --url is overridden on the CLI, still resolve position from that URL's index.
    cfg['csv_url'] = url
    gid = resolve_gid(args.week, cfg, (args.gid or '').strip() or None)
    url = apply_gid(url, gid)

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
