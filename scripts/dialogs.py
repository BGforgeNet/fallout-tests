#!/usr/bin/env python3
"""Validate dialog message references in Fallout scripts.

This module cross-references message IDs used in scripts with their
corresponding .msg files to ensure all referenced messages exist.
Only .msg dialog files use cp1252 encoding; .ssl script files are UTF-8/ASCII.
"""

import argparse
from pathlib import Path
import re
import sys

# Type aliases
MessageList = list[str]  # List of message IDs
MessageDict = dict[str, MessageList]  # Maps message type to list of message IDs

# Regex patterns for message function calls in scripts
_MSG_REGEX0 = re.compile(
    r"[^_]+(?:display_mstr|floater|dude_floater|Reply|GOption|GLowOption|NOption"
    r"|NLowOption|BOption|BLowOption|GMessage|NMessage|BMessage) *\( *([0-9]{3,5}) *[,\)]"
)
_MSG_REGEX1 = re.compile(r"[^_]+mstr *\( *([0-9]{3,5}) *\)")
_MSG_REGEX2 = re.compile(r"[^_]+(?:floater_rand|Reply_Rand) *\( *([0-9]{3,5}) *, *([0-9]{3,5})")
_MSG_REGEX_GEN = re.compile(r"[^_]+g_mstr *\( *([0-9]{3,5}) *\)")

parser = argparse.ArgumentParser(
    description="Find inconsistencies between ssl and msg",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("DIALOG_DIR", help="path to msg dialog directory")
parser.add_argument("SCRIPTS_DIR", help="path to scripts directory")


def get_generic_messages(file_path: str | Path) -> MessageList | None:
    """Extract message IDs from generic.msg file.

    Args:
        file_path: Path to the generic.msg file

    Returns:
        List of message IDs found in the file, or None if the file cannot be opened
    """
    g_dialog_messages: MessageList = []
    try:
        with open(file_path, encoding="cp1252") as fdialog:
            for line in fdialog:
                g_dialog_messages.extend(re.findall(r"\{([0-9]{3,5})\}", line))
    except OSError:
        return None
    return g_dialog_messages


def get_script_paths(dir_path: str | Path) -> list[Path]:
    """Find all .ssl script files in the given directory tree.

    Args:
        dir_path: Root directory to search for scripts

    Returns:
        List of paths to .ssl files
    """
    return list(Path(dir_path).rglob("*.ssl"))


def get_script_messages(line: str) -> MessageList:
    """Extract message IDs from a line of script code.

    Args:
        line: Single line of script code to analyze

    Returns:
        List of message IDs referenced in the line
    """
    messages = []
    messages.extend(re.findall(_MSG_REGEX0, line))
    messages.extend(re.findall(_MSG_REGEX1, line))
    match = re.search(_MSG_REGEX2, line)
    if match:
        messages.extend([str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)])
    return messages


def get_gen_messages(line: str) -> MessageList:
    """Extract generic message IDs from a line of script code.

    Args:
        line: Single line of script code to analyze

    Returns:
        List of generic message IDs referenced in the line
    """
    messages = re.findall(_MSG_REGEX_GEN, line)
    return messages


def get_dialog_path(script_text: str, script_path: str | Path, dialog_dir: str | Path) -> Path:
    """Determine the dialog file path for a given script.

    Args:
        script_text: Full text content of the script
        script_path: Path to the script file
        dialog_dir: Directory containing dialog files

    Returns:
        Expected path to the corresponding .msg file
    """
    script_path = Path(script_path)
    dialog_dir = Path(dialog_dir)

    match = re.search(r"#define NAME +SCRIPT_([A-Z0-9_]+)", script_text)
    if not match:
        match = re.search(r".+/(.+)\.ssl", str(script_path))
    if match:
        return dialog_dir / (match.group(1).lower() + ".msg")
    # Fallback to script filename if no match found
    return dialog_dir / (script_path.stem.lower() + ".msg")


def get_dialog_messages(dialog_path: str | Path) -> MessageList | None:
    """Extract message IDs from a dialog .msg file.

    Args:
        dialog_path: Path to the .msg file

    Returns:
        List of message IDs if file exists, None if file not found
    """
    dialog_messages: MessageList = []
    try:
        with open(dialog_path, encoding="cp1252") as fdialog:
            for line in fdialog:
                dialog_messages.extend(re.findall(r"\{([0-9]{3,5})\}", line))
    except OSError:
        return None
    return dialog_messages


def get_messages_from_file(script_text: str) -> MessageDict:
    """Extract all message references from script text.

    Args:
        script_text: Full text content of the script

    Returns:
        Dictionary with 'script' and 'gen' message lists
    """
    script_messages: MessageList = []
    gen_messages: MessageList = []
    lines = re.sub(r"/\*.+?\*/", "", script_text, flags=re.DOTALL).split("\n")
    for line in lines:
        if line.lstrip().startswith("//"):
            continue
        messages = get_script_messages(line)
        script_messages.extend(messages)
        messages = get_gen_messages(line)
        gen_messages.extend(messages)
    return {"script": script_messages, "gen": gen_messages}


def main(argv: list[str] | None = None) -> None:
    """Main entry point for dialog validation."""
    args = parser.parse_args(argv)
    dialog_dir = Path(args.DIALOG_DIR)
    scripts_dir = Path(args.SCRIPTS_DIR)

    g_dialog_path = dialog_dir / "generic.msg"
    message_count = 0

    # If generic.msg is missing, generic message validation is skipped
    g_dialog_messages: MessageList = get_generic_messages(g_dialog_path) or []

    script_paths = get_script_paths(scripts_dir)
    found_missing = False

    for script_path in script_paths:
        script_messages = []
        g_script_messages = []

        with open(script_path, encoding="utf-8") as fhandle:
            script_text = fhandle.read()

        messages = get_messages_from_file(script_text)
        script_messages.extend(messages["script"])
        g_script_messages.extend(messages["gen"])

        script_messages = list(dict.fromkeys(script_messages))
        g_script_messages = list(dict.fromkeys(g_script_messages))

        cur_dialog_path = get_dialog_path(script_text, script_path, dialog_dir)

        dialog_messages = get_dialog_messages(cur_dialog_path)
        if dialog_messages is None:
            continue

        script_only = [item for item in script_messages if item not in dialog_messages]
        if script_only:
            print(f"Messages in {script_path} missing from {cur_dialog_path}: {' '.join(script_only)}")
            found_missing = True
        message_count += len(script_messages)

        g_script_only = [item for item in g_script_messages if item not in g_dialog_messages]
        if g_script_only:
            print(f"Generic messages in {script_path} missing from {g_dialog_path}: {' '.join(g_script_only)}")
            found_missing = True

        message_count += len(g_script_messages)

    print(f"Messages checked: {message_count}")

    if found_missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
