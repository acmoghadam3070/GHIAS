#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Auto Sync Engine
Version: 0.9.0
"""

import subprocess
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_git(command):

    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True,
            cwd=PROJECT_ROOT,
            stderr=subprocess.STDOUT
        )

        return result.strip()

    except subprocess.CalledProcessError as e:
        return e.output.strip()



def get_branch():

    return run_git(
        "git branch --show-current"
    )



def get_status():

    return run_git(
        "git status --porcelain"
    )



def pull_changes():

    print("\nChecking remote updates...")

    result = run_git(
        "git pull"
    )

    print(result)



def show_changes():

    changes = get_status()

    print()

    print("=" * 45)
    print(" GHIAS Auto Sync v0.9.0 ")
    print("=" * 45)

    print()

    print("Branch:")
    print(
        get_branch()
    )

    print()

    if changes:

        print("Local Changes:")

        for item in changes.splitlines():

            print(
                "-",
                item
            )

    else:

        print(
            "No local changes detected."
        )

    print()

    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "=" * 45
    )



def sync():

    show_changes()

    pull_changes()



if __name__ == "__main__":

    sync()