import shutil
from pathlib import Path

from config import (
    REPO,
    CPP_FOLDER,
    PYTHON_FOLDER,
    MYSQL_FOLDER,
    CPP_NAME,
    PYTHON_NAME,
    MYSQL_NAME,
)


def get_new_filename(language):
    if language == CPP_FOLDER:
        return CPP_NAME

    if language == PYTHON_FOLDER:
        return PYTHON_NAME

    if language == MYSQL_FOLDER:
        return MYSQL_NAME

    return None


def create_destination(language, difficulty, problem_name):
    """
    Create destination folder.

    Example:

    C++/
        Easy/
            0001-two-sum/
    """

    destination = REPO / language / difficulty / problem_name

    destination.mkdir(parents=True, exist_ok=True)

    return destination


def organize_problem(info):
    """
    Move one LeetCode problem.
    """

    language = info["language"]
    difficulty = info["difficulty"]
    solution = info["solution"]
    readme = info["readme"]
    problem_name = info["name"]

    if language is None:
        print("   Skipped (Language not detected)")
        return

    if difficulty == "Unknown":
        print("   Skipped (Difficulty Unknown)")
        return

    destination = create_destination(
        language,
        difficulty,
        problem_name
    )

    new_name = get_new_filename(language)

    destination_solution = destination / new_name

    if destination_solution.exists():
        print("   Already Organized")
        return

    shutil.copy2(solution, destination_solution)

    if readme.exists():
        shutil.copy2(
            readme,
            destination / "README.md"
        )

    print("   Moved Successfully")