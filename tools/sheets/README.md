# Google Sheets ingest (Phase 2)

Primary path: **publish the tab to the web as CSV**, then let GitHub Actions pull it. No PAT and no Apps Script required.

## Published CSV (recommended)

Workbook: https://docs.google.com/spreadsheets/d/1ari_H6Dk_J1AfEWrpQV-VJ1rBZ-mBWF1jJbFkj5zBkQ

The base published feed is stored in `published.json` (`csv_url`, **without** a `gid=`). The tab for each week is chosen **by position**: week N pulls the Nth tab (sheet) in the workbook. The per-tab `gid` is discovered automatically by reading the published HTML index (`pub?output=html`), which embeds every tab's `gid` in tab order — so there is **no API key, no extra sharing, and no per-week gid entry** required.

That link is public anyone-with-the-URL.

**One-time setup**

Publish the workbook to web: **File → Share → Publish to web → Entire document → CSV**. Keep it published. (Each tab becomes fetchable by its gid; the document-level publish is what exposes the tab index the tool reads.)

**Run a week**

GitHub → **Actions → Process week CSV → Run workflow**:
- source: `published_sheet`
- season / week / opponent

The Action resolves the Nth tab's gid automatically and downloads it into `csv/{season}/Wk{N}_{Opponent}.csv`, runs `run_week.py`, and deploys. Make sure the week's tab is the Nth sheet in the workbook (drag tabs to reorder if needed) — non-week tabs (e.g. `Config`) count toward the position, so keep week tabs at the front in order.

Local dry run:

```bash
python3 tools/fetch_published_csv.py --season 2026-2027 --week 1 --opponent Holland
python3 tools/fetch_published_csv.py --season 2026-2027 --week 2 --opponent Fruitport
```

Optional `--gid 1234567890` to override the resolved gid for one run.

## Apps Script push (optional)

`Code.gs` can still **Film Review → Publish this tab** via the GitHub Contents API if you do not want a public CSV. See the bind steps below. Prefer the published feed unless you need the sheet to stay private.

1. Extensions → Apps Script → paste `Code.gs` + `appsscript.json`
2. Script properties: `GITHUB_TOKEN` (contents:write on `GH-Flim-Review` only)
3. Config tab: `season` | `2026-2027`
