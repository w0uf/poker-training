#!/usr/bin/env python3
"""
Générateur de questions de quiz avec support multiway (squeeze, vs_limpers)
Utilise action_sequence pour les situations complexes
"""

import sqlite3
import random
import json
from typing import Dict, List, Optional, Set
from pathlib import Path

# Imports locaux
from poker_constants import (
    ALL_POKER_HANDS, sort_actions, normalize_action, translate_action
)
from hand_selector import smart_hand_choice, get_all_hands_not_in_ranges


class QuizGenerator:
    """Génère des questions de quiz depuis les contextes validés"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Chemin absolu depuis le module
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "poker_trainer.db"
        self.db_path = Path(db_path)

    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_question(self, context_id: int) -> Optional[Dict]:
        """
        Génère une question pour un contexte donné.
        Point d'entrée principal.

        Args:
            context_id: ID du contexte

        Returns:
            Question dict ou None
        """
        conn = self.get_connection()

        try:
            # Récupérer le contexte
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, display_name, table_format, hero_position, 
                    primary_action, vs_position, stack_depth, action_sequence
                FROM range_contexts 
                WHERE id = ? AND quiz_ready = 1
            """, (context_id,))

            context_row = cursor.fetchone()
            if not context_row:
                print(f"[QUIZ] ❌ SKIP: Contexte ID={context_id} non trouvé en DB")
                return None

            context = dict(context_row)

            # 🆕 Log du contexte pour debug
            print(f"\n[QUIZ CONTEXT] ID={context['id']}")
            print(f"  📋 Name: {context['display_name']}")
            print(f"  🎯 Action: {context['primary_action']}")
            print(f"  📍 Position: {context['hero_position']} ({context['table_format']})")

            # Parser action_sequence JSON
            if context.get('action_sequence'):
                try:
                    context['action_sequence'] = json.loads(context['action_sequence'])
                    if context['action_sequence']:
                        print(f"  🔗 Sequence: {context['action_sequence']}")
                except:
                    context['action_sequence'] = None

            # Récupérer les ranges
            cursor.execute("""
                SELECT 
                    r.id, r.range_key, r.name, r.label_canon,
                    GROUP_CONCAT(DISTINCT rh.hand) as hands
                FROM ranges r
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                GROUP BY r.id
                ORDER BY r.range_key
            """, (context_id,))

            ranges = []
            for row in cursor.fetchall():
                hands_str = row[4]
                if hands_str:
                    ranges.append({
                        'id': row[0],
                        'range_key': row[1],
                        'name': row[2],
                        'label_canon': row[3],
                        'hands': hands_str.split(',')
                    })

            if not ranges:
                print(f"[QUIZ] ❌ Aucune range trouvée pour ce contexte")
                return None

            print(f"  📊 {len(ranges)} ranges trouvées:")
            for r in ranges[:5]:  # Afficher max 5 premières
                hands_count = len(r['hands']) if r['hands'] else 0
                print(f"    - Range {r['range_key']}: {r['name']} (label={r['label_canon']}, {hands_count} mains)")
            if len(ranges) > 5:
                print(f"    ... et {len(ranges) - 5} autres ranges")

            # Générer la question (simple uniquement pour l'instant)
            return self._generate_simple_question(context, ranges)

        finally:
            conn.close()

    def _generate_simple_question(self, context: Dict, ranges: List[Dict]) -> Optional[Dict]:
        """
        Génère une question simple sur l'action principale.

        Args:
            context: Dictionnaire du contexte
            ranges: Liste des ranges

        Returns:
            Question dict ou None
        """
        # Trouver la range principale
        main_range = None
        for r in ranges:
            if r['range_key'] == '1':
                main_range = r
                break

        if not main_range or not main_range['hands']:
            print(f"[QUIZ] SKIP: Pas de range principale pour context_id={context['id']}")
            return None

        correct_action = main_range.get('label_canon')

        if not correct_action or correct_action == 'None' or correct_action == '':
            print(f"[QUIZ] SKIP: label_canon invalide pour range principale")
            return None

        normalized_action = normalize_action(correct_action)

        if not normalized_action:
            print(f"[QUIZ] SKIP: normalisation échouée pour '{correct_action}'")
            return None

        # Préparer les mains IN et OUT
        in_range_hands = set(main_range['hands'])
        out_of_range_hands = get_all_hands_not_in_ranges(in_range_hands)

        # 50% de chances in/out avec choix intelligent
        is_in_range = random.random() >= 0.5

        if is_in_range:
            # Main DANS la range
            hand = smart_hand_choice(in_range_hands, out_of_range_hands, is_in_range=True)

            # Si c'est un contexte DEFENSE, trouver l'action dans les sous-ranges
            if normalized_action == 'DEFENSE':
                correct_answer = self._find_subrange_action(hand, ranges)
                if not correct_answer:
                    print(f"[QUIZ] SKIP: Main {hand} dans defense mais sans action dans sous-ranges")
                    return None

                # 🎯 CONVERSION CONTEXTUELLE : 3BET → RAISE pour l'affichage en DEFENSE
                if correct_answer == '3BET':
                    correct_answer = 'RAISE'

            else:
                correct_answer = normalized_action

            print(f"[QUIZ] ✅ Question IN-RANGE: {hand} → {correct_answer}")
            print(
                f"       Context: '{context['display_name']}' (ID={context['id']}, action={context['primary_action']})")
        else:
            # Main HORS de la range
            hand = smart_hand_choice(in_range_hands, out_of_range_hands, is_in_range=False)
            correct_answer = 'FOLD'
            print(f"[QUIZ] ✅ Question OUT-OF-RANGE: {hand} → FOLD")
            print(
                f"       Context: '{context['display_name']}' (ID={context['id']}, action={context['primary_action']})")

        if not hand:
            print(f"[QUIZ] SKIP: Impossible de choisir une main")
            return None

        # Générer options
        options = self._generate_action_options(correct_answer, normalized_action, ranges, context)
        options = [opt for opt in options if opt is not None]

        if len(options) < 2:
            print(f"[QUIZ] SKIP: Pas assez d'options valides ({len(options)})")
            return None

        # Générer le texte de la question
        question_text = self._format_question(context, hand)

        print(f"[QUIZ] Options générées : {options}")
        print(f"[QUIZ] 📝 Question texte: '{question_text}'")
        print(f"[QUIZ] ✅ Question finale - Main: {hand}, Réponse: {correct_answer}, Options: {options}\n")

        return {
            'type': 'simple',
            'context_id': context['id'],
            'hand': hand,
            'question': question_text,
            'options': options,
            'correct_answer': correct_answer,
            'context_info': context
        }

    def _find_subrange_action(self, hand: str, ranges: List[Dict]) -> Optional[str]:
        """
        Trouve l'action correcte pour une main dans les sous-ranges.
        Utilisé pour DEFENSE et autres contextes où l'action est dans les sous-ranges.

        Args:
            hand: La main
            ranges: Liste des ranges

        Returns:
            Action normalisée ou None
        """
        # Chercher dans les sous-ranges (range_key != '1')
        for r in ranges:
            if r['range_key'] != '1' and hand in r['hands']:
                label = r.get('label_canon')
                if label and label != 'None' and label != '':
                    normalized = normalize_action(label)
                    if normalized:
                        print(f"  [SUBRANGE] {hand} trouvé dans '{r['name']}' → {normalized}")
                        return normalized

        print(f"  [SUBRANGE] ⚠️ {hand} pas trouvé dans sous-ranges")
        return None

    def _generate_action_options(
            self,
            correct_answer: str,
            main_range_action: str,
            ranges: List[Dict],
            context: Dict
    ) -> List[str]:
        """
        Génère les options de réponse adaptées au contexte.

        Pour une question SIMPLE sur l'action principale,
        les sous-ranges NE SONT PAS utilisées comme distracteurs
        (ce sont des réponses conditionnelles futures).

        Args:
            correct_answer: La bonne réponse
            main_range_action: Action de la range principale
            ranges: Liste des ranges
            context: Contexte du quiz

        Returns:
            Liste des options triées
        """
        options = []

        # 1. Toujours inclure la bonne réponse
        if correct_answer:
            options.append(correct_answer)

        # 2. 🎯 NE JAMAIS AJOUTER 'DEFENSE' - ce n'est pas une action jouable
        # Les autres actions principales peuvent être ajoutées comme alternatives
        if main_range_action and main_range_action not in options and main_range_action != 'DEFENSE':
            options.append(main_range_action)

        # 3. FOLD si pas déjà présent
        primary = context.get('primary_action', '').lower()
        hero_position = context.get('hero_position', '')

        # Si BB et action de check (pas de relance)
        if hero_position == 'BB' and 'check' in primary:
            if 'CHECK' not in options:
                options.append('CHECK')
        else:
            # Sinon, toujours FOLD
            if 'FOLD' not in options:
                options.append('FOLD')

        # 4. ❌ NE PAS utiliser les sous-ranges pour les questions simples

        # 5. Si on a moins de 3 options, ajouter des distracteurs contextuels
        if len(options) < 3:
            distractors = self._get_contextual_distractors(primary)
            for distractor in distractors:
                if distractor not in options:
                    options.append(distractor)
                    if len(options) >= 3:  # S'arrêter à 3 options
                        break

        # Trier dans un ordre fixe
        return sort_actions(options)
    def _get_contextual_distractors(self, primary_action: str) -> List[str]:
        """
        Retourne des distracteurs pertinents selon le contexte.

        Args:
            primary_action: Action principale du contexte

        Returns:
            Liste de distracteurs (max 2 pour avoir 3 options total)
        """
        if 'defense' in primary_action:
            return ['CALL', 'RAISE']  # 🎯 Actions vs open (RAISE au lieu de 3BET pour l'UI)
        elif 'open' in primary_action:
            return ['CALL']  # limp comme alternative (RAISE = redondant avec OPEN)
        elif 'squeeze' in primary_action:
            return ['CALL']  # overcall comme alternative
        elif 'vs_limpers' in primary_action or 'iso' in primary_action:
            return ['CALL', 'ISO']  # overcall ou iso
        elif 'check' in primary_action:
            return ['RAISE']  # raise si checké vers nous
        elif '3bet' in primary_action:
            return ['CALL']  # call le 3bet
        else:
            return ['CALL']  # générique

    def _format_question(self, context: Dict, hand: str) -> str:
        """
        Formate le texte de la question selon le contexte.
        Gère action_sequence pour squeeze et vs_limpers.

        Args:
            context: Dictionnaire du contexte
            hand: Main pour la question

        Returns:
            Texte de la question formaté
        """
        table = context.get('table_format', '6max')
        position = context.get('hero_position', 'BTN')
        stack = context.get('stack_depth', '100bb')
        primary_action = context.get('primary_action', '').lower()
        action_seq = context.get('action_sequence')

        parts = []
        parts.append(f"Table {table}, vous êtes {position} avec {stack}")

        if primary_action == 'open':
            # Ne rien ajouter, c'est implicite qu'on est premier de parole
            pass

        elif primary_action == 'defense':
            if action_seq and action_seq.get('opener'):
                opener = action_seq['opener']
                parts.append(f"{opener} ouvre")
            else:
                # Fallback
                vs_pos = context.get('vs_position', 'UTG')
                if vs_pos and vs_pos != 'N/A':
                    parts.append(f"{vs_pos} ouvre")
                else:
                    parts.append("Un adversaire ouvre")

        elif primary_action == 'squeeze':
            if action_seq:
                opener = action_seq.get('opener', 'UTG')
                callers = action_seq.get('callers', [])

                parts.append(f"{opener} ouvre")

                if callers:
                    if len(callers) == 1:
                        parts.append(f"{callers[0]} call")
                    else:
                        caller_str = ", ".join(callers[:-1]) + f" et {callers[-1]}"
                        parts.append(f"{caller_str} callent")
            else:
                # Fallback
                parts.append("Un adversaire ouvre, un autre call")

        elif primary_action == 'vs_limpers':
            if action_seq:
                limpers = action_seq.get('limpers', [])

                if limpers:
                    if len(limpers) == 1:
                        parts.append(f"{limpers[0]} limp")
                    else:
                        limper_str = ", ".join(limpers[:-1]) + f" et {limpers[-1]}"
                        parts.append(f"{limper_str} limpent")
            else:
                # Fallback
                parts.append("Un ou plusieurs adversaires limpent")

        elif primary_action == 'check':
            parts.append("Personne n'a ouvert")

        # Ajouter la main et la question
        question = ". ".join(parts) + f". Vous avez {hand}. Que faites-vous ?"

        return question


# Fonction utilitaire pour app.py
def generate_single_question(conn, context_id: int) -> Optional[Dict]:
    """
    Fonction wrapper pour compatibilité avec app.py

    Args:
        conn: Connexion SQLite (non utilisée, pour compatibilité)
        context_id: ID du contexte

    Returns:
        Question dict ou None
    """
    generator = QuizGenerator()
    return generator.generate_question(context_id)