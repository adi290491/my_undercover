"""Run the UnderCover Agent: uv run -m agent CLM-1001, or uv run -m agent queue."""

import sys
import uuid

from agent.main import run, work_queue

USAGE = "Usage: uv run -m agent CLM-1001, or uv run -m agent queue"


def main(args: list[str]) -> int:
    if len(args) != 1:
        print(USAGE)
        return 2
    if args[0] == "queue":
        for line in work_queue():
            print(line, flush=True)
    else:
        print(run(args[0], str(uuid.uuid4())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
