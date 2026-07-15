import os
import subprocess
from datetime import datetime


PROJECT_NAME = "GHIAS"


def run_git_command(command):
    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True,
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


def show_status():

    print("=" * 40)
    print(" GHIAS Assistant v0.1 ")
    print("=" * 40)

    print()

    print("Project:")
    print(PROJECT_NAME)

    print()

    print("Path:")
    print(os.getcwd())

    print()

    print("Branch:")
    print(get_current_branch())

    print()

    print("Last Commit:")
    print(get_last_commit())

    print()

    print("Time:")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print()

    print("Status:")
    print("Ready")

    print("=" * 40)


if __name__ == "__main__":
    show_status()