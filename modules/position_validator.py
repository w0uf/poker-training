#!/usr/bin/env python3
"""
Module de validation de cohérence des positions pour les contextes de poker.
Vérifie la logique des positions dans les situations multiway (squeeze, vs_limpers, defense).
Version 4.1 : Validations optionnelles + support limpers_count
"""

from typing import Optional, List, Tuple, Union
import re

# Positions disponibles par format de table
POSITIONS_BY_FORMAT = {
    '5max': ['UTG', 'CO', 'BTN', 'SB', 'BB'],
    '6max': ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'],
    '9max': ['UTG', 'UTG+1', 'MP', 'MP+1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB'],
    'HU': ['BTN', 'BB']
}

# Ordre des positions (pour validation future si nécessaire)
POSITION_ORDER = {
    'UTG': 0,
    'UTG+1': 1,
    'MP': 2,
    'MP+1': 3,
    'LJ': 4,
    'HJ': 5,
    'CO': 6,
    'BTN': 7,
    'SB': 8,
    'BB': 9
}


def _validate_positions_exist(
        positions: List[str],
        table_format: str
) -> Tuple[bool, Optional[str]]:
    """
    Vérifie que toutes les positions sont valides pour le format de table.

    Args:
        positions: Liste des positions à vérifier
        table_format: Format de table (5max, 6max, 9max, HU)

    Returns:
        (True, None) si valide
        (False, message) si invalide
    """
    if table_format not in POSITIONS_BY_FORMAT:
        return False, f"Format de table inconnu: '{table_format}'"

    valid_positions = POSITIONS_BY_FORMAT[table_format]

    for pos in positions:
        if pos not in valid_positions:
            return False, f"Position '{pos}' invalide pour format {table_format} (positions valides: {', '.join(valid_positions)})"

    return True, None


def _validate_no_duplicates(
        positions: List[str],
        context: str = "positions"
) -> Tuple[bool, Optional[str]]:
    """
    Vérifie qu'il n'y a pas de doublons dans une liste de positions.

    Args:
        positions: Liste des positions à vérifier
        context: Contexte pour le message d'erreur (ex: "callers", "limpers")

    Returns:
        (True, None) si pas de doublons
        (False, message) si doublons détectés
    """
    if len(positions) != len(set(positions)):
        duplicates = [pos for pos in set(positions) if positions.count(pos) > 1]
        return False, f"Doublons détectés dans {context}: {', '.join(duplicates)}"

    return True, None


def _validate_hero_not_in_list(
        hero_position: str,
        positions: List[str],
        context: str
) -> Tuple[bool, Optional[str]]:
    """
    Vérifie que le hero n'est pas dans une liste de positions.

    Args:
        hero_position: Position du hero
        positions: Liste des positions à vérifier
        context: Contexte pour le message d'erreur

    Returns:
        (True, None) si hero pas dans la liste
        (False, message) si hero présent
    """
    if hero_position in positions:
        return False, f"Hero ({hero_position}) ne peut pas être dans {context}"

    return True, None


def _validate_limpers_count(
        limpers_count: Union[int, str]
) -> Tuple[bool, Optional[str]]:
    """
    Valide le format de limpers_count.

    Args:
        limpers_count: Nombre de limpers (int ou string "3+")

    Returns:
        (True, None) si valide
        (False, message) si invalide
    """
    if isinstance(limpers_count, str):
        # Gérer format "3+", "2+", etc.
        if not re.match(r'^\d+\+?$', limpers_count):
            return False, f"limpers_count invalide: '{limpers_count}' (format attendu: nombre ou 'X+')"
    else:
        try:
            count = int(limpers_count)
            if count < 1:
                return False, f"limpers_count doit être >= 1, reçu: {count}"
        except (ValueError, TypeError):
            return False, f"limpers_count invalide: {limpers_count}"

    return True, None


