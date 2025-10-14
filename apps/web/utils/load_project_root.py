import sys
from pathlib import Path


def load_project_root() -> None:
    # Add project root to Python path
    # Notebook is in examples/, so project root is one level up
    current_dir = Path.cwd()
    if current_dir.name == "examples":
        project_root = current_dir.parent
    else:
        # Try to find project root by looking for pyproject.toml
        project_root = current_dir
        while project_root != project_root.parent:
            if (project_root / "pyproject.toml").exists():
                break
            project_root = project_root.parent
        else:
            # Fallback: assume we're in examples/ and go up one level
            project_root = Path.cwd().parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
