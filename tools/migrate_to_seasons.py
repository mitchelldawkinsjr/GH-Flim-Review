#!/usr/bin/env python3
"""
One-time migration script to move existing content from out/ to out/2025-2026/
"""
import argparse
from pathlib import Path
import shutil


def main():
    ap = argparse.ArgumentParser(description='Migrate existing content to season folder structure')
    ap.add_argument('--out_root', default='out', help='Root output directory (default: out)')
    ap.add_argument('--season', default='2025-2026', help='Season identifier (default: 2025-2026)')
    ap.add_argument('--dry-run', action='store_true', help='Show what would be moved without actually moving')
    args = ap.parse_args()
    
    out_root = Path(args.out_root)
    season_dir = out_root / args.season
    
    if not out_root.exists():
        print(f"Output root {out_root} does not exist. Nothing to migrate.")
        return
    
    # Items to move (exclude index.html which will be regenerated)
    items_to_move = []
    for item in out_root.iterdir():
        if item.name == 'index.html':
            continue  # Skip root index, will be regenerated
        if item.name == args.season:
            continue  # Skip season folder if it already exists
        items_to_move.append(item)
    
    if not items_to_move:
        print(f"No items to migrate. Content may already be in {season_dir}")
        return
    
    print(f"Migration plan:")
    print(f"  Source: {out_root}")
    print(f"  Destination: {season_dir}")
    print(f"  Items to move:")
    for item in items_to_move:
        print(f"    - {item.name}")
    
    if args.dry_run:
        print("\n[DRY RUN] No files were moved. Run without --dry-run to perform migration.")
        return
    
    # Create season directory
    season_dir.mkdir(parents=True, exist_ok=True)
    
    # Move items
    moved_count = 0
    for item in items_to_move:
        dest = season_dir / item.name
        if dest.exists():
            print(f"Warning: {dest} already exists. Skipping {item.name}")
            continue
        print(f"Moving {item.name}...")
        shutil.move(str(item), str(dest))
        moved_count += 1
    
    print(f"\nMigration complete! Moved {moved_count} item(s) to {season_dir}")
    print(f"\nNext steps:")
    print(f"  1. Regenerate season selector: python tools/make_season_selector.py --out_root {out_root}")
    print(f"  2. Regenerate season index: python tools/make_site_index.py --out_root {out_root} --season {args.season}")


if __name__ == '__main__':
    main()

