"""Module for generating human-readable reports from catalog and duplicate data."""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime


def load_json(file_path: str) -> Dict:
    """Load a JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        return json.load(f)


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def generate_duplicate_report(duplicate_report_path: str, output_path: Optional[str] = None,
                              top_n: int = 20) -> str:
    """
    Generate a human-readable report from a duplicate report JSON file.

    Args:
        duplicate_report_path: Path to duplicate report JSON file
        output_path: Optional path to save the report (if None, returns as string)
        top_n: Number of top items to show in each category

    Returns:
        The report as a string
    """
    print(f"Loading duplicate report: {duplicate_report_path}")
    data = load_json(duplicate_report_path)

    lines = []
    lines.append("=" * 80)
    lines.append("DUPLICATE FILES REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Summary section
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Analysis timestamp: {data.get('analysis_timestamp', 'N/A')}")
    lines.append(f"Catalogs analyzed: {', '.join(data.get('catalogs_analyzed', []))}")
    lines.append("")
    lines.append(f"Total unique files: {data.get('total_unique_files', 0):,}")
    lines.append(f"Duplicate files found: {data.get('duplicate_file_count', 0):,}")
    lines.append(f"Total redundant space: {format_size(data.get('total_redundant_size', 0))}")
    lines.append("")

    duplicates = data.get('duplicates', {})

    if not duplicates:
        lines.append("No duplicates found!")
        report_text = "\n".join(lines)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_path}")

        return report_text

    # Top duplicates by redundant size
    lines.append(f"TOP {top_n} DUPLICATES BY REDUNDANT SPACE")
    lines.append("-" * 80)

    sorted_by_size = sorted(
        duplicates.values(),
        key=lambda x: x['redundant_size'],
        reverse=True
    )

    for i, dup in enumerate(sorted_by_size[:top_n], 1):
        lines.append(f"\n{i}. {dup['filename']}")
        lines.append(f"   File size: {format_size(dup['size'])}")
        lines.append(f"   Number of copies: {dup['copy_count']}")
        lines.append(f"   Redundant space: {format_size(dup['redundant_size'])}")
        lines.append(f"   Locations:")
        for loc in dup['locations']:
            lines.append(f"     - {loc['volume']}: {loc['path']}")

    lines.append("")

    # Files with most copies
    lines.append(f"TOP {top_n} FILES WITH MOST COPIES")
    lines.append("-" * 80)

    sorted_by_copies = sorted(
        duplicates.values(),
        key=lambda x: x['copy_count'],
        reverse=True
    )

    for i, dup in enumerate(sorted_by_copies[:top_n], 1):
        lines.append(f"\n{i}. {dup['filename']}")
        lines.append(f"   Number of copies: {dup['copy_count']}")
        lines.append(f"   File size: {format_size(dup['size'])}")
        lines.append(f"   Redundant space: {format_size(dup['redundant_size'])}")
        lines.append(f"   Locations:")
        for loc in dup['locations']:
            lines.append(f"     - {loc['volume']}: {loc['path']}")

    lines.append("")

    # Breakdown by volume
    lines.append("REDUNDANCY BY VOLUME")
    lines.append("-" * 80)

    volume_stats = {}
    for dup in duplicates.values():
        for loc in dup['locations']:
            volume = loc['volume']
            if volume not in volume_stats:
                volume_stats[volume] = {'duplicate_count': 0, 'redundant_size': 0}
            volume_stats[volume]['duplicate_count'] += 1
            # This file on this volume is redundant if it exists elsewhere
            if dup['copy_count'] > 1:
                volume_stats[volume]['redundant_size'] += dup['size']

    lines.append("")
    for volume in sorted(volume_stats.keys()):
        stats = volume_stats[volume]
        lines.append(f"{volume}:")
        lines.append(f"  Duplicate files: {stats['duplicate_count']:,}")
        lines.append(f"  Potential space to free: {format_size(stats['redundant_size'])}")
        lines.append("")

    lines.append("=" * 80)

    report_text = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_text)
        print(f"\nReport saved to: {output_path}")

    return report_text


def generate_consolidation_report(consolidation_plan_path: str,
                                  output_path: Optional[str] = None) -> str:
    """
    Generate a human-readable report from a consolidation plan JSON file.

    Args:
        consolidation_plan_path: Path to consolidation plan JSON file
        output_path: Optional path to save the report (if None, returns as string)

    Returns:
        The report as a string
    """
    print(f"Loading consolidation plan: {consolidation_plan_path}")
    data = load_json(consolidation_plan_path)

    lines = []
    lines.append("=" * 80)
    lines.append("CONSOLIDATION PLAN REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Summary section
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Plan timestamp: {data.get('plan_timestamp', 'N/A')}")
    lines.append("")
    lines.append(f"Total unique files: {data.get('total_unique_files', 0):,}")
    lines.append(f"Total size needed: {format_size(data.get('total_size_needed', 0))}")
    lines.append(f"Drives required: {data.get('drives_required', 0)} of {data.get('drives_available', 0)}")
    lines.append(f"Space saved: {format_size(data.get('space_saved', 0))}")
    lines.append("")

    # Drive recommendations
    lines.append("DRIVE RECOMMENDATIONS")
    lines.append("-" * 80)

    recommendations = data.get('recommendations', [])

    for rec in recommendations:
        lines.append("")
        lines.append(f"Volume: {rec['volume']}")
        lines.append(f"  Capacity: {format_size(rec['capacity'])}")
        lines.append(f"  Target used: {format_size(rec['target_used'])} ({rec['utilization_percent']:.1f}%)")
        lines.append(f"  Target available: {format_size(rec['target_available'])}")
        lines.append(f"  Files to keep: {rec['files_to_keep_count']:,}")
        lines.append(f"  Files to delete: {rec['files_to_delete_count']:,}")

        # Show sample of files to delete if there are any
        if rec['files_to_delete_count'] > 0:
            lines.append(f"  Sample files to delete (first 10):")
            for path in rec['files_to_delete'][:10]:
                lines.append(f"    - {path}")
            if rec['files_to_delete_count'] > 10:
                lines.append(f"    ... and {rec['files_to_delete_count'] - 10} more")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    lines.append("NOTE: This is a recommendation only. Review carefully before taking action.")
    lines.append("Always ensure you have backups before deleting files.")
    lines.append("")

    report_text = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_text)
        print(f"\nReport saved to: {output_path}")

    return report_text


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.report <json_file> [-o output.txt] [--top N]")
        sys.exit(1)

    json_file = sys.argv[1]
    output_file = None
    top_n = 20

    # Parse optional arguments
    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    if '--top' in sys.argv:
        idx = sys.argv.index('--top')
        if idx + 1 < len(sys.argv):
            try:
                top_n = int(sys.argv[idx + 1])
            except ValueError:
                print("Warning: Invalid --top value, using default (20)")

    # Determine report type based on content
    try:
        data = load_json(json_file)

        if 'duplicates' in data:
            report = generate_duplicate_report(json_file, output_file, top_n)
        elif 'recommendations' in data:
            report = generate_consolidation_report(json_file, output_file)
        else:
            print("Error: Unknown JSON format")
            sys.exit(1)

        if not output_file:
            print(report)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
