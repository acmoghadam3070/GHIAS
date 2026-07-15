#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Project Management Core
Version 0.5
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


# -------------------------------------------------
# Paths
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]

CONFIG_FILE = BASE_DIR / "config.json"


# -------------------------------------------------
# Config
# -------------------------------------------------

def load_config():

    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {
            "project_name": "GHIAS",
            "version": "0.5"
        }


# -------------------------------------------------
# Git Functions
# -------------------------------------------------

def run_git_command(command):

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

        return "Unknown"



def get_current_branch():

    return run_git_command(
        "git branch --show-current"
    )



def get_last_commit():

    return run_git_command(
        'git log -1 --pretty=format:"%h - %s"'
    )



def get_changed_files():

    result = run_git_command(
        "git status --porcelain"
    )


    if not result:

        return []


    return result.splitlines()



# -------------------------------------------------
# Daily Report
# -------------------------------------------------

def create_daily_report():

    from report_generator import create_report


    description = input(
        "\nWhat did you do today?\n> "
    )


    report = create_report(
        description
    )


    print()

    print(
        "Report created:"
    )

    print(report)



# -------------------------------------------------
# Display Status
# -------------------------------------------------

def show_status():

    config = load_config()


    print("=" * 45)

    print(
        f" GHIAS Assistant v{config.get('version')}"
    )

    print("=" * 45)


    print()

    print("Project:")
    print(
        config.get("project_name")
    )


    print()

    print("Path:")
    print(
        PROJECT_ROOT
    )


    print()

    print("Branch:")
    print(
        get_current_branch()
    )


    print()

    print("Last Commit:")
    print(
        get_last_commit()
    )


    print()

    print("Changes:")


    changes = get_changed_files()


    if changes:

        for item in changes:

            print(
                item
            )

    else:

        print(
            "No changes detected"
        )


    print()

    print(
        "Time:"
    )

    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    print()

    print("=" * 45)



# -------------------------------------------------
# Main
# -------------------------------------------------

if __name__ == "__main__":

    show_status()

    create_daily_report()