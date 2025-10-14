#!/usr/bin/env python3
"""
Script de diagnostic pour identifier pourquoi certains contextes sont ignorés
"""

import sqlite3
import json
import sys
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))


def diagnose_contexts(db_path: str = "data/poker_trainer.db"):
    """Diagnostique tous les contextes et identifie les problèmes"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Récupérer TOUS les contextes (pas seulement quiz_ready=1)
    cursor.execute("""
        SELECT 
            id, display_name, table_format, hero_position, 
            primary_action, quiz_ready, action_sequence
        FROM range_contexts 
        ORDER BY id
    """)

    contexts = cursor.fetchall()

    print(f"🔍 DIAGNOSTIC DE {len(contexts)} CONTEXTES\n")
    print("=" * 80)

    for ctx in contexts:
        ctx_id = ctx['id']
        print(f"\n📋 CONTEXTE #{ctx_id}: {ctx['display_name']}")
        print(f"   Action: {ctx['primary_action']}")
        print(f"   Position: {ctx['hero_position']} ({ctx['table_format']})")

        # Vérifier quiz_ready
        if ctx['quiz_ready'] != 1:
            print(f"   ❌ PROBLÈME: quiz_ready = {ctx['quiz_ready']} (doit être 1)")
            continue
        else:
            print(f"   ✅ quiz_ready = 1")

        # Vérifier action_sequence si nécessaire
        if ctx['action_sequence']:
            try:
                seq = json.loads(ctx['action_sequence'])
                print(f"   📗 action_sequence: {seq}")
            except:
                print(f"   ⚠️  action_sequence invalide")

        # Vérifier les ranges
        cursor.execute("""
            SELECT 
                r.id, r.range_key, r.name, r.label_canon,
                COUNT(DISTINCT rh.hand) as hand_count
            FROM ranges r
            LEFT JOIN range_hands rh ON r.id = rh.range_id
            WHERE r.context_id = ?
            GROUP BY r.id
            ORDER BY r.range_key
        """, (ctx_id,))

        ranges = cursor.fetchall()

        if not ranges:
            print(f"   ❌ PROBLÈME: Aucune range trouvée")
            continue

        print(f"   📊 {len(ranges)} ranges:")

        # Vérifier la range principale
        main_range = None
        for r in ranges:
            is_main = "🎯" if r['range_key'] == '1' else "  "
            print(f"      {is_main} Range {r['range_key']}: {r['name']}")
            print(f"         label_canon='{r['label_canon']}', {r['hand_count']} mains")

            if r['range_key'] == '1':
                main_range = r

        if not main_range:
            print(f"   ❌ PROBLÈME: Pas de range principale (range_key='1')")
            continue

        if main_range['hand_count'] == 0:
            print(f"   ❌ PROBLÈME: Range principale vide (0 mains)")
            continue

        if not main_range['label_canon'] or main_range['label_canon'] == 'None':
            print(f"   ❌ PROBLÈME: label_canon invalide pour range principale")
            continue

        # Test de normalisation
        from poker_constants import normalize_action
        normalized = normalize_action(main_range['label_canon'])

        if not normalized:
            print(f"   ❌ PROBLÈME: label_canon '{main_range['label_canon']}' ne se normalise pas")
            continue

        print(f"   ✅ label_canon '{main_range['label_canon']}' → '{normalized}'")
        print(f"   ✅✅✅ CONTEXTE VALIDE - Devrait générer des questions")

    conn.close()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    diagnose_contexts()