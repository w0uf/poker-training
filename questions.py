#!/usr/bin/env python3
"""
Générateur de questions corrigé pour l'entraînement aux ranges de poker
CORRECTION: Questions plus précises avec contexte complet
"""

import sqlite3
import json
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from pathlib import Path


# ============================================================================
# QUESTION MODELS CORRIGÉS
# ============================================================================

class QuestionType(Enum):
    HAND_IN_RANGE = "hand_in_range"  # "AKs est dans Call ?"
    ACTION_FOR_HAND = "action_for_hand"  # "Avec AA que faire ?"
    RANGE_COVERAGE = "range_coverage"  # "Combien de mains dans cette range ?"
    CONTEXT_QUESTION = "context_question"  # "Position CO signifie ?"


class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3


@dataclass
class Question:
    """Une question de quiz avec sa réponse et contexte complet"""
    id: str
    question_type: QuestionType
    question: str
    correct_answer: str
    choices: List[str]
    explanation: str
    difficulty: Difficulty
    context_id: int
    context_name: str
    metadata: Dict


# ============================================================================
# HAND STRENGTH EVALUATOR AMÉLIORÉ
# ============================================================================

class HandStrengthEvaluator:
    """Évalue la force relative des mains preflop avec plus de précision"""

    def __init__(self):
        self.hand_rankings = self._build_detailed_hand_rankings()

    def _build_detailed_hand_rankings(self) -> Dict[str, int]:
        """Crée une hiérarchie détaillée des mains preflop"""
        rankings = {}

        # Paires premium (169-150)
        premium_pairs = ['AA', 'KK', 'QQ', 'JJ']
        for i, pair in enumerate(premium_pairs):
            rankings[pair] = 169 - i

        # Paires moyennes (149-140)
        medium_pairs = ['TT', '99', '88', '77']
        for i, pair in enumerate(medium_pairs):
            rankings[pair] = 149 - i

        # Petites paires (139-130)
        small_pairs = ['66', '55', '44', '33', '22']
        for i, pair in enumerate(small_pairs):
            rankings[pair] = 139 - i

        # Aces suitées premium (129-120)
        premium_aces_s = ['AKs', 'AQs', 'AJs', 'ATs']
        for i, hand in enumerate(premium_aces_s):
            rankings[hand] = 129 - i

        # Aces offsuits premium (119-110)
        premium_aces_o = ['AKo', 'AQo', 'AJo', 'ATo']
        for i, hand in enumerate(premium_aces_o):
            rankings[hand] = 119 - i

        # Suited broadways (109-100)
        suited_broadways = ['KQs', 'KJs', 'KTs', 'QJs', 'QTs', 'JTs']
        for i, hand in enumerate(suited_broadways):
            rankings[hand] = 109 - i

        # Le reste avec des valeurs approximatives...
        remaining_hands = [
            ('KQo', 99), ('T9s', 98), ('KJo', 97), ('A9s', 96),
            ('98s', 95), ('QJo', 94), ('87s', 93), ('A8s', 92),
            ('76s', 91), ('KTo', 90)
        ]

        for hand, rank in remaining_hands:
            rankings[hand] = rank

        return rankings

    def get_strength(self, hand: str) -> int:
        """Retourne la force d'une main (plus haut = plus fort)"""
        return self.hand_rankings.get(hand, 50)  # Default 50 pour mains non listées

    def categorize_hand(self, hand: str) -> str:
        """Catégorise une main pour les explications"""
        strength = self.get_strength(hand)

        if strength >= 160:
            return "premium"
        elif strength >= 140:
            return "strong"
        elif strength >= 100:
            return "playable"
        elif strength >= 70:
            return "marginal"
        else:
            return "weak"


# ============================================================================
# GÉNÉRATEUR DE QUESTIONS CORRIGÉ
# ============================================================================

