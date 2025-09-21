#!/usr/bin/env python3
"""
Standardisateur de noms de ranges pour une détection d'action fiable
Propose des noms normalisés basés sur les actions détectées
"""

import sqlite3
import json
import re
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


class RangeNameStandardizer:
    """Standardise les noms de ranges et contextes pour une meilleure détection d'actions"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.standard_actions = {
            'call': ['call', 'calling', 'flat'],
            'fold': ['fold', 'folding'],
            '3bet_value': ['3bet value', '3-bet value', 'value 3bet', 'raise value'],
            '3bet_bluff': ['3bet bluff', '3-bet bluff', 'bluff 3bet', 'raise bluff'],
            'squeeze_value': ['squeeze value', 'squeeze val'],
            'squeeze_bluff': ['squeeze bluff', 'squeeze blf'],
            '4bet_value': ['4bet value', '4-bet value', 'value 4bet'],
            '4bet_bluff': ['4bet bluff', '4-bet bluff', 'bluff 4bet'],
            'open_raise': ['open', 'opening', 'rfi', 'raise first in'],
            'check': ['check', 'checking'],
            'shove': ['shove', 'all-in', 'jam', 'push'],
            'limp': ['limp', 'limping']
        }

        self.standard_positions = {
            'UTG': ['utg', 'under the gun'],
            'UTG1': ['utg+1', 'utg1', 'utg+', 'under the gun +1'],
            'MP': ['mp', 'middle position'],
            'MP1': ['mp+1', 'mp1', 'mp+', 'middle position +1'],
            'LJ': ['lj', 'lojack'],
            'HJ': ['hj', 'hijack'],
            'CO': ['co', 'cutoff', 'cut-off'],
            'BTN': ['btn', 'bu', 'button'],
            'SB': ['sb', 'small blind'],
            'BB': ['bb', 'big blind']
        }

    def analyze_context_names(self) -> List[Dict]:
        """Analyse les noms de contextes et propose des standardisations"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, file_id
                FROM range_contexts
                ORDER BY name
            """)

            contexts = []
            for row in cursor.fetchall():
                context_id, name, file_id = row

                # Analyser le nom du contexte
                standardized_name = self._standardize_context_name(name)

                contexts.append({
                    'id': context_id,
                    'current_name': name,
                    'suggested_name': standardized_name,
                    'file_id': file_id,
                    'needs_change': standardized_name != name
                })

            return contexts

    def _standardize_context_name(self, context_name: str) -> str:
        """Standardise le nom d'un contexte"""

        name = context_name.strip()

        # Normaliser les positions
        for standard_pos, variations in self.standard_positions.items():
            for variation in variations:
                # Remplacer en respectant les majuscules/minuscules et espaces
                pattern = r'\b' + re.escape(variation) + r'\b'
                name = re.sub(pattern, standard_pos, name, flags=re.IGNORECASE)

        # Normaliser les termes courants
        replacements = {
            r'\bOpen\b': 'open',
            r'\bRaise\b': 'raise',
            r'\bDefense\b|\bDefence\b|\bDéfense\b': 'defense',
            r'\bvs\.?\b|\bv\.?\b': 'vs',
            r'\bcontre\b': 'vs'
        }

        for pattern, replacement in replacements.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        # Nettoyer les espaces multiples
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def interactive_full_standardization(self):
        """Mode interactif pour standardiser contextes ET ranges"""

        print("🔧 STANDARDISATION COMPLÈTE (CONTEXTES + RANGES)")
        print("=" * 60)

        # Étape 1: Standardiser les contextes
        print("\n📋 ÉTAPE 1: STANDARDISATION DES CONTEXTES")
        print("-" * 40)

        contexts = self.analyze_context_names()
        contexts_to_change = [c for c in contexts if c['needs_change']]

        if contexts_to_change:
            print(f"📊 {len(contexts_to_change)} contextes à standardiser:")

            for i, context in enumerate(contexts_to_change, 1):
                print(f"\n   {i}. Contexte actuel: '{context['current_name']}'")
                print(f"      Nom suggéré: '{context['suggested_name']}'")

            choice = input(f"\n🔧 Standardiser ces contextes ? (o/n): ").strip().lower()

            if choice.startswith('o'):
                context_changes = self._apply_context_standardization(contexts_to_change)
                print(f"✅ {context_changes} contextes standardisés")
            else:
                print("⏭️ Standardisation des contextes ignorée")
        else:
            print("✅ Tous les contextes ont déjà des noms standards")

        # Étape 2: Standardiser les ranges
        print(f"\n📋 ÉTAPE 2: STANDARDISATION DES RANGES")
        print("-" * 40)

        self.interactive_standardization()

    def _apply_context_standardization(self, contexts_to_change: List[Dict]) -> int:
        """Applique la standardisation aux contextes"""

        changes_applied = 0

        with sqlite3.connect(self.db_path) as conn:
            for context in contexts_to_change:
                try:
                    # Mettre à jour le nom du contexte en base
                    conn.execute("""
                        UPDATE range_contexts 
                        SET name = ?
                        WHERE id = ?
                    """, (context['suggested_name'], context['id']))

                    changes_applied += 1
                    print(f"  ✅ '{context['current_name']}' → '{context['suggested_name']}'")

                except Exception as e:
                    print(f"  ❌ Erreur pour '{context['current_name']}': {e}")

            conn.commit()

        return changes_applied

    def analyze_range_names(self, context_id: int) -> List[Dict]:
        """Analyse les noms de ranges d'un contexte et propose des standardisations"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, range_key, color
                FROM ranges
                WHERE context_id = ?
                ORDER BY range_key
            """, (context_id,))

            ranges = []
            for row in cursor.fetchall():
                range_id, name, range_key, color = row

                # Analyser le nom actuel
                detected_action = self._detect_action_from_name(name)
                suggested_name = self._suggest_standard_name(name, detected_action)

                ranges.append({
                    'id': range_id,
                    'current_name': name,
                    'range_key': range_key,
                    'color': color,
                    'detected_action': detected_action,
                    'suggested_name': suggested_name,
                    'needs_change': suggested_name != name
                })

            return ranges

    def _detect_action_from_name(self, name: str) -> Optional[str]:
        """Détecte l'action d'une range basée sur son nom - VERSION CORRIGÉE"""

        name_lower = name.lower().strip()
        if 'défense' in name_lower or 'defense' in name_lower:
            return 'defense'
        # PRIORITÉ 1: Actions du héros au début du nom (plus importantes)
        hero_action_priority = [
            ('defense', ['def', 'déf', 'defend']),
            ('call', ['call', 'calling', 'flat']),
            ('fold', ['fold', 'folding']),
            ('open_raise', ['open', 'opening', 'rfi']),
            ('check', ['check', 'checking']),
            ('shove', ['shove', 'all-in', 'jam', 'push']),
            ('limp', ['limp', 'limping'])
        ]

        # Vérifier si le nom COMMENCE par une action du héros
        for action, keywords in hero_action_priority:
            for keyword in keywords:
                if name_lower.startswith(keyword):
                    return action

        # PRIORITÉ 2: Actions 3bet/4bet avec value/bluff
        bet_patterns = {
            'squeeze_value': r'squeeze.*val|val.*squeeze',
            'squeeze_bluff': r'squeeze.*bluff|bluff.*squeeze',
            '3bet_value': r'3\s*bet.*val|val.*3\s*bet|raise.*val',
            '3bet_bluff': r'3\s*bet.*bluff|bluff.*3\s*bet|raise.*bluff',
            '4bet_value': r'4\s*bet.*val|val.*4\s*bet',
            '4bet_bluff': r'4\s*bet.*bluff|bluff.*4\s*bet'
        }

        for action, pattern in bet_patterns.items():
            if re.search(pattern, name_lower, re.IGNORECASE):
                return action

        # PRIORITÉ 3: Actions simples (sans value/bluff)
        simple_patterns = {
            '3bet_value': r'\b3\s*bet\b|\b3-bet\b',  # 3bet simple = value par défaut
            '4bet_value': r'\b4\s*bet\b|\b4-bet\b',  # 4bet simple = value par défaut
            'squeeze_value': r'\bsqueeze\b'  # squeeze simple = value par défaut
        }

        for action, pattern in simple_patterns.items():
            if re.search(pattern, name_lower, re.IGNORECASE):
                return action

        # PRIORITÉ 4: Fallback basé sur des mots dans le nom (peu fiable)
        fallback_keywords = {
            'call': ['call', 'calling', 'flat'],
            'fold': ['fold', 'folding'],
            'open_raise': ['open', 'opening', 'rfi']  # Seulement si pas déjà détecté en priorité 1
        }

        # Pour le fallback, vérifier que ce n'est pas dans un contexte "vs"
        if not re.search(r'vs\s+\w+\s+(open|call|fold)', name_lower):
            for action, keywords in fallback_keywords.items():
                for keyword in keywords:
                    if keyword in name_lower:
                        return action

        return None

    def _suggest_standard_name(self, current_name: str, detected_action: Optional[str]) -> str:
        """Propose un nom standardisé"""

        name_lower = current_name.lower().strip()

        # Gérer les noms génériques problématiques
        generic_names = [
            'range principale', 'range principal', 'range', 'principal', 'principale',
            'main range', 'default', 'défaut', 'base', 'general', 'général',
            'sous-range', 'sub-range', 'range 1', 'range 2', 'range 3'
        ]

        if any(generic in name_lower for generic in generic_names):
            # Pour les noms génériques, essayer de deviner basé sur le contexte
            return self._guess_action_from_generic_name(current_name)

        if detected_action:
            return detected_action

        # Si aucune action détectée, essayer de deviner
        # Patterns fréquents
        if any(word in name_lower for word in ['def', 'defend']):
            return 'call'  # Défense = souvent call
        elif 'tight' in name_lower:
            return '3bet_value'
        elif 'loose' in name_lower or 'wide' in name_lower:
            return '3bet_bluff'

        # Si vraiment rien trouvé, proposer une action par défaut
        return 'call'  # Action la plus commune par défaut

    def _guess_action_from_generic_name(self, generic_name: str) -> str:
        """Devine l'action pour un nom générique basé sur des indices"""

        name_lower = generic_name.lower()

        # Basé sur des patterns numériques ou des indices
        if any(pattern in name_lower for pattern in ['1', 'un', 'first', 'premier']):
            return 'fold'  # Premier choix souvent fold
        elif any(pattern in name_lower for pattern in ['2', 'deux', 'second', 'deuxième']):
            return 'call'  # Deuxième choix souvent call
        elif any(pattern in name_lower for pattern in ['3', 'trois', 'third', 'troisième']):
            return '3bet_value'  # Troisième choix souvent 3bet

        # Basé sur des mots-clés dans le nom générique
        if 'principal' in name_lower or 'main' in name_lower:
            return 'call'  # Action principale souvent call
        elif 'sous' in name_lower or 'sub' in name_lower:
            return '3bet_value'  # Sous-range souvent plus agressive

        # Fallback
        return 'call'

    def interactive_standardization(self):
        """Mode interactif pour standardiser les noms de ranges"""

        print("🔧 STANDARDISATION DES NOMS DE RANGES")
        print("=" * 50)

        # Récupérer tous les contextes
        contexts = self._get_all_contexts()

        if not contexts:
            print("❌ Aucun contexte trouvé")
            return

        print(f"📋 {len(contexts)} contextes trouvés\n")

        total_changes = 0

        for i, context in enumerate(contexts, 1):
            print(f"{'=' * 60}")
            print(f"📋 CONTEXTE {i}/{len(contexts)}: {context['name']}")
            print(f"{'=' * 60}")

            # Analyser les ranges de ce contexte
            ranges = self.analyze_range_names(context['id'])
            ranges_to_change = [r for r in ranges if r['needs_change']]

            if not ranges_to_change:
                print("✅ Toutes les ranges ont déjà des noms standards")
                continue

            print(f"📊 {len(ranges_to_change)} ranges à standardiser:")

            # Afficher les propositions
            for j, range_data in enumerate(ranges_to_change, 1):
                print(f"\n   {j}. Range actuelle: '{range_data['current_name']}'")
                print(f"      Action détectée: {range_data['detected_action'] or 'Aucune'}")
                print(f"      Nom suggéré: '{range_data['suggested_name']}'")

            # Demander confirmation
            choice = input(
                f"\n🔧 Standardiser ces {len(ranges_to_change)} ranges ? (o/n/d pour détails): ").strip().lower()

            if choice == 'd':
                self._show_detailed_suggestions(ranges_to_change)
                choice = input("Procéder à la standardisation ? (o/n): ").strip().lower()

            if choice.startswith('o'):
                # Appliquer les changements
                changes_applied = self._apply_standardization(context, ranges_to_change)
                total_changes += changes_applied
                print(f"✅ {changes_applied} ranges standardisées")
            else:
                print("⏭️ Contexte ignoré")

        if total_changes > 0:
            print(f"\n🎉 STANDARDISATION TERMINÉE")
            print(f"✅ {total_changes} ranges standardisées au total")
            print("💡 Relancez l'enrichissement pour bénéficier des noms standards")
        else:
            print("\n👍 Aucune standardisation nécessaire")

    def _get_all_contexts(self) -> List[Dict]:
        """Récupère tous les contextes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, file_id
                FROM range_contexts
                ORDER BY name
            """)

            return [{'id': row[0], 'name': row[1], 'file_id': row[2]} for row in cursor.fetchall()]

    def _show_detailed_suggestions(self, ranges: List[Dict]):
        """Affiche les suggestions détaillées"""

        print(f"\n📋 DÉTAIL DES STANDARDISATIONS:")
        print("-" * 40)

        for range_data in ranges:
            print(f"\nRange: {range_data['current_name']}")
            print(f"  🔍 Analyse: {range_data['detected_action'] or 'Action non détectée'}")
            print(f"  💡 Suggestion: {range_data['suggested_name']}")

            if range_data['detected_action']:
                print(f"  ✅ Confiance: Élevée")
            else:
                print(f"  ⚠️ Confiance: Faible (basé sur heuristiques)")

    def _apply_standardization(self, context: Dict, ranges_to_change: List[Dict]) -> int:
        """Applique la standardisation aux ranges"""

        changes_applied = 0

        with sqlite3.connect(self.db_path) as conn:
            for range_data in ranges_to_change:
                try:
                    # Mettre à jour le nom en base
                    conn.execute("""
                        UPDATE ranges 
                        SET name = ?
                        WHERE id = ?
                    """, (range_data['suggested_name'], range_data['id']))

                    changes_applied += 1
                    print(f"  ✅ '{range_data['current_name']}' → '{range_data['suggested_name']}'")

                except Exception as e:
                    print(f"  ❌ Erreur pour '{range_data['current_name']}': {e}")

            conn.commit()

        return changes_applied

    def update_source_json_files(self):
        """Met à jour les fichiers JSON sources avec les noms standardisés"""

        print("\n🔄 MISE À JOUR DES FICHIERS JSON SOURCES")
        print("=" * 50)

        # Récupérer les fichiers et leurs ranges actuelles
        file_updates = self._prepare_json_updates()

        if not file_updates:
            print("✅ Aucune mise à jour JSON nécessaire")
            return

        print(f"📁 {len(file_updates)} fichiers à mettre à jour")

        for file_path, updates in file_updates.items():
            print(f"\n📄 {file_path}:")
            for old_name, new_name in updates:
                print(f"  '{old_name}' → '{new_name}'")

        confirm = input(f"\n💾 Mettre à jour les fichiers JSON sources ? (o/n): ").strip().lower()

        if confirm.startswith('o'):
            updated_count = self._update_json_files(file_updates)
            print(f"✅ {updated_count} fichiers mis à jour")
        else:
            print("❌ Mise à jour des JSON annulée")

    def _prepare_json_updates(self) -> Dict[str, List[Tuple[str, str]]]:
        """Prépare les mises à jour nécessaires pour les fichiers JSON"""

        file_updates = {}

        with sqlite3.connect(self.db_path) as conn:
            # Récupérer les informations de tous les fichiers et ranges
            cursor = conn.execute("""
                SELECT rf.filename, r.range_key, r.name, rc.original_data
                FROM ranges r
                JOIN range_contexts rc ON r.context_id = rc.id
                JOIN range_files rf ON rc.file_id = rf.id
                ORDER BY rf.filename, r.range_key
            """)

            current_file = None
            current_data = None

            for row in cursor.fetchall():
                filename, range_key, current_name, original_data_str = row

                if filename != current_file:
                    current_file = filename
                    current_data = json.loads(original_data_str)

                # Vérifier si le nom a changé par rapport au JSON original
                original_name = current_data.get('data', {}).get('ranges', {}).get(range_key, {}).get('name', '')

                if original_name and original_name != current_name:
                    file_path = f"data/ranges/{filename}"

                    if file_path not in file_updates:
                        file_updates[file_path] = []

                    file_updates[file_path].append((original_name, current_name))

        return file_updates

    def _update_json_files(self, file_updates: Dict[str, List[Tuple[str, str]]]) -> int:
        """Met à jour les fichiers JSON avec les nouveaux noms"""

        updated_count = 0

        for file_path, updates in file_updates.items():
            try:
                # Backup du fichier original
                backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(file_path, backup_path)
                print(f"💾 Backup créé: {backup_path}")

                # Charger le JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Appliquer les changements
                ranges_data = data.get('data', {}).get('ranges', {})

                for old_name, new_name in updates:
                    for range_key, range_info in ranges_data.items():
                        if range_info.get('name') == old_name:
                            range_info['name'] = new_name
                            break

                # Sauvegarder le JSON modifié
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                updated_count += 1
                print(f"✅ {file_path} mis à jour")

            except Exception as e:
                print(f"❌ Erreur mise à jour {file_path}: {e}")

        return updated_count


