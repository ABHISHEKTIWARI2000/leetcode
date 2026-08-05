import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LANGUAGE_MAP = {
    ".cpp": ("C++", "solution.cpp"),
    ".cc": ("C++", "solution.cpp"),
    ".cxx": ("C++", "solution.cpp"),
    ".py": ("Python", "solution.py"),
    ".sql": ("MySQL", "solution.sql"),
}

SKIP_FOLDERS = {
    ".git",
    ".github",
    "scripts",
    "C++",
    "Python",
    "MySQL",
}


def is_problem_folder(folder):
    if not folder.is_dir():
        return False

    if folder.name in SKIP_FOLDERS:
        return False

    return folder.name[0].isdigit()


def organize():
    moved = 0

    for folder in ROOT.iterdir():

        if not is_problem_folder(folder):
            continue

        files = list(folder.glob("*"))

        solution = None

        for f in files:
            if f.suffix.lower() in LANGUAGE_MAP:
                solution = f
                break

        if solution is None:
            continue

        language, new_name = LANGUAGE_MAP[solution.suffix.lower()]

        destination = ROOT / language / folder.name

        destination.mkdir(parents=True, exist_ok=True)

        shutil.move(str(solution), destination / new_name)

        readme = folder / "README.md"

        if readme.exists():
            shutil.move(str(readme), destination / "README.md")

        try:
            folder.rmdir()
        except:
            pass

        moved += 1

    print(f"Moved {moved} problem(s).")


if __name__ == "__main__":
    organize()