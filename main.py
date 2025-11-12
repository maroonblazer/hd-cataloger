#!/usr/bin/env python3
"""
HD Cataloger - Tool for cataloging and consolidating files across external drives.

This tool helps you:
1. Create catalogs of files on external drives
2. Find duplicate files across drives
3. Plan consolidation to minimize the number of drives needed
"""

import argparse
import sys
import os

from src.catalog import scan_drive
from src.duplicates import find_duplicates
from src.consolidate import plan_consolidation


def cmd_catalog(args):
    """Handle the 'catalog' command."""
    try:
        scan_drive(args.drive_path, args.output_dir, args.include_hidden)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_find_duplicates(args):
    """Handle the 'find-duplicates' command."""
    try:
        output_path = args.output if args.output else None
        find_duplicates(args.catalogs, output_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_consolidate(args):
    """Handle the 'consolidate' command."""
    try:
        # Parse drive capacities if provided
        drive_capacities = None
        if args.capacities:
            drive_capacities = {}
            for capacity_str in args.capacities:
                try:
                    volume, capacity = capacity_str.split(':')
                    # Convert capacity to bytes (assumes input in GB)
                    drive_capacities[volume] = int(float(capacity) * 1024 * 1024 * 1024)
                except ValueError:
                    print(f"Warning: Invalid capacity format '{capacity_str}'. Expected format: 'VolumeName:SizeInGB'")

        output_path = args.output if args.output else None
        plan_consolidation(args.duplicate_report, args.catalogs, drive_capacities, output_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='HD Cataloger - Manage and consolidate files across external drives',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a drive
  %(prog)s catalog /Volumes/MyDrive

  # Scan a Time Machine backup (includes hidden files)
  %(prog)s catalog /Volumes/.timemachine --include-hidden

  # Find duplicates across multiple drives
  %(prog)s find-duplicates catalogs/Drive1_catalog.json catalogs/Drive2_catalog.json

  # Plan consolidation
  %(prog)s consolidate catalogs/duplicate_report.json catalogs/Drive1_catalog.json catalogs/Drive2_catalog.json

  # Plan consolidation with drive capacity specifications
  %(prog)s consolidate catalogs/duplicate_report.json catalogs/*.json --capacities Drive1:2000 Drive2:4000
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True

    # Catalog command
    parser_catalog = subparsers.add_parser(
        'catalog',
        help='Scan a drive and create a catalog of all files'
    )
    parser_catalog.add_argument(
        'drive_path',
        help='Path to the drive to scan (e.g., /Volumes/MyDrive)'
    )
    parser_catalog.add_argument(
        '-o', '--output-dir',
        default='catalogs',
        help='Directory to save catalog files (default: catalogs)'
    )
    parser_catalog.add_argument(
        '--include-hidden',
        action='store_true',
        help='Include hidden files and directories (useful for Time Machine backups)'
    )
    parser_catalog.set_defaults(func=cmd_catalog)

    # Find duplicates command
    parser_duplicates = subparsers.add_parser(
        'find-duplicates',
        help='Find duplicate files across multiple catalogs'
    )
    parser_duplicates.add_argument(
        'catalogs',
        nargs='+',
        help='Paths to catalog JSON files'
    )
    parser_duplicates.add_argument(
        '-o', '--output',
        help='Path to save duplicate report (default: catalogs/duplicate_report.json)'
    )
    parser_duplicates.set_defaults(func=cmd_find_duplicates)

    # Consolidate command
    parser_consolidate = subparsers.add_parser(
        'consolidate',
        help='Plan file consolidation to minimize drives needed'
    )
    parser_consolidate.add_argument(
        'duplicate_report',
        help='Path to duplicate report JSON file'
    )
    parser_consolidate.add_argument(
        'catalogs',
        nargs='+',
        help='Paths to catalog JSON files'
    )
    parser_consolidate.add_argument(
        '-c', '--capacities',
        nargs='+',
        help='Drive capacities in format VolumeName:SizeInGB (e.g., Drive1:2000 Drive2:4000)'
    )
    parser_consolidate.add_argument(
        '-o', '--output',
        help='Path to save consolidation plan (default: catalogs/consolidation_plan.json)'
    )
    parser_consolidate.set_defaults(func=cmd_consolidate)

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate command
    args.func(args)


if __name__ == '__main__':
    main()
