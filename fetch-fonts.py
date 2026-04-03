#!/usr/bin/env python3
import os
import subprocess
import tempfile
import shutil
import re

try:
    from environment import OVERLEAF_TOKEN, OVERLEAF_PROJECT_ID
except ImportError:
    OVERLEAF_TOKEN = ""
    OVERLEAF_PROJECT_ID = ""

# Repository root and key file paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
STYLE_FILE = os.path.join(REPO_ROOT, "00-shared", "config", "preamble-shared.sty")
TARGET_DIR = os.path.join(REPO_ROOT, "00-shared", "fonts")
BACKUP_FILE = STYLE_FILE + ".bak"
MARKER_FILE = os.path.join(REPO_ROOT, ".fonts_fetched")  # Marker for successful fetch
ENV_PATH = os.path.join(REPO_ROOT, ".env")


def log(msg: str):
    print(f"[Pre-build] {msg}")


def get_overleaf_url():
    # Build the Overleaf git URL from env vars
    token = OVERLEAF_TOKEN
    project = OVERLEAF_PROJECT_ID

    if not project or not token:
        return None

    return f"https://git:{token}@git.overleaf.com/{project}"


# Regex to locate font configuration block
FONT_BLOCK_PATTERN = re.compile(
    r"(%{5,}\n%%% Fonts.*?)(\\newfontfamily\\notefont\{.*?\}.*?\])",
    re.DOTALL
)

# Fallback font setup
FALLBACK_CONTENT = r"""
%%%%%%%%%%%%%%%%%%%%%%
%%% Fonts Fallback %%%
%%%%%%%%%%%%%%%%%%%%%%

\usepackage{fontspec,xltxtra,xunicode}
\defaultfontfeatures{Mapping=tex-text}

\IfFontExistsTF{TeX Gyre Heros}{
    \setmainfont{TeX Gyre Heros}
    \setmonofont{TeX Gyre Heros}
    \newfontfamily\notefont{TeX Gyre Heros}
}{
    \setmainfont{Helvetica}
    \setmonofont{Helvetica}
    \newfontfamily\notefont{Helvetica}
}

""".strip()


def clone_fonts():
    # Try to clone fonts from Overleaf into TARGET_DIR
    # Skip fetch if fonts folder exists and is not empty
    if os.path.exists(TARGET_DIR) and os.listdir(TARGET_DIR):
        log(f"Fonts already exist in {TARGET_DIR}, skipping fetch.")
        # Still write marker to indicate fonts are "available"
        with open(MARKER_FILE, "w") as f:
            f.write("ok")
        return True

    git_url = get_overleaf_url()
    if not git_url:
        log("⚠️ Failed to set the Overleaf project. Cannot fetch official fonts.")
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = os.path.join(tmpdir, "project")
        try:
            subprocess.run(
                ["git", "clone", git_url, project_dir],
                check=True
            )
            fonts_src = os.path.join(project_dir, "fonts")
            if os.path.exists(fonts_src):
                if os.path.exists(TARGET_DIR):
                    shutil.rmtree(TARGET_DIR)
                shutil.copytree(fonts_src, TARGET_DIR)
                log(f"✅ Fonts copied to {TARGET_DIR}")

                # Write marker to indicate fetch succeeded
                with open(MARKER_FILE, "w") as f:
                    f.write("ok")
                return True
        except subprocess.CalledProcessError:
            log("⚠️ Unable to fetch fonts from Overleaf.")
    return False


def apply_fallback():
    # Replace font block with fallback if fonts cannot be fetched
    if not os.path.exists(STYLE_FILE):
        log(f"⚠️ Style file not found: {STYLE_FILE}")
        return None

    shutil.copy2(STYLE_FILE, BACKUP_FILE) # Backup

    with open(STYLE_FILE, "r", encoding="utf-8") as f:
        original_content = f.read()

    new_content, count = FONT_BLOCK_PATTERN.subn(lambda m: FALLBACK_CONTENT, original_content)
    if count > 0:
        with open(STYLE_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
            f.flush()
            os.fsync(f.fileno())
        log("Fallback fonts configured in preamble-shared.sty.")
        log("⚠️ The compiled PDF will look different from the public version.")
        return original_content
    return None


def main():
    # Try fetching fonts; if failed, apply fallback
    fonts_fetched = clone_fonts()
    if not fonts_fetched:
        apply_fallback()


if __name__ == "__main__":
    main()
