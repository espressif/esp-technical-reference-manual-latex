# Check Todo Notes or Commented Code

The script is used to detect and remove todo notes and commented code from `.tex` files when pushing to GitHub.

## Features

The script has the following features:
 - Process only .tex files. The file `revision-history__CN/EN.tex` is ignored, as it contains commented-out Jira tickets that help us track the background of updates.
 - Check for todo notes and commented code, printing their line numbers and content.
 - If found, the script should remove them and print the details of what was removed, including their line numbers and content.
 - Skip the commented code documented in an ignore file.
 - Provide one option to either simply check and list the content, and another option to remove the content and list the content.

## Usage

1. **Run the Script:**

   Depending on the Python version you are using, run the following command:

   `python3 check_todo_notes_commented_code.py <path_to_file_or_directory> [-d]`

   For example,

   `python3 check_todo_notes_commented_code.py '../Test Examples/Test Examples/simple_EN.tex'`

   `python3 check_todo_notes_commented_code.py '../Test Examples/Test Examples' -d`

   > **Note:** The `-d` option is used to delete todo notes or commented code from `.tex` files, while omitting `-d` will only locate the information without removing it.

2. **Ignore certain todo notes or commented code:**

   If you wish to ignore specific todo notes or commented code, add them in a one-per-line format to an [ignored_todo_notes_commented_code.txt](ignored_todo_notes_commented_code.txt) file.

   `python3 check_todo_notes_commented_code.py <path_to_file_or_directory> [-d] [-i <path_to_ignored_sensitive_info_file>]`

## Todo Notes or Commented Code Formats

Todo notes comes in the following formats:
 - \todo[inline]{todo note example}
 - \todoreminder{todo note example}
 - \tododone{todo note example}
 - \todo{todo note example}

Commented code comes in the following formats:
 - Code commented with the percent sign `%`.
 - Code between `\begin {comment}` and `\end{comment}`.
