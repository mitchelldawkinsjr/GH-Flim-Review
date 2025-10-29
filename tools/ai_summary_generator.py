#!/usr/bin/env python3
"""
AI Summary Generator for Film Review App
Generates intelligent summaries for weekly and season player performance
"""

import re
from typing import Dict, List, Optional, Tuple
import pandas as pd


def generate_weekly_summary(player: str, week: int, opponent: str, totals: Dict, rates: Dict, 
                          code_counts: Dict, notes: str = "") -> str:
    """
    Generate an AI-powered weekly summary for a player
    """
    # Extract key metrics
    snaps = totals.get('snaps', 0)
    targets = totals.get('targets', 0)
    catches = totals.get('catches', 0)
    rec_yards = totals.get('rec_yards', 0)
    rush_yards = totals.get('rush_yards', 0)
    touchdowns = totals.get('touchdowns', 0)
    drops = totals.get('drops', 0)
    ma = totals.get('ma', 0)
    loafs = totals.get('loafs', 0)
    score = rates.get('score', 0)
    grade = rates.get('grade', 'F')
    
    # Calculate derived metrics
    total_yards = rec_yards + rush_yards
    ypc = (rec_yards / catches) if catches > 0 else 0
    catch_rate = rates.get('catch_rate', 0)
    drops_rate = rates.get('drops_rate', 0)
    ypt = rates.get('ypt', 0)
    
    # Code analysis
    tds = code_counts.get('TD', 0)
    elite_routes = code_counts.get('ER', 0)
    good_routes = code_counts.get('GR', 0)
    bad_routes = code_counts.get('BR', 0)
    good_blocks = code_counts.get('GB', 0)
    pancakes = code_counts.get('P', 0)
    first_downs = code_counts.get('FD', 0)
    spectacular_catches = code_counts.get('SC', 0)
    broken_tackles = code_counts.get('BT', 0)
    effort = code_counts.get('E', 0)
    missed_assignments = code_counts.get('MA', 0)
    loafs_codes = code_counts.get('L', 0)
    
    # Generate summary components
    summary_parts = []
    
    # Performance overview
    if score >= 90:
        performance_desc = "exceptional"
    elif score >= 80:
        performance_desc = "strong"
    elif score >= 70:
        performance_desc = "solid"
    elif score >= 60:
        performance_desc = "below average"
    else:
        performance_desc = "struggling"
    
    summary_parts.append(f"{player} had a {performance_desc} performance against {opponent} with a {grade} grade ({score:.1f}).")
    
    # Statistical highlights
    if catches > 0:
        if ypc >= 15:
            summary_parts.append(f"His {ypc:.1f} yards per catch demonstrates explosive playmaking ability.")
        elif ypc >= 10:
            summary_parts.append(f"His {ypc:.1f} yards per catch shows solid production.")
        else:
            summary_parts.append(f"His {ypc:.1f} yards per catch indicates short-area/possession work.")
    
    if targets > 0:
        if catch_rate >= 0.8:
            summary_parts.append(f"Excellent reliability with {catches}/{targets} catches ({catch_rate:.1%} catch rate).")
        elif catch_rate >= 0.6:
            summary_parts.append(f"Decent reliability with {catches}/{targets} catches ({catch_rate:.1%} catch rate).")
        else:
            summary_parts.append(f"Concerning reliability with {catches}/{targets} catches ({catch_rate:.1%} catch rate).")
    
    # Code-based insights
    if tds > 0:
        summary_parts.append(f"Scored {tds} touchdown{'s' if tds > 1 else ''} to lead the offense.")
    
    if elite_routes > 0:
        summary_parts.append(f"Executed {elite_routes} elite route{'s' if elite_routes > 1 else ''} showing advanced technique.")
    
    if good_blocks > 0:
        summary_parts.append(f"Delivered {good_blocks} good block{'s' if good_blocks > 1 else ''} in the run game.")
    
    if pancakes > 0:
        summary_parts.append(f"Dominant blocking with {pancakes} pancake block{'s' if pancakes > 1 else ''}.")
    
    if broken_tackles > 0:
        summary_parts.append(f"Showcased after-catch ability with {broken_tackles} broken tackle{'s' if broken_tackles > 1 else ''}.")
    
    if spectacular_catches > 0:
        summary_parts.append(f"Made {spectacular_catches} spectacular catch{'es' if spectacular_catches > 1 else ''}.")
    
    # Areas of concern
    concerns = []
    if drops > 0:
        concerns.append(f"{drops} drop{'s' if drops > 1 else ''}")
    if missed_assignments > 0:
        concerns.append(f"{missed_assignments} missed assignment{'s' if missed_assignments > 1 else ''}")
    if loafs > 0:
        concerns.append(f"{loafs} loaf{'s' if loafs > 1 else ''}")
    if bad_routes > 0:
        concerns.append(f"{bad_routes} bad route{'s' if bad_routes > 1 else ''}")
    
    if concerns:
        summary_parts.append(f"Areas for improvement: {', '.join(concerns)}.")
    
    # Usage analysis
    if snaps > 0:
        targets_per30 = (targets * 30) / snaps
        if targets_per30 >= 8:
            summary_parts.append(f"High usage with {targets_per30:.1f} targets per 30 snaps.")
        elif targets_per30 >= 5:
            summary_parts.append(f"Moderate usage with {targets_per30:.1f} targets per 30 snaps.")
        else:
            summary_parts.append(f"Limited opportunities with {targets_per30:.1f} targets per 30 snaps.")
    
    # Coaching recommendations
    recommendations = []
    if catch_rate < 0.6 and targets > 2:
        recommendations.append("Focus on route precision and timing")
    if drops > catches * 0.2:
        recommendations.append("Work on concentration and hand-eye coordination")
    if missed_assignments > 0:
        recommendations.append("Study film to improve assignment recognition")
    if loafs > 0:
        recommendations.append("Increase effort level and intensity")
    if ypc < 8 and catches > 0:
        recommendations.append("Develop after-catch skills and YAC ability")
    
    if recommendations:
        summary_parts.append(f"Recommendations: {'; '.join(recommendations)}.")
    
    return " ".join(summary_parts)


