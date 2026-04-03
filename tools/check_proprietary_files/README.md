# Check Proprietary Files

A Python script that detects and optionally deletes proprietary file types (e.g. `.docx`, `.drawio`, `.odg`) in the repository or in given file paths.

## Features

The script `check_proprietary_files.py`:
- Detects files with proprietary extensions including but not limited to:
  - .odg, .drawio, .graffle, .dia, .svg, .csv, .key, .zip, .ods, .docx, .html
- Works on both:
  - The entire repository if no paths are provided
  - Specific files or directories
- Supports delete mode `-d` to remove detected files

## Usage

You can use this script to scan your repository for proprietary file types or automatically remove them.
It supports both full-repo scans and specific file/directory checks.

### Check the Entire Repository

Scans the whole repository recursively and lists any proprietary files found.

```bash
python3 tools/check_proprietary_files/check_proprietary_files.py
```

### Check Specific Files or Directories

Scans only the specified files or folders instead of the entire repository.

```bash
python3 tools/check_proprietary_files/check_proprietary_files.py path/to/file1 path/to/dir2
```

### Delete Detected Proprietary Files

Scans and automatically deletes any proprietary files found.


```bash
python3 tools/check_proprietary_files/check_proprietary_files.py -d path/to/dir
```
