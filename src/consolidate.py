"""Module for planning file consolidation across drives."""

import json
import os
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict


def load_json(file_path: str) -> Dict:
    """Load a JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        return json.load(f)


def get_drive_capacities(catalog_paths: List[str]) -> Dict[str, Dict]:
    """
    Get capacity information for each drive from catalogs.

    Args:
        catalog_paths: List of paths to catalog JSON files

    Returns:
        Dictionary mapping volume labels to capacity info
    """
    capacities = {}

    for path in catalog_paths:
        catalog = load_json(path)
        volume = catalog['volume_label']

        capacities[volume] = {
            'current_used': catalog['total_size'],
            'file_count': catalog['total_files']
        }

    return capacities


def plan_consolidation(duplicate_report_path: str, catalog_paths: List[str],
                       drive_capacities: Dict[str, int] = None,
                       output_path: str = None) -> Dict:
    """
    Create a consolidation plan to minimize the number of drives in use.

    Args:
        duplicate_report_path: Path to the duplicate report JSON
        catalog_paths: List of paths to catalog JSON files
        drive_capacities: Optional dict mapping volume labels to total capacity in bytes
        output_path: Optional path to save the consolidation plan

    Returns:
        Dictionary containing the consolidation plan
    """
    print("Loading duplicate report and catalogs...")

    # Load duplicate report
    dup_report = load_json(duplicate_report_path)

    # Load all catalogs
    catalogs = {}
    for path in catalog_paths:
        catalog = load_json(path)
        catalogs[catalog['volume_label']] = catalog
        print(f"  Loaded catalog: {catalog['volume_label']}")

    if not catalogs:
        print("Error: No catalogs loaded")
        return {}

    print("\nAnalyzing files for consolidation...")

    # Build a comprehensive file inventory
    # For duplicates, we'll track all locations
    # For unique files, we'll track their single location

    file_inventory = {}  # (size, filename) -> list of locations
    duplicates_set = set()

    # Add all duplicates
    for dup_key, dup_info in dup_report.get('duplicates', {}).items():
        key = (dup_info['size'], dup_info['filename'])
        file_inventory[key] = dup_info['locations']
        duplicates_set.add(key)

    # Add all unique files (not in duplicates)
    for volume, catalog in catalogs.items():
        for file_entry in catalog['files']:
            key = (file_entry['size'], file_entry['filename'])

            if key not in duplicates_set:
                if key not in file_inventory:
                    file_inventory[key] = []

                file_inventory[key].append({
                    'volume': volume,
                    'path': file_entry['path'],
                    'size': file_entry['size'],
                    'filename': file_entry['filename']
                })

    print(f"  Total unique files: {len(file_inventory):,}")

    # Create list of unique files with their total size
    unique_files = []
    for key, locations in file_inventory.items():
        size, filename = key
        unique_files.append({
            'filename': filename,
            'size': size,
            'is_duplicate': len(locations) > 1,
            'copy_count': len(locations),
            'locations': locations
        })

    # Sort files by size (largest first) for better bin packing
    unique_files.sort(key=lambda x: x['size'], reverse=True)

    # Get or estimate drive capacities
    if drive_capacities is None:
        drive_capacities = {}
        print("\nNote: Drive capacities not provided. Using current usage as minimum capacity.")
        for volume, catalog in catalogs.items():
            drive_capacities[volume] = catalog['total_size']

    # Initialize drives with their capacities
    drives = {}
    for volume in catalogs.keys():
        capacity = drive_capacities.get(volume, catalogs[volume]['total_size'])
        drives[volume] = {
            'capacity': capacity,
            'used': 0,
            'available': capacity,
            'files_to_keep': []
        }

    # Bin packing: assign each file to a drive
    print("\nPlanning file assignments...")

    total_size_needed = sum(f['size'] for f in unique_files)
    files_assigned = 0

    for file_info in unique_files:
        # Try to find a drive that has enough space
        assigned = False

        # Sort drives by available space (use fuller drives first)
        sorted_drives = sorted(drives.items(), key=lambda x: x[1]['available'], reverse=True)

        for volume, drive_info in sorted_drives:
            if drive_info['available'] >= file_info['size']:
                # Assign file to this drive
                drive_info['files_to_keep'].append(file_info)
                drive_info['used'] += file_info['size']
                drive_info['available'] -= file_info['size']
                assigned = True
                files_assigned += 1
                break

        if not assigned:
            print(f"  Warning: Could not assign {file_info['filename']} ({format_size(file_info['size'])})")

    # Determine which drives are in use
    drives_in_use = [v for v, d in drives.items() if d['used'] > 0]

    print(f"\nConsolidation Plan Complete!")
    print(f"  Total unique files: {len(unique_files):,}")
    print(f"  Files assigned: {files_assigned:,}")
    print(f"  Total size needed: {format_size(total_size_needed)}")
    print(f"  Drives required: {len(drives_in_use)} of {len(drives)}")

    # Generate detailed recommendations
    recommendations = []

    for volume in drives_in_use:
        drive_info = drives[volume]
        print(f"\n  Drive: {volume}")
        print(f"    Capacity: {format_size(drive_info['capacity'])}")
        print(f"    Will use: {format_size(drive_info['used'])} ({drive_info['used'] / drive_info['capacity'] * 100:.1f}%)")
        print(f"    Files to keep: {len(drive_info['files_to_keep']):,}")

        # Determine which files to keep vs. delete
        files_to_keep = set()
        for file_info in drive_info['files_to_keep']:
            for loc in file_info['locations']:
                if loc['volume'] == volume:
                    files_to_keep.add(loc['path'])

        # Get all files currently on this drive
        current_files = set()
        for file_entry in catalogs[volume]['files']:
            current_files.add(file_entry['path'])

        # Files to delete = current files - files to keep
        files_to_delete = current_files - files_to_keep

        recommendations.append({
            'volume': volume,
            'capacity': drive_info['capacity'],
            'target_used': drive_info['used'],
            'target_available': drive_info['available'],
            'utilization_percent': (drive_info['used'] / drive_info['capacity'] * 100) if drive_info['capacity'] > 0 else 0,
            'files_to_keep_count': len(files_to_keep),
            'files_to_delete_count': len(files_to_delete),
            'files_to_keep': sorted(list(files_to_keep)),
            'files_to_delete': sorted(list(files_to_delete))
        })

    # Create consolidation plan
    plan = {
        'plan_timestamp': datetime.now().isoformat(),
        'duplicate_report': duplicate_report_path,
        'catalogs_analyzed': list(catalogs.keys()),
        'total_unique_files': len(unique_files),
        'total_size_needed': total_size_needed,
        'drives_required': len(drives_in_use),
        'drives_available': len(drives),
        'space_saved': dup_report.get('total_redundant_size', 0),
        'recommendations': recommendations
    }

    # Save plan
    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(plan, f, indent=2)
        print(f"\nConsolidation plan saved to: {output_path}")
    else:
        default_output = 'catalogs/consolidation_plan.json'
        with open(default_output, 'w') as f:
            json.dump(plan, f, indent=2)
        print(f"\nConsolidation plan saved to: {default_output}")

    return plan


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m src.consolidate <duplicate_report.json> <catalog1.json> <catalog2.json> [...]")
        sys.exit(1)

    dup_report_path = sys.argv[1]
    catalog_paths = sys.argv[2:]

    plan_consolidation(dup_report_path, catalog_paths)
