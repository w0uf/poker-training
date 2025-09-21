#!/usr/bin/env python3
"""
Script de débogage pour diagnostiquer les problèmes de validation
"""

import sqlite3
import json
from pathlib import Path


def debug_database_content(db_path: str):
    """Débogue le contenu de la base de données"""

    print("🔍 DIAGNOSTIC DE LA BASE DE DONNÉES")
    print("=" * 50)

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        return

    with sqlite3.connect(db_path) as conn:

        # 1. Vérifier les fichiers importés
        print("\n📁 FICHIERS IMPORTÉS:")
        cursor = conn.execute("SELECT COUNT(*) FROM range_files")
        file_count = cursor.fetchone()[0]
        print(f"   Fichiers: {file_count}")

        if file_count > 0:
            cursor = conn.execute("SELECT filename, status FROM range_files")
            for row in cursor.fetchall():
                print(f"   • {row[0]} - {row[1]}")

        # 2. Vérifier les contextes
        print("\n📋 CONTEXTES:")
        cursor = conn.execute("SELECT COUNT(*) FROM range_contexts")
        context_count = cursor.fetchone()[0]
        print(f"   Contextes: {context_count}")

        if context_count > 0:
            cursor = conn.execute("""
                SELECT id, name, 
                       CASE 
                           WHEN enriched_metadata = '{}' OR enriched_metadata IS NULL THEN 'Non enrichi'
                           WHEN json_extract(enriched_metadata, '$.enriched_by_user') = 'true' THEN 'Enrichi'
                           ELSE 'Partiellement enrichi'
                       END as status
                FROM range_contexts
            """)

            enriched_count = 0
            for row in cursor.fetchall():
                print(f"   • [{row[0]}] {row[1]} - {row[2]}")
                if row[2] == 'Enrichi':
                    enriched_count += 1

            print(f"\n✅ Contextes enrichis: {enriched_count}/{context_count}")

        # 3. Vérifier les ranges
        print("\n🎯 RANGES:")
        cursor = conn.execute("SELECT COUNT(*) FROM ranges")
        range_count = cursor.fetchone()[0]
        print(f"   Ranges: {range_count}")

        # 4. Vérifier les mains
        print("\n🃏 MAINS:")
        cursor = conn.execute("SELECT COUNT(*) FROM range_hands")
        hand_count = cursor.fetchone()[0]
        print(f"   Mains: {hand_count}")

        # 5. Examiner un contexte en détail (si disponible)
        cursor = conn.execute("SELECT id, name, enriched_metadata FROM range_contexts LIMIT 1")
        row = cursor.fetchone()

        if row:
            print(f"\n🔬 EXEMPLE DE CONTEXTE:")
            print(f"   ID: {row[0]}")
            print(f"   Nom: {row[1]}")
            print(f"   Métadonnées enrichies:")

            try:
                metadata = json.loads(row[2]) if row[2] else {}
                if metadata:
                    for key, value in metadata.items():
                        print(f"      {key}: {value}")
                else:
                    print("      (vides)")
            except json.JSONDecodeError:
                print(f"      (erreur de parsing): {row[2]}")


def fix_validation_query():
    """Propose une requête corrigée pour trouver les contextes"""

    print("\n🔧 REQUÊTES DE DIAGNOSTIC:")

    queries = [
        ("Tous les contextes", "SELECT COUNT(*) FROM range_contexts"),
        ("Contextes avec métadonnées",
         "SELECT COUNT(*) FROM range_contexts WHERE enriched_metadata != '{}' AND enriched_metadata IS NOT NULL"),
        ("Contextes marqués enrichis",
         "SELECT COUNT(*) FROM range_contexts WHERE json_extract(enriched_metadata, '$.enriched_by_user') = 'true'"),
        ("Contextes marqués enrichis (string)",
         "SELECT COUNT(*) FROM range_contexts WHERE json_extract(enriched_metadata, '$.enriched_by_user') = 'true'"),
        ("Contextes avec confiance > 0", "SELECT COUNT(*) FROM range_contexts WHERE confidence > 0"),
    ]

    db_path = "data/poker_trainer.db"

    if Path(db_path).exists():
        with sqlite3.connect(db_path) as conn:
            for desc, query in queries:
                try:
                    cursor = conn.execute(query)
                    result = cursor.fetchone()[0]
                    print(f"   {desc}: {result}")
                except Exception as e:
                    print(f"   {desc}: ERREUR - {e}")


def suggest_fixes():
    """Propose des solutions selon le diagnostic"""

    print("\n💡 SOLUTIONS PROPOSÉES:")
    print("=" * 30)

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("1. 🔴 Lancer l'import des ranges:")
        print("   python import_ranges.py")
        return

    with sqlite3.connect(db_path) as conn:
        # Vérifier s'il y a des contextes
        cursor = conn.execute("SELECT COUNT(*) FROM range_contexts")
        context_count = cursor.fetchone()[0]

        if context_count == 0:
            print("1. 🔴 Aucun contexte trouvé - lancer l'import:")
            print("   python import_ranges.py")
            return

        # Vérifier s'il y a des contextes enrichis
        cursor = conn.execute("""
            SELECT COUNT(*) FROM range_contexts 
            WHERE json_extract(enriched_metadata, '$.enriched_by_user') = true
        """)
        enriched_count = cursor.fetchone()[0]

        if enriched_count == 0:
            print("1. 🟡 Contextes importés mais non enrichis:")
            print("   python enrich_ranges.py")

            # Vérifier si des métadonnées existent quand même
            cursor = conn.execute("""
                SELECT COUNT(*) FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.enriched_by_user') = true
                OR (enriched_metadata != '{}' 
                    AND json_extract(enriched_metadata, '$.hero_position') IS NOT NULL)
            """)
            partial_count = cursor.fetchone()[0]

            if partial_count > 0:
                print("\n2. 🔧 Ou corriger la requête de validation:")
                print("   Les métadonnées existent mais le flag 'enriched_by_user' n'est pas défini")
        else:
            print("1. ✅ Contextes enrichis trouvés - le problème est ailleurs")
            print("   Vérifier la logique de validation")


def main():
    """Point d'entrée du diagnostic"""

    db_path = "data/poker_trainer.db"

    debug_database_content(db_path)
    fix_validation_query()
    suggest_fixes()

    print("\n" + "=" * 50)
    print("🎯 CONCLUSION:")
    print("Suivez les solutions proposées dans l'ordre pour résoudre le problème.")


if __name__ == "__main__":
    main()