def main():
    """Point d'entrée principal"""

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord l'import des ranges")
        return

    standardizer = RangeNameStandardizer(db_path)

    print("Choisissez une option:")
    print("1. Standardisation complète (contextes + ranges)")
    print("2. Standardiser seulement les noms de ranges")
    print("3. Standardiser seulement les contextes")
    print("4. Mettre à jour les fichiers JSON sources")

    choice = input("\nVotre choix (1-4): ").strip()

    if choice == "1":
        standardizer.interactive_full_standardization()

        # Proposer mise à jour JSON après standardisation
        update_json = input("\n💾 Mettre à jour les fichiers JSON sources ? (o/n): ").strip().lower()
        if update_json.startswith('o'):
            standardizer.update_source_json_files()

    elif choice == "2":
        standardizer.interactive_standardization()

    elif choice == "3":
        contexts = standardizer.analyze_context_names()
        contexts_to_change = [c for c in contexts if c['needs_change']]

        if contexts_to_change:
            print(f"📊 {len(contexts_to_change)} contextes à standardiser:")
            for i, context in enumerate(contexts_to_change, 1):
                print(f"   {i}. '{context['current_name']}' → '{context['suggested_name']}'")

            choice = input("\nStandardiser ? (o/n): ").strip().lower()
            if choice.startswith('o'):
                changes = standardizer._apply_context_standardization(contexts_to_change)
                print(f"✅ {changes} contextes standardisés")
        else:
            print("✅ Tous les contextes sont déjà standards")

    elif choice == "4":
        standardizer.update_source_json_files()

    else:
        print("❌ Choix invalide")


if __name__ == "__main__":
    main()