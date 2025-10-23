#!/usr/bin/env python3
"""
Script de test pour diagnostiquer la détection de conflits
À lancer depuis la racine du projet : python3 test_conflits.py
"""
import sys
from pathlib import Path

# Ajouter le dossier modules au path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules"))

from conflict_detector import ConflictDetector

# IDs des contextes à tester
CONTEXT_IDS = [1, 2]


def test_conflict_detection():
    print("=" * 60)
    print("TEST DE DÉTECTION DE CONFLITS")
    print("=" * 60)

    # Chemin vers la BDD
    db_path = project_root / "data" / "poker_trainer.db"
    print(f"\n📁 Base de données : {db_path}")

    if not db_path.exists():
        print(f"❌ ERREUR : Base de données non trouvée à {db_path}")
        return

    detector = ConflictDetector(str(db_path))

    # Charger les contextes
    conn = detector.get_connection()
    contexts = detector._load_contexts(conn, CONTEXT_IDS)

    print(f"\n📋 Contextes chargés : {len(contexts)}")
    for ctx in contexts:
        print(f"\n  ID {ctx['id']}: {ctx['display_name']}")
        print(f"    - Format: {ctx['table_format']}")
        print(f"    - Position: {ctx['hero_position']}")
        print(f"    - Stack: {ctx['stack_depth']}")
        print(f"    - Action: {ctx['primary_action']}")
        print(f"    - Sequence: {ctx.get('action_sequence')}")

    # Générer les clés de métadonnées
    print("\n🔑 Clés de métadonnées (ce que le système compare) :")
    metadata_keys = {}
    for ctx in contexts:
        key = detector._get_displayed_metadata_key(ctx)
        metadata_keys[ctx['id']] = key
        print(f"  ID {ctx['id']}: {key}")

    # Vérifier si les clés sont identiques
    unique_keys = set(metadata_keys.values())
    if len(unique_keys) > 1:
        print("\n⚠️  LES CONTEXTES ONT DES MÉTADONNÉES DIFFÉRENTES !")
        print("     → Ils ne seront PAS groupés ensemble pour la détection")
        print("     → Aucun conflit ne peut être détecté entre eux")
    else:
        print("\n✅ Les contextes ont les MÊMES métadonnées visibles")

    # Grouper par métadonnées
    groups = detector._group_by_displayed_metadata(contexts)
    print(f"\n📦 Groupes trouvés : {len(groups)}")
    for key, group_contexts in groups.items():
        print(f"\n  Groupe '{key}':")
        for ctx in group_contexts:
            print(f"    - ID {ctx['id']}: {ctx['display_name']}")

    if not groups:
        print("\n⚠️  Aucun groupe trouvé → Les contextes ne peuvent pas être en conflit")
        print("     car ils ont des métadonnées différentes")
        conn.close()
        return

    # Charger les ranges pour analyse
    print("\n📊 Chargement des ranges...")
    contexts_with_ranges = detector._load_ranges_for_contexts(conn, contexts)

    for ctx in contexts_with_ranges:
        ranges = ctx.get('ranges', [])
        print(f"\n  ID {ctx['id']} : {len(ranges)} range(s)")
        if ranges:
            for r in ranges[:5]:  # Afficher max 5 ranges
                print(f"    - {r['name']} ({r['label_canon']}) : {len(r['hands'])} mains")
            if len(ranges) > 5:
                print(f"    ... et {len(ranges) - 5} autres ranges")

    # Détecter les conflits
    print("\n🔍 Détection des conflits...")
    conflicts = detector.detect_conflicts(CONTEXT_IDS)

    if conflicts:
        print(f"\n⚠️  {len(conflicts)} groupe(s) avec conflits détectés !")
        for metadata_key, conflict_data in conflicts.items():
            print(f"\n{'=' * 60}")
            print(f"Groupe: {metadata_key}")
            print(f"{'=' * 60}")
            print(f"\nContextes impliqués:")
            for ctx in conflict_data['contexts']:
                print(f"  - ID {ctx['id']}: {ctx['name']}")
            print(f"\nTotal conflits: {conflict_data['total_conflicts']}")

            for level, hands_dict in conflict_data['conflicts_by_level'].items():
                print(f"\n📍 Niveau {level} : {len(hands_dict)} main(s) en conflit")
                # Afficher max 10 exemples
                displayed = 0
                for hand, actions in hands_dict.items():
                    if displayed < 10:
                        actions_str = ", ".join([f"Ctx{ctx_id}→{action}" for ctx_id, action in actions.items()])
                        print(f"    {hand}: {actions_str}")
                        displayed += 1
                if len(hands_dict) > 10:
                    print(f"    ... et {len(hands_dict) - 10} autres mains")
    else:
        print("\n✅ Aucun conflit détecté")
        print("\n🔍 Vérifications à faire:")
        print("  1. Les contextes ont-ils les MÊMES métadonnées visibles ?")
        print("     → Vérifie les 'Clés de métadonnées' ci-dessus")
        print("  2. Les contextes sont-ils quiz_ready=1 ?")
        print("  3. Y a-t-il des ranges chargées pour chaque contexte ?")
        print("  4. Les ranges ont-elles des mains en commun ?")

    conn.close()


if __name__ == "__main__":
    test_conflict_detection()