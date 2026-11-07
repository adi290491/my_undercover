"""Run the UnderCover Agent: uv run -m agent CLM-1001, or uv run -m agent queue."""

import sys
from uuid import uuid4

from agent.main import run, work_queue


def main(target: str) -> None:
    if target != "queue":
        print(run(target, str(uuid4())))
        return
    for claim_id, reply in work_queue():
        print(f"{claim_id}: {reply}")


if __name__ == "__main__":
    main(sys.argv[1])
