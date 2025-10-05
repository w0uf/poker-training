#!/usr/bin/env python3
"""
Module de standardisation des noms de contextes
Extrait et nettoie les métadonnées basiques des noms de contextes
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class TableFormat(Enum):
    FIVEMAX = "5max"
    SIXMAX = "6max"
    NINEMAX = "9max"
    HEADSUP = "heads-up"


class Position(Enum):
    UTG = "UTG"
    UTG1 = "UTG+1"
    MP = "MP"
    MP1 = "MP+1"
    LJ = "LJ"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class Action(Enum):
    OPEN = "open"
    CALL = "call"
    RAISE_3BET = "3bet"
    RAISE_4BET = "4bet"
    FOLD = "fold"
    CHECK = "check"
    DEFENSE = "defense"


@dataclass
class StandardizedMetadata:
    """Métadonnées standardisées extraites du nom"""
    original_name: str
    cleaned_name: str
    table_format: Optional[TableFormat] = None
    hero_position: Optional[Position] = None
    vs_position: Optional[Position] = None
    primary_action: Optional[Action] = None
    confidence: float = 0.0


class NameStandardizer:
    """Standardiseur de noms de contextes de poker"""

    def __init__(self):
        # Patterns de détection (simplifiés par rapport à enrich_ranges.py)
        self.table_format_patterns = {
            r'\b5[\s-]?max\b|\b5m\b': TableFormat.FIVEMAX,
            r'\b6[\s-]?max\b|\b6m\b': TableFormat.SIXMAX,
            r'\b9[\s-]?max\b|\b9m\b|\bfull[\s-]?ring\b': TableFormat.NINEMAX,
            r'\bhu\b|\bheads[\s-]?up\b': TableFormat.HEADSUP,
        }

        self.position_patterns = {
            # Ordre important pour éviter les conflits (UTG+1 avant UTG)
            r'\bUTG\+1\b|\bUnder[\s_]?the[\s_]?Gun\+1\b': Position.UTG1,
            r'\bUTG\b(?!\+)|\bUnder[\s_]?the[\s_]?Gun\b(?!\+)': Position.UTG,
            r'\bMP\+1\b|\bMiddle[\s_]?Position\+1\b': Position.MP1,
            r'\bMP\b(?!\+)|\bMiddle[\s_]?Position\b(?!\+)': Position.MP,
            r'\bLJ\b|\bLojack\b': Position.LJ,
            r'\bHJ\b|\bHijack\b': Position.HJ,
            r'\bCO\b|\bCutoff\b': Position.CO,
            r'\bBTN\b|\bBU\b|\bButton\b': Position.BTN,
            r'\bSB\b|\bSmall[\s_]?Blind\b': Position.SB,
            r'\bBB\b|\bBig[\s_]?Blind\b': Position.BB,
        }

        self.action_patterns = {
            # Défense en priorité pour éviter confusion avec "defense"
            r'\bDefense?\b|\bDefend\b|\bDefending\b|\bDef\b': Action.DEFENSE,
            r'\bOpen\b|\bOpening\b|\bRFI\b': Action.OPEN,
            r'\b3[\s_-]?[Bb]et\b|\bReraise\b': Action.RAISE_3BET,
            r'\b4[\s_-]?[Bb]et\b': Action.RAISE_4BET,
            r'\bCall\b|\bCalling\b|\bFlat\b': Action.CALL,
            r'\bFold\b|\bFolding\b': Action.FOLD,
            r'\bCheck\b|\bChecking\b': Action.CHECK,
        }

        self.vs_patterns = [r'\bvs\b', r'\bv\b', r'\bcontre\b', r'\bversus\b']

    def standardize(self, context_name: str) -> StandardizedMetadata:
        """Standardise un nom de contexte et extrait les métadonnées"""
        print(f"[STANDARDIZER] Analyse: '{context_name}'")

        # Nettoyer le nom d'abord
        cleaned = self._clean_name(context_name)

        metadata = StandardizedMetadata(
            original_name=context_name,
            cleaned_name=cleaned
        )

        # Extraire les métadonnées
        confidence_factors = []

        # Détecter le format de table
        table_format = self._detect_table_format(cleaned)
        if table_format:
            metadata.table_format = table_format
            confidence_factors.append(0.8)

        # Détecter les positions avec logique vs
        positions = self._detect_positions_with_vs(cleaned)
        if positions['hero']:
            metadata.hero_position = positions['hero']
            confidence_factors.append(positions['hero_confidence'])
        if positions['vs']:
            metadata.vs_position = positions['vs']
            confidence_factors.append(positions['vs_confidence'])

        # Détecter l'action principale
        action = self._detect_primary_action(cleaned)
        if action:
            metadata.primary_action = action
            confidence_factors.append(0.7)

        # Calculer la confiance globale
        metadata.confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        self._log_results(metadata)
        return metadata

    def _clean_name(self, name: str) -> str:
        """Nettoie le nom de contexte"""
        # Supprimer l'extension
        cleaned = re.sub(r'\.[a-zA-Z0-9]+$', '', name)

        # Remplacer underscores et tirets par espaces
        cleaned = re.sub(r'[_-]+', ' ', cleaned)

        # Normaliser les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def _detect_table_format(self, text: str) -> Optional[TableFormat]:
        """Détecte le format de table"""
        for pattern, table_format in self.table_format_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return table_format
        return None

    def _detect_positions_with_vs(self, text: str) -> Dict[str, Any]:
        """Détecte les positions avec logique 'vs'"""
        result = {
            'hero': None,
            'vs': None,
            'hero_confidence': 0.0,
            'vs_confidence': 0.0
        }

        # Trouver toutes les positions
        positions_found = []
        for pattern, position in self.position_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                positions_found.append({
                    'position': position,
                    'start': match.start(),
                    'end': match.end()
                })

        if not positions_found:
            return result

        # Chercher structure "vs"
        vs_match = None
        for vs_pattern in self.vs_patterns:
            match = re.search(vs_pattern, text, re.IGNORECASE)
            if match:
                vs_match = {'start': match.start(), 'end': match.end()}
                break

        if len(positions_found) == 1:
            # Une seule position = héros
            result['hero'] = positions_found[0]['position']
            result['hero_confidence'] = 0.6
        elif len(positions_found) >= 2 and vs_match:
            # Logique avec "vs": avant = héros, après = adversaire
            vs_position = vs_match['start']

            before_vs = [p for p in positions_found if p['end'] <= vs_position]
            after_vs = [p for p in positions_found if p['start'] >= vs_match['end']]

            if before_vs:
                result['hero'] = before_vs[-1]['position']  # Dernière avant vs
                result['hero_confidence'] = 0.8

            if after_vs:
                result['vs'] = after_vs[0]['position']  # Première après vs
                result['vs_confidence'] = 0.8
        elif len(positions_found) >= 2:
            # Plusieurs positions sans "vs" - heuristique
            result['hero'] = positions_found[0]['position']
            result['hero_confidence'] = 0.4

        return result

    def _detect_primary_action(self, text: str) -> Optional[Action]:
        """Détecte l'action principale"""
        for pattern, action in self.action_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return action
        return None

    def _log_results(self, metadata: StandardizedMetadata):
        """Log les résultats de standardisation"""
        print(f"[STANDARDIZER] Nom nettoyé: '{metadata.cleaned_name}'")
        if metadata.table_format:
            print(f"[STANDARDIZER] Format table: {metadata.table_format.value}")
        if metadata.hero_position:
            print(f"[STANDARDIZER] Position héros: {metadata.hero_position.value}")
        if metadata.vs_position:
            print(f"[STANDARDIZER] Vs position: {metadata.vs_position.value}")
        if metadata.primary_action:
            print(f"[STANDARDIZER] Action: {metadata.primary_action.value}")
        print(f"[STANDARDIZER] Confiance: {metadata.confidence:.1%}")


if __name__ == "__main__":
    # Tests
    standardizer = NameStandardizer()

    test_names = [
        "6max BB Defense vs CO",
        "UTG Open 100bb",
        "CO 3Bet vs BTN",
        "SB Complete heads-up"
    ]

    for name in test_names:
        result = standardizer.standardize(name)
        print("-" * 50)