class ImprovedPokerQuestionGenerator:
    """Générateur de questions amélioré avec contextes précis"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.hand_evaluator = HandStrengthEvaluator()
        self.contexts = self._load_enriched_contexts()

    def _load_enriched_contexts(self) -> List[Dict]:
        """Charge les contextes enrichis V4"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, enriched_metadata 
                FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.version') = 'v4'
                  AND json_extract(enriched_metadata, '$.question_friendly') = true
                  AND json_extract(enriched_metadata, '$.hero_position') IS NOT NULL
            """)

            contexts = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[2]) if row[2] else {}
                    if self._is_context_suitable_for_questions(metadata):
                        contexts.append({
                            'id': row[0],
                            'name': row[1],
                            'metadata': metadata,
                            'ranges': self._load_context_ranges(row[0])
                        })
                except json.JSONDecodeError:
                    continue

            return contexts

    def _is_context_suitable_for_questions(self, metadata: Dict) -> bool:
        """Vérifie si un contexte est approprié pour générer des questions"""
        required_fields = [
            'hero_position',
            'primary_action',
            'game_format',
            'variant'
        ]
        return all(metadata.get(field) for field in required_fields)

    def _load_context_ranges(self, context_id: int) -> List[Dict]:
        """Charge les ranges d'un contexte avec leurs mains"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT r.id, r.name, r.color, r.range_key
                FROM ranges r
                WHERE r.context_id = ?
            """, (context_id,))

            ranges = []
            for row in cursor.fetchall():
                range_id, name, color, range_key = row

                # Charger les mains de cette range
                hands_cursor = conn.execute("""
                    SELECT hand, frequency
                    FROM range_hands
                    WHERE range_id = ?
                """, (range_id,))

                hands = [{'hand': h[0], 'frequency': h[1]} for h in hands_cursor.fetchall()]

                ranges.append({
                    'id': range_id,
                    'name': name,
                    'color': color,
                    'range_key': range_key,
                    'hands': hands
                })

            return ranges

    def generate_improved_action_question(self, context: Dict, difficulty: Difficulty = Difficulty.MEDIUM) -> Question:
        """Génère une question d'action AMÉLIORÉE avec contexte unique"""

        if not context['ranges'] or len(context['ranges']) < 2:
            raise ValueError(f"Pas assez de ranges dans {context['name']}")

        metadata = context['metadata']

        # Construire le contexte précis avec action précédente
        situation = self._build_complete_situation_description(metadata)

        # Choisir une main appropriée à la difficulté
        test_hands = self._select_test_hands_by_difficulty(context, difficulty)
        if not test_hands:
            raise ValueError("Aucune main appropriée trouvée")

        chosen_hand_data = random.choice(test_hands)
        hand = chosen_hand_data['hand']
        correct_ranges = chosen_hand_data['ranges']

        # Convertir la range en action de table
        correct_action = self._convert_range_to_table_action(correct_ranges[0], metadata)

        # Créer les choix avec les actions de table standards
        choices = self._generate_table_action_choices(context, metadata, correct_action)

        # Question SANS répétition du contexte
        question_text = f"Vous recevez {hand}.\nQuelle est votre action ?"

        # Explication détaillée
        hand_category = self.hand_evaluator.categorize_hand(hand)
        explanation = self._generate_action_explanation(hand, hand_category, correct_action, metadata)

        return Question(
            id=f"action_only_{context['id']}_{hand}",
            question_type=QuestionType.ACTION_FOR_HAND,
            question=question_text,
            correct_answer=correct_action,
            choices=choices,
            explanation=explanation,
            difficulty=difficulty,
            context_id=context['id'],
            context_name=context['name'],
            metadata={
                'hand': hand,
                'situation': situation,
                'hand_category': hand_category,
                'context_metadata': metadata
            }
        )

    def _build_complete_situation_description(self, metadata: Dict) -> str:
        """Construit une description complète avec action précédente CLAIRE"""
        parts = []

        # Format de jeu
        variant = metadata.get('variant', 'No Limit Hold\'em')
        table_format = metadata.get('table_format', '6max')
        hero_pos = metadata.get('hero_position', 'MP')
        vs_pos = metadata.get('vs_position')
        action = metadata.get('primary_action', 'open')

        # Construction selon le type d'action - CLARIFIÉE
        if action == 'open':
            parts.append(f"Partie {table_format} de {variant}")
            parts.append(f"vous êtes en {hero_pos}")
            parts.append("foldé jusqu'à vous")  # CLAIR: c'est un open
        elif action == 'defense' and vs_pos:
            parts.append(f"Partie {table_format} de {variant}")
            parts.append(f"{vs_pos} ouvre")
            parts.append(f"vous êtes en {hero_pos}")
        elif action == 'call' and vs_pos:
            parts.append(f"Partie {table_format} de {variant}")
            parts.append(f"{vs_pos} raise")
            parts.append(f"vous êtes en {hero_pos}")
        elif action == '3bet' and vs_pos:
            parts.append(f"Partie {table_format} de {variant}")
            parts.append(f"{vs_pos} ouvre")
            parts.append(f"vous êtes en {hero_pos}")
        else:
            # Fallback - essayer de deviner selon vs_position
            parts.append(f"Partie {table_format} de {variant}")
            if vs_pos:
                parts.append(f"{vs_pos} ouvre")
                parts.append(f"vous êtes en {hero_pos}")
            else:
                parts.append(f"vous êtes en {hero_pos}")
                parts.append("foldé jusqu'à vous")  # Par défaut = open

        # Stack depth si spécifié
        stack = metadata.get('stack_depth')
        if stack and stack != '100bb':
            parts.append(f"({stack})")

        return ", ".join(parts) + "."

    def _convert_range_to_table_action(self, range_obj: Dict, metadata: Dict) -> str:
        """Convertit une range en action de table (FOLD, CALL, RAISE seulement)"""
        range_name = range_obj['name'].lower()

        # Mapping simple des ranges vers actions de base
        if any(word in range_name for word in ['fold']):
            return "FOLD"
        elif any(word in range_name for word in ['call', 'flat']):
            return "CALL"
        elif any(word in range_name for word in ['open', 'rfi', 'raise', '3bet', '4bet', 'reraise']):
            return "RAISE"
        else:
            # Déterminer l'action selon le contexte
            primary_action = metadata.get('primary_action', 'open')
            if primary_action == 'open':
                return "RAISE"  # Open = raise
            elif primary_action in ['defense', '3bet']:
                return "RAISE"  # Défense agressive = 3bet = raise
            else:
                return "CALL"  # Défense passive = call

    def _generate_table_action_choices(self, context: Dict, metadata: Dict, correct_action: str) -> List[str]:
        """Génère les choix d'actions de table selon la situation - VERSION FINALE"""

        vs_pos = metadata.get('vs_position')
        hero_pos = metadata.get('hero_position', 'MP')

        # LOGIQUE SIMPLE ET CLAIRE : Si pas de vs_position = situation d'ouverture
        if not vs_pos:
            # Situation d'ouverture (foldé jusqu'à nous)
            if hero_pos == 'SB':
                # Small Blind : peut call pour compléter
                possible_actions = ["RAISE", "CALL", "FOLD"]
            else:
                # TOUTES les autres positions : PAS DE CALL !
                possible_actions = ["RAISE", "FOLD"]
        else:
            # Face à une action (vs_position existe)
            possible_actions = ["RAISE", "CALL", "FOLD"]

        # S'assurer que la réponse correcte est dans les actions possibles
        if correct_action not in possible_actions:
            possible_actions.append(correct_action)

        return possible_actions

    def _generate_action_explanation(self, hand: str, hand_category: str, correct_action: str, metadata: Dict) -> str:
        """Génère une explication détaillée basée sur les JSON de l'utilisateur"""
        primary_action = metadata.get('primary_action', 'open')
        hero_pos = metadata.get('hero_position', 'MP')
        vs_pos = metadata.get('vs_position')

        explanation = f"Avec {hand} ({hand_category}) "

        if primary_action == 'open':
            if hero_pos == 'SB':
                explanation += f"en {hero_pos} (foldé jusqu'à vous), "
            else:
                explanation += f"en {hero_pos} sans action avant vous, "
        elif primary_action == 'defense' and vs_pos:
            explanation += f"en {hero_pos} face à un open de {vs_pos}, "
        elif vs_pos:
            explanation += f"en {hero_pos} face à {vs_pos}, "
        else:
            explanation += f"en {hero_pos}, "

        # AJOUT : Préciser que ça vient des JSON
        explanation += f"l'action optimale d'après vos JSON est '{correct_action}'"

        # Ajouter la logique derrière l'action (avec spécificité SB)
        if correct_action == "FOLD":
            if hero_pos == 'SB':
                explanation += " car cette main ne fait pas partie de vos ranges de completion ou d'open"
            else:
                explanation += " car cette main n'est pas dans votre range d'ouverture"
        elif correct_action == "CALL":
            if hero_pos == 'SB' and primary_action == 'open':
                explanation += " selon votre range de completion des blinds"
            else:
                explanation += " selon votre range de call défensive"
        elif correct_action == "RAISE":
            if primary_action == 'open':
                explanation += " selon votre range d'ouverture"
            elif primary_action in ['defense', '3bet']:
                explanation += " selon votre range de 3-bet"
            else:
                explanation += " selon vos ranges définies"

        return explanation + "."

    def _build_situation_description(self, metadata: Dict) -> str:
        """Construit une description précise de la situation - DÉPRÉCIÉ"""
        # Cette fonction est remplacée par _build_complete_situation_description
        return self._build_complete_situation_description(metadata)

    def _select_test_hands_by_difficulty(self, context: Dict, difficulty: Difficulty) -> List[Dict]:
        """Sélectionne des mains appropriées selon la difficulté"""

        # Construire la liste main -> ranges
        hand_to_ranges = {}
        for range_obj in context['ranges']:
            for hand_data in range_obj['hands']:
                hand = hand_data['hand']
                if hand not in hand_to_ranges:
                    hand_to_ranges[hand] = []
                hand_to_ranges[hand].append(range_obj)

        test_hands = []

        for hand, ranges in hand_to_ranges.items():
            hand_strength = self.hand_evaluator.get_strength(hand)

            # Filtrer selon difficulté
            if difficulty == Difficulty.EASY:
                # Mains évidentes : très fortes ou très faibles
                if hand_strength >= 140 or hand_strength <= 70:
                    test_hands.append({'hand': hand, 'ranges': ranges})

            elif difficulty == Difficulty.MEDIUM:
                # Mains moyennes avec décision claire
                if 100 <= hand_strength <= 139:
                    test_hands.append({'hand': hand, 'ranges': ranges})

            else:  # HARD
                # Mains borderline avec décisions difficiles
                if 80 <= hand_strength <= 120 and len(ranges) >= 1:
                    test_hands.append({'hand': hand, 'ranges': ranges})

        return test_hands

    def generate_range_membership_question(self, context: Dict, difficulty: Difficulty = Difficulty.EASY) -> Question:
        """Génère une question 'main dans range' AMÉLIORÉE"""

        if not context['ranges']:
            raise ValueError(f"Aucune range dans {context['name']}")

        metadata = context['metadata']
        situation = self._build_situation_description(metadata)

        # Choisir une range
        target_range = random.choice(context['ranges'])
        range_hands = [h['hand'] for h in target_range['hands']]

        if not range_hands:
            raise ValueError(f"Range '{target_range['name']}' vide")

        # 70% main dans la range, 30% hors range
        if random.random() < 0.7:
            hand = random.choice(range_hands)
            correct_answer = "Oui"
            explanation = f"Dans cette situation, {hand} fait partie de la range '{target_range['name']}'"
        else:
            # Trouver des mains hors range
            all_possible_hands = self._get_common_poker_hands()
            hands_not_in_range = [h for h in all_possible_hands if h not in range_hands]

            if hands_not_in_range:
                hand = random.choice(hands_not_in_range)
                correct_answer = "Non"
                explanation = f"Dans cette situation, {hand} ne fait PAS partie de la range '{target_range['name']}'"
            else:
                # Fallback
                hand = random.choice(range_hands)
                correct_answer = "Oui"
                explanation = f"Dans cette situation, {hand} fait partie de la range '{target_range['name']}'"

        question_text = f"{situation}\nLa main {hand} fait-elle partie de votre range '{target_range['name']}' ?"

        return Question(
            id=f"range_member_{context['id']}_{target_range['id']}_{hand}",
            question_type=QuestionType.HAND_IN_RANGE,
            question=question_text,
            correct_answer=correct_answer,
            choices=["Oui", "Non"],
            explanation=explanation,
            difficulty=difficulty,
            context_id=context['id'],
            context_name=context['name'],
            metadata={
                'hand': hand,
                'range_name': target_range['name'],
                'situation': situation
            }
        )

    def _get_common_poker_hands(self) -> List[str]:
        """Retourne les mains de poker les plus communes pour les tests"""
        pairs = [f"{r}{r}" for r in "AKQJT98765432"]

        suited = []
        offsuit = []
        ranks = "AKQJT98765432"

        for i, r1 in enumerate(ranks):
            for r2 in ranks[i + 1:]:
                suited.append(f"{r1}{r2}s")
                offsuit.append(f"{r1}{r2}o")

        # Retourner seulement les mains les plus communes
        common_hands = pairs[:9] + suited[:20] + offsuit[:15]
        return common_hands

    def generate_random_question(self, difficulty: Difficulty = None) -> Question:
        """Génère une question aléatoire - SEULEMENT des questions d'action"""

        if not self.contexts:
            raise ValueError("Aucun contexte enrichi V4 disponible pour les questions")

        if difficulty is None:
            difficulty = random.choice(list(Difficulty))

        context = random.choice(self.contexts)

        # SEULEMENT des questions d'action (FOLD/CALL/RAISE)
        try:
            return self.generate_improved_action_question(context, difficulty)
        except ValueError as e:
            # Essayer un autre contexte
            if len(self.contexts) > 1:
                other_contexts = [c for c in self.contexts if c['id'] != context['id']]
                if other_contexts:
                    context = random.choice(other_contexts)
                    return self.generate_improved_action_question(context, difficulty)
            raise e


