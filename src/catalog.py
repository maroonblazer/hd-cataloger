"""Module for scanning drives and creating file catalogs."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def get_volume_label(drive_path: str) -> str:
    """
    Extract volume label from drive path.

    On macOS, drives are typically mounted at /Volumes/<volume_name>

    Args:
        drive_path: Path to the drive

    Returns:
        Volume label/name
    """
    path = Path(drive_path).resolve()

    # Check if path is under /Volumes/
    if '/Volumes/' in str(path):
        parts = str(path).split('/Volumes/')
        if len(parts) > 1:
            volume_name = parts[1].split('/')[0]
            return volume_name

    # Otherwise, use the basename of the path
    return path.name if path.name else 'unknown_volume'


def scan_drive(drive_path: str, output_dir: str = 'catalogs', include_hidden: bool = False) -> Dict:
    """
    Scan a drive and create a catalog of all files.

    Args:
        drive_path: Path to the drive to scan
        output_dir: Directory where catalog JSON will be saved
        include_hidden: Whether to include hidden files and directories (default: False)

    Returns:
        Dictionary containing the catalog data
    """
    drive_path = os.path.abspath(drive_path)

    if not os.path.exists(drive_path):
        raise FileNotFoundError(f"Drive path does not exist: {drive_path}")

    if not os.path.isdir(drive_path):
        raise NotADirectoryError(f"Path is not a directory: {drive_path}")

    volume_label = get_volume_label(drive_path)
    catalog_data = {
        'volume_label': volume_label,
        'scan_path': drive_path,
        'scan_timestamp': datetime.now().isoformat(),
        'files': []
    }

    print(f"Scanning drive: {volume_label}")
    print(f"Path: {drive_path}")

    file_count = 0
    total_size = 0

    # Walk through all directories and files
    for root, dirs, files in os.walk(drive_path):
        # Skip hidden directories (starting with .) unless include_hidden is True
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            # Skip hidden files unless include_hidden is True
            if not include_hidden and filename.startswith('.'):
                continue

            file_path = os.path.join(root, filename)

            try:
                file_size = os.path.getsize(file_path)

                file_entry = {
                    'filename': filename,
                    'path': file_path,
                    'size': file_size
                }

                catalog_data['files'].append(file_entry)
                file_count += 1
                total_size += file_size

                if file_count % 1000 == 0:
                    print(f"  Scanned {file_count} files...")

            except (OSError, IOError) as e:
                print(f"  Warning: Could not access {file_path}: {e}")
                continue

    catalog_data['total_files'] = file_count
    catalog_data['total_size'] = total_size

    print(f"\nScan complete!")
    print(f"  Files found: {file_count:,}")
    print(f"  Total size: {format_size(total_size)}")

    # Save catalog to JSON file
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{volume_label}_catalog.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w') as f:
        json.dump(catalog_data, f, indent=2)

    print(f"\nCatalog saved to: {output_path}")

    return catalog_data


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.catalog <drive_path> [--include-hidden]")
        sys.exit(1)

    drive_path = sys.argv[1]
    include_hidden = '--include-hidden' in sys.argv
    scan_drive(drive_path, include_hidden=include_hidden)
