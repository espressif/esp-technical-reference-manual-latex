#!/usr/bin/env python3
import os
import shutil

# Repository root and key file paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
STYLE_FILE = os.path.join(REPO_ROOT, "00-shared", "config", "preamble-shared.sty")
BACKUP_FILE = STYLE_FILE + ".bak"
MARKER_FILE = os.path.join(REPO_ROOT, ".fonts_fetched")  # Marker created when fetch succeeds


def log(msg: str):
    print(f"[Post-build] {msg}")


def restore_fonts():
    # Restore original style file from backup if it exists

    if os.path.exists(MARKER_FILE):
        log("Fonts were fetched successfully. No restore needed.")
        # Clean up marker for next run
        os.remove(MARKER_FILE)
        return
    if os.path.exists(BACKUP_FILE):
        shutil.move(BACKUP_FILE, STYLE_FILE)
        log("Fonts restored in preamble-shared.sty.")
    else:
        log("⚠️ No backup found. Nothing to restore.")


if __name__ == "__main__":
    restore_fonts()
