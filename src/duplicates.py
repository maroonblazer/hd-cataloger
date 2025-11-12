"""Module for finding duplicate files across catalogs."""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime


def load_catalog(catalog_path: str) -> Dict:
    """
    Load a catalog JSON file.

    Args:
        catalog_path: Path to the catalog JSON file

    Returns:
        Dictionary containing catalog data
    """
    if not os.path.exists(catalog_path):
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    with open(catalog_path, 'r') as f:
        return json.load(f)


def find_duplicates(catalog_paths: List[str], output_path: str = None) -> Dict:
    """
    Find duplicate files across multiple catalogs.

    Duplicates are identified by matching (size, filename) tuples.

    Args:
        catalog_paths: List of paths to catalog JSON files
        output_path: Optional path to save the duplicate report

    Returns:
        Dictionary containing duplicate analysis
    """
    print(f"Loading {len(catalog_paths)} catalog(s)...")

    # Load all catalogs
    catalogs = []
    for path in catalog_paths:
        try:
            catalog = load_catalog(path)
            catalogs.append(catalog)
            print(f"  Loaded: {catalog['volume_label']} ({catalog['total_files']:,} files)")
        except Exception as e:
            print(f"  Error loading {path}: {e}")
            continue

    if len(catalogs) < 2:
        print("\nError: Need at least 2 catalogs to find duplicates")
        return {}

    print("\nAnalyzing files for duplicates...")

    # Group files by (size, filename)
    file_groups = defaultdict(list)

    for catalog in catalogs:
        volume_label = catalog['volume_label']

        for file_entry in catalog['files']:
            key = (file_entry['size'], file_entry['filename'])

            file_groups[key].append({
                'volume': volume_label,
                'path': file_entry['path'],
                'size': file_entry['size'],
                'filename': file_entry['filename']
            })

    # Find duplicates (files that appear on multiple drives)
    duplicates = {}
    total_redundant_size = 0
    duplicate_count = 0

    for key, locations in file_groups.items():
        if len(locations) > 1:
            size, filename = key
            duplicate_count += 1

            # Redundant size = (number of copies - 1) * file size
            redundant_size = (len(locations) - 1) * size
            total_redundant_size += redundant_size

            duplicates[f"{filename}_{size}"] = {
                'filename': filename,
                'size': size,
                'copy_count': len(locations),
                'redundant_size': redundant_size,
                'locations': locations
            }

    # Create report
    report = {
        'analysis_timestamp': datetime.now().isoformat(),
        'catalogs_analyzed': [cat['volume_label'] for cat in catalogs],
        'total_unique_files': len(file_groups),
        'duplicate_file_count': duplicate_count,
        'total_redundant_size': total_redundant_size,
        'duplicates': duplicates
    }

    # Print summary
    print(f"\nDuplicate Analysis Complete!")
    print(f"  Total unique files: {len(file_groups):,}")
    print(f"  Duplicate files found: {duplicate_count:,}")
    print(f"  Total redundant space: {format_size(total_redundant_size)}")

    # Print top duplicates by redundant size
    if duplicates:
        print(f"\nTop 10 duplicates by redundant space:")
        sorted_dups = sorted(
            duplicates.values(),
            key=lambda x: x['redundant_size'],
            reverse=True
        )

        for i, dup in enumerate(sorted_dups[:10], 1):
            print(f"  {i}. {dup['filename']}")
            print(f"     Size: {format_size(dup['size'])}, Copies: {dup['copy_count']}, "
                  f"Redundant: {format_size(dup['redundant_size'])}")

    # Save report if output path specified
    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDuplicate report saved to: {output_path}")
    else:
        # Default output path
        default_output = 'catalogs/duplicate_report.json'
        with open(default_output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDuplicate report saved to: {default_output}")

    return report


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m src.duplicates <catalog1.json> <catalog2.json> [catalog3.json ...]")
        sys.exit(1)

    catalog_paths = sys.argv[1:]
    find_duplicates(catalog_paths)