def _validate_limpers_count_consistency(
        limpers: List[str],
        limpers_count: Union[int, str]
) -> Tuple[bool, Optional[str]]:
    """
    Valide la cohérence entre limpers et limpers_count.

    Args:
        limpers: Liste des positions des limpers
        limpers_count: Nombre attendu de limpers

    Returns:
        (True, None) si cohérent
        (False, message) si incohérent
    """
    actual_count = len(limpers)

    if isinstance(limpers_count, str):
        # Gérer "3+"
        if '+' in limpers_count:
            min_count = int(limpers_count.replace('+', ''))
            if actual_count < min_count:
                return False, f"limpers_count='{limpers_count}' mais seulement {actual_count} limper(s) fourni(s)"
        else:
            expected_count = int(limpers_count)
            if actual_count != expected_count:
                return False, f"limpers_count={expected_count} mais {actual_count} limper(s) fourni(s)"
    else:
        expected_count = int(limpers_count)
        if actual_count != expected_count:
            return False, f"limpers_count={expected_count} mais {actual_count} limper(s) fourni(s)"

    return True, None


def validate_position_consistency(
        primary_action: str,
        hero_position: str,
        table_format: str,
        opener: Optional[str] = None,
        callers: Optional[List[str]] = None,
        limpers: Optional[List[str]] = None,
        limpers_count: Optional[Union[int, str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Valide la cohérence logique des positions selon le contexte.

    Version 4.1 - Validations OPTIONNELLES :
    - Les positions ne sont PAS obligatoires (permet ranges génériques)
    - Si positions fournies → validation stricte
    - Si positions absentes → range générique (OK)
    - Support limpers_count pour vs_limpers

    Règles de validation:
    1. Toutes les positions doivent être valides pour le format de table
    2. Hero ne peut pas être simultanément dans plusieurs rôles
    3. Pas de doublons dans les listes (callers, limpers)
    4. Opener ne peut pas être dans les callers (squeeze)
    5. Cohérence limpers/limpers_count si les deux fournis

    Args:
        primary_action: Type de contexte ('open', 'defense', 'squeeze', 'vs_limpers')
        hero_position: Position du hero
        table_format: Format de table ('5max', '6max', '9max', 'HU')
        opener: Position de l'ouvreur (pour defense, squeeze) - OPTIONNEL
        callers: Liste des positions ayant callé (pour squeeze) - OPTIONNEL
        limpers: Liste des positions ayant limpé (pour vs_limpers) - OPTIONNEL
        limpers_count: Nombre de limpers (int ou "3+") - OPTIONNEL

    Returns:
        (True, None) si toutes les validations passent
        (False, message_erreur) si une validation échoue
    """

    # ============================================================================
    # VALIDATION 1 : Toutes les positions doivent être valides pour le format
    # ============================================================================

    all_positions = [hero_position]

    if opener:
        all_positions.append(opener)

    if callers:
        all_positions.extend(callers)

    if limpers:
        all_positions.extend(limpers)

    is_valid, error_msg = _validate_positions_exist(all_positions, table_format)
    if not is_valid:
        return False, error_msg

    # ============================================================================
    # VALIDATION 2 : Pas de doublons dans les listes
    # ============================================================================

    if callers:
        is_valid, error_msg = _validate_no_duplicates(callers, "les callers")
        if not is_valid:
            return False, error_msg

    if limpers:
        is_valid, error_msg = _validate_no_duplicates(limpers, "les limpers")
        if not is_valid:
            return False, error_msg

    # ============================================================================
    # VALIDATION 3 : Règles spécifiques par primary_action
    # ============================================================================

    primary_action_lower = primary_action.lower()

    # --- DEFENSE ---
    if primary_action_lower == 'defense':
        # Si opener fourni → valider
        if opener:
            # Hero ne peut pas être l'ouvreur
            if opener == hero_position:
                return False, f"Hero ({hero_position}) ne peut pas être l'ouvreur en defense"
        # Si opener absent → OK (range générique)

    # --- SQUEEZE ---
    elif primary_action_lower == 'squeeze':
        # Si opener ET callers fournis → valider
        if opener and callers:
            # Hero ne peut pas être l'ouvreur
            if opener == hero_position:
                return False, f"Hero ({hero_position}) ne peut pas être l'ouvreur en squeeze"

            # Hero ne peut pas être dans les callers
            is_valid, error_msg = _validate_hero_not_in_list(
                hero_position, callers, "les callers"
            )
            if not is_valid:
                return False, error_msg

            # Opener ne peut pas être dans les callers
            if opener in callers:
                return False, f"Opener '{opener}' ne peut pas être dans les callers"

        # Si un seul fourni (opener OU callers) → Potentiel warning mais on accepte
        # Si aucun fourni → OK (range générique)

    # --- VS_LIMPERS ---
    elif primary_action_lower == 'vs_limpers':
        # Si limpers fournis → valider positions
        if limpers:
            # Hero ne peut pas être dans les limpers
            is_valid, error_msg = _validate_hero_not_in_list(
                hero_position, limpers, "les limpers"
            )
            if not is_valid:
                return False, error_msg

            # Si limpers_count aussi fourni → vérifier cohérence
            if limpers_count is not None:
                is_valid, error_msg = _validate_limpers_count_consistency(limpers, limpers_count)
                if not is_valid:
                    return False, error_msg

        # Si limpers_count fourni seul → valider format
        elif limpers_count is not None:
            is_valid, error_msg = _validate_limpers_count(limpers_count)
            if not is_valid:
                return False, error_msg

        # Si ni limpers ni limpers_count → OK (range générique)

    # --- OPEN ---
    elif primary_action_lower == 'open':
        # Pas de validation spécifique pour open
        # (pas d'autres positions impliquées)
        pass

    # --- CONTEXTE INCONNU ---
    else:
        # On ne bloque pas les contextes inconnus (check, etc.)
        pass

    # ============================================================================
    # TOUTES LES VALIDATIONS ONT PASSÉ
    # ============================================================================

    return True, None


def validate_and_clean_positions(
        positions_str: str,
        separator: str = ','
) -> List[str]:
    """
    Nettoie et valide une chaîne de positions.

    Args:
        positions_str: Chaîne de positions séparées (ex: "UTG, CO, BTN")
        separator: Séparateur utilisé

    Returns:
        Liste de positions nettoyées et en majuscules
    """
    if not positions_str:
        return []

    positions = [
        pos.strip().upper()
        for pos in positions_str.split(separator)
        if pos.strip()
    ]

    return positions


# ============================================================================
# FONCTIONS DE TEST / DEBUG
# ============================================================================

def test_validation():
    """Fonction de test pour valider le module."""

    print("=" * 60)
    print("Tests de validation des positions - Version 4.1")
    print("=" * 60)

    # ========================================================================
    # TESTS VALIDATIONS STRICTES (avec positions)
    # ========================================================================

    # Test 1 : SQUEEZE valide ✅
    print("\n[Test 1] SQUEEZE valide (avec positions)")
    is_valid, msg = validate_position_consistency(
        primary_action='squeeze',
        hero_position='BTN',
        table_format='6max',
        opener='UTG',
        callers=['CO']
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 1 devrait passer"

    # Test 2 : SQUEEZE invalide - opener dans callers ❌
    print("\n[Test 2] SQUEEZE invalide - opener dans callers")
    is_valid, msg = validate_position_consistency(
        primary_action='squeeze',
        hero_position='BTN',
        table_format='6max',
        opener='UTG',
        callers=['UTG', 'CO']
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 2 devrait échouer"
    assert "Opener" in msg and "callers" in msg

    # Test 3 : VS_LIMPERS invalide - hero dans limpers ❌
    print("\n[Test 3] VS_LIMPERS invalide - hero dans limpers")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers=['UTG', 'CO', 'BTN']
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 3 devrait échouer"
    assert "Hero" in msg and "limpers" in msg

    # Test 4 : VS_LIMPERS valide ✅
    print("\n[Test 4] VS_LIMPERS valide (avec positions)")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers=['UTG', 'CO']
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 4 devrait passer"

    # Test 5 : DEFENSE invalide - hero = opener ❌
    print("\n[Test 5] DEFENSE invalide - hero = opener")
    is_valid, msg = validate_position_consistency(
        primary_action='defense',
        hero_position='CO',
        table_format='6max',
        opener='CO'
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 5 devrait échouer"
    assert "Hero" in msg and "ouvreur" in msg

    # Test 6 : DEFENSE valide ✅
    print("\n[Test 6] DEFENSE valide (avec positions)")
    is_valid, msg = validate_position_consistency(
        primary_action='defense',
        hero_position='CO',
        table_format='6max',
        opener='UTG'
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 6 devrait passer"

    # ========================================================================
    # TESTS RANGES GÉNÉRIQUES (sans positions) - NOUVEAU v4.1
    # ========================================================================

    # Test 7 : DEFENSE générique (sans opener) ✅
    print("\n[Test 7] DEFENSE générique (sans opener) - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='defense',
        hero_position='CO',
        table_format='6max'
        # Pas d'opener → range générique
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 7 devrait passer (range générique)"

    # Test 8 : SQUEEZE générique (sans positions) ✅
    print("\n[Test 8] SQUEEZE générique (sans opener/callers) - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='squeeze',
        hero_position='BTN',
        table_format='6max'
        # Pas d'opener ni callers → range générique
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 8 devrait passer (range générique)"

    # Test 9 : VS_LIMPERS générique (sans positions) ✅
    print("\n[Test 9] VS_LIMPERS générique (sans limpers) - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max'
        # Pas de limpers → range générique
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 9 devrait passer (range générique)"

    # ========================================================================
    # TESTS LIMPERS_COUNT - NOUVEAU v4.1
    # ========================================================================

    # Test 10 : VS_LIMPERS avec limpers_count seul ✅
    print("\n[Test 10] VS_LIMPERS avec limpers_count=2 seul - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers_count=2
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 10 devrait passer"

    # Test 11 : VS_LIMPERS avec limpers_count="3+" ✅
    print("\n[Test 11] VS_LIMPERS avec limpers_count='3+' - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers_count="3+"
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 11 devrait passer"

    # Test 12 : VS_LIMPERS cohérence limpers + limpers_count ✅
    print("\n[Test 12] VS_LIMPERS positions + count cohérents - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers=['UTG', 'CO'],
        limpers_count=2
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert is_valid, "Test 12 devrait passer"

    # Test 13 : VS_LIMPERS incohérence count ❌
    print("\n[Test 13] VS_LIMPERS incohérence limpers/count - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers=['UTG', 'CO'],
        limpers_count=3  # Incohérent !
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 13 devrait échouer"
    assert "limpers_count" in msg

    # Test 14 : VS_LIMPERS count invalide ❌
    print("\n[Test 14] VS_LIMPERS limpers_count invalide - NOUVEAU")
    is_valid, msg = validate_position_consistency(
        primary_action='vs_limpers',
        hero_position='BTN',
        table_format='6max',
        limpers_count=0  # < 1 !
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 14 devrait échouer"
    assert ">= 1" in msg

    # ========================================================================
    # TESTS DIVERS
    # ========================================================================

    # Test 15 : Position invalide pour format ❌
    print("\n[Test 15] Position invalide pour format HU")
    is_valid, msg = validate_position_consistency(
        primary_action='squeeze',
        hero_position='BTN',
        table_format='HU',
        opener='UTG',  # UTG n'existe pas en HU
        callers=['CO']
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 15 devrait échouer"
    assert "invalide pour format" in msg

    # Test 16 : Doublons dans callers ❌
    print("\n[Test 16] Doublons dans callers")
    is_valid, msg = validate_position_consistency(
        primary_action='squeeze',
        hero_position='BTN',
        table_format='6max',
        opener='UTG',
        callers=['CO', 'CO']  # Doublon
    )
    print(f"Résultat: {'✅ VALIDE' if is_valid else f'❌ INVALIDE: {msg}'}")
    assert not is_valid, "Test 16 devrait échouer"
    assert "Doublons" in msg

    # Test 17 : validate_and_clean_positions
    print("\n[Test 17] Nettoyage de chaîne de positions")
    result = validate_and_clean_positions("utg, co, btn")
    print(f"Input: 'utg, co, btn' → Output: {result}")
    assert result == ['UTG', 'CO', 'BTN'], "Test 17 devrait retourner positions en majuscules"

    print("\n" + "=" * 60)
    print("✅ TOUS LES TESTS PASSENT !")
    print("=" * 60)
    print("\n📊 Résumé:")
    print("  - Validations strictes: 6 tests")
    print("  - Ranges génériques: 3 tests")
    print("  - Limpers_count: 5 tests")
    print("  - Divers: 3 tests")
    print("  - TOTAL: 17 tests ✅")


if __name__ == "__main__":
    # Lancer les tests si exécuté directement
    test_validation()