# Google Sheets ingest (Phase 2)

Primary path: **publish the tab to the web as CSV**, then let GitHub Actions pull it. No PAT and no Apps Script required.

## Published CSV (recommended)

Workbook: https://docs.google.com/spreadsheets/d/1ari_H6Dk_J1AfEWrpQV-VJ1rBZ-mBWF1jJbFkj5zBkQ

Current published feed (gid `916210750`):

https://docs.google.com/spreadsheets/d/e/2PACX-1vSJN_QZbNJCypAsHSmr2YLaspdsvhMF8kVYDLPhSZaDStCU7V3PVlRJyZDHXHqrtrhSRXPl9Jq_HKwf/pub?gid=916210750&single=true&output=csv

URL is stored in `published.json`. That link is public anyone-with-the-URL.

**Publish a week**

1. Finish the week tab (`Wk1 Holland`, etc.).
2. **File → Share → Publish to web** — entire document as CSV (or that tab). Keep it published.
3. Copy the tab **gid** from the Sheet URL (`gid=916210750`).
4. GitHub → **Actions → Process week CSV → Run workflow**:
   - source: `published_sheet`
   - season / week / opponent
   - `sheets_gid` if this is not the default tab

The Action downloads the CSV into `csv/{season}/Wk{N}_{Opponent}.csv`, runs `run_week.py`, and deploys.

Local dry run:

```bash
python3 tools/fetch_published_csv.py --season 2026-2027 --week 1 --opponent Holland
```

Optional `--gid 916210750` to target another published tab in the same workbook.

## Apps Script push (optional)

`Code.gs` can still **Film Review → Publish this tab** via the GitHub Contents API if you do not want a public CSV. See the bind steps below. Prefer the published feed unless you need the sheet to stay private.

1. Extensions → Apps Script → paste `Code.gs` + `appsscript.json`
2. Script properties: `GITHUB_TOKEN` (contents:write on `GH-Flim-Review` only)
3. Config tab: `season` | `2026-2027`
