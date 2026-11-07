"""Run the UnderCover Agent on one claim: uv run -m agent CLM-1001."""

import sys
import uuid

from agent.main import run


def main(claim_id: str) -> None:
    print(run(claim_id, str(uuid.uuid4())))


if __name__ == "__main__":
    main(sys.argv[1])
