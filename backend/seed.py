"""Rebuild the UnderCover database from data/."""

from backend.db import db_path, seed

if __name__ == "__main__":
    seed()
    print(f"Seeded {db_path()}")
