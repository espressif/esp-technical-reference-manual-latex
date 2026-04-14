#!/usr/bin/env python3
import os
import re
import argparse

# Folders to skip
EXCLUDED_FOLDERS = ['00-chip-spec-content/revision-history__CN.tex','00-chip-spec-content/revision-history__EN.tex','00-chip-spec-content/revision-history-latest__CN.tex','00-chip-spec-content/revision-history-latest__EN.tex','00-shared']
DEFAULT_IGNORE_FILE = 'ignored_todo_notes_commented_code.txt'
FILE_EXTENSION = '.tex'

TODO_PATTERNS_RAW = [
    r'\\todo',
    r'\\todo\[inline\]',
    r'\\todoreminder',
    r'\\tododone',
    r'\\todoattention'
]

TODO_PATTERNS = [
    r'(\\todo{.*?})',
    r'(\\todo\[inline\]{.*?})',
    r'(\\todoreminder{.*?})',
    r'(\\tododone{.*?})',
    r'(\\todoattention{.*?})'
]

TODO_MULTI_LINE_PATTERNS = [
    r'(\\todo{.*?})',
    r'(\\todo\[inline\]{.*)',
    r'(\\todoreminder{.*)',
    r'(\\tododone{.*)',
    r'(\\todoattention{.*)'
]

# Sentinel: mid-line % comments are handled by _strip_midline_percent_comments (see docstring).
_INLINE_PERCENT_COMMENTS = object()

PERCENT_LINESTART_PATTERN = r'^((?:\\\\)*%(?!\\subfileinclude).*)\n'  # line-start % (optional \\ pairs)

COMMENTED_CODE_PATTERNS = [
    PERCENT_LINESTART_PATTERN,
    _INLINE_PERCENT_COMMENTS,
    r'(\\begin{comment}.*?\\end{comment})'  # Code between \begin{comment} and \end{comment}
]

COMMENTED_CODE_MULTI_LINE_PATTERNS = [
    r'(\\begin{comment}.*)'  # Code between \begin{comment} and \end{comment}
]

MULTI_LINE_END_PATTERN = r'(.*?})'
MULTI_LINE_COMMENT_END_PATTERN = r'(.*?\\end{comment})'

COMPILED_TODO_PATTERN = re.compile(r'(' + '|'.join(TODO_PATTERNS_RAW) + r')\s*{')


def remove_todo_commands(text):
    i = 0
    result = ''
    while i < len(text):
        match = COMPILED_TODO_PATTERN.search(text, i)
        if not match:
            result += text[i:]
            break

        start = match.start()
        end = match.end()
        result += text[i:start]

        brace_count = 1
        j = end
        while j < len(text):
            if text[j] == '{':
                brace_count += 1
            elif text[j] == '}':
                brace_count -= 1
                if brace_count == 0:
                    j += 1
                    break
            j += 1

        if brace_count == 0:
            i = j
        else:
            result = text
            break

    return result


def _backslashes_before_percent(line, pct_index):
    """Count consecutive backslashes immediately before line[pct_index] ('%')."""
    n = 0
    j = pct_index - 1
    while j >= 0 and line[j] == '\\':
        n += 1
        j -= 1
    return n


def _percent_followed_only_by_whitespace_to_eol(line, pct_index, nl_index):
    """True if '%' only hides the newline (no non-whitespace between '%' and the newline)."""
    if nl_index <= pct_index:
        return False
    return not line[pct_index + 1:nl_index].strip()


def _linestart_comment_percent_index(line):
    """
    If the line begins with zero or more ``\\\\`` pairs followed by ``%``, return the index of
    that ``%``. Otherwise return -1.
    """
    j = 0
    n = len(line)
    while j + 1 < n and line[j] == '\\' and line[j + 1] == '\\':
        j += 2
    if j < n and line[j] == '%':
        return j
    return -1


def _strip_linestart_percent_comment_line(line, ignore_patterns):
    """
    Remove only from the line-initial comment ``%`` through the following newline, keeping any
    leading ``\\\\`` pairs (same effect as mid-line strip; avoids ``re.sub`` eating the prefix).
    Returns (new_line, changed, segment_for_display).
    """
    pct = _linestart_comment_percent_index(line)
    if pct < 0:
        return line, False, None
    if line.startswith('\\subfileinclude', pct + 1):
        return line, False, None
    nl = line.find('\n', pct)
    if nl == -1:
        return line, False, None
    if _percent_followed_only_by_whitespace_to_eol(line, pct, nl):
        return line, False, None
    segment = line[pct:nl]
    if segment.strip() in ignore_patterns:
        return line, False, None
    suffix = line[nl + 1 :]
    new_line = line[:pct] + suffix
    if line.endswith('\n') and not new_line.endswith('\n'):
        new_line += '\n'
    return new_line, True, segment


