#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Commit Manager Module
v0.8
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

    if not result:
        return []

    return [
        line[3:].strip()
        for line in result.splitlines()
    ]



def generate_commit_message():

    files = get_changes()

    if not files:
        return "No changes"



    now = datetime.now()


    message = (
        f"GHIAS Assistant update "
        f"{now.strftime('%Y-%m-%d')} "
        f"({len(files)} files changed)"
    )


    return message



def create_commit(message=None):

    files = get_changes()


    if not files:

        print(
            "No changes detected."
        )

        return False



    print("=" * 45)
    print(" GHIAS Commit Manager v0.8 ")
    print("=" * 45)


    print()

    print("Changed files:")


    for file in files:

        print(
            "-",
            file
        )


    if not message:

        message = generate_commit_message()


    print()

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
        "Commit completed."
    )


    return True




if __name__ == "__main__":

    create_commit()