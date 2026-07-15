#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GHIAS Assistant
Core Engine v0.7.1
"""

from datetime import datetime


from project_info import (
    get_project_info
)


from git_analyzer import (
    analyze_changes
)


from report_generator import (
    create_report
)



def print_changes(changes):

    total_changes = (
        changes["modified"]
        +
        changes["added"]
        +
        changes["deleted"]
    )


    if total_changes:

        for item in total_changes:

            print(
                "-",
                item
            )

    else:

        print(
            "No changes"
        )




def run_assistant():

    print("=" * 45)

    print(
        " GHIAS Assistant Core v0.7.1 "
    )

    print("=" * 45)



    print()


    print(
        "Collecting project information..."
    )


    project = get_project_info()



    print(
        "Analyzing Git changes..."
    )


    changes = analyze_changes()



    print()


    print(
        "Project:"
    )

    print(
        project["project"]
    )



    print()


    print(
        "Path:"
    )

    print(
        project["path"]
    )



    print()


    print(
        "Branch:"
    )

    print(
        project["branch"]
    )



    print()


    print(
        "Last Commit:"
    )

    print(
        project["last_commit"]
    )



    print()


    print(
        "Changed Files:"
    )


    print_changes(
        changes
    )



    print()


    work = input(
        "What did you do today?\n> "
    )



    report = create_report(
        work,
        project,
        changes
    )



    print()


    print(
        "Daily Report Created:"
    )


    print(
        report
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




if __name__ == "__main__":

    run_assistant()