def generate_season_summary(player: str, season_data: pd.DataFrame, 
                          weekly_scores: List[float], weekly_grades: List[str]) -> str:
    """
    Generate an AI-powered season summary for a player
    """
    # Calculate season totals
    total_snaps = season_data['snaps'].sum()
    total_targets = season_data['targets'].sum()
    total_catches = season_data['catches'].sum()
    total_rec_yards = season_data['rec_yards'].sum()
    total_rush_yards = season_data['rush_yards'].sum()
    total_touchdowns = season_data['touchdowns'].sum()
    total_drops = season_data['drops'].sum()
    total_ma = season_data['missed_assignments'].sum()
    total_loafs = season_data['loafs'].sum()
    
    # Calculate averages
    avg_score = sum(weekly_scores) / len(weekly_scores) if weekly_scores else 0
    games_played = len(weekly_scores) if weekly_scores else len(season_data['week'].unique()) if 'week' in season_data.columns else len(season_data)
    
    # Calculate rates
    season_catch_rate = (total_catches / (total_catches + total_drops)) if (total_catches + total_drops) > 0 else 0
    season_ypc = (total_rec_yards / total_catches) if total_catches > 0 else 0
    season_ypt = ((total_rec_yards + total_rush_yards) / total_targets) if total_targets > 0 else 0
    
    # Calculate per-game averages
    avg_catches_per_game = total_catches / games_played
    avg_yards_per_game = (total_rec_yards + total_rush_yards) / games_played
    avg_targets_per_game = total_targets / games_played
    
    summary_parts = []
    
    # Season overview
    if avg_score >= 85:
        performance_desc = "outstanding"
    elif avg_score >= 75:
        performance_desc = "excellent"
    elif avg_score >= 65:
        performance_desc = "solid"
    elif avg_score >= 55:
        performance_desc = "inconsistent"
    else:
        performance_desc = "struggling"
    
    summary_parts.append(f"{player} had a {performance_desc} season with an average grade of {avg_score:.1f} over {games_played} games.")
    
    # Statistical summary
    summary_parts.append(f"He finished with {total_catches} catches for {total_rec_yards} receiving yards and {total_touchdowns} touchdowns.")
    
    if total_rush_yards > 0:
        summary_parts.append(f"He also contributed {total_rush_yards} rushing yards.")
    
    # Per-game production
    summary_parts.append(f"His per-game averages: {avg_catches_per_game:.1f} catches, {avg_yards_per_game:.1f} total yards, {avg_targets_per_game:.1f} targets.")
    
    # Efficiency analysis
    if season_catch_rate >= 0.8:
        summary_parts.append(f"Excellent reliability with a {season_catch_rate:.1%} catch rate.")
    elif season_catch_rate >= 0.6:
        summary_parts.append(f"Solid reliability with a {season_catch_rate:.1%} catch rate.")
    else:
        summary_parts.append(f"Needs improvement with a {season_catch_rate:.1%} catch rate.")
    
    if season_ypc >= 15:
        summary_parts.append(f"Explosive playmaker averaging {season_ypc:.1f} yards per catch.")
    elif season_ypc >= 10:
        summary_parts.append(f"Solid production averaging {season_ypc:.1f} yards per catch.")
    else:
        summary_parts.append(f"Short-area specialist averaging {season_ypc:.1f} yards per catch.")
    
    # Trend analysis
    if len(weekly_scores) >= 3:
        recent_scores = weekly_scores[-3:]
        early_scores = weekly_scores[:3] if len(weekly_scores) >= 6 else weekly_scores[:len(weekly_scores)//2]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        early_avg = sum(early_scores) / len(early_scores)
        
        if recent_avg > early_avg + 5:
            summary_parts.append("He showed significant improvement as the season progressed.")
        elif recent_avg < early_avg - 5:
            summary_parts.append("His performance declined in the latter part of the season.")
        else:
            summary_parts.append("He maintained consistent performance throughout the season.")
    
    # Areas of concern
    concerns = []
    if total_drops > total_catches * 0.15:
        concerns.append(f"{total_drops} drops")
    if total_ma > games_played:
        concerns.append(f"{total_ma} missed assignments")
    if total_loafs > games_played:
        concerns.append(f"{total_loafs} loafs")
    
    if concerns:
        summary_parts.append(f"Areas for improvement: {', '.join(concerns)}.")
    
    # Season recommendations
    recommendations = []
    if season_catch_rate < 0.6:
        recommendations.append("Focus on route running and timing")
    if season_ypc < 10:
        recommendations.append("Develop after-catch skills")
    if total_ma > games_played * 0.5:
        recommendations.append("Improve assignment recognition")
    if avg_score < 70:
        recommendations.append("Increase overall effort and focus")
    
    if recommendations:
        summary_parts.append(f"Offseason focus: {'; '.join(recommendations)}.")
    
    return " ".join(summary_parts)


def extract_notes_insights(notes: str) -> Dict[str, int]:
    """
    Extract insights from coach notes using keyword analysis
    """
    if not isinstance(notes, str):
        return {}
    
    notes_lower = notes.lower()
    insights = {
        'yac': notes_lower.count('yac') + notes_lower.count('after catch') + notes_lower.count('broken tackle'),
        'route': notes_lower.count('route') + notes_lower.count('cut') + notes_lower.count('break'),
        'blocking': notes_lower.count('block') + notes_lower.count('pancake'),
        'effort': notes_lower.count('effort') + notes_lower.count('intensity') + notes_lower.count('hustle'),
        'timing': notes_lower.count('timing') + notes_lower.count('timing') + notes_lower.count('rhythm'),
        'concentration': notes_lower.count('focus') + notes_lower.count('concentration') + notes_lower.count('attention'),
        'technique': notes_lower.count('technique') + notes_lower.count('form') + notes_lower.count('fundamentals')
    }
    
    return insights
