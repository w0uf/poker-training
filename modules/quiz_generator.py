#!/usr/bin/env python3
"""
Générateur de questions de quiz avec support multiway (squeeze, vs_limpers)
🆕 Intégration des questions à tiroirs (drill_down)
🎚️ Support de l'agressivité de la table (low/medium/high)
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
from drill_down_generator import DrillDownGenerator  # 🆕
from aggression_settings import get_aggression_settings  # 🎚️


class QuizGenerator:
    """Génère des questions de quiz depuis les contextes validés"""

    def __init__(self, db_path: str = None, aggression_level: str = 'medium'):
        """
        Initialise le générateur de quiz
        
        Args:
            db_path: Chemin vers la base de données
            aggression_level: Niveau d'agressivité ('low', 'medium', 'high')
        """
        if db_path is None:
            # Chemin absolu depuis le module
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "poker_trainer.db"
        self.db_path = Path(db_path)

        # 🎚️ Paramètres d'agressivité
        self.aggression_level = aggression_level
        self.aggression = get_aggression_settings(aggression_level)
        print(f"[QUIZ GEN] 🎚️ Agressivité: {aggression_level.upper()} - {self.aggression.get('description', '')}")

        # 🆕 Générateur de questions à tiroirs (avec agressivité)
        self.drill_down_gen = DrillDownGenerator(aggression_settings=self.aggression)

        # Positions par format
        self.POSITIONS_BY_FORMAT = {
            '5max': ['UTG', 'CO', 'BTN', 'SB', 'BB'],
            '6max': ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'],
            '9max': ['UTG', 'UTG+1', 'MP', 'MP+1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB'],
            'HU': ['BTN', 'BB']
        }

    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_question(self, context_id: int, used_hands: set = None) -> Optional[Dict]:
        """
        Génère une question pour un contexte donné.
        🆕 Décide entre question simple ou drill_down.
        🆕 v4.3.7 : Évite de réutiliser les mêmes mains abstraites

        Args:
            context_id: ID du contexte
            used_hands: Set des mains abstraites déjà utilisées dans le quiz

        Returns:
            Question dict ou None
        """
        if used_hands is None:
            used_hands = set()
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

            # Log du contexte pour debug
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
                    r.action_sequence,
                    GROUP_CONCAT(DISTINCT rh.hand) as hands
                FROM ranges r
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                GROUP BY r.id
                ORDER BY r.range_key
            """, (context_id,))

            ranges = []
            for row in cursor.fetchall():
                action_seq = row[4]
                hands_str = row[5]
                if hands_str:
                    ranges.append({
                        'id': row[0],
                        'range_key': row[1],
                        'name': row[2],
                        'label_canon': row[3],
                        'action_sequence': action_seq,
                        'hands': hands_str.split(',')
                    })

            if not ranges:
                print(f"[QUIZ] ❌ Aucune range trouvée pour ce contexte")
                return None

            print(f"  📊 {len(ranges)} ranges trouvées:")
            for r in ranges[:5]:
                hands_count = len(r['hands']) if r['hands'] else 0
                print(f"    - Range {r['range_key']}: {r['name']} (label={r['label_canon']}, {hands_count} mains)")
            if len(ranges) > 5:
                print(f"    ... et {len(ranges) - 5} autres ranges")

            # 🆕 DÉCISION : drill_down ou simple ?
            can_drill = self.drill_down_gen.can_generate_drill_down(ranges)

            if can_drill:
                # 🎚️ Probabilité de drill-down selon l'agressivité
                use_drill_down_prob = self.aggression['use_drill_down_prob']
                use_drill_down = random.random() < use_drill_down_prob
                print(f"  🎲 Type de question: {'DRILL_DOWN' if use_drill_down else 'SIMPLE'} (prob={use_drill_down_prob*100:.0f}%)")

                if use_drill_down:
                    # Préparer les mains pour drill_down
                    main_range = self._get_main_range(ranges)
                    if main_range and main_range['hands']:
                        in_range_hands = set(main_range['hands'])
                        out_of_range_hands = get_all_hands_not_in_ranges(in_range_hands)

                        # Tenter de générer drill_down avec évitement des mains utilisées
                        drill_question = self.drill_down_gen.generate_drill_down_question(
                            context, ranges, in_range_hands, out_of_range_hands, used_hands
                        )

                        if drill_question:
                            # Ajouter la main au contexte pour _format_level_question
                            context['hand'] = drill_question['hand']
                            return drill_question
                        else:
                            print("  ⚠️  Drill_down échoué, fallback sur simple")

            # Fallback : générer question simple avec évitement des mains utilisées
            return self._generate_simple_question(context, ranges, used_hands)

        finally:
            conn.close()

    def _get_main_range(self, ranges: List[Dict]) -> Optional[Dict]:
        """Retourne la range principale (range_key='1')"""
        for r in ranges:
            if r['range_key'] == '1':
                return r
        return None

    def _generate_simple_question(self, context: Dict, ranges: List[Dict], used_hands: set = None) -> Optional[Dict]:
        """
        Génère une question simple sur l'action principale.
        🆕 v4.3.7 : Évite de réutiliser les mêmes mains abstraites

        Args:
            context: Dictionnaire du contexte
            ranges: Liste des ranges
            used_hands: Set des mains abstraites déjà utilisées

        Returns:
            Question dict ou None
        """
        if used_hands is None:
            used_hands = set()
        
        # Trouver la range principale
        main_range = self._get_main_range(ranges)

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
        
        # 🆕 v4.3.7 : Filtrer les mains déjà utilisées
        available_in_range = in_range_hands - used_hands
        available_out_range = out_of_range_hands - used_hands
        
        # Si on a fait le tour de TOUTES les mains, réinitialiser
        if not available_in_range and not available_out_range:
            print(f"[QUIZ] ♻️  Toutes les mains utilisées, réinitialisation du pool")
            available_in_range = in_range_hands
            available_out_range = out_of_range_hands
        # Si seulement in_range est vide, forcer out_range
        elif not available_in_range:
            print(f"[QUIZ] ⚠️  Plus de mains in-range disponibles, force out-range")
            is_in_range = False
        # Si seulement out_range est vide, forcer in_range
        elif not available_out_range:
            print(f"[QUIZ] ⚠️  Plus de mains out-range disponibles, force in-range")
            is_in_range = True
        else:
            # 50% de chances in/out avec choix intelligent
            is_in_range = random.random() >= 0.5

        if is_in_range:
            # Main DANS la range (utiliser le pool filtré)
            hand = smart_hand_choice(available_in_range, available_out_range, is_in_range=True)

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
                # 🆕 CONVERSION : OPEN → RAISE pour l'UI
                if normalized_action == 'OPEN':
                    correct_answer = 'RAISE'
                else:
                    # Conversion : OPEN → RAISE pour l'UI
                    if normalized_action == 'OPEN':
                        correct_answer = 'RAISE'
                    else:
                        correct_answer = normalized_action

            print(f"[QUIZ] ✅ Question IN-RANGE: {hand} → {correct_answer}")
            print(
                f"       Context: '{context['display_name']}' (ID={context['id']}, action={context['primary_action']})")
        else:
            # Main HORS de la range (utiliser le pool filtré)
            hand = smart_hand_choice(available_in_range, available_out_range, is_in_range=False)
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
                        print(
                            f"  [SUBRANGE] {hand} trouvé dans '{r['name']}' (range_key={r['range_key']}, label={label}) → {normalized}")
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

        # 2. 🎯 NE JAMAIS AJOUTER 'DEFENSE' ou 'OPEN' - ce ne sont pas des actions jouables
        # Convertir OPEN → RAISE si nécessaire
        if main_range_action and main_range_action not in options:
            if main_range_action == 'DEFENSE':
                pass  # Ne pas ajouter DEFENSE
            elif main_range_action == 'OPEN':
                if 'RAISE' not in options:
                    options.append('RAISE')
            else:
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

        # 4. ✗ NE PAS utiliser les sous-ranges pour les questions simples

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

    # FONCTIONS HELPER POUR POSITIONS DYNAMIQUES

    def _get_positions(self, table_format: str) -> List[str]:
        """Retourne les positions pour un format donné"""
        return self.POSITIONS_BY_FORMAT.get(table_format, self.POSITIONS_BY_FORMAT['6max'])

    def _get_random_opener_for_defense(self, hero_pos: str, table_format: str, action_seq: Dict) -> str:
        """
        Retourne l'opener pour une situation de defense.
        🔧 CLARIFICATION : Utilise action_sequence si présent (opener réel), 
        sinon choisit aléatoirement de manière logique.
        """
        # Option 1 : Opener spécifique dans action_sequence (RÉEL)
        if action_seq and action_seq.get('opener'):
            opener = action_seq['opener']
            print(f"  ✅ Opener RÉEL depuis action_sequence: {opener}")
            return opener

        # Option 2 : Range générique → choisir aléatoirement (INVENTÉ)
        positions = self._get_positions(table_format)

        if hero_pos not in positions:
            print(f"  ⚠️ Hero position invalide, opener par défaut: UTG")
            return "UTG"  # Fallback

        hero_idx = positions.index(hero_pos)

        # Positions valides = toutes celles avant le héros
        valid_openers = positions[:hero_idx]

        if valid_openers:
            opener = random.choice(valid_openers)
            print(f"  🎲 Opener INVENTÉ logiquement: {opener} (parmi {valid_openers})")
            return opener

        print(f"  ⚠️ Pas de positions avant hero, fallback: UTG")
        return "UTG"  # Fallback

    def _get_squeeze_scenario(self, hero_pos: str, table_format: str, action_seq: Dict) -> tuple:
        """
        Retourne le scénario complet pour squeeze (opener, callers_text).
        🔧 CLARIFICATION : Utilise action_sequence si présent (positions réelles), 
        sinon génère aléatoirement de manière logique.
        """
        positions = self._get_positions(table_format)

        if hero_pos not in positions:
            return "UTG", "un joueur call"

        hero_idx = positions.index(hero_pos)

        # OPENER
        if action_seq and action_seq.get('opener'):
            opener = action_seq['opener']
            print(f"  ✅ Squeeze opener RÉEL: {opener}")
        else:
            # Choisir un opener au moins 2 positions avant héros
            valid_openers = positions[:max(0, hero_idx - 2)]
            opener = random.choice(valid_openers) if valid_openers else "UTG"
            print(f"  🎲 Squeeze opener INVENTÉ: {opener}")

        # CALLERS
        if action_seq and action_seq.get('callers'):
            callers = action_seq['callers']
            print(f"  ✅ Callers RÉELS: {callers}")
            if len(callers) == 1:
                callers_text = f"{callers[0]} call"
            else:
                callers_text = f"{' et '.join(callers)} callent"
        elif action_seq and action_seq.get('callers_count'):
            count = action_seq['callers_count']
            callers_text = f"{count} joueur(s) callent"
            print(f"  ✅ Nombre de callers RÉEL: {count}")
        else:
            # Générique : 1 caller aléatoire entre opener et héros
            if opener in positions:
                opener_idx = positions.index(opener)
                valid_callers = positions[opener_idx + 1:hero_idx]
                if valid_callers:
                    caller = random.choice(valid_callers)
                    callers_text = f"{caller} call"
                    print(f"  🎲 Caller INVENTÉ: {caller}")
                else:
                    callers_text = "un joueur call"
                    print(f"  🎲 Caller GÉNÉRIQUE (pas de positions entre opener et hero)")
            else:
                callers_text = "un joueur call"
                print(f"  🎲 Caller GÉNÉRIQUE (opener invalide)")

        return opener, callers_text

    def _get_limpers_scenario(self, hero_pos: str, table_format: str, action_seq: Dict) -> str:
        """
        Retourne le scénario pour vs_limpers.
        🔧 CLARIFICATION : Utilise action_sequence si présent (positions réelles), 
        sinon génère aléatoirement de manière logique.
        """
        positions = self._get_positions(table_format)

        if hero_pos not in positions:
            return "un joueur limp"

        hero_idx = positions.index(hero_pos)

        if action_seq and action_seq.get('limpers'):
            limpers = action_seq['limpers']
            print(f"  ✅ Limpers RÉELS: {limpers}")
            if len(limpers) == 1:
                return f"{limpers[0]} limp"
            else:
                return f"{', '.join(limpers[:-1])} et {limpers[-1]} limpent"

        elif action_seq and action_seq.get('limpers_count'):
            count = action_seq['limpers_count']
            print(f"  ✅ Nombre de limpers RÉEL: {count}")
            return f"{count} joueur(s) limpent"

        else:
            # Générique : 1-2 limpers aléatoires
            valid_limpers = positions[:hero_idx]
            num_limpers = random.randint(1, min(2, len(valid_limpers)))
            limpers = random.sample(valid_limpers, num_limpers)

            print(f"  🎲 Limpers INVENTÉS: {limpers}")

            if len(limpers) == 1:
                return f"{limpers[0]} limp"
            else:
                return f"{', '.join(limpers[:-1])} et {limpers[-1]} limpent"

    def _format_question(self, context: Dict, hand: str) -> str:
        """
        Formate le texte de la question selon le contexte.
        Gère action_sequence pour squeeze et vs_limpers.
        🆕 Génère aléatoirement opener/callers/limpers si non spécifiés.

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
            # 🆕 Utiliser la fonction helper avec choix aléatoire
            opener = self._get_random_opener_for_defense(position, table, action_seq)
            parts.append(f"{opener} ouvre")

        elif primary_action == 'squeeze':
            # 🆕 Utiliser la fonction helper avec choix aléatoire
            opener, callers_text = self._get_squeeze_scenario(position, table, action_seq)
            parts.append(f"{opener} ouvre")
            parts.append(callers_text)

        elif primary_action == 'vs_limpers':
            # 🆕 Utiliser la fonction helper avec choix aléatoire
            limpers_text = self._get_limpers_scenario(position, table, action_seq)
            parts.append(limpers_text)

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