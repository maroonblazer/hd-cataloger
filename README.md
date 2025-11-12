# HD Cataloger

A Python tool for cataloging and consolidating files across multiple external hard drives.

## Overview

HD Cataloger helps you manage large collections of files spread across multiple external drives by:

1. **Cataloging** - Scanning drives and creating detailed inventories of all files
2. **Finding Duplicates** - Identifying files that exist on multiple drives (by size + filename)
3. **Planning Consolidation** - Recommending how to consolidate files to minimize the number of drives needed

## Features

- **Fast scanning** - Efficiently walks directory trees and catalogs file metadata
- **Duplicate detection** - Identifies duplicate files by matching size and filename
- **Smart consolidation** - Uses bin-packing algorithm to minimize drives needed
- **Read-only analysis** - Never modifies your files, only provides recommendations
- **JSON output** - All reports in easy-to-read JSON format
- **macOS optimized** - Designed for macOS external drive management

## Installation

### Prerequisites

- Python 3.7 or higher
- macOS (tool is optimized for macOS drive management)

### Setup

1. Clone or download this repository
2. No external dependencies required - uses Python standard library only!

```bash
cd hd-cataloger
python3 main.py --help
```

## Usage

### Workflow

The typical workflow involves three steps:

1. **Catalog each drive** - Creates JSON files with file inventories
2. **Find duplicates** - Analyzes catalogs to identify duplicate files
3. **Plan consolidation** - Generates recommendations for file consolidation

### Step 1: Catalog Your Drives

Scan each external drive to create a catalog:

```bash
python3 main.py catalog /Volumes/MyDrive1
python3 main.py catalog /Volumes/MyDrive2
python3 main.py catalog /Volumes/MyDrive3
```

**For Time Machine backups:** Time Machine stores backups in hidden directories (starting with `.`). Use the `--include-hidden` flag to scan these:

```bash
python3 main.py catalog /Volumes/.timemachine --include-hidden
```

This creates catalog files in the `catalogs/` directory:
- `MyDrive1_catalog.json`
- `MyDrive2_catalog.json`
- `MyDrive3_catalog.json`

Each catalog contains:
- Volume label
- Scan timestamp
- List of all files with paths and sizes
- Total file count and size

### Step 2: Find Duplicates

Analyze multiple catalogs to find duplicate files:

```bash
python3 main.py find-duplicates catalogs/MyDrive1_catalog.json catalogs/MyDrive2_catalog.json catalogs/MyDrive3_catalog.json
```

Or use a wildcard to include all catalogs:

```bash
python3 main.py find-duplicates catalogs/*_catalog.json
```

This creates `catalogs/duplicate_report.json` containing:
- List of all duplicate files
- Number of copies of each duplicate
- Total redundant space consumed
- All locations where each duplicate exists

### Step 3: Plan Consolidation

Generate a consolidation plan to minimize drives needed:

```bash
python3 main.py consolidate catalogs/duplicate_report.json catalogs/*_catalog.json
```

Optionally specify drive capacities (in GB):

```bash
python3 main.py consolidate catalogs/duplicate_report.json catalogs/*_catalog.json \
  --capacities MyDrive1:2000 MyDrive2:4000 MyDrive3:1000
```

This creates `catalogs/consolidation_plan.json` containing:
- Number of drives required
- For each drive:
  - Files to keep
  - Files to delete
  - Expected utilization
- Total space that will be saved

## Command Reference

### catalog

Scan a drive and create a file catalog.

```bash
python3 main.py catalog <drive_path> [options]
```

**Arguments:**
- `drive_path` - Path to the drive (e.g., `/Volumes/MyDrive`)

**Options:**
- `-o, --output-dir` - Directory to save catalog files (default: `catalogs`)
- `--include-hidden` - Include hidden files and directories (useful for Time Machine backups)

**Examples:**
```bash
# Scan a regular drive
python3 main.py catalog /Volumes/Backup2024

# Scan a Time Machine backup with hidden files
python3 main.py catalog /Volumes/.timemachine --include-hidden
```

### find-duplicates

Find duplicate files across multiple catalogs.

```bash
python3 main.py find-duplicates <catalog1> <catalog2> [...] [options]
```

**Arguments:**
- `catalogs` - Paths to catalog JSON files (minimum 2 required)

**Options:**
- `-o, --output` - Path to save duplicate report (default: `catalogs/duplicate_report.json`)

**Example:**
```bash
python3 main.py find-duplicates catalogs/*.json -o my_duplicates.json
```

### consolidate

Plan file consolidation to minimize drives needed.

