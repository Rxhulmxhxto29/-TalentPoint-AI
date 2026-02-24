
import sqlite3
import os
from config import DATABASE_PATH

def dump_results():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- RANKINGS ---")
    rankings = cursor.execute("SELECT * FROM rankings").fetchall()
    for r in rankings:
        print(dict(r))

    print("\n--- FEEDBACK ---")
    feedback = cursor.execute("SELECT * FROM feedback").fetchall()
    for f in feedback:
        print(dict(f))

    print("\n--- FEEDBACK STATS ---")
    total = cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    accepts = cursor.execute("SELECT COUNT(*) FROM feedback WHERE decision = 'accept'").fetchone()[0]
    rejects = cursor.execute("SELECT COUNT(*) FROM feedback WHERE decision = 'reject'").fetchone()[0]
    print(f"Total: {total}, Accepts: {accepts}, Rejects: {rejects}")

    print("\n--- RESUMES ---")
    resumes = cursor.execute("SELECT id, name FROM resumes").fetchall()
    for r in resumes:
        print(dict(r))

    conn.close()

if __name__ == "__main__":
    dump_results()
