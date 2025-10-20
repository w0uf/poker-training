#!/usr/bin/env python3
"""
Constantes liées au poker : mains, forces, mappings
"""

# Liste complète des 169 mains de poker
ALL_POKER_HANDS = [
    # Paires
    'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
    # Suited
    'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
    'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s',
    'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'J4s', 'J3s', 'J2s',
    'T9s', 'T8s', 'T7s', 'T6s', 'T5s', 'T4s', 'T3s', 'T2s',
    '98s', '97s', '96s', '95s', '94s', '93s', '92s',
    '87s', '86s', '85s', '84s', '83s', '82s',
    '76s', '75s', '74s', '73s', '72s',
    '65s', '64s', '63s', '62s',
    '54s', '53s', '52s',
    '43s', '42s',
    '32s',
    # Offsuit
    'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
    'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'K6o', 'K5o', 'K4o', 'K3o', 'K2o',
    'QJo', 'QTo', 'Q9o', 'Q8o', 'Q7o', 'Q6o', 'Q5o', 'Q4o', 'Q3o', 'Q2o',
    'JTo', 'J9o', 'J8o', 'J7o', 'J6o', 'J5o', 'J4o', 'J3o', 'J2o',
    'T9o', 'T8o', 'T7o', 'T6o', 'T5o', 'T4o', 'T3o', 'T2o',
    '98o', '97o', '96o', '95o', '94o', '93o', '92o',
    '87o', '86o', '85o', '84o', '83o', '82o',
    '76o', '75o', '74o', '73o', '72o',
    '65o', '64o', '63o', '62o',
    '54o', '53o', '52o',
    '43o', '42o',
    '32o'
]

# Force relative des mains (100 = meilleure, 1 = pire)
HAND_STRENGTH = {
    # Paires premium (100-90)
    'AA': 100, 'KK': 99, 'QQ': 98, 'JJ': 97, 'TT': 96,
    '99': 91, '88': 87, '77': 83, '66': 79, '55': 75,
    '44': 71, '33': 67, '22': 63,

    # Broadways suited (95-85)
    'AKs': 95, 'AQs': 94, 'AJs': 92, 'ATs': 90, 'KQs': 88,
    'KJs': 86, 'QJs': 84, 'JTs': 82,

    # Broadways offsuit (93-80)
    'AKo': 93, 'AQo': 89, 'AJo': 85, 'ATo': 81,
    'KQo': 80, 'KJo': 78, 'KTo': 76, 'QJo': 74, 'QTo': 72, 'JTo': 70,

    # Suited connectors et Ax suited (80-60)
    'A9s': 80, 'A8s': 78, 'A7s': 76, 'A6s': 74, 'A5s': 73,
    'A4s': 72, 'A3s': 71, 'A2s': 70,
    'T9s': 69, '98s': 68, '87s': 67, '76s': 66, '65s': 65,
    '54s': 64, 'K9s': 63, 'KTs': 77, 'Q9s': 62, 'QTs': 75,
    'J9s': 61,

    # Offsuit semi-connectés (60-40)
    'A9o': 60, 'A8o': 58, 'A7o': 56, 'A6o': 54, 'A5o': 53,
    'A4o': 52, 'A3o': 51, 'A2o': 50,
    'K9o': 49, 'Q9o': 48, 'J9o': 47, 'T9o': 46,
    '98o': 45, '87o': 44, '76o': 43, '65o': 42, '54o': 41,

    # Suited moyen-faibles (55-35)
    'K8s': 55, 'K7s': 53, 'K6s': 51, 'K5s': 49, 'K4s': 47, 'K3s': 45, 'K2s': 43,
    'Q8s': 54, 'Q7s': 52, 'Q6s': 50, 'Q5s': 48, 'Q4s': 46, 'Q3s': 44, 'Q2s': 42,
    'J8s': 53, 'J7s': 51, 'J6s': 49, 'J5s': 47, 'J4s': 45, 'J3s': 43, 'J2s': 41,
    'T8s': 52, 'T7s': 50, 'T6s': 48, 'T5s': 46, 'T4s': 44, 'T3s': 42, 'T2s': 40,
    '97s': 51, '96s': 49, '95s': 47, '94s': 45, '93s': 43, '92s': 41,
    '86s': 50, '85s': 48, '84s': 46, '83s': 44, '82s': 42,
    '75s': 49, '74s': 47, '73s': 45, '72s': 40,
    '64s': 48, '63s': 46, '62s': 44,
    '53s': 47, '52s': 45,
    '43s': 46, '42s': 44,
    '32s': 43,

    # Offsuit faibles (40-1)
    'K8o': 38, 'K7o': 36, 'K6o': 34, 'K5o': 32, 'K4o': 30, 'K3o': 28, 'K2o': 26,
    'Q8o': 37, 'Q7o': 35, 'Q6o': 33, 'Q5o': 31, 'Q4o': 29, 'Q3o': 27, 'Q2o': 25,
    'J8o': 36, 'J7o': 34, 'J6o': 32, 'J5o': 30, 'J4o': 28, 'J3o': 26, 'J2o': 24,
    'T8o': 35, 'T7o': 33, 'T6o': 31, 'T5o': 29, 'T4o': 27, 'T3o': 25, 'T2o': 23,
    '97o': 34, '96o': 32, '95o': 30, '94o': 28, '93o': 26, '92o': 22,
    '86o': 33, '85o': 31, '84o': 29, '83o': 27, '82o': 21,
    '75o': 32, '74o': 30, '73o': 28, '72o': 1,  # Pire main
    '64o': 31, '63o': 29, '62o': 20,
    '54o': 30, '53o': 28, '52o': 19,
    '43o': 29, '42o': 18,
    '32o': 17
}

