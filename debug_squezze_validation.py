#!/usr/bin/env python3
"""
Debug pourquoi SQUEEZE ne génère pas de questions
"""

import sys
from pathlib import Path

# Ajouter src au path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

import sqlite3


def debug_squeeze():
    """Debug complet du contexte squeeze"""

    print("🔍 DEBUG DU CONTEXTE SQUEEZE\n")
    print("=" * 80)

    # 1. Vérifier la base de données
    conn = sqlite3.connect("data/poker_trainer.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            rc.id,
            rc.display_name,
            rc.primary_action,
            rc.quiz_ready,
            r.range_key,
            r.name as range_name,
            r.label_canon,
            COUNT(rh.hand) as hand_count
        FROM range_contexts rc
        JOIN ranges r ON rc.id = r.context_id
        LEFT JOIN range_hands rh ON r.id = rh.range_id
        WHERE rc.primary_action = 'squeeze'
        GROUP BY r.id
        ORDER BY CAST(r.range_key AS INTEGER)
    """)

    squeeze_data = cursor.fetchall()

    if not squeeze_data:
        print("❌ Aucun contexte avec primary_action='squeeze' trouvé !")
        print("\nVérifions tous les primary_action :")
        cursor.execute("SELECT DISTINCT primary_action FROM range_contexts")
        actions = cursor.fetchall()
        for a in actions:
            print(f"  - {a[0]}")
        conn.close()
        return

    print(f"✅ Contexte squeeze trouvé : ID={squeeze_data[0]['id']}")
    print(f"   Nom: {squeeze_data[0]['display_name']}")
    print(f"   quiz_ready: {squeeze_data[0]['quiz_ready']}")
    print(f"\n📊 Ranges du contexte squeeze :")

    main_range = None
    for row in squeeze_data:
        is_main = "🎯" if row['range_key'] == '1' else "  "
        print(f"{is_main} Range {row['range_key']}: {row['range_name']}")
        print(f"   label_canon='{row['label_canon']}', {row['hand_count']} mains")

        if row['range_key'] == '1':
            main_range = row

    conn.close()

    if not main_range:
        print("\n❌ Pas de range principale (range_key='1') !")
        return

    # 2. Tester la normalisation
    print(f"\n{'=' * 80}")
    print("🔧 TEST DE NORMALISATION")
    print("=" * 80)

    label = main_range['label_canon']
    print(f"\nLabel de la range principale : '{label}'")

    try:
        from poker_constants import normalize_action

        normalized = normalize_action(label)
        print(f"Résultat de normalize_action('{label}') : '{normalized}'")

        if not normalized:
            print(f"\n❌ PROBLÈME TROUVÉ : normalize_action('{label}') retourne None !")
            print(f"\n💡 Solution : Ajouter '{label}' dans le mapping de normalize_action")
            print(f"\nDans poker_constants.py, vérifiez que le mapping contient :")
            print(f"  'SQUEEZE': 'RAISE'  ou  'SQUEEZE': 'SQUEEZE'")
        else:
            print(f"✅ Normalisation OK : '{label}' → '{normalized}'")

    except ImportError as e:
        print(f"❌ Impossible d'importer poker_constants : {e}")
        return

    # 3. Tester la génération de question
    print(f"\n{'=' * 80}")
    print("🎲 TEST DE GÉNÉRATION DE QUESTION")
    print("=" * 80)

    try:
        from quiz_generator import QuizGenerator

        generator = QuizGenerator()
        context_id = main_range['id']

        print(f"\nTentative de génération pour context_id={context_id}")

        for i in range(1, 4):
            print(f"\n  Tentative {i}/3:")
            question = generator.generate_question(context_id)

            if question:
                print(f"  ✅ Question générée !")
                print(f"     Main: {question['hand']}")
                print(f"     Réponse: {question['correct_answer']}")
                break
            else:
                print(f"  ❌ Échec (voir logs [QUIZ] ci-dessus)")

    except Exception as e:
        print(f"❌ Erreur lors de la génération : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_squeeze()