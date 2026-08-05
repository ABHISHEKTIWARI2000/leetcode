from pathlib import Path
from parser import is_problem_folder, parse_problem
from mover import organize_problem
from config import REPO


def scan_repository():
    """
    Scan the repository for LeetCode problem folders.
    """

    if not REPO.exists():
        print(f"[ERROR] Repository not found: {REPO}")
        return

    print("=" * 60)
    print(" LeetCode Organizer ")
    print("=" * 60)

    total = 0

    for folder in REPO.iterdir():

        if not is_problem_folder(folder):
            continue

        total += 1

        info = parse_problem(folder)

        print(f"\nProcessing : {info['name']}")

        organize_problem(info)

    print("\n" + "=" * 60)
    print(f"Completed. Total Problems Processed : {total}")
    print("=" * 60)


if __name__ == "__main__":
    scan_repository()