# Ordre fixe des actions pour l'affichage
ACTION_ORDER = {
    'FOLD': 1,
    'CHECK': 2,
    'CALL': 3,
    'RAISE': 4,
    'OPEN': 5,
    'ISO': 6,
    '3BET': 7,
    'SQUEEZE': 7,  # Même ordre que 3BET
    '4BET': 8,
    'ALLIN': 9
}

# Normalisation des actions (fusionner value/bluff)
ACTION_NORMALIZATION = {
    'R3_VALUE': '3BET',
    'R3_BLUFF': '3BET',
    'R4_VALUE': '4BET',
    'R4_BLUFF': '4BET',
    'R5_ALLIN': 'ALLIN',
    'ISO_VALUE': 'ISO',
    'ISO_BLUFF': 'ISO',
    'ISO_RAISE': 'ISO',
    'SQUEEZE': 'RAISE',
}

# Traductions françaises des actions
ACTION_TRANSLATIONS = {
    'open': 'ouvrez avec',
    'defense': 'défendez avec',
    '3bet': '3-bet avec',
    'squeeze': 'squeezez avec',
    '4bet': '4-bet avec',
    'call': 'call avec',
    'raise': 'relancez avec',
    'iso': 'isolez avec',
    'vs_limpers': 'face aux limpers avec'
}


def sort_actions(actions):
    """
    Trie les actions dans un ordre logique et constant.

    Args:
        actions: Liste d'actions à trier

    Returns:
        Liste triée selon ACTION_ORDER
    """
    if not actions:
        return []

    return sorted(actions, key=lambda x: ACTION_ORDER.get(x, 999))


def normalize_action(action):
    """
    Normalise une action en fusionnant value/bluff.

    Args:
        action: Action à normaliser (ex: 'R3_VALUE', '3BET', 'ISO_BLUFF')

    Returns:
        Action normalisée (ex: '3BET', 'ISO') ou None si invalide
    """
    # Gérer les valeurs nulles/invalides
    if not action or action == 'None' or action == 'null' or action == '':
        return None

    # Retourner la normalisation ou l'action elle-même
    return ACTION_NORMALIZATION.get(action, action)


def translate_action(action):
    """
    Traduit une action en français pour les questions.

    Args:
        action: Action en anglais

    Returns:
        Traduction française
    """
    if not action:
        return 'jouez avec'

    return ACTION_TRANSLATIONS.get(action.lower(), action)


def get_hand_strength(hand):
    """
    Récupère la force d'une main.

    Args:
        hand: Main de poker (ex: 'AA', 'KQs')

    Returns:
        Force de la main (0-100) ou 50 par défaut
    """
    return HAND_STRENGTH.get(hand, 50)

AVAILABLE_LABELS = {
    'OPEN': 'Open',
    'CALL': 'Call',
    'FOLD': 'Fold',
    'RAISE': 'Raise',
    'R3_VALUE': '3bet Value',
    'R3_BLUFF': '3bet Bluff',
    'R4_VALUE': '4bet Value',
    'R4_BLUFF': '4bet Bluff',
    'R5_ALLIN': '5bet All-in',
    'ISO_VALUE': 'Iso Value',
    'ISO_BLUFF': 'Iso Bluff',
    'CHECK': 'Check',
    'DEFENSE': 'Defense',
    'UNKNOWN': 'Inconnu'
}