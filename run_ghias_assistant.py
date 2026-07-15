#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Main Launcher
Version: 1.0.0
"""

import subprocess
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent


ASSISTANT = (
    PROJECT_ROOT
    / "tools"
    / "ghias_assistant"
    / "auto_sync.py"
)



def show_banner():

    print("=" * 50)
    print(" GHIAS Assistant Launcher v1.0.0 ")
    print("=" * 50)

    print()

    print(
        "Starting GHIAS Assistant..."
    )

    print(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print()



def start():

    if not ASSISTANT.exists():

        print(
            "GHIAS Assistant engine not found!"
        )

        return


    subprocess.run(
        [
            "python",
            str(ASSISTANT)
        ],
        cwd=PROJECT_ROOT
    )



if __name__ == "__main__":

    show_banner()

    start()