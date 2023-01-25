#!/usr/bin/env python3

import os
from glob import glob
import sys
import re
import argparse

parser = argparse.ArgumentParser(
    description="Find inconsistencies between ssl and msg",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("DIALOG_DIR", help="path to msg dialog directory")
parser.add_argument("SCRIPTS_DIR", help="path to scripts directory")
args = parser.parse_args()
G_DIALOG_PATH = os.path.join(args.DIALOG_DIR, "generic.msg")


def get_generic_messages(file_path):
    g_dialog_messages = []
    with open(file_path, encoding="cp1252") as fdialog:
        for line in fdialog:
            g_dialog_messages.extend(re.findall(r"\{([0-9]{3,5})\}", line))
    return g_dialog_messages


def get_script_paths(dir_path):
    script_paths = [y for x in os.walk(dir_path) for y in glob(os.path.join(x[0], "*.ssl"))]
    return script_paths


def get_script_messages(line):
    # pylint: disable=invalid-name
    MSG_REGEX0 = re.compile(
        r"[^_]+(?:display_mstr|floater|dude_floater|Reply|GOption|GLowOption|NOption"
        r"|NLowOption|BOption|BLowOption|GMessage|NMessage|BMessage) *\( *([0-9]{3,5}) *[,\)]"
    )
    # pylint: disable=invalid-name
    MSG_REGEX1 = re.compile(r"[^_]+mstr *\( *([0-9]{3,5}) *\)")
    # pylint: disable=invalid-name
    MSG_REGEX2 = re.compile(r"[^_]+(?:floater_rand|Reply_Rand) *\( *([0-9]{3,5}) *, *([0-9]{3,5})")
    messages = []
    messages.extend(re.findall(MSG_REGEX0, line))
    messages.extend(re.findall(MSG_REGEX1, line))
    match = re.search(MSG_REGEX2, line)
    if match:
        messages.extend([str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)])
    return messages


def get_gen_messages(line):
    # pylint: disable=invalid-name
    MSG_REGEX = re.compile("[^_]+g_mstr *( *([0-9]{3,5}) *)")
    messages = re.findall(MSG_REGEX, line)
    return messages


def get_dialog_path(script_text, script_path, dialog_dir):
    match = re.search(r"#define NAME +SCRIPT_([A-Z0-9_]+)", script_text)
    if not match:
        match = re.search(".+/(.+).ssl", script_path)
    dialog_path = os.path.join(dialog_dir, match.group(1).lower() + ".msg")
    return dialog_path


def get_dialog_messages(dialog_path):
    dialog_messages = []
    try:
        with open(dialog_path, encoding="cp1252") as fdialog:
            for line in fdialog:
                dialog_messages.extend(re.findall(r"\{([0-9]{3,5})\}", line))
    except IOError:
        return None
    return dialog_messages


def main():
    message_count = 0
    g_dialog_messages = get_generic_messages(G_DIALOG_PATH)
    script_paths = get_script_paths(args.SCRIPTS_DIR)
    found_missing = False

    for script_path in script_paths:
        script_messages = []
        g_script_messages = []
        with open(script_path, encoding="cp1252") as fscript:
            script_text = fscript.read()
            lines = re.sub(r"/\*.+?\*/", "", script_text, flags=re.DOTALL).split("\n")
            for line in lines:
                if line.lstrip().startswith("//"):
                    continue
                messages = get_script_messages(line)
                script_messages.extend(messages)
                messages = get_gen_messages(line)
                g_script_messages.extend(messages)

        script_messages = list(dict.fromkeys(script_messages))
        g_script_messages = list(dict.fromkeys(g_script_messages))

        dialog_path = get_dialog_path(script_text, script_path, args.DIALOG_DIR)

        dialog_messages = get_dialog_messages(dialog_path)
        if dialog_messages is None:
            continue

        script_only = [item for item in script_messages if item not in dialog_messages]
        if script_only:
            print("Messages in " + script_path + " that missed in " + dialog_path + ": " + " ".join(script_only))
            found_missing = True
        message_count += len(script_messages)

        g_script_only = [item for item in g_script_messages if item not in g_dialog_messages]
        if g_script_only:
            print(
                "Generic messages in "
                + script_path
                + " that missed in "
                + G_DIALOG_PATH
                + ": "
                + " ".join(g_script_only)
            )
            found_missing = True

        message_count += len(g_script_messages)

    print("Messages tested: " + str(message_count))

    if found_missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
