#!/usr/bin/env python3
"""
Exemple d'utilisation de action_sequence dans le drill down
Montre comment parser et utiliser les séquences d'actions
"""

import sqlite3
import random
from typing import List, Dict, Optional, Set
from poker_constants import RANGE_STRUCTURE


class DrillDownGenerator:
    """Gestionnaire de drill down utilisant action_sequence"""

    def __init__(self, db_path: str = "data/poker_trainer.db"):
        self.db_path = db_path
        # Positions par format de table
        self.POSITIONS_BY_FORMAT = {
            '5max': ['UTG', 'CO', 'BTN', 'SB', 'BB'],
            '6max': ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'],
            '9max': ['UTG', 'UTG+1', 'MP', 'MP+1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB'],
            'HU': ['BTN', 'BB']
        }

    def _generate_villain_position(self, hero_position: str, table_format: str) -> str:
        """
        🆕 Génère une position cohérente pour le Vilain (position après le héros).
        
        Args:
            hero_position: Position du héros (ex: "UTG", "CO")
            table_format: Format de table (ex: "5max", "6max")
            
        Returns:
            Position du Vilain choisie aléatoirement après le héros
        """
        positions = self.POSITIONS_BY_FORMAT.get(table_format, self.POSITIONS_BY_FORMAT['6max'])
        
        try:
            hero_idx = positions.index(hero_position)
            # Prendre une position après le héros (pas avant, car il ne peut pas 3bet)
            possible_positions = positions[hero_idx + 1:]
            
            if possible_positions:
                return random.choice(possible_positions)
        except (ValueError, IndexError):
            pass
        
        # Fallback : retourner une position aléatoire
        return random.choice(['CO', 'BTN', 'SB', 'BB'])

    def parse_action_step(self, step_str: str) -> Dict:
        """
        Parse une étape de la séquence

        Args:
            step_str: Une étape (ex: "RAISE", "RAISE/CALL")

        Returns:
            Dict avec type et action(s)
        """
        if "/" in step_str:
            # C'est un choix entre plusieurs actions
            actions = step_str.split("/")
            return {
                "type": "choice",
                "actions": actions,
                "text": f"Choisissez entre {' ou '.join(actions)}"
            }
        else:
            # Action unique
            return {
                "type": "single",
                "action": step_str,
                "text": f"Action: {step_str}"
            }

    def get_drill_down_sequence(self, hand: str, context_id: int) -> List[Dict]:
        """
        Récupère la séquence d'actions pour une main dans un contexte

        Args:
            hand: Main de poker (ex: "AKs")
            context_id: ID du contexte

        Returns:
            Liste des étapes parsées
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Récupérer les ranges contenant cette main
            cursor.execute("""
                SELECT DISTINCT r.action_sequence, r.name, r.label_canon
                FROM ranges r
                JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                  AND rh.hand = ?
                  AND r.action_sequence IS NOT NULL
                ORDER BY r.range_key
            """, (context_id, hand))

            results = cursor.fetchall()

            if not results:
                print(f"❌ Aucune séquence trouvée pour {hand} dans le contexte {context_id}")
                return []

            # Prendre la première séquence (ou fusionner si plusieurs)
            sequence_str = results[0][0]
            range_name = results[0][1]
            label_canon = results[0][2]

            print(f"✅ Séquence trouvée pour {hand} ({range_name}, {label_canon}): {sequence_str}")

            # Parser la séquence
            steps = sequence_str.split("→")
            parsed_steps = []

            for i, step in enumerate(steps, 1):
                parsed = self.parse_action_step(step)
                parsed["step_number"] = i
                parsed_steps.append(parsed)

            return parsed_steps

    def validate_answer(self, hand: str, context_id: int, step_number: int, user_action: str) -> Dict:
        """
        Valide la réponse de l'utilisateur pour une étape

        Args:
            hand: Main jouée
            context_id: ID du contexte
            step_number: Numéro de l'étape (1, 2, 3...)
            user_action: Action choisie par l'utilisateur (RAISE, CALL, FOLD)

        Returns:
            Dict avec correct, message, etc.
        """
        sequence = self.get_drill_down_sequence(hand, context_id)

        if not sequence or step_number > len(sequence):
            return {
                "correct": False,
                "message": "❌ Étape invalide"
            }

        current_step = sequence[step_number - 1]

        if current_step["type"] == "single":
            # Action unique attendue
            expected = current_step["action"]
            if user_action == expected:
                return {
                    "correct": True,
                    "message": f"✅ Correct ! {user_action} est la bonne action."
                }
            else:
                return {
                    "correct": False,
                    "message": f"❌ Incorrect. L'action attendue était {expected}."
                }

        elif current_step["type"] == "choice":
            # Choix multiple : toutes les actions du choix sont valides
            valid_actions = current_step["actions"]
            if user_action in valid_actions:
                return {
                    "correct": True,
                    "message": f"✅ Correct ! {user_action} est une bonne action dans cette situation.",
                    "note": f"Les autres options valides étaient : {', '.join([a for a in valid_actions if a != user_action])}"
                }
            else:
                return {
                    "correct": False,
                    "message": f"❌ Incorrect. Les actions valides étaient : {' ou '.join(valid_actions)}"
                }

    def display_drill_down_question(self, hand: str, context_id: int, step_number: int):
        """
        Affiche une question de drill down
        """
        sequence = self.get_drill_down_sequence(hand, context_id)

        if not sequence or step_number > len(sequence):
            print("❌ Pas de question disponible")
            return

        current_step = sequence[step_number - 1]

        # Construire le contexte (historique des actions précédentes)
        history = []
        for i in range(step_number - 1):
            prev_step = sequence[i]
            if prev_step["type"] == "single":
                history.append(prev_step["action"])
            else:
                history.append(f"({'/'.join(prev_step['actions'])})")

        print(f"\n{'=' * 60}")
        print(f"🎮 DRILL DOWN - Étape {step_number}/{len(sequence)}")
        print(f"{'=' * 60}")
        print(f"Main : {hand}")

        if history:
            print(f"Historique : {' → '.join(history)}")

        print(f"\n{current_step['text']}")

        if current_step["type"] == "choice":
            print("\n💡 Plusieurs actions sont valides dans cette situation")
            for action in current_step["actions"]:
                print(f"   [{action}]")
        else:
            print(f"\n   [{current_step['action']}]")

        print(f"{'=' * 60}\n")

    def can_generate_drill_down(self, ranges: List[Dict]) -> bool:
        """
        Vérifie si on peut générer des questions de drill down pour ces ranges

        Args:
            ranges: Liste des ranges du contexte (avec action_sequence)

        Returns:
            True si drill down possible (au moins une sous-range existe), False sinon
        """
        # Il faut AU MOINS une sous-range (range_key != '1')
        # Si l'utilisateur n'a créé que la range principale, pas de drill down
        has_subranges = any(r.get('range_key') != '1' for r in ranges)

        if not has_subranges:
            print("[DRILL] Pas de sous-ranges → pas de drill down")
            return False

        print(
            f"[DRILL] {sum(1 for r in ranges if r.get('range_key') != '1')} sous-ranges détectées → drill down possible")
        return True

    def generate_drill_down_question(
            self,
            context: Dict,
            ranges: List[Dict],
            in_range_hands: Set[str],
            out_of_range_hands: Set[str],
            used_hands: set = None
    ) -> Optional[Dict]:
        """
        Génère une question de drill down pour le système de quiz
        🆕 v4.3.7 : Évite de réutiliser les mêmes mains abstraites

        Args:
            context: Dict du contexte avec id, display_name, etc.
            ranges: Liste des ranges
            in_range_hands: Set des mains dans la range principale
            out_of_range_hands: Set des mains hors range
            used_hands: Set des mains abstraites déjà utilisées

        Returns:
            Dict avec la question drill down complète, ou None si impossible
        """
        from hand_selector import smart_hand_choice

        if used_hands is None:
            used_hands = set()

        context_id = context['id']
        primary_action = context.get('primary_action', 'open')

        # 🔧 BUGFIX v4.3.6 : Générer la position du Vilain UNE SEULE FOIS pour tout le drill-down
        villain_position = self._generate_fixed_villain_position(context)
        context['villain_position_fixed'] = villain_position  # Stocker pour réutilisation
        print(f"[DRILL] 🎯 Position du Vilain fixée pour toute la séquence: {villain_position}")

        # 1. Vérifier qu'il y a des sous-ranges
        subranges = [r for r in ranges if r.get('range_key') != '1']
        if not subranges:
            print(f"[DRILL] Pas de sous-ranges pour contexte {context_id} → pas de drill down")
            return None

        # 🆕 v4.3.7 : Filtrer les mains déjà utilisées
        available_in_range = in_range_hands - used_hands
        available_out_range = out_of_range_hands - used_hands
        
        # Si on a fait le tour, réinitialiser
        if not available_in_range and not available_out_range:
            print(f"[DRILL] ♻️  Toutes les mains utilisées, réinitialisation")
            available_in_range = in_range_hands
            available_out_range = out_of_range_hands
        elif not available_in_range:
            print(f"[DRILL] ⚠️  Plus de mains in-range disponibles")
            available_in_range = set()  # Vide, forcera out-range
        elif not available_out_range:
            print(f"[DRILL] ⚠️  Plus de mains out-range disponibles")
            available_out_range = set()  # Vide, forcera in-range

        # 2. Choisir une main dans la range principale
        # 80% in-range, 20% out-range pour drill down
        is_in_range = random.random() >= 0.2 and len(available_in_range) > 0

        if is_in_range and available_in_range:
            hand = smart_hand_choice(available_in_range, available_out_range, is_in_range=True)
            print(f"[DRILL] Main choisie IN-RANGE: {hand}")
        else:
            hand = smart_hand_choice(available_out_range, available_in_range, is_in_range=False)
            print(f"[DRILL] Main choisie OUT-RANGE: {hand}")
            is_in_range = False

        # 3. Chercher dans quelle sous-range est la main
        subrange_with_hand = None
        for subrange in subranges:
            if hand in subrange.get('hands', []):
                subrange_with_hand = subrange
                print(
                    f"[DRILL] ✅ Main {hand} trouvée dans sous-range: {subrange.get('name')} ({subrange.get('label_canon')})")
                break

        if not subrange_with_hand:
            print(f"[DRILL] ⚠️ Main {hand} n'est dans AUCUNE sous-range → FOLD implicite")

        # 4. Générer ou récupérer la séquence
        if subrange_with_hand and subrange_with_hand.get('action_sequence'):
            # La main est dans une sous-range avec séquence
            sequence_str = subrange_with_hand['action_sequence']
            print(f"[DRILL] Séquence trouvée dans {subrange_with_hand['name']}: {sequence_str}")
        else:
            # Main pas dans les sous-ranges → FOLD implicite
            sequence_str = self._generate_implicit_fold_sequence(primary_action)
            print(f"[DRILL] FOLD implicite généré: {sequence_str}")

            if not sequence_str:
                print(f"[DRILL] ❌ Impossible de générer une séquence pour {hand}")
                return None

        # 5. Parser la séquence
        steps_str = sequence_str.split("→")
        full_sequence = []
        for step in steps_str:
            parsed_step = self.parse_action_step(step)
            full_sequence.append(parsed_step)

        total_steps = len(full_sequence)

        # 6. 🎲 Décider combien d'étapes on va faire (50% de continuer à chaque fois)
        # ⚠️ EXCEPTION : Pour les FOLD implicites, forcer 2 étapes minimum (sinon pas pédagogique)
        is_implicit_fold = (subrange_with_hand is None) and ("FOLD" in sequence_str)

        if is_implicit_fold:
            # FOLD implicite : toujours montrer les 2 étapes (RAISE→FOLD)
            num_steps_to_use = min(2, total_steps)
            print(f"[DRILL] FOLD implicite détecté → forcer 2 étapes minimum")
        else:
            # Séquence normale : tirage probabiliste
            num_steps_to_use = 1  # Au minimum 1 étape
            for step_num in range(2, total_steps + 1):
                if random.random() < 1.0:  # 🧪 TEST: 100% de chance de continuer (normalement 0.5)
                    num_steps_to_use = step_num
                else:
                    break  # On s'arrête là

        print(f"[DRILL] Séquence complète: {total_steps} étapes → on en fait: {num_steps_to_use}")

        # Tronquer la séquence
        sequence = full_sequence[:num_steps_to_use]

        # 7. Formater la question
        question_text = self._format_drill_question(context, hand, step_number=1, total_steps=num_steps_to_use)

        # 8. Première étape pour les options initiales
        first_step = sequence[0]

        if first_step["type"] == "single":
            correct_action = first_step["action"]
            correct_actions = None
            options = [correct_action, "CALL", "FOLD", "RAISE"]
            options = list(set(options))[:3]
        else:
            correct_actions = first_step["actions"]
            correct_action = correct_actions[0]
            options = list(correct_actions) + ["FOLD"]
            options = list(set(options))

        # 9. 🆕 Construire le tableau "levels" avec réactions du Vilain
        levels = []
        for i, step in enumerate(sequence):
            level_num = i + 1

            # 🔧 CORRECTION v2 : Un seul appel à _get_villain_reaction_at_level pour éviter double random
            villain_reaction = self._get_villain_reaction_at_level(i, sequence[i - 1]["action"], 
                                                                   context) if i > 0 else None

            # Texte de la question
            if level_num == 1:
                level_question = question_text
            else:
                if villain_reaction:
                    level_question = f"{villain_reaction['text']}. Que faites-vous ?"
                else:
                    level_question = "Que faites-vous ?"

            # Options pour cette étape
            if step["type"] == "single":
                # 🆕 AMÉLIORATION : Gérer RAISE face à ALL-IN → convertir en CALL
                correct_action = step["action"]
                
                # Si Vilain est ALL-IN et notre action prévue est RAISE, on doit CALL
                if villain_reaction and not villain_reaction.get('allows_raise', True):
                    if correct_action == "RAISE":
                        correct_action = "CALL"
                        print(f"  🔄 ALL-IN détecté: RAISE converti en CALL")
                
                # Options de base
                base_options = [correct_action, "CALL", "FOLD"]

                # 🆕 Ajouter RAISE seulement si le Vilain n'est pas all-in
                if not villain_reaction or villain_reaction.get('allows_raise', True):
                    base_options.append("RAISE")

                step_options = list(set(base_options))

                # 🆕 Tri dans l'ordre immuable FOLD → CALL → RAISE
                from poker_constants import sort_actions
                step_options = sort_actions(step_options)[:3]  # Max 3 options

                level_data = {
                    "question": level_question,
                    "options": step_options,
                    "correct_answer": correct_action,  # 🔧 Utiliser correct_action modifié
                    "villain_reaction": villain_reaction  # 🆕 Pour le frontend
                }
            else:
                # Choix multiple (ex: RAISE/CALL)
                original_actions = list(step["actions"])
                step_options = original_actions + ["FOLD"]

                # 🆕 AMÉLIORATION : Gérer ALL-IN pour les choix multiples
                correct_answer = original_actions[0]  # Par défaut, première action
                
                if villain_reaction and not villain_reaction.get('allows_raise', True):
                    # Vilain est ALL-IN : retirer RAISE des options
                    step_options = [opt for opt in step_options if opt not in ['RAISE', '4BET', '5BET']]
                    
                    # Si CALL est dans les actions originales, c'est la bonne réponse
                    if "CALL" in original_actions:
                        correct_answer = "CALL"
                        print(f"  🔄 ALL-IN détecté: RAISE/CALL → CALL accepté")

                step_options = list(set(step_options))

                # 🆕 Tri dans l'ordre immuable
                from poker_constants import sort_actions
                step_options = sort_actions(step_options)

                level_data = {
                    "question": level_question,
                    "options": step_options,
                    "correct_answers": original_actions,  # Pour référence (actions originales)
                    "correct_answer": correct_answer,  # 🔧 Bonne réponse adaptée
                    "villain_reaction": villain_reaction  # 🆕 Pour le frontend
                }

            levels.append(level_data)

        # 10. Construire la question complète
        question = {
            "type": "drill_down",
            "hand": hand,
            "context_id": context_id,
            "context_name": context.get('display_name', ''),
            "is_in_range": is_in_range,
            "question_text": question_text,
            "correct_action": correct_action,  # Pour compatibilité backend
            "correct_answer": correct_action,  # Pour compatibilité frontend JS
            "correct_actions": correct_actions,
            "options": options,
            "current_step": 1,
            "total_steps": num_steps_to_use,
            "sequence": sequence,
            "levels": levels,
            "villain_position": villain_position,  # 🆕 v4.3.6 : Position fixe du Vilain
            "context_info": {
                "table_format": context.get('table_format', '6max'),
                "hero_position": context.get('hero_position', 'BTN'),
                "stack_depth": context.get('stack_depth', '100bb'),
                "primary_action": context.get('primary_action', 'open'),
                "display_name": context.get('display_name', ''),  # ← Ajout pour le JS
                "villain_position": villain_position  # 🆕 v4.3.6 : Position fixe du Vilain
            },
            "question": question_text
        }

        print(f"[DRILL] 📝 Question générée: {num_steps_to_use} étapes, première action={correct_action}")

        return question

    def _format_drill_question(self, context: Dict, hand: str, step_number: int, total_steps: int) -> str:
        """
        Formate le texte de la question pour une étape de drill down
        🔧 CORRECTION : Utilise les mêmes fonctions que quiz_generator pour cohérence

        Args:
            context: Contexte du quiz
            hand: Main jouée
            step_number: Numéro de l'étape actuelle
            total_steps: Nombre total d'étapes

        Returns:
            Texte de la question formaté
        """
        # Pour l'étape 1, utiliser le formateur de quiz_generator pour cohérence
        if step_number == 1:
            # Importer dynamiquement pour éviter les imports circulaires
            try:
                from quiz_generator import QuizGenerator

                # Créer une instance temporaire (sans DB car on utilise juste le formateur)
                temp_gen = QuizGenerator(db_path=None)

                # Utiliser la fonction de formatage qui gère defense/squeeze/vs_limpers
                question = temp_gen._format_question(context, hand)

                return question

            except ImportError:
                # Fallback si import échoue
                table = context.get('table_format', '6max')
                position = context.get('hero_position', 'BTN')
                stack = context.get('stack_depth', '100bb')
                primary_action = context.get('primary_action', '').lower()

                # Construire manuellement selon le contexte
                parts = []
                parts.append(f"Table {table}, vous êtes {position} avec {stack}")

                if primary_action == 'defense':
                    # Essayer de récupérer l'opener
                    action_seq = context.get('action_sequence')
                    if action_seq and isinstance(action_seq, dict) and action_seq.get('opener'):
                        opener = action_seq['opener']
                    else:
                        opener = "UTG"  # Fallback
                    parts.append(f"{opener} ouvre")

                elif primary_action == 'squeeze':
                    parts.append("UTG ouvre, un joueur call")

                elif primary_action == 'vs_limpers':
                    parts.append("un joueur limp")

                question = ". ".join(parts) + f". Vous avez {hand}. Que faites-vous ?"
                return question

        # Pour les étapes suivantes
        return f"Étape {step_number}/{total_steps} - Que faites-vous ?"

    def _generate_implicit_fold_sequence(self, primary_action: str) -> Optional[str]:
        """
        Génère une séquence avec FOLD implicite quand la main n'est dans aucune sous-range

        Args:
            primary_action: Action principale du contexte (open, defense, squeeze, vs_limpers)

        Returns:
            Séquence d'actions avec FOLD implicite, ou None
        """
        if primary_action == 'open':
            # On open, puis on fold au 3bet
            return 'RAISE→FOLD'

        elif primary_action == 'defense':
            # On fold face à l'ouverture
            return 'FOLD'

        elif primary_action == 'squeeze':
            # On fold face au squeeze
            return 'FOLD'

        elif primary_action == 'vs_limpers':
            # On fold face aux limpers
            return 'FOLD'

        # Fallback
        return None

    def _generate_fixed_villain_position(self, context: Dict) -> str:
        """
        🆕 v4.3.6 : Génère la position du Vilain UNE SEULE FOIS pour toute la séquence drill-down.
        
        Args:
            context: Contexte avec primary_action, hero_position, etc.
            
        Returns:
            Position du Vilain (ex: "CO", "BB", "UTG")
        """
        primary_action = context.get('primary_action', '')
        action_seq = context.get('action_sequence')
        vs_position = context.get('vs_position')  # Depuis la BDD
        
        # 1️⃣ Pour OPEN : Générer une position cohérente (après le héros)
        if primary_action == 'open':
            if vs_position:
                return vs_position
            else:
                hero_pos = context.get('hero_position', 'UTG')
                table_format = context.get('table_format', '6max')
                return self._generate_villain_position(hero_pos, table_format)
        
        # 2️⃣ Pour defense/squeeze : utiliser l'opener
        elif primary_action in ['defense', 'squeeze']:
            if vs_position:
                return vs_position
            elif action_seq and isinstance(action_seq, dict) and action_seq.get('opener'):
                return action_seq['opener']
            elif primary_action == 'defense':
                # Fallback basé sur le nom du contexte
                display_name = context.get('display_name', '')
                if 'vs UTG' in display_name or 'UTG' in display_name:
                    return 'UTG'
                elif 'vs CO' in display_name or 'CO' in display_name:
                    return 'CO'
                elif 'vs MP' in display_name or 'MP' in display_name:
                    return 'MP'
                elif 'vs BTN' in display_name or 'BTN' in display_name:
                    return 'BTN'
        
        # Fallback générique
        return "Vilain"

    def _get_villain_reaction_at_level(self, level: int, hero_last_action: str, context: Dict = None) -> Optional[Dict]:
        """
        🆕 Génère la réaction du Vilain de manière réaliste selon le niveau.
        🔧 CORRECTION v2 : Génère intelligemment la position du Vilain pour OPEN

        Workflow 5Bet/All-In :
        - Niveau 1 (après notre open) : Vilain 3bet
        - Niveau 2 (après notre 4bet) : 50% 5bet, 50% all-in

        Args:
            level: Niveau actuel (0, 1, 2...)
            hero_last_action: Dernière action du héros
            context: Contexte avec action_sequence pour récupérer l'opener

        Returns:
            Dict avec action du Vilain, ou None
        """
        # 🔧 BUGFIX v4.3.6 : Utiliser la position fixe générée une seule fois
        villain_position = "Vilain"  # Fallback
        
        if context and 'villain_position_fixed' in context:
            # Utiliser la position fixe générée au début du drill-down
            villain_position = context['villain_position_fixed']
        elif context:
            # Fallback si la position fixe n'existe pas (ancien code)
            villain_position = "Vilain"

        # Niveau 1 : Vilain 3bet après notre open/squeeze
        if level == 1:
            return {
                'action': 'RAISE',
                'text': f'{villain_position} 3bet',
                'sizing': '3bet',
                'allows_raise': True  # On peut 4bet
            }

        # Niveau 2 : Workflow 5Bet/All-In (après notre 4bet)
        elif level == 2 and hero_last_action == 'RAISE':
            # 50% chance de 5bet, 50% chance de all-in
            is_allin = random.random() < 0.5

            if is_allin:
                print(f"  🎲 Vilain reaction niveau 2: ALL-IN")
                return {
                    'action': 'ALL_IN',
                    'text': f'{villain_position} all-in',
                    'sizing': 'all-in',
                    'allows_raise': False  # On ne peut plus raise face à all-in
                }
            else:
                print(f"  🎲 Vilain reaction niveau 2: 5BET")
                return {
                    'action': 'RAISE',
                    'text': f'{villain_position} 5bet',
                    'sizing': '5bet',
                    'allows_raise': True  # On peut 6bet (rare mais possible)
                }

        return None

    def _format_drill_step_question(self, context: Dict, hand: str, step_number: int, sequence: List[Dict]) -> str:
        """
        Formate le texte d'une étape spécifique du drill down

        Args:
            context: Contexte du quiz
            hand: Main jouée
            step_number: Numéro de l'étape (1, 2, 3...)
            sequence: Séquence complète des étapes

        Returns:
            Texte de la question pour cette étape
        """
        primary_action = context.get('primary_action', 'open')

        # Étape 1 : déjà gérée dans _format_drill_question
        if step_number == 1:
            return self._format_drill_question(context, hand, 1, len(sequence))

        # Étape 2+ : dépend du contexte
        if primary_action == 'open':
            if step_number == 2:
                return "CO vous 3bet. Que faites-vous ?"
            elif step_number == 3:
                return "CO vous 5bet all-in. Que faites-vous ?"
            else:
                return f"Étape {step_number} - Que faites-vous ?"

        elif primary_action == 'defense':
            if step_number == 2:
                return "L'ouvreur vous 4bet. Que faites-vous ?"
            elif step_number == 3:
                return "L'ouvreur vous 5bet all-in. Que faites-vous ?"
            else:
                return f"Étape {step_number} - Que faites-vous ?"

        elif primary_action == 'squeeze':
            if step_number == 2:
                return "L'ouvreur vous 4bet. Que faites-vous ?"
            elif step_number == 3:
                return "L'ouvreur vous 5bet all-in. Que faites-vous ?"
            else:
                return f"Étape {step_number} - Que faites-vous ?"

        # Fallback générique
        return f"Étape {step_number} - Que faites-vous ?"


def example_usage():
    """Exemple d'utilisation du DrillDownGenerator"""

    drill = DrillDownGenerator()

    # Exemple 1 : Récupérer et afficher une séquence
    print("=" * 70)
    print("EXEMPLE 1 : Récupération d'une séquence")
    print("=" * 70)

    hand = "AKs"
    context_id = 1

    sequence = drill.get_drill_down_sequence(hand, context_id)

    if sequence:
        print(f"\nSéquence complète pour {hand}:")
        for step in sequence:
            print(f"  Étape {step['step_number']}: {step['text']}")

    # Exemple 2 : Afficher une question
    print("\n" + "=" * 70)
    print("EXEMPLE 2 : Affichage d'une question")
    print("=" * 70)

    drill.display_drill_down_question(hand, context_id, step_number=1)

    # Exemple 3 : Valider une réponse
    print("=" * 70)
    print("EXEMPLE 3 : Validation d'une réponse")
    print("=" * 70)

    # Test avec une action correcte
    result = drill.validate_answer(hand, context_id, step_number=1, user_action="RAISE")
    print(f"\nRéponse 'RAISE' à l'étape 1:")
    print(f"  Correct: {result['correct']}")
    print(f"  Message: {result['message']}")

    # Test avec une étape avec choix (step 3)
    if len(sequence) >= 3:
        drill.display_drill_down_question(hand, context_id, step_number=3)

        result = drill.validate_answer(hand, context_id, step_number=3, user_action="RAISE")
        print(f"\nRéponse 'RAISE' à l'étape 3:")
        print(f"  Correct: {result['correct']}")
        print(f"  Message: {result['message']}")
        if 'note' in result:
            print(f"  Note: {result['note']}")


