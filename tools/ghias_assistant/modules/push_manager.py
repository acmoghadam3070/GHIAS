#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Push Manager
Version: 1.0.0
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
            stderr=subprocess.STDOUT
        )

        return result.strip()


    except subprocess.CalledProcessError as e:

        return e.output.strip()



def get_branch():

    return run_git(
        "git branch --show-current"
    )



def push_changes():

    print("=" * 45)
    print(" GHIAS Push Manager v1.0.0 ")
    print("=" * 45)

    print()

    print("Branch:")
    print(
        get_branch()
    )

    print()


    confirm = input(
        "Push changes to GitHub? (y/n): "
    )


    if confirm.lower() != "y":

        print(
            "Push cancelled."
        )

        return



    print()

    print(
        "Pushing..."
    )


    result = run_git(
        "git push"
    )


    print()

    print(
        result
    )


    print()

    print(
        "Push completed."
    )

    print("=" * 45)



if __name__ == "__main__":

    push_changes()