def _strip_midline_percent_comments(line, check_only, ignore_patterns, line_number):
    """
    Strip each substring from a '%' that starts a LaTeX comment through the following newline.

    '%' begins a comment when the run of backslashes before it has even length (0, 2, 4, …).
    So '\\\\%' (line break + %) is a comment, while '\\%' is a literal percent.
    Leading '%' on the line is handled by _strip_linestart_percent_comment_line.
    Trailing '%' with only whitespace after it (end-of-line spacer) is ignored.
    """
    modified = False
    start = 0
    out = []
    pos = 0
    while pos < len(line):
        pct = line.find('%', pos)
        if pct == -1:
            break
        if pct == 0:
            pos = 1
            continue
        if _backslashes_before_percent(line, pct) % 2 == 1:
            pos = pct + 1
            continue
        nl = line.find('\n', pct)
        if nl == -1:
            pos = pct + 1
            continue
        if _percent_followed_only_by_whitespace_to_eol(line, pct, nl):
            pos = pct + 1
            continue
        segment = line[pct:nl]
        match_strip = segment.strip()
        if match_strip in ignore_patterns:
            pos = pct + 1
            continue
        if check_only:
            print(f"\033[1;36mCommented code found at line {line_number}\033[0m: {segment.rstrip()}")
        else:
            print(f"\033[0;31mCommented code removed from line {line_number}\033[0m: {segment.rstrip()}")
        out.append(line[start:pct])
        start = nl + 1
        pos = start
        modified = True
    out.append(line[start:])
    return ''.join(out), modified


def is_excluded_folder(folder):
    """Check if a folder is in the excluded list."""
    for excluded in EXCLUDED_FOLDERS:
        if excluded in folder:
            return True
    return False


def process_file(filepath, check_only=True, ignore_patterns=[]):
    """Process a single .tex file, checking or removing 2do notes and commented code."""
    print(f'\033[1;32mprocessing file {filepath}\033[0m')
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    modified = False
    new_lines = []
    todo_multiline = False
    comment_multiline = False

    for i, line in enumerate(lines):
        if todo_multiline:  # in a 2do block
            matches = re.findall(MULTI_LINE_END_PATTERN, line, re.DOTALL)
            if matches and not line.rstrip().endswith('\\'):
                for match in matches:
                    match_strip = match.strip()
                    if match_strip not in ignore_patterns:  # multi lines ignore 2do
                        todo_multiline = False
                        print(f"Line {i + 1}: {match}")
                        line = re.sub(MULTI_LINE_END_PATTERN, '', line,
                                      flags=re.DOTALL)  # because one line may have more than one 2do
                        modified = True
                        if not line.strip():  # ignore spaces in pure comment lines
                            line = ''  # delete the whole line
                        break  # only once
            else:
                print(f"Line {i + 1}: {line.rstrip()}")
                continue
        elif comment_multiline:  # in a comment block
            matches = re.findall(MULTI_LINE_COMMENT_END_PATTERN, line, re.DOTALL)
            if matches:
                for match in matches:
                    match_strip = match.strip()
                    if match_strip not in ignore_patterns:  # multi lines ignore 2do
                        comment_multiline = False
                        print(f"Line {i + 1}: {match}")
                        line = re.sub(MULTI_LINE_COMMENT_END_PATTERN, '', line,
                                    flags=re.DOTALL)  # because one line may have more than one 2do
                        modified = True
                        if not line.strip():  # ignore spaces in pure comment lines
                            line = ''  # delete the whole line
                        break  # only once
            else:
                print(f"Line {i + 1}: {line.rstrip()}")
                continue

        line_strip = line.strip()
        if line_strip:
            if line_strip.startswith('%%%') and line_strip.endswith('%%%'):
                pass  # ignore this
            else:
                for pattern in COMMENTED_CODE_PATTERNS:  # Check for commented code, respecting ignored patterns
                    if pattern is _INLINE_PERCENT_COMMENTS:
                        line, cm = _strip_midline_percent_comments(
                            line, check_only, ignore_patterns, i + 1)
                        if cm:
                            modified = True
                        continue
                    if pattern == PERCENT_LINESTART_PATTERN:
                        line, ch, seg = _strip_linestart_percent_comment_line(line, ignore_patterns)
                        if ch:
                            if check_only:
                                print(
                                    f"\033[1;36mCommented code found at line {i + 1}\033[0m: {seg.rstrip()}"
                                )
                            else:
                                print(
                                    f"\033[0;31mCommented code removed from line {i + 1}\033[0m: {seg.rstrip()}"
                                )
                            modified = True
                        continue
                    matches = re.findall(pattern, line, re.DOTALL)
                    if matches:
                        for match in matches:
                            match_strip = match.strip()
                            if match_strip not in ignore_patterns:
                                if check_only:
                                    print(f"\033[1;36mCommented code found at line {i + 1}\033[0m: {match.rstrip()}")
                                else:
                                    print(
                                        f"\033[0;31mCommented code removed from line {i + 1}\033[0m: {match.rstrip()}")
                                line = re.sub(pattern, '', line, flags=re.DOTALL)
                                modified = True

                for pattern in TODO_PATTERNS:  # Check for todos
                    matches = re.findall(pattern, line, re.DOTALL)
                    if matches:
                        for match in matches:
                            match_strip = match.strip()
                            if match_strip not in ignore_patterns:

                                # line = re.sub(pattern, '', line, flags=re.DOTALL)
                                raw_line=line
                                line = remove_todo_commands(line) #忽略注释中出现嵌套的{}
                                if not line.strip():
                                    if check_only:
                                        print(f"\033[1;36mTodo notes found at line {i + 1}\033[0m: {raw_line.rstrip()}")
                                    else:
                                        print(
                                            f"\033[0;31mTodo notes removed from line {i + 1}\033[0m: {raw_line.rstrip()}")
                                elif line != raw_line:
                                    if check_only:
                                        print(f"\033[1;36mTodo notes found at line {i + 1}\033[0m: {match.rstrip()}")
                                    else:
                                        print(
                                            f"\033[0;31mTodo notes removed from line {i + 1}\033[0m: {match.rstrip()}")
                                modified = True

                if not line.strip():  # ignore spaces in pure comment lines
                    line = ''  # delete the whole line
                else:  # if multiple lines
                    for pattern in TODO_MULTI_LINE_PATTERNS:
                        matches = re.findall(pattern, line, re.DOTALL)
                        if matches:
                            for match in matches:
                                match_strip = match.strip()
                                if match_strip not in ignore_patterns:  # multi lines ignore todo
                                    todo_multiline = True
                                    if check_only:
                                        print(
                                            f"\033[1;36mTodo note block found:\033[0m\nLine {i + 1}: {match.rstrip()}")
                                    else:
                                        print(
                                            f"\033[0;31mTodo note block removed from:\033[0m\nLine {i + 1}: {match.rstrip()}")
                                    line = re.sub(pattern, '', line, flags=re.DOTALL)
                                    modified = True

                    for pattern in COMMENTED_CODE_MULTI_LINE_PATTERNS:
                        matches = re.findall(pattern, line, re.DOTALL)
                        if matches:
                            for match in matches:
                                match_strip = match.strip()
                                if match_strip not in ignore_patterns:  # multi lines ignore todo
                                    comment_multiline = True
                                    if check_only:
                                        print(f"\033[1;36mCommented code block found:\033[0m\nLine {i + 1}: {match.rstrip()}")
                                    else:
                                        print(
                                            f"\033[0;31mCommented code block removed from:\033[0m\nLine {i + 1}: {match.rstrip()}")
                                    line = re.sub(pattern, '', line, flags=re.DOTALL)
                                    modified = True

                    if not line.strip():  # ignore spaces in pure comment lines
                        line = ''  # delete the whole line
                    elif line[-1] != '\n':
                        line += '\n'  # when after text, it needs to have a new line sign

        new_lines.append(line)

    if not check_only and modified:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.writelines(new_lines)

    return modified


