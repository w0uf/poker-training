"""
Script pour vérifier la structure de la base de données
"""
import sqlite3
from pathlib import Path

db_path = Path("data/poker_trainer.db")

if not db_path.exists():
    print("Base de données non trouvée !")
    exit(1)

with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()

    # Récupérer la structure de range_contexts
    cursor.execute("PRAGMA table_info(range_contexts)")
    columns = cursor.fetchall()

    print("=" * 60)
    print("STRUCTURE DE LA TABLE range_contexts")
    print("=" * 60)

    for col in columns:
        print(f"{col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else ''}")

    print("\n" + "=" * 60)
    print("EXEMPLE DE DONNÉES")
    print("=" * 60)

    # Afficher un exemple
    cursor.execute("SELECT * FROM range_contexts LIMIT 1")
    row = cursor.fetchone()

    if row:
        for i, col in enumerate(columns):
            print(f"{col[1]:20} = {row[i]}")
    else:
        print("Aucune donnée dans la table")