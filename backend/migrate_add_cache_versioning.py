"""
One-time migration: add source_pathway and corpus_version columns to cache_exact.

- source_pathway: "retrieval", "model", or "seed" — NULL for existing entries.
- corpus_version: hex digest of corpus files at write time — NULL for existing entries.

Existing entries with NULL source_pathway are treated conservatively:
  - In lookup_exact: retrieval invalidation only fires for rows where
    source_pathway == 'retrieval', so NULL rows are not affected.
  - This means pre-existing entries continue to be served until they expire
    normally via the 24h TTL.

Run from backend/:  python migrate_add_cache_versioning.py
"""
import sqlite3

COLUMNS = [
    ("source_pathway", "TEXT"),
    ("corpus_version",  "TEXT"),
]

con = sqlite3.connect("aiflow.db")
cur = con.cursor()

existing = {row[1] for row in cur.execute("PRAGMA table_info(cache_exact)").fetchall()}
print(f"Existing cache_exact columns: {sorted(existing)}")

added = []
for col_name, col_type in COLUMNS:
    if col_name not in existing:
        cur.execute(f"ALTER TABLE cache_exact ADD COLUMN {col_name} {col_type}")
        added.append(col_name)
        print(f"  Added: {col_name} {col_type}")
    else:
        print(f"  Already exists — skipped: {col_name}")

con.commit()

total = cur.execute("SELECT COUNT(*) FROM cache_exact").fetchone()[0]
retrieval_tagged = cur.execute(
    "SELECT COUNT(*) FROM cache_exact WHERE source_pathway='retrieval'"
).fetchone()[0]
print(f"\ncache_exact total rows: {total}")
print(f"  source_pathway='retrieval': {retrieval_tagged}")
print(f"  source_pathway=NULL:        {total - retrieval_tagged}")
if added:
    print(f"\nAdded {len(added)} column(s): {added}")
else:
    print("\nNo columns added — migration already applied.")
con.close()
print("Migration complete.")
