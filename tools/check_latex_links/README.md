# Check LaTeX Links

This script checks for broken links in esp-technical-reference-manual-latex documentation:
- **Internal links**: by extracting undefined and multiply defined labels from the log file
- **External links**: by scanning LaTeX source files for bad/malformed URLs

**Important**: Run this script only after successfully building the target chip documentation. The build must generate a log file (e.g., `ESP32-H4-main__EN.log` or `ESP32-H4-main__CN.log`) located at `<target_chip>/out/` before running this script.

## Usage

```bash
python3 tools/check_latex_links/check_latex_links.py <target> <lang> [-int | -ext | -all] [-reg]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `<target>` | Target name (e.g., ESP32-C5) |
| `<lang>` | Language code (EN or CN) |

## Options

| Option | Description |
|--------|-------------|
| `-int` | Check internal links only (skips register/field-related warnings by default) |
| `-ext` | Check external links only (includes malformed `\href` usage) |
| `-all` | Check both internal and external links |
| `-reg` | Include register/field-related label warnings (valid with `-int` or `-all`) |

**Note**: If no option is provided, the script runs with `-int` (excluding reg warnings) and `-ext`.

## Examples

```bash
# Default: internal (no reg) + external
python3 tools/check_latex_links/check_latex_links.py ESP32-H4 EN

# Internal only (no reg)
python3 tools/check_latex_links/check_latex_links.py ESP32-H4 CN -int

# Internal only (with reg)
python3 tools/check_latex_links/check_latex_links.py ESP32-H4 CN -int -reg

# External only
python3 tools/check_latex_links/check_latex_links.py ESP32-H4 CN -ext

# All checks
python3 tools/check_latex_links/check_latex_links.py ESP32-H4 CN -all
```

## Requirements

The script requires the following Python packages:
- `requests` - for checking external URLs

Install dependencies:
```bash
pip install requests
```

## How It Works

### Internal Link Checking
- Parses the LaTeX build log file (`.log`) for warnings
- Identifies undefined references and multiply-defined labels
- Filters out register/field-related warnings by default (unless `-reg` is specified)

### External Link Checking
- Scans all `.tex` files in the target directory
- Extracts URLs from `\href{}{}` and `\url{}` commands
- Validates each URL with HTTP requests (with retry logic)
- Reports broken or inaccessible links

## Output

The script provides clear status indicators:
- ✅ No issues found
- ⚠️ LaTeX warnings (for internal links)
- ❌ Broken external links (with file locations)
