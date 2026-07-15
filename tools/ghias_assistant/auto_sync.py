#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Auto Sync Engine
Version: 1.0.0
"""

import subprocess
from pathlib import Path
from datetime import datetime

from report_generator import create_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_DIR = Path(__file__).resolve().parent


def run_command(command):

    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True,
            cwd=PROJECT_ROOT,
            stderr=subprocess.STDOUT
        )

        return result.strip()

    except Exception as e:
        return str(e)



def get_branch():

    return run_command(
        "git branch --show-current"
    )



def get_changes():

    result = run_command(
        "git status --porcelain"
    )

    if not result:
        return []

    return result.splitlines()



def show_header():

    print("=" * 45)
    print(" GHIAS Auto Sync v1.0.0 ")
    print("=" * 45)



def create_commit():

    manager = (
        BASE_DIR /
        "modules" /
        "commit_manager.py"
    )

    subprocess.run(
        [
            "python",
            str(manager)
        ],
        cwd=PROJECT_ROOT
    )



def check_remote():

    print()
    print("Checking remote updates...")

    result = run_command(
        "git pull"
    )

    print(result)



def main():

    show_header()

    print()

    print("Branch:")
    print(get_branch())

    print()

    changes = get_changes()


    if not changes:

        print(
            "No local changes detected."
        )

        check_remote()

        return



    print("Detected Changes:")

    for item in changes:

        print(
            "-",
            item
        )


    print()


    answer = input(
        "Create report and commit? (y/n): "
    )


    if answer.lower() != "y":

        print(
            "Cancelled."
        )

        return



    work = input(
        "\nWhat did you do today?\n> "
    )


    report = create_report(
        work
    )


    print()

    print(
        "Daily Report Created:"
    )

    print(report)



    print()

    create_commit()


    print()

    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    print("=" * 45)



if __name__ == "__main__":

    main()