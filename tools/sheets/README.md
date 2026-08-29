# Google Sheets publish (Phase 2)

Bound to the WR film log:

https://docs.google.com/spreadsheets/d/1ari_H6Dk_J1AfEWrpQV-VJ1rBZ-mBWF1jJbFkj5zBkQ

This script does **not** grade film. It writes `csv/{season}/Wk{N}_{Opponent}.csv` to `main`. GitHub Action `process-week.yml` does the rest.

## Bind

1. Open the spreadsheet → **Extensions → Apps Script**.
2. Replace the default files with `Code.gs` and `appsscript.json` from this folder.
3. **Project Settings → Script properties** → add `GITHUB_TOKEN`:
   - Fine-grained PAT with **Contents: Read and write** on `mitchelldawkinsjr/GH-Flim-Review` only.
   - Do not put the token in a sheet cell or in git.
4. Add a tab named **Config** with:

   | A      | B          |
   |--------|------------|
   | season | 2026-2027  |

5. Reload the spreadsheet. Menu **Film Review → Publish this tab**.

## Tab names

Active tab must match `Wk1 Holland` or `Wk1_Holland`. Opponent spaces become the filename token (`Holland`, `ComstockPark`).

Re-publish overwrites the same path and rebuilds that week.
