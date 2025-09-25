#!/usr/bin/env python3
"""
v25092025
Standardisateur de noms de ranges pour une détection d'action fiable
Propose des noms normalisés basés sur les actions détectées
VERSION CORRIGÉE: Validation des positions selon le format de table + corrections sécurisées
"""

import sqlite3
import json
import re
import shutil
import tempfile
import os
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

    def _validate_position_for_table_format(self, position: str, table_format: str) -> str:
        """Valide et corrige une position selon le format de table"""

        # Positions valides par format
        valid_positions = {
            '5max': ['UTG', 'CO', 'BTN', 'SB', 'BB'],
            '6max': ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'],
            '9max': ['UTG', 'UTG1', 'MP', 'MP1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB'],
            'heads-up': ['BTN', 'BB']
        }

        # Mapping des positions invalides vers valides
        position_mapping = {
            '5max': {
                'MP': 'CO',  # MP n'existe pas en 5max -> CO
                'MP1': 'CO',  # MP+1 n'existe pas en 5max -> CO
                'UTG1': 'CO',  # UTG+1 n'existe pas en 5max -> CO
                'HJ': 'CO',  # HJ n'existe pas en 5max -> CO
                'LJ': 'CO'  # LJ n'existe pas en 5max -> CO
            },
            '6max': {
                'MP1': 'CO',  # MP+1 n'existe pas en 6max
                'UTG1': 'MP',  # UTG+1 devient MP en 6max
                'LJ': 'CO',  # LJ devient CO en 6max
                'HJ': 'CO'  # HJ devient CO en 6max
            }
        }

        # Si position valide pour ce format, la retourner
        if position in valid_positions.get(table_format, []):
            return position

        # Sinon, mapper vers position valide
        return position_mapping.get(table_format, {}).get(position, position)

    def _detect_table_format_from_context_name(self, context_name: str) -> str:
        """Détecte le format de table depuis le nom du contexte"""
        name_lower = context_name.lower()

        if any(indicator in name_lower for indicator in ['5max', '5-max', '5 max']):
            return '5max'
        elif any(indicator in name_lower for indicator in ['6max', '6-max', '6 max']):
            return '6max'
        elif any(indicator in name_lower for indicator in ['9max', '9-max', '9 max', 'full ring', 'fr']):
            return '9max'
        elif any(indicator in name_lower for indicator in ['hu', 'heads up', 'heads-up']):
            return 'heads-up'
        else:
            return '6max'  # Défaut

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
        """Standardise le nom d'un contexte - VERSION CORRIGÉE avec validation positions"""

        name = context_name.strip()

        # Détecter le format de table AVANT de normaliser les positions
        table_format = self._detect_table_format_from_context_name(name)

        # Normaliser les positions
        for standard_pos, variations in self.standard_positions.items():
            for variation in variations:
                # Remplacer en respectant les majuscules/minuscules et espaces
                pattern = r'\b' + re.escape(variation) + r'\b'
                name = re.sub(pattern, standard_pos, name, flags=re.IGNORECASE)

        # NOUVEAU: Valider les positions selon le format de table
        # Extraire les positions du nom standardisé
        positions_in_name = []
        for std_pos in self.standard_positions.keys():
            if std_pos in name:
                positions_in_name.append(std_pos)

        # Corriger les positions invalides
        for position in positions_in_name:
            corrected_position = self._validate_position_for_table_format(position, table_format)
            if corrected_position != position:
                name = name.replace(position, corrected_position)

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
                print("⭐ Standardisation des contextes ignorée")
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
                print("⭐ Contexte ignoré")

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

    def _prepare_json_updates(self) -> Dict[str, List[Tuple[str, str]]]:
        """Version améliorée avec validation et gestion d'erreurs"""
        file_updates = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT rf.filename, r.range_key, r.name, rc.original_data
                FROM ranges r
                JOIN range_contexts rc ON r.context_id = rc.id
                JOIN range_files rf ON rc.file_id = rf.id
                WHERE r.name != '' AND r.name IS NOT NULL
                ORDER BY rf.filename, r.range_key
            """)

            processed_files = {}

            for row in cursor.fetchall():
                filename, range_key, current_name, original_data_str = row

                try:
                    # Parser le JSON original pour ce fichier (une seule fois par fichier)
                    if filename not in processed_files:
                        original_data = json.loads(original_data_str)
                        processed_files[filename] = original_data

                    original_data = processed_files[filename]
                    original_ranges = original_data.get('data', {}).get('ranges', {})

                    # Vérifier si le nom a changé par rapport au JSON original
                    if range_key in original_ranges:
                        original_name = original_ranges[range_key].get('name', '')

                        if original_name and original_name != current_name:
                            file_path = f"data/ranges/{filename}"

                            if file_path not in file_updates:
                                file_updates[file_path] = []

                            # Éviter les doublons
                            update_pair = (original_name, current_name)
                            if update_pair not in file_updates[file_path]:
                                file_updates[file_path].append(update_pair)

                except json.JSONDecodeError as e:
                    print(f"⚠️ Erreur JSON pour {filename}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ Erreur processing {filename}: {e}")
                    continue

        return file_updates

    def _validate_json_structure(self, data: dict) -> bool:
        """
        Valide que le JSON a la structure attendue pour un fichier de ranges
        """
        try:
            # Vérifications de base
            if not isinstance(data, dict):
                return False

            # Vérifier la structure 'data' > 'ranges' et 'values'
            if 'data' not in data:
                return False

            data_section = data['data']
            if not isinstance(data_section, dict):
                return False

            if 'ranges' not in data_section or 'values' not in data_section:
                return False

            ranges = data_section['ranges']
            values = data_section['values']

            if not isinstance(ranges, dict) or not isinstance(values, dict):
                return False

            # Vérifier que chaque range a un nom et une couleur
            for range_key, range_info in ranges.items():
                if not isinstance(range_info, dict):
                    return False
                if 'name' not in range_info or 'color' not in range_info:
                    return False

            # Vérifier que values contient des listes d'entiers
            for hand, range_ids in values.items():
                if not isinstance(range_ids, list):
                    return False
                for range_id in range_ids:
                    if not isinstance(range_id, int):
                        return False

            return True

        except Exception:
            return False

    def _apply_updates_with_validation(
            self,
            data: dict,
            updates: List[Tuple[str, str]]
    ) -> int:
        """
        Applique les mises à jour avec validation de chaque changement
        Retourne le nombre de changements effectivement appliqués
        """
        changes_applied = 0
        ranges_data = data.get('data', {}).get('ranges', {})

        for old_name, new_name in updates:
            # Éviter les changements inutiles
            if old_name == new_name:
                continue

            # Chercher et appliquer TOUS les matches (pas seulement le premier)
            matches_found = 0
            for range_key, range_info in ranges_data.items():
                if range_info.get('name') == old_name:
                    # Valider que le nouveau nom n'est pas vide
                    if new_name and new_name.strip():
                        range_info['name'] = new_name.strip()
                        matches_found += 1

            if matches_found > 0:
                changes_applied += matches_found
                print(f"   ✓ '{old_name}' → '{new_name}' ({matches_found} occurrences)")
            else:
                print(f"   ⚠️ '{old_name}' non trouvé dans le fichier")

        return changes_applied

    def _safe_update_single_file(self, file_path: str, updates: List[Tuple[str, str]]) -> str:
        """
        Met à jour un fichier JSON de manière sécurisée avec validation
        """
        print(f"\n📁 Traitement: {Path(file_path).name}")

        # Vérifications préliminaires
        if not Path(file_path).exists():
            print(f"❌ Fichier non trouvé: {file_path}")
            return "error"

        if not updates:
            print("ℹ️ Aucune mise à jour nécessaire")
            return "no_changes"

        temp_file = None
        backup_path = None

        try:
            # Étape 1: Charger et valider le JSON original
            print("📖 Chargement du JSON original...")
            with open(file_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)

            # Valider la structure JSON
            if not self._validate_json_structure(original_data):
                print("❌ Structure JSON invalide")
                return "error"

            # Étape 2: Créer une copie de travail
            modified_data = json.loads(json.dumps(original_data))  # Deep copy

            # Étape 3: Appliquer les modifications avec validation
            print(f"🔄 Application de {len(updates)} modifications...")
            changes_applied = self._apply_updates_with_validation(modified_data, updates)

            if changes_applied == 0:
                print("ℹ️ Aucun changement appliqué")
                return "no_changes"

            # Étape 4: Valider le JSON modifié
            if not self._validate_json_structure(modified_data):
                print("❌ Structure JSON corrompue après modifications")
                return "error"

            # Étape 5: Test de sérialisation
            try:
                test_json = json.dumps(modified_data, indent=2, ensure_ascii=False)
                json.loads(test_json)  # Vérifier que le JSON est valide
            except Exception as e:
                print(f"❌ Erreur de sérialisation: {e}")
                return "error"

            # Étape 6: Créer le backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{file_path}.backup.{timestamp}"
            shutil.copy2(file_path, backup_path)
            print(f"💾 Backup créé: {Path(backup_path).name}")

            # Étape 7: Écriture atomique via fichier temporaire
            temp_dir = Path(file_path).parent
            with tempfile.NamedTemporaryFile(
                    mode='w',
                    encoding='utf-8',
                    dir=temp_dir,
                    delete=False,
                    suffix='.json.tmp'
            ) as temp_f:
                temp_file = temp_f.name
                json.dump(modified_data, temp_f, indent=2, ensure_ascii=False)
                temp_f.flush()
                os.fsync(temp_f.fileno())  # Forcer l'écriture sur disque

            # Étape 8: Validation du fichier temporaire
            with open(temp_file, 'r', encoding='utf-8') as f:
                validation_data = json.load(f)

            if not self._validate_json_structure(validation_data):
                print("❌ Validation du fichier temporaire échouée")
                return "error"

            # Étape 9: Remplacement atomique
            shutil.move(temp_file, file_path)
            temp_file = None  # Éviter le cleanup

            print(f"✅ Fichier mis à jour avec succès ({changes_applied} modifications)")

            # Afficher les changements appliqués
            for old_name, new_name in updates[:3]:  # Limiter l'affichage
                print(f"   '{old_name}' → '{new_name}'")
            if len(updates) > 3:
                print(f"   ... et {len(updates) - 3} autres")

            return "success"

        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON: {e}")
            return "error"
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return "error"

        finally:
            # Cleanup du fichier temporaire si nécessaire
            if temp_file and Path(temp_file).exists():
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    def _update_json_files(self, file_updates: Dict[str, List[Tuple[str, str]]]) -> int:
        """
        Version sécurisée - Met à jour les fichiers JSON avec validation complète
        """
        results = {}
        success_count = 0

        if not file_updates:
            return 0

        print(f"🔧 MISE À JOUR SÉCURISÉE DE {len(file_updates)} FICHIERS JSON")
        print("=" * 60)

        for file_path, updates in file_updates.items():
            result = self._safe_update_single_file(file_path, updates)
            results[file_path] = result
            if result == "success":
                success_count += 1

        # Résumé
        error_count = sum(1 for status in results.values() if status == "error")
        no_changes_count = sum(1 for status in results.values() if status == "no_changes")

        print(f"\n📊 RÉSUMÉ:")
        print(f"✅ Succès: {success_count}")
        print(f"❌ Erreurs: {error_count}")
        print(f"ℹ️ Aucun changement: {no_changes_count}")

        return success_count

    def update_source_json_files(self):
        """
        Version sécurisée de update_source_json_files
        """
        print("🔄 MISE À JOUR DES FICHIERS JSON SOURCES")
        print("=" * 50)

        # Préparer les mises à jour
        file_updates = self._prepare_json_updates()

        if not file_updates:
            print("✅ Aucune mise à jour JSON nécessaire")
            return

        print(f"📁 {len(file_updates)} fichiers à mettre à jour")

        # Afficher un aperçu
        for file_path, updates in file_updates.items():
            file_name = Path(file_path).name
            print(f"📄 {file_name}:")

            # Afficher les premières modifications
            for old_name, new_name in updates[:4]:
                print(f"  '{old_name}' → '{new_name}'")
            if len(updates) > 4:
                print(f"  ... et {len(updates) - 4} autres")

        # Demander confirmation
        confirm = input(f"💾 Mettre à jour les fichiers JSON sources ? (o/n): ").strip().lower()

        if not confirm.startswith('o'):
            print("❌ Mise à jour annulée")
            return

        # Appliquer les mises à jour
        success_count = self._update_json_files(file_updates)

        if success_count > 0:
            print(f"✅ {success_count} fichiers mis à jour")
        else:
            print("❌ Aucun fichier mis à jour")


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