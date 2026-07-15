#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Commit Manager Module
v0.8.1
"""

import subprocess
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_git(command):

    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True,
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL
        )

        return result.strip()

    except Exception:
        return ""



def get_changes():

    result = run_git(
        "git status --porcelain"
    )

    changes = []


    if not result:
        return changes


    for line in result.splitlines():

        status = line[:2]
        path = line[3:].strip()


        if status == "??":
            change_type = "Added"

        elif "M" in status:
            change_type = "Modified"

        elif "D" in status:
            change_type = "Deleted"

        else:
            change_type = "Changed"


        changes.append(
            {
                "type": change_type,
                "file": path
            }
        )


    return changes



def generate_commit_message(changes):

    count = len(changes)

    date = datetime.now().strftime(
        "%Y-%m-%d"
    )


    return (
        f"GHIAS Assistant update "
        f"{date} "
        f"({count} files changed)"
    )



def create_commit():

    changes = get_changes()


    print("=" * 45)
    print(" GHIAS Commit Manager v0.8.1 ")
    print("=" * 45)


    print()


    if not changes:

        print(
            "No changes detected."
        )

        return False



    print(
        "Detected Changes:"
    )

    print()


    for item in changes:

        print(
            f"{item['type']}: {item['file']}"
        )


    print()


    message = generate_commit_message(
        changes
    )


    print(
        "Commit Message:"
    )

    print(
        message
    )


    print()


    confirm = input(
        "Create commit? (y/n): "
    )


    if confirm.lower() != "y":

        print(
            "Cancelled."
        )

        return False



    run_git(
        "git add ."
    )


    subprocess.call(
        [
            "git",
            "commit",
            "-m",
            message
        ],
        cwd=PROJECT_ROOT
    )


    print()

    print(
        "Commit completed successfully."
    )


    return True



if __name__ == "__main__":

    create_commit()