def test_all_sequences():
    """Teste toutes les séquences dans la base"""

    drill = DrillDownGenerator()

    with sqlite3.connect(drill.db_path) as conn:
        cursor = conn.cursor()

        # Récupérer toutes les séquences uniques
        cursor.execute("""
            SELECT DISTINCT action_sequence, COUNT(*) as count
            FROM ranges
            WHERE action_sequence IS NOT NULL
            GROUP BY action_sequence
            ORDER BY count DESC
        """)

        results = cursor.fetchall()

        print("\n" + "=" * 70)
        print("TOUTES LES SÉQUENCES D'ACTIONS DANS LA BASE")
        print("=" * 70)

        for sequence_str, count in results:
            print(f"\n📊 Séquence: {sequence_str} (utilisée {count} fois)")

            # Parser et afficher chaque étape
            steps = sequence_str.split("→")
            for i, step in enumerate(steps, 1):
                parsed = drill.parse_action_step(step)
                print(f"   Étape {i}: {parsed['text']}")


if __name__ == "__main__":
    print("\n🎮 DÉMONSTRATION DU DRILL DOWN AVEC action_sequence\n")

    try:
        # Exemple complet
        example_usage()

        print("\n" + "=" * 70)
        print("\n🧪 Test de toutes les séquences disponibles\n")

        # Test de toutes les séquences
        test_all_sequences()

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback

        traceback.print_exc()