"""
One-time migration: add is_demo column and mark seed fixtures.
Run from backend/: python migrate_add_is_demo.py
"""
import sqlite3

con = sqlite3.connect("aiflow.db")
cur = con.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(receipts)").fetchall()]
print("Current columns:", cols)

if "is_demo" not in cols:
    cur.execute("ALTER TABLE receipts ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")
    con.commit()
    print("Added is_demo column")
else:
    print("Column already exists — skipping ALTER")

# Mark AF-0261 to AF-0284 as demo (the seed_demo.py fixtures)
# Seed IDs are the first 24: AF-0261 … AF-0284
seed_ids = [f"AF-{n:04d}" for n in range(261, 285)]
placeholders = ",".join("?" * len(seed_ids))
cur.execute(
    f"UPDATE receipts SET is_demo=1 WHERE id IN ({placeholders})",
    seed_ids,
)
updated = cur.rowcount
con.commit()
print(f"Marked {updated} rows as is_demo=1")

real = cur.execute("SELECT COUNT(*) FROM receipts WHERE is_demo=0").fetchone()[0]
demo = cur.execute("SELECT COUNT(*) FROM receipts WHERE is_demo=1").fetchone()[0]
print(f"Real execution rows: {real}   Demo rows: {demo}")
con.close()
print("Migration complete.")
