#!/usr/bin/env python3
"""
Générateur de questions pour l'entraînement aux ranges de poker
Utilise les données enrichies pour créer des quiz adaptatifs
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
# QUESTION MODELS - Structures pour les questions
# ============================================================================

class QuestionType(Enum):
    HAND_IN_RANGE = "hand_in_range"  # "AKs est dans Call ?"
    ACTION_FOR_HAND = "action_for_hand"  # "Avec AA que faire ?"
    STRONGEST_IN_RANGE = "strongest_in_range"  # "Plus forte main en Call ?"
    COMPARE_RANGES = "compare_ranges"  # "Range A vs Range B ?"
    CONTEXT_QUESTION = "context_question"  # "Position CO signifie ?"


class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3


@dataclass
class Question:
    """Une question de quiz avec sa réponse"""
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


@dataclass
class QuizSession:
    """Session de quiz avec paramètres"""
    questions: List[Question]
    current_index: int = 0
    score: int = 0
    start_time: datetime = None
    settings: Dict = None


# ============================================================================
# HAND STRENGTH EVALUATOR - Évaluation force des mains
# ============================================================================

class HandStrengthEvaluator:
    """Évalue la force relative des mains preflop"""

    def __init__(self):
        self.hand_rankings = self._build_hand_rankings()

    def _build_hand_rankings(self) -> Dict[str, int]:
        """Crée une hiérarchie approximative des mains preflop"""
        rankings = {}

        # Paires (AA = 169, KK = 168, etc.)
        pairs = ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22']
        for i, pair in enumerate(pairs):
            rankings[pair] = 169 - i

        # Suited aces (AKs = 155, AQs = 154, etc.)
        suited_aces = ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s']
        for i, hand in enumerate(suited_aces):
            rankings[hand] = 155 - i

        # Offsuit aces (AKo = 143, AQo = 142, etc.)
        offsuit_aces = ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o']
        for i, hand in enumerate(offsuit_aces):
            rankings[hand] = 143 - i

        # Suited kings (KQs = 131, KJs = 130, etc.)
        suited_kings = ['KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s']
        for i, hand in enumerate(suited_kings):
            rankings[hand] = 131 - i

        # Continuer avec les autres mains...
        # Pour la simplicité, on va assigner des valeurs approximatives
        remaining_hands = [
            'KQo', 'QJs', 'KJo', 'JTs', 'QTs', 'QJo', 'KTo', 'A9s', 'QTo', 'JTo'
        ]
        for i, hand in enumerate(remaining_hands):
            rankings[hand] = 120 - i

        return rankings

    def get_strength(self, hand: str) -> int:
        """Retourne la force d'une main (plus haut = plus fort)"""
        return self.hand_rankings.get(hand, 0)

    def compare_hands(self, hand1: str, hand2: str) -> int:
        """Compare deux mains. Retourne 1 si hand1 > hand2, -1 si hand1 < hand2, 0 si égal"""
        strength1 = self.get_strength(hand1)
        strength2 = self.get_strength(hand2)

        if strength1 > strength2:
            return 1
        elif strength1 < strength2:
            return -1
        else:
            return 0


# ============================================================================
# QUESTION GENERATOR - Générateur principal
# ============================================================================

