# Contributing Guide

Thank you for your interest in contributing to Espressif Technical Reference Manuals in LaTeX. This document explains what we accept, how to contribute, and the standards to follow so your contribution can be reviewed and merged quickly.


## Contribution Scope

We welcome contributions that improve the TRM content and repository documentation. Typical accepted changes:

- Edits in LaTeX source and supporting files that correct or clarify technical content.
- Improvements to README, CONTRIBUTING, and other repository documentation.

If you’re unsure whether a change is in-scope, open an issue first describing your proposed change.


## Legal Requirements

Before we can accept your contribution, sign the [Espressif Contributor Agreement](http://docs.espressif.com/projects/esp-idf/en/stable/contribute/contributor-agreement.html). You will be prompted automatically when opening your first PR.


## Getting Started

To contribute:

1. **Fork** the repository.
2. **Create a new branch** from `master`.
3. **Make your changes** following the conventions below.
4. **Submit a PR** with a clear, descriptive title.

### Language, Style, and Build

Primary sources in this repository are LaTeX (`.tex`) and accompanying style files. Follow these instructions:

- For LaTeX basics, see [Learn LaTeX](https://www.learnlatex.org/en/)
- For writing styles, see [Espressif Manual of Style](https://mos.espressif.com/)
- For local build, see [Build Instructions](./README.md#build-instructions)


### Branch Naming Conventions

```
git checkout -b feature/add_gdma_chapter_to_esp32-c5_trm
```

1. **Prefixes**: Start the branch name with `docs/`, `bugfix/`, or `feature/`.

- `docs/`: Use this prefix when updating build scripts, document templates, or supportive tooling.
- `bugfix/`: Use this prefix when fixing typos, bugs, or mistakes in a document.
- `feature/`: Use this prefix when preparing the initial release or a new feature for a document.

2. **No spaces**: Use underscores to replace spaces.
3. **Lowercase only**: No uppercase letters.
4. **Single task per branch**: For example, when preparing a new document, first create a branch for the code change based on the template. After the branch is merged, create a new one for the content change that requires review.

### Commit Message Conventions

```
git commit -m "Chip/short name of TRM module: Add/Update/Remove..."
```

1. **Keywords**: Start the branch name with chip or chip/short name of TRM module, for example, `ESP32-H2` or `ESP32-S3/UART`.

   > **Note**: When updating the same TRM module for multiple TRMs, or updating multiple TRM modules for the same TRM in one MR, please separate different chip or module names with a comma (e.g. `ESP32-S3, ESP32-H2/UART`).

2. **Summarize the purpose in one line**: Try to keep each commit focused on a single logical change.

   > **Note**: Use the present tense of the verb and capitalize the initial letter of the verb.
