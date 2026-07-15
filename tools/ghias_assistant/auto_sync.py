#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Auto Sync Engine
Version: 0.9.2

Features:
- Git change detection
- Daily report generation
- Commit manager integration
- Remote sync check
"""

import subprocess
from pathlib import Path
from datetime import datetime


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

    except subprocess.CalledProcessError as e:

        return e.output.strip()



def get_changes():

    result = run_command(
        "git status --porcelain"
    )

    if not result:
        return []

    return result.splitlines()



def pull_updates():

    print()

    print("Checking remote updates...")

    result = run_command(
        "git pull"
    )

    print(result)



def create_daily_report():

    print()

    work = input(
        "What did you do today?\n> "
    )


    generator = (
        BASE_DIR /
        "report_generator.py"
    )


    subprocess.run(
        [
            "python",
            str(generator),
        ],
        cwd=PROJECT_ROOT
    )



def run_commit_manager():

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



def show_header():

    print("=" * 45)

    print(
        " GHIAS Auto Sync v0.9.2 "
    )

    print("=" * 45)



def main():

    show_header()


    print()

    print("Checking local changes...")


    changes = get_changes()


    if changes:

        print()

        print(
            "Detected Changes:"
        )


        for item in changes:

            print(
                "-",
                item
            )


        print()


        answer = input(
            "Create daily report and commit? (y/n): "
        )


        if answer.lower() == "y":

            create_daily_report()

            run_commit_manager()


    else:

        print(
            "No local changes detected."
        )


    pull_updates()


    print()

    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    print("=" * 45)



if __name__ == "__main__":

    main()