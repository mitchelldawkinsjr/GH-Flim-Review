#!/usr/bin/env python3
"""Shared rubric for the film-review grading pipeline.

Canonical home for the code legend, point values, rate helpers, and the
codes parser. Other modules should import from here instead of redefining
these constants/functions.
"""
from __future__ import annotations

import re
import sys

# Point values per the coach's legend.
LEGEND_POINTS = {
    "TD": 15,
    "E": 5,
    "ER": 7,
    "GR": 2,
    "GB": 2,
    "P": 10,
    "FD": 5,
    "MA": -10,
    "SC": 10,
    "DP": -15,
    "H": 0,
    "BR": -2,
    "L": -2,
    "NFS": -3,
    "W": -1,
    "LF": -0.5,
    "BBL": -0.5,
    "EP": 2,
}

CODE_LABELS = {
    "TD": "Touchdown",
    "E": "Relentless Effort",
    "ER": "Elite Route",
    "GR": "Good Route",
    "GB": "Good Block",
    "P": "Pancake",
    "FD": "First Down",
    "MA": "Missed Assignment",
    "SC": "Spectacular Catch",
    "DP": "Dropped Pass",
    "H": "Holding",
    "BR": "Bad Route",
    "L": "Loaf (Laziness)",
    "NFS": "Not Full Speed",
    "W": "Whiffed",
    "BT": "Broken Tackle",
    "LF": "Lack of Focus",
    "BBL": "Bad Body Language",
    "EP": "Extra Point Conversion",
}

# Codes that count as a positive key play.
POSITIVE_CODES_FOR_KEYPLAYS = {"TD", "SC", "ER", "GR", "GB", "P", "FD", "E", "EP"}

# A Lack-of-Focus (LF) counts as half a full loaf (L) for discipline.
LOAF_UNIT_L = 1.0
LOAF_UNIT_LF = 0.5

# Variable-valued code patterns (support both +N and -N).
PATTERN_CATCH_YARDS = re.compile(r'^C(?P<sign>[+-])(?P<n>\d+)$', flags=re.IGNORECASE)
PATTERN_RUSH_YARDS = re.compile(r'^R(?P<sign>[+-])(?P<n>\d+)$', flags=re.IGNORECASE)
PATTERN_BT_YARDS = re.compile(r'^BT(?P<sign>[+-])(?P<n>\d+)$', flags=re.IGNORECASE)


def safe_div(n, d) -> float:
    try:
        n = float(n)
        d = float(d)
        if d == 0:
            return 0.0
        return n / d
    except Exception:
        return 0.0


def per30(n, snaps) -> float:
    try:
        snaps = float(snaps)
        n = float(n)
        if snaps <= 0:
            return 0.0
        return n * 30.0 / snaps
    except Exception:
        return 0.0


def clamp(x, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, x))


def letter(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def cell_text(val) -> str:
    """Clean string for a CSV cell: '' for NaN/None/blank, else stripped text."""
    try:
        if pd_isna(val):
            return ""
    except Exception:
        pass
    if isinstance(val, str):
        s = val.strip()
        return "" if s.lower() == "nan" or s == "" else s
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def pd_isna(val) -> bool:
    try:
        import pandas as pd  # local import keeps rubric usable without pandas
        return bool(pd.isna(val))
    except Exception:
        return val is None


def fmt_count(x) -> str:
    """Format a count that may be fractional (e.g. 0.5 loaf) without trailing zeros."""
    try:
        f = float(x)
    except Exception:
        return str(x)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def parse_codes_to_points(codes_str, warn_unknown: bool = False):
    """Parse a codes string into (total_points, counts, yards_c, yards_r,
    derived_keyplays).

    Accepts forms like "143(E,P)", "61(C+16, FD, SC)", "54(C-2)", with
    parentheses/commas/semicolons/spaces as separators. Play-number prefixes
    (e.g. "143") are ignored. Variable yardage codes support both +N and -N.
    A code attached to the same play more than once (e.g. when a play is listed
    in both the ++ and -- columns) is counted once. Unknown tokens are ignored;
    when warn_unknown is True they are reported to stderr so data-entry typos
    surface instead of silently dropping points.
    """
    total = 0
    counts = {k: 0 for k in LEGEND_POINTS}
    counts["BT"] = 0
    yards_c = 0
    yards_r = 0
    derived_keyplays = 0

    if not isinstance(codes_str, str) or not codes_str.strip():
        return total, counts, yards_c, yards_r, derived_keyplays

    def account_token(t, seen):
        nonlocal total, yards_c, yards_r, derived_keyplays
        m_c = PATTERN_CATCH_YARDS.match(t)
        if m_c:
            n = int(m_c.group('n')) * (-1 if m_c.group('sign') == '-' else 1)
            total += 0.5 * n
            yards_c += n
            return
        m_r = PATTERN_RUSH_YARDS.match(t)
        if m_r:
            n = int(m_r.group('n')) * (-1 if m_r.group('sign') == '-' else 1)
            total += 0.5 * n
            yards_r += n
            return
        m_bt = PATTERN_BT_YARDS.match(t)
        if m_bt:
            n = int(m_bt.group('n')) * (-1 if m_bt.group('sign') == '-' else 1)
            total += 0.5 * n
            counts['BT'] = counts.get('BT', 0) + 1
            return
        t_up = t.upper()
        if t_up in LEGEND_POINTS:
            key = ('code', t_up)
            if key in seen:
                return
            seen.add(key)
            total += LEGEND_POINTS[t_up]
            counts[t_up] += 1
            if t_up in POSITIVE_CODES_FOR_KEYPLAYS:
                derived_keyplays += 1
        elif warn_unknown and not t_up.isdigit():
            print(f"WARNING: unrecognized code token {t!r} in {codes_str!r}", file=sys.stderr)

    seen = set()
    # Parse play-numbered segments "143(E,P)" and dedupe codes per play.
    for m in re.finditer(r'(\d+)\s*\(([^)]*)\)', codes_str):
        play = m.group(1)
        for tok in re.split(r'[\s,;]+', m.group(2)):
            tok = tok.strip()
            if not tok:
                continue
            key = (play, tok.upper())
            if key in seen:
                continue
            seen.add(key)
            account_token(tok, seen)
    # Parse any free-floating tokens outside parens (e.g. "ER C+12 FD").
    remainder = re.sub(r'\d+\s*\([^)]*\)', ' ', codes_str)
    for tok in re.split(r'[\s,;]+', remainder.replace('(', ' ').replace(')', ' ')):
        tok = tok.strip()
        if tok:
            account_token(tok, seen)

    return total, counts, yards_c, yards_r, derived_keyplays


def effective_drops(sheet_drops, counts: dict) -> int:
    """Reconcile the sheet drops column with DP codes: take the larger so a
    drop recorded either way is captured without double-counting."""
    try:
        sheet = int(sheet_drops)
    except Exception:
        sheet = 0
    dp = int(counts.get('DP', 0))
    return max(sheet, dp)


def effective_ma(sheet_ma, counts: dict) -> int:
    """Reconcile the sheet Missed Assignment column with MA codes."""
    try:
        sheet = int(sheet_ma)
    except Exception:
        sheet = 0
    return max(sheet, int(counts.get('MA', 0)))


def effective_loafs(sheet_loafs, counts: dict) -> float:
    """Reconcile the sheet Loaf column with L codes. LF (Lack of Focus) is a
    separate code, not a loaf, so it does not feed the loaf discipline total."""
    try:
        sheet = float(sheet_loafs)
    except Exception:
        sheet = 0.0
    return max(sheet, float(counts.get('L', 0)))
