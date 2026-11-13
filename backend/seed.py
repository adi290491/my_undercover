"""Rebuild the database from data/, with every claim waiting."""

from backend import db

if __name__ == "__main__":
    count = db.seed()
    print(f"Seeded {db.db_path()} with {count} claims, all waiting.")
