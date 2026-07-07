"""Enforce a conventional-commit-style prefix on the commit subject.

Invoked by the `commit-msg` prek hook with the path to the commit message
file as its single argument.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Allowed subject prefixes, e.g. "feat: ...", "fix(scope): ...".
PATTERN = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|perf|build|ci|style|revert)"
    r"(\([\w./-]+\))?!?: .+"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("check_commit_msg: missing commit message file argument")
        return 1

    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    # First non-comment, non-blank line is the subject.
    subject = next(
        (
            line
            for line in message.splitlines()
            if line.strip() and not line.startswith("#")
        ),
        "",
    )

    # Ignore merge commits and other git-generated messages.
    if subject.startswith(("Merge ", "Revert ", "fixup!", "squash!")):
        return 0

    if not PATTERN.match(subject):
        print(
            "Commit subject must start with a conventional-commit prefix, e.g.\n"
            "  feat: add X\n  fix(parser): handle Y\n\n"
            f"Got: {subject!r}"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
