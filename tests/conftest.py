"""Shared pytest fixtures for the Fallout validator test suite."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

PINNED_INTEGRATION_REPO_COMMIT = "0b17617003fc404ebdbbbcfc39c23d82ef86bcde"

# Add the scripts directory to sys.path so tests can import the validator modules directly.
# The scripts directory is not a package and lives alongside this tests directory.
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def integration_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the managed integration checkout, updating it to the pinned commit if needed.

    When FALLOUT_TEST_REPO is set, it is treated as the integration cache path owned by the
    test fixture rather than a read-only working copy.
    """
    del tmp_path_factory

    configured_repo = os.environ.get("FALLOUT_TEST_REPO")
    if configured_repo:
        repo = Path(configured_repo)
    else:
        cache_root = Path(__file__).parent.parent / "tmp"
        cache_root.mkdir(exist_ok=True)
        repo = cache_root / "Fallout2_Unofficial_Patch"

    git_dir = repo / ".git"
    if not git_dir.exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth=1", "https://github.com/BGforgeNet/Fallout2_Unofficial_Patch", str(repo)],
            check=True,
        )
    else:
        current_head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if current_head == PINNED_INTEGRATION_REPO_COMMIT:
            return repo

    subprocess.run(
        ["git", "-C", str(repo), "fetch", "--depth=1", "origin", PINNED_INTEGRATION_REPO_COMMIT],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "--detach", PINNED_INTEGRATION_REPO_COMMIT],
        check=True,
    )

    return repo
