#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Professional Git Analyzer v0.6
"""

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]



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



def clean_path(path):

    path = path.strip()

    if path.startswith("ools/"):
        path = "tools/" + path[5:]

    return path



def analyze_changes():

    result = run_git(
        "git status --porcelain=v1"
    )


    analysis = {

        "modified": [],
        "added": [],
        "deleted": [],
        "renamed": [],
        "unknown": []

    }



    if not result:

        return analysis



    for line in result.splitlines():

        if len(line) < 3:
            continue


        status = line[:2].strip()


        file_name = clean_path(
            line[3:]
        )


        if status == "??":

            analysis["added"].append(
                file_name
            )


        elif "M" in status:

            analysis["modified"].append(
                file_name
            )


        elif "D" in status:

            analysis["deleted"].append(
                file_name
            )


        elif "R" in status:

            analysis["renamed"].append(
                file_name
            )


        else:

            analysis["unknown"].append(
                file_name
            )


    return analysis




def print_section(title, items):

    print()
    print(title)


    if items:

        for item in items:

            print(
                "-",
                item
            )

    else:

        print("None")




def print_analysis():

    data = analyze_changes()


    print("=" * 45)

    print(
        " GHIAS Git Analyzer v0.6 "
    )

    print("=" * 45)


    print_section(
        "Modified Files:",
        data["modified"]
    )


    print_section(
        "New Files:",
        data["added"]
    )


    print_section(
        "Deleted Files:",
        data["deleted"]
    )


    print_section(
        "Renamed Files:",
        data["renamed"]
    )


    print_section(
        "Unknown Changes:",
        data["unknown"]
    )


    print()

    print("=" * 45)




if __name__ == "__main__":

    print_analysis()