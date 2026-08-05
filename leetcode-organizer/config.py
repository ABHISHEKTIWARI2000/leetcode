"""
Configuration file for LeetCode Organizer
Edit only these values according to your system.
"""

from pathlib import Path

# ==========================================
# LeetCode Repository Location (LOCAL PATH)
# ==========================================

# Example (Windows):
# REPO_PATH = r"C:\Users\Abhishek\Documents\leetcode-solutions"

REPO_PATH = r"E:\leetcode\ leetcode-solutions"


# ==========================================
# Folder Names
# ==========================================

CPP_FOLDER = "C++"
PYTHON_FOLDER = "Python"
MYSQL_FOLDER = "MySQL"

EASY = "Easy"
MEDIUM = "Medium"
HARD = "Hard"


# ==========================================
# Supported File Extensions
# ==========================================

CPP_EXTENSIONS = [".cpp", ".cc", ".cxx"]
PYTHON_EXTENSIONS = [".py"]
MYSQL_EXTENSIONS = [".sql"]


# ==========================================
# File Rename
# ==========================================

CPP_NAME = "solution.cpp"
PYTHON_NAME = "solution.py"
MYSQL_NAME = "solution.sql"


# ==========================================
# Git Settings
# ==========================================

AUTO_COMMIT = False
AUTO_PUSH = False


# ==========================================
# Logging
# ==========================================

SHOW_LOGS = True


# ==========================================
# Derived Path
# ==========================================

REPO = Path(REPO_PATH)