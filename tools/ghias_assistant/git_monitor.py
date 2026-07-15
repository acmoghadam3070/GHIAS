#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Git Change Monitor
"""

import subprocess
from pathlib import Path


def run_git(command):

    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True
        )

        return result.strip()

    except Exception:
        return ""


def get_changed_files():

    result = run_git(
        "git status --porcelain"
    )

    if not result:
        return []


    files = []

    for line in result.splitlines():

        status = line[:2].strip()
        file_name = line[3:]

        files.append(
            {
                "status": status,
                "file": file_name
            }
        )

    return files



def show_changes():

    print("=" * 40)
    print(" GHIAS Git Monitor ")
    print("=" * 40)

    changes = get_changed_files()


    if not changes:

        print()
        print("No changes detected")
        return


    print()

    print("Detected Changes:")
    print()


    for item in changes:

        print(
            f"[{item['status']}] {item['file']}"
        )


if __name__ == "__main__":

    show_changes()