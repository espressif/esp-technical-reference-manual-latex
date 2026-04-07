# Espressif Technical Reference Manuals in LaTeX

This repository contains LaTeX sources and helper scripts for developing and building Espressif Technical Reference Manuals (TRMs).

Currently, TRMs for all chips except ESP8266 are hosted here.

> **Note**: The source code in this repository may be ahead of the published PDF version. The PDF is published periodically, and there could be a delay before recent changes are reflected.


## Table of Contents

- [Build Instructions](#build-instructions)
   - [Quick Start](#quick-start)
   - [Building Locally](#building-locally)
   - [Building in Dev Container](#building-in-dev-container)
   - [Build Artifacts](#build-artifacts)
   - [Building Without Proprietary Fonts](#building-without-proprietary-fonts)
- [Common Build Issues & Troubleshooting](#common-build-issues--troubleshooting)
   - [Package Minted Error](#package-minted-error)
   - [Recipe Termination Error](#recipe-termination-error)
   - [Missing Font Error](#missing-font-error)
   - [Ghostscript Initialization Error](#ghostscript-initialization-error)
- [Pre-Commit Hooks](#pre-commit-hooks)
   - [Features](#features)
   - [Install and Usage](#install-and-usage)
- [License](#license)
- [Feedback and Contribution](#feedback-and-contribution)


## Build Instructions

### Quick Start

You can build TRM PDFs either inside the provided Visual Studio Code Dev Container or locally with a TeX Live installation (often faster on macOS/Windows). Choose the approach that best fits your environment.

#### Requirements for Either Approach

1. Install [Visual Studio Code](https://code.visualstudio.com/Download).

   A quick way to open the content of a folder in VS Code from a terminal is:

   ```sh
   cd <repo-folder>
   code .
   ```

2. In VS Code, install these extensions:
   - [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
   - [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)

#### Recommended: VS Code Dev Container

Using the Dev Container gives you a reproducible environment with TeX Live and other build dependencies preinstalled.

1. Install [Docker Desktop](https://www.docker.com/).
2. Open the repository in VS Code and choose `Reopen in Container`.

   The first run will pull the image and may take several minutes. Subsequent opens are much faster.

   Each time the folder with a development container is opened, VS Code shows a notification offering to reopen the repository in the container. Accept it and wait for the process to finish. If you miss the notification, click the `><` box in the bottom-left corner and execute `Reopen in Container`.

#### Optional: Local TeX Live Installation

If you prefer to build locally, install TeX Live for your OS:

- macOS: MacTeX — https://tug.org/mactex/
- Windows/Linux: TeX Live — https://tug.org/texlive/

Note the full TeX Live installation is large (several GB).

### Building in Dev Container

1. Reopen repository in the Dev Container. See [Recommended: VS Code Dev Container](#recommended-vs-code-dev-container).
2. Use the same LaTeX Workshop build action in [Building Locally](#building-locally) inside the container.

### Building Locally

1. Open any module root `.tex` file, usually `ESP32-XX-main__EN.tex/...__CN.tex` under each chip folder.
2. Click the green build triangle `▷` on the right side of the top tab bar.
3. Monitor the build status on the left side of the bottom status bar. While building you will see the word `Build`; on completion you will see `✓` (success) or `✕` (failure).
4. Open the generated PDF from the editor by clicking the book icon next to the build triangle.

For more details about keyboard shortcuts, build recipes and configuration options, see the [LaTeX Workshop Wiki](https://github.com/James-Yu/LaTeX-Workshop/wiki).

### Build Artifacts

Each module’s build creates an `out/` subdirectory containing the PDF, logs, and other artifacts. This keeps source directories clean and is configured in `.vscode/settings.json`.

To view artifacts, click the `TEX` icon on the left side bar, then select `View log messages` > `View LaTeX compiler log`.

### Building Without Proprietary Fonts

TRM sources reference proprietary official fonts that cannot be distributed publicly.

The entry point for building documents is the script `build_with_fetched_fonts.py`. This script is referenced in `.vscode/settings.json`, so building locally with LaTeX Workshop will invoke it automatically.

To make building possible for external users, the build scripts include a fallback mechanism. When official fonts are not available, the build switches to common substitute fonts (TeX Gyre Heroes or Helvetica).

In this case, the PDF will build and the content will be correct, but visual appearance may differ from the published version.

Example log:

```sh
[Pre-build] ⚠️ Failed to set the Overleaf project. Cannot fetch official fonts.
[Pre-build] Fallback fonts configured in preamble-shared.sty.
[Pre-build] ⚠️ The compiled PDF will look different from the public version.
```

See where to find logs in Section [Build Artifacts](#build-artifacts).


## Common Build Issues & Troubleshooting

### Package Minted Error

During project compilation you may see the following error:

```
/Users/../esp-technical-reference-manual-latex/ESP32-S3/ESP32-S3-main__EN.tex:21: Package minted Error: You must have `pygmentize' installed to use this package.
```

If the issue occurs when using local TeX Live installation, open a terminal and run the command `pygmentize -V` to check if you have Python package `pytments` installed:

```
pygmentize -V
Pygments version 2.13.0, (c) 2006-2022 by Georg Brandl, Matthäus Chajdas and contributors.
```

If you get the message `command not found: pygmentize` then install the package by running `pip3 install pygments`.

For **Windows** users, if the `pip3` command is not recognized in your PowerShell environment, try to install [Python](https://www.python.org/downloads/) first then run `python -m pip install pygments`. You may also need to add the path to the package executable to the `$PATH` environment variable after the installation. A sample path looks like `C:\Users\username\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts`. To add executables to the `$PATH` environment variable, see [Recipe Termination Error](#recipe-termination-error).

Note that the [Docker](.devcontainer/Dockerfile) container included in this project already provides the missing package.


### Recipe Termination Error

During project compilation you may see another error:

```
LaTeX fatal error: spawn latexmk ENOENT, . PID: undefined.
```

If the issue occurs, add the path to TeX executables to the `$PATH` environment variable.

For **macOS** users, modify the configuration file in the home directory with text editors to include the path to TeX executables. Bash shell users may add `export PATH="/Library/TeX/texbin/:$PATH"` to the `.bashrc` file. Zsh shell users may add `export PATH="/Library/TeX/texbin/:$PATH"` to the `.zshrc` file.

For **Windows** users, open the `Start` menu and search for `Environment Variables`. Go to `Edit the system environment variables` > `Environment Variables`. In the `User variables` section, click `New`. Enter `TeX` for the variable name, and the path to the directory containing the TeX executables (e.g., C:\texlive\2022\bin\win32) for the variable value. Click `OK` to save the new variable.

Then restart VS Code and try to compile again.


### Missing Font Error

During the installation of TeX Live on your PC you may get errors of missing fonts. Install fonts that are missing.

For **Windows** users, if the following error pops up:

```
c:/texlive/2022/texmf-dist/tex/latex/ctex/fontset/ctex-fontset-windows.def:101: Package fontspec Error: The font "SimHei" cannot be found.
```

Under `Optional features`, install `Chinese (Simplified) Supplemental Fonts`. See [The font "SimHei" cannot be found](https://github.com/sjtug/SJTUThesis/issues/564) for details.


### Ghostscript Initialization Error

When compiling PDF documents using XeLaTeX, the following error may occur:

```
GPL Ghostscript 9.55.0: Can't find initialization file gs_init.ps.
xdvipdfmx:fatal: pdf_link_obj(): passed invalid object.
```

This happens when Ghostscript could not locate the required initialization file `gs_init.ps`. To solve it, set the `GS_LIB` environment variable permanently to point to the correct `gs_init.ps` directory.

**How to Find `gs_init.ps` Path**

Use the following command in your terminal to locate the file:

```
find /usr -name gs_init.ps 2>/dev/null
```

This will output a path similar to:

```
/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init/gs_init.ps
```

Copy the directory containing `gs_init.ps` (i.e., everything up to `/Init`).

**Set `GS_LIB` Environment Variable**

Set the `GS_LIB` variable to the directory you found above.

For Zsh:

```
echo 'export GS_LIB=/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init' >> ~/.zshrc
source ~/.zshrc
```

For Bash:

```
echo 'export GS_LIB=/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init' >> ~/.bashrc
source ~/.bashrc
```

Replace the path with the correct one on your system. Then restart VS Code and try to compile again.


## Pre-Commit Hooks

### Features

Pre-commit hooks help prevent sensitive or irrelevant content from entering the repository and catch common issues early. Typical checks included here:
- Detects and removes todo notes or commented code in `.tex` files.
- Detects and removes certain proprietary or binary file types (e.g., `.csv`, `.docx`, `.odg`, `.zip`).
- Detects and corrects common misspellings in various file types using codespell.
- Runs locally on staged files before commit as well as in CI.

### Install and Usage

1. Install `pre-commit`:
   ```sh
   pip install pre-commit
   ```

2. Enable hooks in the repository:
   ```sh
   pre-commit install
   ```

3. Normal workflow:
   ```sh
   git add <files>
   git commit -m "Your message"
   ```

   If a hook modifies staged files, the commit will be aborted. Re-stage and commit after reviewing the changes.

   Example log:

   ```sh
   Check todo notes or commented code.......................................Failed
   - hook id: check-todo-notes-commented-code
   - exit code: 1
   - files were modified by this hook

   processing file ESP8684/07-RESCLK__CN.tex
   Todo notes removed from line 2: \todoreminder{test}
   processing file ESP8684/07-RESCLK__EN.tex
   Commented code removed from line 2: %Test

   Check proprietary files..................................................Failed
   - hook id: check-proprietary-files
   - exit code: 1
   - files were modified by this hook

   Proprietary files detected and deleted:
      test.csv
      test.odg

   codespell................................................................Failed
   - hook id: check-proprietary-files
   - files were modified by this hook

   FIXED: README.md
   ```

4. Ignore specific code:
- To allow specific todo markers or commented snippets, add them to `./tools/check_todo_notes_commented_code/ignored_todo_notes_commented_code.txt`.

  Remember to commit this file so CI checks that also rely on it can pass.

- To allow specific spellings, add words to the `ignore-words-list` in `.codespellrc`.


## License

This repository is distributed under different licenses:
- All scripts are licensed under the [Apache License 2.0](./LICENSE-APACHE).
- All documentation is licensed under the [Creative Commons Attribution Share Alike 4.0 International (CC-BY-SA 4.0)](./LICENSE-CC-BY-SA).


## Feedback and Contribution

Espressif Documentation Team encourages contributions from the community to enhance and refine the Technical Reference Manual.

If you have insights, updates, or suggestions to share, feel free to:

- Leave a comment using the `Submit Documentation Feedback` button at the bottom of any [documentation page](https://documentation.espressif.com/esp32_technical_reference_manual_en.pdf).
- Report an issue via [GitHub Issues](https://github.com/espressif/esp-technical-reference-manual-latex/issues).
- Submit a fix via [Pull Request (PR)](https://github.com/espressif/esp-technical-reference-manual-latex/pulls).
    > For PRs, follow the [Contributing Guide](./CONTRIBUTING.md).