# ============================================================================
# QUIZ RUNNER AMÉLIORÉ
# ============================================================================

class ImprovedQuizRunner:
    """Interface console améliorée pour les quiz"""

    def __init__(self, db_path: str):
        self.generator = ImprovedPokerQuestionGenerator(db_path)

    def run_interactive_quiz(self):
        """Lance un quiz interactif amélioré"""

        print("🃏 GÉNÉRATEUR DE QUESTIONS POKER - VERSION AMÉLIORÉE")
        print("=" * 60)

        if not self.generator.contexts:
            print("❌ Aucun contexte V4 enrichi et question-friendly trouvé!")
            print("💡 Assurez-vous d'avoir:")
            print("   1. Importé vos ranges: python poker-training.py")
            print("   2. Enrichi en V4: python enrich_ranges.py")
            print("   3. Marqué comme question-friendly")
            return

        print(f"✅ {len(self.generator.contexts)} contextes disponibles:")
        for ctx in self.generator.contexts:
            print(f"   • {ctx['metadata'].get('display_name', ctx['name'])}")

        # Configuration du quiz
        num_questions = self._ask_quiz_config()

        print(f"\n🎲 Génération de {num_questions} questions améliorées...")

        try:
            questions = []
            for _ in range(num_questions):
                question = self.generator.generate_random_question()
                questions.append(question)

            print(f"✅ {len(questions)} questions générées")
            self._play_improved_quiz(questions)

        except Exception as e:
            print(f"❌ Erreur génération: {e}")

    def _ask_quiz_config(self) -> int:
        """Demande la configuration du quiz"""
        try:
            num = int(input("\nNombre de questions (1-20) [5]: ") or "5")
            return max(1, min(20, num))
        except ValueError:
            return 5

    def _play_improved_quiz(self, questions: List[Question]):
        """Joue un quiz amélioré"""

        print(f"\n🚀 DÉBUT DU QUIZ AMÉLIORÉ")
        print("=" * 40)

        score = 0

        for i, question in enumerate(questions, 1):
            print(f"\n📋 Question {i}/{len(questions)}")
            print(f"Type: {question.question_type.value}")
            print(f"Contexte: {question.metadata.get('situation', question.context_name)}")
            print(f"\n❓ {question.question}")

            # Afficher les choix
            for j, choice in enumerate(question.choices, 1):
                emoji = "🔥" if choice == question.correct_answer else "•"
                print(f"   {j}. {choice}")

            # Récupérer la réponse
            while True:
                try:
                    answer = input(f"\nVotre réponse (1-{len(question.choices)}) ou 'q': ").strip()

                    if answer.lower() == 'q':
                        print("❌ Quiz interrompu")
                        return

                    answer_idx = int(answer) - 1
                    if 0 <= answer_idx < len(question.choices):
                        user_answer = question.choices[answer_idx]
                        break
                    else:
                        print("❌ Choix invalide!")
                except ValueError:
                    print("❌ Veuillez entrer un nombre!")

            # Vérifier la réponse
            if user_answer == question.correct_answer:
                print("✅ Correct !")
                score += 1
            else:
                print(f"❌ Incorrect. La bonne réponse était: {question.correct_answer}")

            print(f"💡 {question.explanation}")

            if i < len(questions):
                input("\n⏎ Appuyez sur Entrée pour continuer...")

        # Résultats
        self._show_improved_results(score, len(questions))

    def _show_improved_results(self, score: int, total: int):
        """Affiche les résultats améliorés"""

        percentage = (score / total) * 100

        print(f"\n🎉 RÉSULTATS")
        print("=" * 30)
        print(f"Score: {score}/{total} ({percentage:.1f}%)")

        if percentage >= 90:
            print("🏆 Excellent ! Vous maîtrisez parfaitement ces situations.")
        elif percentage >= 70:
            print("👍 Très bien ! Quelques petits ajustements à faire.")
        elif percentage >= 50:
            print("📚 Correct, mais continuez à étudier vos ranges.")
        else:
            print("💪 Revenez aux bases et étudiez vos contextes enrichis.")


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée principal"""

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord: python poker-training.py")
        return

    runner = ImprovedQuizRunner(db_path)
    runner.run_interactive_quiz()


if __name__ == "__main__":
    main()