class PokerQuestionGenerator:
    """Générateur de questions basé sur les ranges enrichies"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.hand_evaluator = HandStrengthEvaluator()
        self.contexts = self._load_enriched_contexts()
        self.all_hands = self._get_all_poker_hands()

    def _load_enriched_contexts(self) -> List[Dict]:
        """Charge les contextes enrichis depuis la base"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, enriched_metadata 
                FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.enriched_by_user') = true
                   OR (enriched_metadata != '{}' 
                       AND json_extract(enriched_metadata, '$.hero_position') IS NOT NULL)
            """)

            contexts = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[2]) if row[2] else {}
                    if metadata and metadata.get('hero_position'):
                        contexts.append({
                            'id': row[0],
                            'name': row[1],
                            'metadata': metadata,
                            'ranges': self._load_context_ranges(row[0])
                        })
                except json.JSONDecodeError:
                    continue

            return contexts

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

    def _get_all_poker_hands(self) -> List[str]:
        """Génère toutes les mains de poker possibles"""
        pairs = [f"{rank}{rank}" for rank in "AKQJT98765432"]

        suited = []
        offsuit = []
        ranks = "AKQJT98765432"

        for i, r1 in enumerate(ranks):
            for r2 in ranks[i + 1:]:
                suited.append(f"{r1}{r2}s")
                offsuit.append(f"{r1}{r2}o")

        return pairs + suited + offsuit

    def generate_hand_in_range_question(self, context: Dict, difficulty: Difficulty = Difficulty.EASY) -> Question:
        """Génère une question 'main dans range'"""

        if not context['ranges']:
            raise ValueError(f"Aucune range dans le contexte {context['name']}")

        # Choisir une range au hasard
        target_range = random.choice(context['ranges'])
        range_hands = [h['hand'] for h in target_range['hands']]

        if not range_hands:
            raise ValueError(f"Aucune main dans la range {target_range['name']}")

        # 70% de chance de prendre une main dans la range, 30% hors range
        if random.random() < 0.7:
            # Main qui EST dans la range
            hand = random.choice(range_hands)
            correct_answer = "Oui"
            explanation = f"{hand} fait partie de la range '{target_range['name']}' dans le contexte {context['name']}"
        else:
            # Main qui N'EST PAS dans la range
            hands_not_in_range = [h for h in self.all_hands if h not in range_hands]
            if hands_not_in_range:
                hand = random.choice(hands_not_in_range)
                correct_answer = "Non"
                explanation = f"{hand} ne fait pas partie de la range '{target_range['name']}' dans le contexte {context['name']}"
            else:
                # Fallback si toutes les mains sont dans la range
                hand = random.choice(range_hands)
                correct_answer = "Oui"
                explanation = f"{hand} fait partie de la range '{target_range['name']}'"

        question_text = f"Dans le contexte '{context['name']}', la main {hand} fait-elle partie de la range '{target_range['name']}' ?"

        return Question(
            id=f"hir_{context['id']}_{target_range['id']}_{hand}",
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
                'range_id': target_range['id']
            }
        )

    def generate_action_for_hand_question(self, context: Dict, difficulty: Difficulty = Difficulty.MEDIUM) -> Question:
        """Génère une question 'quelle action pour cette main'"""

        if len(context['ranges']) < 2:
            raise ValueError(f"Pas assez de ranges dans le contexte {context['name']}")

        # Trouver une main qui est dans plusieurs ranges (actions possibles)
        hand_to_ranges = {}
        for range_obj in context['ranges']:
            for hand_data in range_obj['hands']:
                hand = hand_data['hand']
                if hand not in hand_to_ranges:
                    hand_to_ranges[hand] = []
                hand_to_ranges[hand].append(range_obj)

        # Prendre une main qui a plusieurs actions possibles
        multi_action_hands = {h: ranges for h, ranges in hand_to_ranges.items() if len(ranges) > 1}

        if not multi_action_hands:
            # Fallback: prendre n'importe quelle main
            all_hands_in_context = list(hand_to_ranges.keys())
            if not all_hands_in_context:
                raise ValueError("Aucune main trouvée dans ce contexte")

            hand = random.choice(all_hands_in_context)
            possible_ranges = hand_to_ranges[hand]
        else:
            hand = random.choice(list(multi_action_hands.keys()))
            possible_ranges = multi_action_hands[hand]

        correct_range = random.choice(possible_ranges)
        correct_answer = correct_range['name']

        # Créer des choix de réponse
        all_range_names = [r['name'] for r in context['ranges']]
        wrong_choices = [name for name in all_range_names if name != correct_answer]

        choices = [correct_answer]
        choices.extend(random.sample(wrong_choices, min(3, len(wrong_choices))))
        random.shuffle(choices)

        question_text = f"Dans le contexte '{context['name']}', avec la main {hand}, quelle action devez-vous effectuer ?"
        explanation = f"Avec {hand} dans '{context['name']}', l'action recommandée est '{correct_answer}'"

        return Question(
            id=f"afh_{context['id']}_{hand}_{correct_range['id']}",
            question_type=QuestionType.ACTION_FOR_HAND,
            question=question_text,
            correct_answer=correct_answer,
            choices=choices,
            explanation=explanation,
            difficulty=difficulty,
            context_id=context['id'],
            context_name=context['name'],
            metadata={
                'hand': hand,
                'correct_range': correct_range['name'],
                'all_ranges': all_range_names
            }
        )

    def generate_strongest_hand_question(self, context: Dict, difficulty: Difficulty = Difficulty.MEDIUM) -> Question:
        """Génère une question 'main la plus forte dans une range'"""

        if not context['ranges']:
            raise ValueError(f"Aucune range dans le contexte {context['name']}")

        # Choisir une range qui a plusieurs mains
        ranges_with_hands = [r for r in context['ranges'] if len(r['hands']) > 1]
        if not ranges_with_hands:
            raise ValueError("Aucune range avec plusieurs mains")

        target_range = random.choice(ranges_with_hands)
        range_hands = [h['hand'] for h in target_range['hands']]

        # Trouver la main la plus forte
        strongest_hand = max(range_hands, key=self.hand_evaluator.get_strength)

        # Créer des choix de réponse avec d'autres mains de la range
        other_hands = [h for h in range_hands if h != strongest_hand]
        choices = [strongest_hand]

        if len(other_hands) >= 3:
            choices.extend(random.sample(other_hands, 3))
        else:
            choices.extend(other_hands)
            # Compléter avec des mains aléatoires si nécessaire
            if len(choices) < 4:
                random_hands = random.sample([h for h in self.all_hands if h not in range_hands], 4 - len(choices))
                choices.extend(random_hands)

        random.shuffle(choices)

        question_text = f"Dans la range '{target_range['name']}' du contexte '{context['name']}', quelle est la main la plus forte ?"
        explanation = f"Dans cette range, {strongest_hand} est la main la plus forte"

        return Question(
            id=f"sih_{context['id']}_{target_range['id']}_{strongest_hand}",
            question_type=QuestionType.STRONGEST_IN_RANGE,
            question=question_text,
            correct_answer=strongest_hand,
            choices=choices,
            explanation=explanation,
            difficulty=difficulty,
            context_id=context['id'],
            context_name=context['name'],
            metadata={
                'range_name': target_range['name'],
                'strongest_hand': strongest_hand,
                'all_hands_in_range': range_hands
            }
        )

    def generate_context_question(self, context: Dict, difficulty: Difficulty = Difficulty.EASY) -> Question:
        """Génère une question sur le contexte lui-même"""

        metadata = context['metadata']

        question_types = []
        if metadata.get('hero_position'):
            question_types.append('position')
        if metadata.get('primary_action'):
            question_types.append('action')
        if metadata.get('stack_depth'):
            question_types.append('stack')

        if not question_types:
            raise ValueError("Pas assez de métadonnées pour générer une question contexte")

        q_type = random.choice(question_types)

        if q_type == 'position':
            correct_answer = metadata['hero_position']
            question_text = f"Dans le contexte '{context['name']}', quelle est votre position ?"
            wrong_choices = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
            wrong_choices = [pos for pos in wrong_choices if pos != correct_answer]
            explanation = f"Dans '{context['name']}', vous jouez en position {correct_answer}"

        elif q_type == 'action':
            correct_answer = metadata['primary_action']
            question_text = f"Dans le contexte '{context['name']}', quelle est l'action principale ?"
            wrong_choices = ['open', 'call', '3bet', 'fold', 'defense']
            wrong_choices = [action for action in wrong_choices if action != correct_answer]
            explanation = f"'{context['name']}' concerne principalement l'action '{correct_answer}'"

        else:  # stack
            correct_answer = metadata['stack_depth']
            question_text = f"Dans le contexte '{context['name']}', quelle est la stack depth ?"
            wrong_choices = ['20-40bb', '50-75bb', '100bb', '150bb+']
            wrong_choices = [stack for stack in wrong_choices if stack != correct_answer]
            explanation = f"'{context['name']}' est jouée avec une stack de {correct_answer}"

        choices = [correct_answer] + random.sample(wrong_choices, min(3, len(wrong_choices)))
        random.shuffle(choices)

        return Question(
            id=f"ctx_{context['id']}_{q_type}",
            question_type=QuestionType.CONTEXT_QUESTION,
            question=question_text,
            correct_answer=correct_answer,
            choices=choices,
            explanation=explanation,
            difficulty=difficulty,
            context_id=context['id'],
            context_name=context['name'],
            metadata={
                'question_subtype': q_type,
                'context_metadata': metadata
            }
        )

    def generate_random_question(self, difficulty: Difficulty = None) -> Question:
        """Génère une question aléatoire"""

        if not self.contexts:
            raise ValueError("Aucun contexte enrichi disponible")

        if difficulty is None:
            difficulty = random.choice(list(Difficulty))

        context = random.choice(self.contexts)

        # Choisir le type de question selon la difficulté
        if difficulty == Difficulty.EASY:
            question_types = [
                self.generate_hand_in_range_question,
                self.generate_context_question
            ]
        elif difficulty == Difficulty.MEDIUM:
            question_types = [
                self.generate_hand_in_range_question,
                self.generate_action_for_hand_question,
                self.generate_strongest_hand_question
            ]
        else:  # HARD
            question_types = [
                self.generate_action_for_hand_question,
                self.generate_strongest_hand_question
            ]

        generator = random.choice(question_types)

        try:
            return generator(context, difficulty)
        except ValueError as e:
            # Fallback vers une question simple si erreur
            return self.generate_hand_in_range_question(context, Difficulty.EASY)

    def generate_quiz(self, num_questions: int = 10, difficulty: Difficulty = None) -> QuizSession:
        """Génère un quiz complet"""

        questions = []
        attempts = 0
        max_attempts = num_questions * 3  # Éviter boucle infinie

        while len(questions) < num_questions and attempts < max_attempts:
            try:
                question = self.generate_random_question(difficulty)
                # Éviter les doublons
                if not any(q.id == question.id for q in questions):
                    questions.append(question)
            except Exception as e:
                print(f"Erreur génération question: {e}")

            attempts += 1

        return QuizSession(
            questions=questions,
            start_time=datetime.now(),
            settings={
                'difficulty': difficulty.value if difficulty else 'mixed',
                'num_questions': len(questions)
            }
        )


# ============================================================================
# QUIZ RUNNER - Interface console pour jouer
# ============================================================================

class QuizRunner:
    """Interface console pour jouer aux quiz"""

    def __init__(self, db_path: str):
        self.generator = PokerQuestionGenerator(db_path)

    def run_interactive_quiz(self):
        """Lance un quiz interactif en console"""

        print("🃏 GÉNÉRATEUR DE QUESTIONS POKER")
        print("=" * 50)

        if not self.generator.contexts:
            print("❌ Aucun contexte enrichi trouvé!")
            print("💡 Assurez-vous d'avoir importé et enrichi des ranges")
            return

        print(f"✅ {len(self.generator.contexts)} contextes disponibles:")
        for ctx in self.generator.contexts:
            print(f"   • {ctx['name']} ({len(ctx['ranges'])} ranges)")

        # Paramètres du quiz
        print(f"\n🎯 PARAMÈTRES DU QUIZ")

        try:
            num_questions = int(input("Nombre de questions (1-50) [10]: ") or "10")
            num_questions = max(1, min(50, num_questions))
        except ValueError:
            num_questions = 10

        print("\nDifficulté:")
        print("1. Facile (mains dans ranges, contextes)")
        print("2. Moyen (actions, mains les plus fortes)")
        print("3. Difficile (questions complexes)")
        print("4. Mixte (tous niveaux)")

        try:
            diff_choice = int(input("Votre choix (1-4) [4]: ") or "4")
            if diff_choice == 1:
                difficulty = Difficulty.EASY
            elif diff_choice == 2:
                difficulty = Difficulty.MEDIUM
            elif diff_choice == 3:
                difficulty = Difficulty.HARD
            else:
                difficulty = None  # Mixed
        except ValueError:
            difficulty = None

        # Générer et jouer le quiz
        print(f"\n🎲 Génération de {num_questions} questions...")

        try:
            quiz = self.generator.generate_quiz(num_questions, difficulty)
            if not quiz.questions:
                print("❌ Impossible de générer des questions")
                return

            print(f"✅ {len(quiz.questions)} questions générées")
            self.play_quiz(quiz)

        except Exception as e:
            print(f"❌ Erreur génération quiz: {e}")

    def play_quiz(self, quiz: QuizSession):
        """Joue un quiz en console"""

        print(f"\n🚀 DÉBUT DU QUIZ")
        print("=" * 30)

        for i, question in enumerate(quiz.questions, 1):
            print(f"\n📋 Question {i}/{len(quiz.questions)}")
            print(f"Difficulté: {question.difficulty.name}")
            print(f"Type: {question.question_type.value}")
            print(f"\n❓ {question.question}")

            # Afficher les choix
            for j, choice in enumerate(question.choices, 1):
                print(f"   {j}. {choice}")

            # Récupérer la réponse
            while True:
                try:
                    answer_idx = input(f"\nVotre réponse (1-{len(question.choices)}) ou 'q' pour quitter: ").strip()

                    if answer_idx.lower() == 'q':
                        print("❌ Quiz interrompu")
                        return

                    answer_idx = int(answer_idx) - 1
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
                quiz.score += 1
            else:
                print(f"❌ Incorrect. La bonne réponse était: {question.correct_answer}")

            print(f"💡 {question.explanation}")

            # Pause entre questions
            if i < len(quiz.questions):
                input("\nAppuyez sur Entrée pour continuer...")

        # Résultats finaux
        self.show_quiz_results(quiz)

    def show_quiz_results(self, quiz: QuizSession):
        """Affiche les résultats du quiz"""

        score_pct = (quiz.score / len(quiz.questions)) * 100

        print(f"\n🎉 RÉSULTATS DU QUIZ")
        print("=" * 30)
        print(f"Score: {quiz.score}/{len(quiz.questions)} ({score_pct:.1f}%)")

        if score_pct >= 90:
            print("🏆 Excellent ! Vous maîtrisez très bien ces ranges.")
        elif score_pct >= 70:
            print("👍 Bon travail ! Quelques points à améliorer.")
        elif score_pct >= 50:
            print("📚 Pas mal, mais il y a encore du travail.")
        else:
            print("💪 Courage ! Continuez à vous entraîner.")

        # Statistiques par type de question
        type_stats = {}
        for question in quiz.questions:
            q_type = question.question_type.value
            if q_type not in type_stats:
                type_stats[q_type] = {'total': 0, 'correct': 0}
            type_stats[q_type]['total'] += 1

        print(f"\n📊 Répartition par type:")
        for q_type, stats in type_stats.items():
            print(f"   • {q_type}: {stats['total']} questions")


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée principal"""

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord l'import et l'enrichissement")
        return

    runner = QuizRunner(db_path)
    runner.run_interactive_quiz()


if __name__ == "__main__":
    main()