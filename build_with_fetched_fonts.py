#!/usr/bin/env python3
import subprocess
import sys
import os

# Repository root and script paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
FETCH_FONTS_SCRIPT = os.path.join(REPO_ROOT, "fetch-fonts.py")
RESTORE_FONTS_SCRIPT = os.path.join(REPO_ROOT, "restore-fonts.py")


def run(cmd, description=None, exit_on_fail=True):
    # Run a command and print status. Exit if requested on failure
    if description:
        print(f"{description}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Done: {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        if exit_on_fail:
            sys.exit(e.returncode)
        return False


def main():

    # Require the root TeX file as input (e.g., main.tex or subfile.tex)
    if len(sys.argv) < 2:
        print("Usage: python3 build_with_fetched_fonts.py <main-tex-file>")
        sys.exit(1)

    main_tex = sys.argv[1]

    try:
        # Step 1: Try to fetch fonts from Overleaf repository
        # If fetching fails (no permissions, offline, etc.), use fallback fonts
        run(["python3", FETCH_FONTS_SCRIPT], description="Setting official or fallback fonts...", exit_on_fail=False)

        # Step 2: Compile LaTeX document with latexmk
        latex_cmd = [
            "latexmk",
            "-cd",
            "-r",
            "../latexmkrc",
            "-outdir=./out",
            "-pdf",
            "-shell-escape",
            "-halt-on-error",           # Stops on the first error
            "-interaction=nonstopmode", # Avoids interactive prompts
            main_tex
        ]
        print(f"Compiling LaTeX: {' '.join(latex_cmd)}")

        try:
            subprocess.run(latex_cmd, check=True)
            print("✅ LaTeX compilation finished successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ LaTeX compilation failed with exit code {e.returncode}.")
            sys.exit(e.returncode)

    finally:
        # Step 3: Always restore the original font configuration,
        # regardless of whether compilation succeeded or failed
        run(["python3", RESTORE_FONTS_SCRIPT], description="Restoring official fonts if needed...", exit_on_fail=False)


if __name__ == "__main__":
    main()
