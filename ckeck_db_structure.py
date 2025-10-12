import sqlite3

conn = sqlite3.connect('data/poker_trainer.db')
cursor = conn.cursor()
for context_id in [1, 2]:
    print(f"\n=== CONTEXTE {context_id} ===")
    cursor.execute(f"SELECT id, display_name, quiz_ready, needs_validation FROM range_contexts WHERE id = {context_id}")
    print(cursor.fetchone())


    cursor.execute("""
        SELECT range_key, name, label_canon 
        FROM ranges 
        WHERE context_id = 1 
        ORDER BY CAST(range_key AS INTEGER)
    """)
    for row in cursor.fetchall():
        print(f"Range {row[0]}: {row[1]} → label_canon='{row[2]}'")

conn.close()