```bash
python3 main.py consolidate <duplicate_report> <catalog1> <catalog2> [...] [options]
```

**Arguments:**
- `duplicate_report` - Path to duplicate report JSON file
- `catalogs` - Paths to catalog JSON files

**Options:**
- `-c, --capacities` - Drive capacities in format `VolumeName:SizeInGB`
- `-o, --output` - Path to save consolidation plan (default: `catalogs/consolidation_plan.json`)

**Example:**
```bash
python3 main.py consolidate catalogs/duplicate_report.json catalogs/*.json \
  --capacities Drive1:2000 Drive2:4000 Drive3:1000
```

## How It Works

### Duplicate Detection

Files are considered duplicates if they have:
1. **Same size** (in bytes)
2. **Same filename**

This method is fast and works well for most use cases. It doesn't use file hashing, so it won't detect files that have been renamed but have identical content.

### Consolidation Algorithm

The consolidation planner uses a **bin-packing algorithm** to efficiently assign files to drives:

1. Creates a list of all unique files (removing duplicates)
2. Sorts files by size (largest first)
3. Assigns each file to the first drive that has enough space
4. Generates recommendations showing which files to keep/delete on each drive

The goal is to **minimize the number of drives in use** while ensuring at least one copy of every file is preserved.

### Safety Features

- **Read-only operations** - Never modifies your actual files
- **Skips hidden files** - Ignores files and directories starting with `.`
- **Error handling** - Continues scanning even if some files are inaccessible
- **Preserves data** - Always keeps at least one copy of each file

## Output Format

### Catalog File

```json
{
  "volume_label": "MyDrive",
  "scan_path": "/Volumes/MyDrive",
  "scan_timestamp": "2025-11-12T10:30:00",
  "total_files": 15234,
  "total_size": 1234567890,
  "files": [
    {
      "filename": "document.pdf",
      "path": "/Volumes/MyDrive/Documents/document.pdf",
      "size": 1024000
    }
  ]
}
```

### Duplicate Report

```json
{
  "analysis_timestamp": "2025-11-12T10:35:00",
  "catalogs_analyzed": ["Drive1", "Drive2"],
  "total_unique_files": 20000,
  "duplicate_file_count": 500,
  "total_redundant_size": 50000000000,
  "duplicates": {
    "movie.mp4_1234567890": {
      "filename": "movie.mp4",
      "size": 1234567890,
      "copy_count": 2,
      "redundant_size": 1234567890,
      "locations": [...]
    }
  }
}
```

### Consolidation Plan

```json
{
  "plan_timestamp": "2025-11-12T10:40:00",
  "total_unique_files": 20000,
  "total_size_needed": 1500000000000,
  "drives_required": 2,
  "drives_available": 3,
  "space_saved": 50000000000,
  "recommendations": [
    {
      "volume": "Drive1",
      "capacity": 2000000000000,
      "target_used": 1000000000000,
      "utilization_percent": 50.0,
      "files_to_keep": [...],
      "files_to_delete": [...]
    }
  ]
}
```

## Tips

1. **Catalog regularly** - Re-scan drives periodically as you add files
2. **Backup first** - Before consolidating, ensure you have backups
3. **Check capacity** - Provide actual drive capacities with `--capacities` for accurate planning
4. **Review plans** - Always review consolidation plans before taking action
5. **Test with copies** - Test the consolidation process with non-critical data first
6. **Time Machine backups** - Use `--include-hidden` flag when cataloging Time Machine drives, as backups are stored in hidden directories (e.g., `/Volumes/.timemachine`)

## Limitations

- **Duplicate detection** - Only matches by size + filename, not content hash
- **No file moving** - Tool only provides recommendations, doesn't move files
- **macOS specific** - Volume detection optimized for macOS `/Volumes/` structure
- **No streaming** - Loads entire catalogs into memory (may be slow for millions of files)

## Troubleshooting

**Problem:** "Drive path does not exist"
- **Solution:** Ensure drive is mounted and path is correct (check `/Volumes/`)

**Problem:** "Permission denied" errors during scanning
- **Solution:** Some system files may be protected; the tool will skip them and continue

**Problem:** Time Machine drive shows 0 files found
- **Solution:** Time Machine backups are stored in hidden directories. Use `--include-hidden` flag and ensure you're pointing to the correct path (e.g., `/Volumes/.timemachine` instead of `/Volumes/timemachine`)

**Problem:** Consolidation plan shows "Could not assign file"
- **Solution:** Increase drive capacities or reduce the number of files to consolidate

## License

This tool is provided as-is for personal use.

## Contributing

Feel free to submit issues or pull requests with improvements!
