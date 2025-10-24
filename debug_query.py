import sqlite3
conn = sqlite3.connect('data/poker_trainer.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT r.range_key, r.name, r.label_canon
    FROM ranges r
    JOIN range_hands rh ON r.id = rh.range_id
    WHERE r.context_id = 3
      AND rh.hand = 'AKo'
    ORDER BY r.range_key
""")

print("=== AKo dans quelles ranges ? ===")
for row in cursor.fetchall():
    print(f"Range {row[0]}: {row[1]} (label={row[2]})")