def get_file_list(directory):
    """
    Get all files in the directory or single file.
    """
    file_list = []
    if os.path.isfile(directory):
        return [directory]
    for path, _, files in os.walk(directory, topdown=True):
        subdir_file_list = [os.path.join(path, file) for file in files]
        file_list.extend(subdir_file_list)
    return file_list


def process_directory(directories, check_only=True, custom_ignore_file=None):
    """Process all .tex files in a directory, skipping excluded folders."""
    modified_flag = False
    ignore_patterns = []
    ignore_file = custom_ignore_file if custom_ignore_file else DEFAULT_IGNORE_FILE
    if ignore_file:
        with open(ignore_file, 'r', encoding='utf-8') as file:
            ignore_patterns = [line.strip() for line in file.readlines()]

    for directory in directories:
        file_path_list = get_file_list(directory)
        if not file_path_list:
            print(f'\033[1;31mWarning: {directory} does not exist or the folder is empty.\033[0m')

        for file_path in file_path_list:
            if is_excluded_folder(file_path):  # ignore files in EXCLUDED_FOLDERS
                continue

            if file_path.endswith(FILE_EXTENSION):
                modified = process_file(file_path, check_only, ignore_patterns)
                if modified: # any file modified
                    modified_flag = True
    return modified_flag


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process .tex files to check or remove sensitive information.')
    parser.add_argument('directories', nargs='+', help='Directory to scan for .tex files.')
    parser.add_argument('-i', '--ignore-file', help='File containing patterns to ignore.', default=None)
    args = parser.parse_args()

    delete_mode = os.getenv("CI") != "true"

    overall_modified_flag = process_directory(args.directories, check_only=not delete_mode, custom_ignore_file=args.ignore_file)

    if overall_modified_flag:
        exit(1)  # Exit with non-zero status if any file was modified
    else:
        exit(0)  # Exit with zero status if no files were modified
