#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Version Manager
Version: 1.0.0
"""

from pathlib import Path


VERSION_FILE = (
    Path(__file__).resolve().parents[1]
    / "VERSION"
)



def get_version():

    try:

        return VERSION_FILE.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:

        return "Unknown"



def show_version():

    print("=" * 45)
    print(" GHIAS Version Manager ")
    print("=" * 45)

    print()

    print("Current Version:")

    print(
        get_version()
    )

    print()

    print("=" * 45)



if __name__ == "__main__":

    show_version()