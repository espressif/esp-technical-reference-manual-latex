#!/usr/bin/env python3
import os
import sys

# File extensions considered proprietary (case-insensitive)
PROPRIETARY_EXTS = [
    ".odg", ".drawio", ".graffle", ".dia", ".svg", ".csv", ".key", ".zip", ".ods", ".docx", ".html", ".otg"
]

# Always resolve paths relative to repo root (avoid pre-commit tmp dir issue)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_proprietary(file_path: str) -> bool:
    """Return True if the file has a proprietary extension."""
    return any(file_path.lower().endswith(ext) for ext in PROPRIETARY_EXTS)

def scan_path(path: str):
    """
    Scan a single file or directory:
      - If it's a file, check if it's proprietary.
      - If it's a directory, recursively scan all files inside.
    Returns a list of detected proprietary file paths.
    """
    found = []
    if os.path.isfile(path):
        if is_proprietary(path):
            found.append(os.path.relpath(path, REPO_ROOT))
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for f in files:
                full_path = os.path.join(root, f)
                if is_proprietary(full_path):
                    found.append(os.path.relpath(full_path, REPO_ROOT))
    return found

def main():
    args = sys.argv[1:]
    paths = []
    delete_mode = os.getenv("CI") != "true"

    # Parse args
    for arg in args:
        paths.append(arg)

    found = []
    if paths:
        for path in paths:
            abs_path = os.path.join(REPO_ROOT, path)
            if os.path.exists(abs_path):
                found.extend(scan_path(abs_path))
    else:
        found.extend(scan_path(REPO_ROOT))

    if found:
        if delete_mode:
            print("\033[0;31mProprietary files detected and deleted:\033[0m")
            for f in found:
                print(f"  {f}")
                try:
                    os.remove(os.path.join(REPO_ROOT, f))
                except Exception as e:
                    print(f"  [Error] Could not delete {f}: {e}")
        else:
            print("\033[0;31mProprietary files detected:\033[0m")
            for f in found:
                print(f"  {f}")
        sys.exit(1)
    else:
        print("No proprietary files found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
