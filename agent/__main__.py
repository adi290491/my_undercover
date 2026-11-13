"""Run the UnderCover Agent from the command line: uv run -m agent CLM-1001."""

import sys
import uuid

from agent.main import run

USAGE = "Usage: uv run -m agent CLM-1001"


def main(args: list[str]) -> int:
    if len(args) != 1:
        print(USAGE)
        return 2
    print(run(args[0], str(uuid.uuid4())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
