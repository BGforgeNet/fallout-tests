"""Read global variable files (vault13.gam, maps/*.gam) the way the engine does.

Follows globalVarsRead in fallout2-ce src/game.cc: after the line starting with the section marker, every
line counts as one variable unless it is empty or starts with "//" in the first column. A line holding only
spaces, or a comment indented by a space, therefore still adds a variable.
.gam files are UTF-8/ASCII.
"""

from pathlib import Path

GAME_SECTION = "GAME_GLOBAL_VARS:"
MAP_SECTION = "MAP_GLOBAL_VARS:"


def count_vars(path: str | Path, section: str) -> int | None:
    """Count the variables a .gam file declares.

    Args:
        path: .gam file path
        section: Section marker line, GAME_SECTION or MAP_SECTION

    Returns:
        The variable count, or None when the file has no section marker
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    # The engine compares the first 16 characters only (strncmp).
    starts = [index for index, line in enumerate(lines) if line[:16] == section[:16]]
    if not starts:
        return None
    return sum(1 for line in lines[starts[0] + 1 :] if line and not line.startswith("//"))
