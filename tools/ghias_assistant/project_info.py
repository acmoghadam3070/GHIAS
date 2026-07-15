#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Project Information Module v0.7
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

        return "Unknown"



def get_project_info():

    return {

        "project":
            "GHIAS",

        "path":
            str(PROJECT_ROOT),

        "branch":
            run_git(
                "git branch --show-current"
            ),

        "last_commit":
            run_git(
                'git log -1 --pretty=format:"%h - %s"'
            )

    }



if __name__ == "__main__":

    info = get_project_info()


    for key, value in info.items():

        print(key)

        print(value)

        print("-" * 30)