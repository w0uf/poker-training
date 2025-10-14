#!/usr/bin/env python3
"""
Sélection intelligente de mains pour le quiz
Gère le ratio aléatoire/borderline et la détection des mains limites
"""

import random
from typing import Set, List, Tuple
from poker_constants import ALL_POKER_HANDS, get_hand_strength

# Configuration du ratio de sélection
QUIZ_RANDOM_RATIO = 0.70  # 70% aléatoire, 30% borderline
BORDERLINE_PROXIMITY_THRESHOLD = 12  # Distance max pour être borderline OUT


def smart_hand_choice(
        in_range_hands: Set[str],
        out_range_hands: Set[str],
        is_in_range: bool
) -> str:
    """
    Choisit une main avec équilibre configurable entre aléatoire et borderline.

    Args:
        in_range_hands: Mains dans la range
        out_range_hands: Mains hors de la range
        is_in_range: True si on veut une main IN, False si OUT

    Returns:
        Une main choisie intelligemment ou None
    """
    target_hands = list(in_range_hands) if is_in_range else list(out_range_hands)

    if not target_hands:
        return None

    # Tirer un dé : aléatoire ou borderline ?
    if random.random() < QUIZ_RANDOM_RATIO:
        # 🎲 Choix purement ALÉATOIRE (70% du temps)
        hand = random.choice(target_hands)
        print(f"[CHOICE] Aléatoire {'IN' if is_in_range else 'OUT'}: {hand}")
        return hand
    else:
        # 🎯 Choix BORDERLINE (30% du temps)
        borderline_in, borderline_out = get_borderline_hands(
            in_range_hands,
            out_range_hands,
            BORDERLINE_PROXIMITY_THRESHOLD
        )

        borderline_hands = borderline_in if is_in_range else borderline_out

        if borderline_hands:
            hand = random.choice(borderline_hands)
            print(f"[CHOICE] Borderline {'IN' if is_in_range else 'OUT'}: {hand}")
            return hand
        else:
            # Fallback : aléatoire si pas de borderline
            hand = random.choice(target_hands)
            print(f"[CHOICE] Fallback aléatoire {'IN' if is_in_range else 'OUT'}: {hand}")
            return hand


def get_borderline_hands(
        in_range_hands: Set[str],
        out_range_hands: Set[str],
        proximity_threshold: int = 12
) -> Tuple[List[str], List[str]]:
    """
    Identifie les vrais borderlines :
    - IN : mains aux frontières de la range (trous en dessous/dessus)
    - OUT : mains proches d'une main IN

    Args:
        in_range_hands: Mains dans la range
        out_range_hands: Mains hors de la range
        proximity_threshold: Distance max pour être "proche"

    Returns:
        (borderline_in, borderline_out)
    """
    if not in_range_hands or not out_range_hands:
        return list(in_range_hands), list(out_range_hands)

    # Calculer les forces
    strengths_in = {h: get_hand_strength(h) for h in in_range_hands}
    strengths_out = {h: get_hand_strength(h) for h in out_range_hands}

    # Trier les mains IN par force décroissante
    sorted_in = sorted(in_range_hands, key=lambda h: strengths_in[h], reverse=True)

    borderline_in = []

    # 🎯 Trouver les frontières de la range IN
    for i, hand in enumerate(sorted_in):
        current_strength = strengths_in[hand]
        is_border = False

        # Regarder en DESSOUS (main plus faible suivante)
        if i < len(sorted_in) - 1:
            next_hand = sorted_in[i + 1]
            next_strength = strengths_in[next_hand]
            gap_below = current_strength - next_strength

            if gap_below > 5:  # Gap significatif = frontière
                is_border = True
                print(
                    f"  [BORDER IN] {hand}({current_strength}) : gap de {gap_below} vers {next_hand}({next_strength})")
        else:
            # C'est la main la plus faible de la range → toujours borderline
            is_border = True
            print(f"  [BORDER IN] {hand}({current_strength}) : main la plus faible de la range")

        # Regarder si une main OUT est proche JUSTE EN DESSOUS
        if not is_border:
            closest_out_below = None
            min_distance = float('inf')

            for hand_out, strength_out in strengths_out.items():
                if strength_out < current_strength:  # Seulement en dessous
                    distance = current_strength - strength_out
                    if distance < min_distance:
                        min_distance = distance
                        closest_out_below = hand_out

            if closest_out_below and min_distance <= proximity_threshold:
                # Vérifier qu'il n'y a pas de main IN entre les deux
                has_in_between = any(
                    current_strength > s > strengths_out[closest_out_below]
                    for s in strengths_in.values()
                )

                if not has_in_between:
                    is_border = True
                    print(
                        f"  [BORDER IN] {hand}({current_strength}) : {closest_out_below}({strengths_out[closest_out_below]}) OUT proche en dessous (distance {min_distance})")

        if is_border:
            borderline_in.append(hand)

    # 🎯 Trouver les mains OUT proches d'une frontière IN
    borderline_out = []

    for hand_out, strength_out in strengths_out.items():
        # Trouver la main IN la plus proche
        closest_in = None
        min_distance = float('inf')

        for hand_in, strength_in in strengths_in.items():
            distance = abs(strength_out - strength_in)
            if distance < min_distance:
                min_distance = distance
                closest_in = hand_in

        if min_distance <= proximity_threshold:
            borderline_out.append(hand_out)
            print(
                f"  [BORDER OUT] {hand_out}({strength_out}) : proche de {closest_in}({strengths_in[closest_in]}) IN (distance {min_distance})")

    print(f"[BORDERLINE] IN : {len(borderline_in)} mains → {borderline_in}")
    print(f"[BORDERLINE] OUT : {len(borderline_out)} mains → {borderline_out[:10]}...")

    # Fallback si vides
    if not borderline_in:
        sorted_in_list = sorted(in_range_hands, key=lambda h: strengths_in[h])
        borderline_in = sorted_in_list[:max(1, len(sorted_in_list) // 5)]
        print(f"[BORDERLINE] Fallback IN : {borderline_in[:3]}")

    if not borderline_out:
        sorted_out = sorted(out_range_hands, key=lambda h: strengths_out[h], reverse=True)
        borderline_out = sorted_out[:max(1, len(sorted_out) // 5)]
        print(f"[BORDERLINE] Fallback OUT : {borderline_out[:3]}")

    return borderline_in, borderline_out


def get_all_hands_not_in_ranges(in_range_hands: Set[str]) -> Set[str]:
    """
    Récupère toutes les mains qui ne sont pas dans les ranges.

    Args:
        in_range_hands: Ensemble des mains dans les ranges

    Returns:
        Ensemble des mains hors ranges
    """
    return set(h for h in ALL_POKER_HANDS if h not in in_range_hands)