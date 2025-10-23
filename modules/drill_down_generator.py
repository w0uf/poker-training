#!/usr/bin/env python3
"""
Générateur de questions à tiroirs (drill-down) multi-niveaux.
Gère la progression VALUE vs BLUFF et les cascades de ranges.
✅ R4_VALUE = 4bet + CALL all-in (même range, 2 actions)
✅ R4_BLUFF = 4bet + FOLD all-in (même range, 2 actions)
✅ Texte narratif cumulatif
✅ Options adaptées selon situation (all-in = FOLD|CALL seulement)
✅ FOLD IMPLICITES : mains qui ne continuent pas dans les ranges suivants
"""

import random
from typing import Dict, List, Optional
from poker_constants import normalize_action, sort_actions, RANGE_STRUCTURE


class DrillDownGenerator:
    """Génère des questions à tiroirs avec progression contextuelle"""

    def __init__(self):
        # Utiliser RANGE_STRUCTURE depuis poker_constants
        pass

    def can_generate_drill_down(self, ranges: List[Dict]) -> bool:
        """
        Vérifie si le contexte supporte les questions à tiroirs.
        """
        for range_data in ranges:
            label = self._normalize_label(range_data.get('label_canon', ''))
            if label in RANGE_STRUCTURE:
                struct = RANGE_STRUCTURE[label]
                if len(struct['actions']) > 1:
                    return True
                if struct['next_ranges']:
                    for next_label in struct['next_ranges']:
                        if self._find_range_by_label(next_label, ranges):
                            return True
        return False

    def generate_drill_down_question(
            self,
            context: Dict,
            ranges: List[Dict],
            in_range_hands: set,
            out_of_range_hands: set
    ) -> Optional[Dict]:
        """
        Génère une question à tiroirs complète.
        🆕 Accepte maintenant les FOLD implicites (mains pas dans ranges de continuation)
        """
        # 🆕 Sélectionner depuis le range initial (OPEN, etc.)
        cascade_hand = self._find_hand_for_drill_down(in_range_hands, ranges)

        if not cascade_hand:
            print("[DRILL_DOWN] Aucune main appropriée trouvée")
            return None

        # 🆕 Analyser la cascade (inclut FOLD implicites)
        cascade = self.analyze_hand_cascade(cascade_hand, ranges)

        if len(cascade) < 2:
            print(f"[DRILL_DOWN] Cascade trop courte pour {cascade_hand}: {len(cascade)} niveau(x)")
            return None

        print(f"\n[DRILL_DOWN] ✅ Main sélectionnée: {cascade_hand}")
        print(f"[DRILL_DOWN] Cascade détectée: {len(cascade)} niveaux")
        for i, step in enumerate(cascade):
            fold_marker = " (FOLD IMPLICITE)" if step.get('is_implicit_fold') else ""
            print(
                f"  Niveau {i}: {step['label']} → {step['hero_action']} (villain: {step['villain_action']}){fold_marker}")

        levels = []
        for level_num, step in enumerate(cascade):
            level_data = self._build_level(
                level_num=level_num,
                step=step,
                context=context,
                hand=cascade_hand,
                cascade=cascade
            )
            if level_data:
                levels.append(level_data)

        if not levels:
            print("[DRILL_DOWN] Échec construction des niveaux")
            return None

        print(f"[DRILL_DOWN] ✅ Question complète générée: {len(levels)} niveaux")
        print(f"[DRILL_DOWN] Exemple niveau 0: {levels[0]['question'][:80]}...")
        if len(levels) > 1:
            print(f"[DRILL_DOWN] Exemple niveau 1: {levels[1]['question'][:80]}...")
        print()

        return {
            'type': 'drill_down',
            'context_id': context['id'],
            'hand': cascade_hand,
            'levels': levels,
            'context_info': context
        }

    def analyze_hand_cascade(self, hand: str, ranges: List[Dict]) -> List[Dict]:
        """
        Analyse la cascade complète de ranges/actions pour une main donnée.
        🆕 INCLUT LES FOLD IMPLICITES : continue même si la main n'est pas dans le range suivant
        """
        cascade = []

        # Trouver le range de départ
        start_labels = ['OPEN', 'R3_VALUE', 'R3_BLUFF']
        current_range = None
        current_label = None

        for label in start_labels:
            found_range = self._find_range_with_hand(label, hand, ranges)
            if found_range:
                current_range = found_range
                current_label = label
                break

        if not current_range:
            return []

        visited_ranges = set()

        while current_label and current_label in RANGE_STRUCTURE:
            if current_label in visited_ranges:
                break

            struct = RANGE_STRUCTURE[current_label]

            # Ajouter les actions de ce niveau
            for villain_action, hero_action in struct['actions']:
                cascade.append({
                    'label': current_label,
                    'villain_action': villain_action,
                    'hero_action': hero_action,
                    'range': current_range,
                    'is_implicit_fold': False  # Pas un fold implicite, la main est dans ce range
                })

            visited_ranges.add(current_label)

            # 🆕 Chercher le range suivant
            next_ranges = struct['next_ranges']
            if not next_ranges:
                break

            # Essayer de trouver un range suivant contenant la main
            next_range = None
            next_label = None
            for possible_label in next_ranges:
                found = self._find_range_with_hand(possible_label, hand, ranges)
                if found:
                    next_range = found
                    next_label = possible_label
                    break

            # 🆕 Si la main N'EST PAS dans les ranges de continuation → FOLD IMPLICITE
            if not next_range:
                # Chercher quand même s'il existe des ranges de continuation (pour savoir quelle action villain)
                # pour construire une question pédagogique
                any_next_range = None
                for possible_label in next_ranges:
                    found = self._find_range_by_label(possible_label, ranges)
                    if found:
                        any_next_range = found
                        next_label = possible_label
                        break

                if any_next_range and next_label in RANGE_STRUCTURE:
                    # Il existe un range de continuation, mais la main n'y est pas
                    # → Créer un niveau FOLD IMPLICITE
                    next_struct = RANGE_STRUCTURE[next_label]
                    if next_struct['actions']:
                        # Prendre la première action du villain pour ce niveau
                        villain_action = next_struct['actions'][0][0]

                        cascade.append({
                            'label': next_label,  # Pour référence
                            'villain_action': villain_action,
                            'hero_action': 'FOLD',  # 🆕 FOLD implicite
                            'range': None,  # La main n'est pas dans ce range
                            'is_implicit_fold': True  # 🆕 Marqueur
                        })

                        # Arrêter ici, on ne continue pas après un FOLD
                        break
                else:
                    # Pas de range suivant du tout
                    break
            else:
                # La main est dans le range suivant, continuer normalement
                current_label = next_label
                current_range = next_range

        return cascade

    def _find_hand_for_drill_down(self, in_range_hands: set, ranges: List[Dict]) -> Optional[str]:
        """
        🆕 Trouve une main appropriée pour drill-down.
        Sélectionne depuis le range initial, accepte les cascades avec FOLD implicites.

        Distribution naturelle :
        - Mains "premium" → cascades longues (3-4 niveaux)
        - Mains "borderline" → cascades courtes avec FOLD (2 niveaux)
        """
        candidates = []

        for hand in in_range_hands:
            cascade = self.analyze_hand_cascade(hand, ranges)

            # Accepter les cascades de 2+ niveaux (incluant FOLD implicites)
            if len(cascade) >= 2:
                score = len(cascade)

                # Bonus pour les cascades VALUE (mains premium)
                if any('VALUE' in step['label'] for step in cascade):
                    score += 1

                # Les cascades avec FOLD implicite sont aussi valables
                has_implicit_fold = any(step.get('is_implicit_fold') for step in cascade)

                candidates.append((hand, score, cascade, has_implicit_fold))

        if not candidates:
            return None

        # Mélanger pour avoir une distribution naturelle
        # Les mains avec score élevé (premium) ont plus de chances, mais les borderline aussi
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Sélectionner dans le top 50% pour avoir de la variété
        top_50_percent = max(1, len(candidates) // 2)
        top_candidates = candidates[:top_50_percent]

        chosen = random.choice(top_candidates)
        print(f"[DRILL_DOWN] Main choisie: {chosen[0]} (score={chosen[1]}, implicit_fold={chosen[3]})")
        return chosen[0]

    def _find_range_with_hand(self, label: str, hand: str, ranges: List[Dict]) -> Optional[Dict]:
        """Trouve une range par label_canon contenant la main."""
        for r in ranges:
            r_label = self._normalize_label(r.get('label_canon', ''))
            if r_label == label and hand in r.get('hands', []):
                return r
        return None

    def _find_range_by_label(self, label: str, ranges: List[Dict]) -> Optional[Dict]:
        """Trouve une range par son label_canon (sans vérifier la main)."""
        for r in ranges:
            r_label = self._normalize_label(r.get('label_canon', ''))
            if r_label == label:
                return r
        return None

    def _normalize_label(self, label: str) -> str:
        """Normalise un label_canon vers le système interne."""
        if not label:
            return ''

        label_upper = label.upper().replace('-', '_')

        mappings = {
            'OPEN': 'OPEN',
            'R3_VALUE': 'R3_VALUE',
            'R3_BLUFF': 'R3_BLUFF',
            'R4_VALUE': 'R4_VALUE',
            'R4_BLUFF': 'R4_BLUFF',
            'R5_ALLIN': 'R5_ALLIN',
            'R5': 'R5_ALLIN',
            'CALL': 'CALL'
        }

        if label_upper in mappings:
            return mappings[label_upper]

        if 'R3' in label_upper and 'VALUE' in label_upper:
            return 'R3_VALUE'
        if 'R3' in label_upper and 'BLUFF' in label_upper:
            return 'R3_BLUFF'
        if 'R4' in label_upper and 'VALUE' in label_upper:
            return 'R4_VALUE'
        if 'R4' in label_upper and 'BLUFF' in label_upper:
            return 'R4_BLUFF'
        if 'R5' in label_upper:
            return 'R5_ALLIN'
        if 'CALL' in label_upper:
            return 'CALL'

        return label_upper

    def _build_level(
            self,
            level_num: int,
            step: Dict,
            context: Dict,
            hand: str,
            cascade: List[Dict]
    ) -> Optional[Dict]:
        """
        Construit un niveau de question individuel.
        ✅ Options adaptées selon situation
        ✅ Gère les FOLD implicites
        """
        label = step['label']
        villain_action = step['villain_action']
        hero_action = step['hero_action']
        is_implicit_fold = step.get('is_implicit_fold', False)

        question_text = self._format_level_question(
            level_num, step, context, hand, cascade
        )

        # ✅ Options selon l'action du villain
        if villain_action == 'all-in':
            # Sur ALL-IN : seulement FOLD ou CALL
            options = sort_actions(['FOLD', 'CALL'])
        else:
            # Sinon : toutes les options
            options = sort_actions(['FOLD', 'CALL', 'RAISE'])

        return {
            'level': level_num,
            'question': question_text,
            'correct_answer': hero_action,
            'options': options,
            'range_used': label,
            'is_implicit_fold': is_implicit_fold  # 🆕 Pour debug/stats
        }

    def _format_level_question(
            self,
            level_num: int,
            step: Dict,
            context: Dict,
            hand: str,
            cascade: List[Dict]
    ) -> str:
        """
        Formate le texte de question pour un niveau donné.
        ✅ Accumulation progressive : tout l'historique affiché

        Niveau 0 : Texte initial + "Que faites-vous ?"
        Niveau 1+ : Texte initial <br> Historique des actions <br> "Que faites-vous ?"
        """
        # === Ligne 1 : Contexte initial (toujours présent) ===
        table = context.get('table_format', '6max')
        position = context.get('hero_position', 'BTN')
        stack = context.get('stack_depth', '100bb')
        primary_action = context.get('primary_action', '').lower()

        initial_parts = [f"Table {table}, vous êtes {position} avec {stack}"]

        if primary_action == 'defense':
            action_seq = context.get('action_sequence', {})
            opener = action_seq.get('opener', 'UTG') if action_seq else 'UTG'
            initial_parts.append(f"{opener} ouvre")
        elif primary_action == 'squeeze':
            action_seq = context.get('action_sequence', {})
            opener = action_seq.get('opener', 'UTG') if action_seq else 'UTG'
            initial_parts.append(f"{opener} ouvre")
            initial_parts.append("un joueur call")
        elif primary_action == 'vs_limpers':
            initial_parts.append("un joueur limp")

        initial_line = ". ".join(initial_parts) + f". Vous avez {hand}"

        # === Niveau 0 : Pas d'historique ===
        if level_num == 0:
            return initial_line + ". Que faites-vous ?"

        # === Niveau 1+ : Ajouter l'historique des actions ===
        lines = [initial_line]

        # Pour chaque niveau précédent, construire la ligne "Action héro. Villain action"
        for i in range(level_num):
            hero_text = self._get_hero_action_text(cascade[i]['hero_action'], i)

            # L'action du villain pour ce niveau est dans cascade[i+1]
            if i + 1 <= level_num and i + 1 < len(cascade):
                villain_action = cascade[i + 1]['villain_action']
                if villain_action != 'initial':
                    villain_text = self._get_villain_action_text(villain_action)
                    lines.append(f"{hero_text}. Villain {villain_text}")
                else:
                    lines.append(hero_text)
            else:
                lines.append(hero_text)

        return "<br>".join(lines) + "<br>Que faites-vous ?"

    def _get_hero_action_text(self, hero_action: str, level_num: int) -> str:
        """
        Retourne le texte narratif de l'action du héro.
        """
        if hero_action == 'RAISE':
            if level_num == 0:
                return "Vous avez relancé"
            elif level_num == 1:
                return "Vous avez relancé (4bet)"
            else:
                return "Vous avez relancé"
        elif hero_action == 'CALL':
            return "Vous avez callé"
        elif hero_action == 'FOLD':
            return "Vous avez couché"
        else:
            return f"Vous avez {hero_action.lower()}"

    def _get_villain_action_text(self, villain_action: str) -> str:
        """
        Retourne le texte de l'action du villain.
        """
        action_texts = {
            'initial': '',
            '3bet': '3bet',
            '4bet': '4bet',
            'all-in': 'fait all-in',
            'raise': 'relance'
        }

        return action_texts.get(villain_action, villain_action)