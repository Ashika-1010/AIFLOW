"""
One-time migration: add five CO₂e columns to the receipts table.

Safe to run against an existing database — skips columns that already exist.
Historical rows (including all is_demo=True seeds) will have NULL values in
these columns; they are never fabricated.

Run from backend/:  python migrate_add_co2e.py
"""
import sqlite3

COLUMNS = [
    ("co2e_low",           "REAL"),    # gCO₂e, low energy band
    ("co2e_central",       "REAL"),    # gCO₂e, central energy band
    ("co2e_high",          "REAL"),    # gCO₂e, high energy band
    ("co2e_grid_intensity","INTEGER"), # grid intensity used (gCO₂e/kWh)
    ("co2e_grid_source",   "TEXT"),    # "static" or "live"
]

con = sqlite3.connect("aiflow.db")
cur = con.cursor()

existing = {row[1] for row in cur.execute("PRAGMA table_info(receipts)").fetchall()}
print(f"Existing columns: {sorted(existing)}")

added = []
for col_name, col_type in COLUMNS:
    if col_name not in existing:
        cur.execute(f"ALTER TABLE receipts ADD COLUMN {col_name} {col_type}")
        added.append(col_name)
        print(f"  Added column: {col_name} {col_type}")
    else:
        print(f"  Column already exists — skipped: {col_name}")

con.commit()

real = cur.execute("SELECT COUNT(*) FROM receipts WHERE is_demo=0").fetchone()[0]
demo = cur.execute("SELECT COUNT(*) FROM receipts WHERE is_demo=1").fetchone()[0]
null_co2e = cur.execute(
    "SELECT COUNT(*) FROM receipts WHERE co2e_central IS NULL"
).fetchone()[0]

print(f"\nDatabase state: {real} real rows, {demo} demo rows")
print(f"Rows with NULL co2e_central (historical/demo): {null_co2e}")
if added:
    print(f"\nAdded {len(added)} column(s): {added}")
    print("Historical rows have NULL CO₂e values — this is correct and expected.")
else:
    print("\nNo columns added — migration already applied.")
con.close()
print("Migration complete.")
