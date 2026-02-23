"""
scripts/cleanup_duplicates.py — Remove duplicate resume entries from the database.
"""

import sqlite3
import json
from pathlib import Path

# Adjust path based on execution location
DB_PATH = Path("data/resume_screening.db")

def cleanup():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("🔍 Searching for duplicate candidates...")
    
    # Find names that appear more than once
    duplicates = cursor.execute("""
        SELECT name, COUNT(*) as count 
        FROM resumes 
        GROUP BY name 
        HAVING count > 1
    """).fetchall()

    if not duplicates:
        print("✅ No duplicate candidates found.")
        conn.close()
        return

    print(f"Found {len(duplicates)} names with duplicates.")

    for dup in duplicates:
        name = dup["name"]
        print(f"\nProcessing: '{name}' ({dup['count']} entries)")

        # Get all entries for this name, ordered by date (newest first)
        entries = cursor.execute("""
            SELECT id, created_at 
            FROM resumes 
            WHERE name = ? 
            ORDER BY created_at DESC
        """, (name,)).fetchall()

        # Keep the newest one
        keep_id = entries[0]["id"]
        
        # Get others for removal (using loop to avoid slice indexing issues in some IDEs)
        remove_ids = []
        for i in range(1, len(entries)):
            remove_ids.append(entries[i]["id"])

        print(f"  Keeping ID: {keep_id} (Created at: {entries[0]['created_at']})")
        print(f"  Removing IDs: {remove_ids}")

        # Delete from rankings first (foreign key/integrity)
        for rid in remove_ids:
            cursor.execute("DELETE FROM rankings WHERE resume_id = ?", (rid,))
            cursor.execute("DELETE FROM resumes WHERE id = ?", (rid,))

    conn.commit()
    print(f"\n✨ Cleanup complete. Database vacuuming...")
    conn.execute("VACUUM")
    conn.close()
    print("✅ All done!")

if __name__ == "__main__":
    cleanup()
