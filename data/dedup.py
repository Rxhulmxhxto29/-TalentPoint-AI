"""
data/dedup.py — Remove duplicate resumes keeping only the latest entry per name.
Also cascades deletes to rankings and feedback tables.
"""
import sqlite3
import sys

DB_PATH = "data/resume_screening.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT id, name FROM resumes ORDER BY name, id").fetchall()
print(f"Total resumes before cleanup: {len(rows)}")

# Group by name, keep the highest (latest) id
from collections import defaultdict
groups: defaultdict[str, list[int]] = defaultdict(list)
for r in rows:
    groups[r["name"]].append(r["id"])

to_delete: list[int] = []
for name, ids in groups.items():
    ids_sorted: list[int] = sorted(ids)
    keep = ids_sorted[-1]  # keep newest id
    dupes = ids_sorted[:-1]
    if dupes:
        print(f"  '{name}': keeping id={keep}, deleting ids={dupes}")
        to_delete.extend(dupes)

if not to_delete:
    print("No duplicates found.")
    conn.close()
    sys.exit(0)

# Cascade delete
for rid in to_delete:
    conn.execute("DELETE FROM feedback WHERE resume_id = ?", (rid,))
    conn.execute("DELETE FROM rankings WHERE resume_id = ?", (rid,))
    conn.execute("DELETE FROM resumes WHERE id = ?", (rid,))

conn.commit()

remaining = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
print(f"\nTotal resumes after cleanup: {remaining}")
print("Done!")
conn.close()
