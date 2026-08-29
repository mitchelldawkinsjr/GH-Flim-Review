/**
 * Film Review — publish the active week tab as a CSV into GH-Flim-Review.
 *
 * Bind this project to:
 *   https://docs.google.com/spreadsheets/d/1ari_H6Dk_J1AfEWrpQV-VJ1rBZ-mBWF1jJbFkj5zBkQ
 *
 * One-time setup:
 *   1. Extensions → Apps Script → paste Code.gs + appsscript.json
 *   2. Project Settings → Script properties → GITHUB_TOKEN
 *      (fine-grained PAT: contents:write on mitchelldawkinsjr/GH-Flim-Review only)
 *   3. Add a Config tab with season in A1/B1 (label "season", value "2026-2027")
 *
 * Tab names must look like: Wk1 Holland  or  Wk1_Holland
 * Publishes to: csv/{season}/Wk{N}_{Opponent}.csv on main
 * That commit triggers .github/workflows/process-week.yml
 */

var GITHUB_OWNER = 'mitchelldawkinsjr';
var GITHUB_REPO = 'GH-Flim-Review';
var GITHUB_BRANCH = 'main';
var TAB_RE = /^Wk\s*(\d+)\s*[_\s]\s*(.+)$/i;

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Film Review')
    .addItem('Publish this tab', 'publishActiveTab')
    .addToUi();
}

function publishActiveTab() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  var tabName = sheet.getName();

  var parsed = parseWeekTabName_(tabName);
  if (!parsed) {
    ui.alert(
      'Cannot publish this tab',
      'Active tab "' + tabName + '" must be named like Wk1 Holland or Wk1_Holland. ' +
        'Config and other sheets are skipped.',
      ui.ButtonSet.OK
    );
    return;
  }

  var season = readSeason_(ss);
  var opponentFile = parsed.opponent.replace(/[\s_]+/g, '');
  var filename = 'Wk' + parsed.week + '_' + opponentFile + '.csv';
  var repoPath = 'csv/' + season + '/' + filename;

  var confirm = ui.alert(
    'Publish this tab?',
    'Season: ' + season + '\nWeek: ' + parsed.week + '\nOpponent: ' + opponentFile +
      '\n\nWrites ' + repoPath + ' on ' + GITHUB_BRANCH +
      ' and starts the process-week Action.\n\nDo not publish unfinished film.',
    ui.ButtonSet.YES_NO
  );
  if (confirm !== ui.Button.YES) {
    return;
  }

  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) {
    ui.alert(
      'Missing GITHUB_TOKEN',
      'Add a fine-grained PAT (contents:write on ' + GITHUB_OWNER + '/' + GITHUB_REPO +
        ') under Apps Script → Project Settings → Script properties as GITHUB_TOKEN.',
      ui.ButtonSet.OK
    );
    return;
  }

  var csv = sheetToCsv_(sheet);
  putGithubFile_(token, repoPath, csv, 'Add ' + repoPath + ' from Sheets');
  ui.alert(
    'Published',
    repoPath + ' is on GitHub. Dashboards appear on the Film Review hub in a few minutes.',
    ui.ButtonSet.OK
  );
}

function parseWeekTabName_(name) {
  var m = String(name || '').trim().match(TAB_RE);
  if (!m) {
    return null;
  }
  var opponent = String(m[2] || '').trim();
  if (!opponent) {
    return null;
  }
  return { week: parseInt(m[1], 10), opponent: opponent };
}

function readSeason_(ss) {
  var config = ss.getSheetByName('Config');
  if (!config) {
    throw new Error('Add a Config tab with season in B1 (label season in A1), e.g. 2026-2027.');
  }
  var lastRow = Math.max(config.getLastRow(), 1);
  var values = config.getRange(1, 1, lastRow, 2).getValues();
  for (var i = 0; i < values.length; i++) {
    var key = String(values[i][0] || '').trim().toLowerCase();
    var val = String(values[i][1] || '').trim();
    if (key === 'season' && val) {
      if (!/^\d{4}-\d{4}$/.test(val)) {
        throw new Error('Config season must look like 2026-2027 (got "' + val + '").');
      }
      return val;
    }
  }
  throw new Error('Config tab needs a row: season | 2026-2027');
}

function sheetToCsv_(sheet) {
  var range = sheet.getDataRange();
  var values = range.getValues();
  var lines = [];
  for (var r = 0; r < values.length; r++) {
    var cells = [];
    for (var c = 0; c < values[r].length; c++) {
      cells.push(csvEscape_(values[r][c]));
    }
    lines.push(cells.join(','));
  }
  return lines.join('\n') + '\n';
}

function csvEscape_(value) {
  if (value === null || value === undefined) {
    return '';
  }
  if (Object.prototype.toString.call(value) === '[object Date]') {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  var s = String(value);
  if (/[",\n\r]/.test(s)) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function putGithubFile_(token, path, content, message) {
  var api = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO +
    '/contents/' + path.split('/').map(encodeURIComponent).join('/');
  var sha = githubFileSha_(token, api);
  var payload = {
    message: message,
    content: Utilities.base64Encode(content, Utilities.Charset.UTF_8),
    branch: GITHUB_BRANCH
  };
  if (sha) {
    payload.sha = sha;
  }
  var res = UrlFetchApp.fetch(api, {
    method: 'put',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'flim-review-sheets'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  var code = res.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error('GitHub write failed (' + code + '): ' + res.getContentText());
  }
}

function githubFileSha_(token, api) {
  var res = UrlFetchApp.fetch(api + '?ref=' + encodeURIComponent(GITHUB_BRANCH), {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'flim-review-sheets'
    },
    muteHttpExceptions: true
  });
  if (res.getResponseCode() === 404) {
    return null;
  }
  if (res.getResponseCode() !== 200) {
    throw new Error('GitHub read failed (' + res.getResponseCode() + '): ' + res.getContentText());
  }
  var body = JSON.parse(res.getContentText());
  return body.sha || null;
}
