#!/usr/bin/env python3
"""
Module d'enrichissement des métadonnées automatique (mode web)
Applique les heuristiques d'enrichissement sans interaction utilisateur
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Réutiliser les enums du standardizer
from name_standardizer import Position, Action, TableFormat


class GameFormat(Enum):
    CASH = "cash game"
    TOURNAMENT = "tournament"
    SNG = "sit & go"
    SPIN = "spin & go"


class Variant(Enum):
    NLHE = "No Limit Hold'em"
    PLO = "Pot Limit Omaha"
    PLO5 = "5-Card PLO"


class StackDepth(Enum):
    SHORT = "20-40bb"
    MID = "50-75bb"
    STANDARD = "100bb"
    DEEP = "150bb+"


class ContextStatus(Enum):
    QUIZ_READY = "quiz_ready"
    NEEDS_VALIDATION = "needs_validation"
    ERROR = "error"


@dataclass
class EnrichedMetadata:
    """Métadonnées enrichies complètes"""
    # Métadonnées de base (du standardizer)
    original_name: str
    cleaned_name: str
    table_format: Optional[TableFormat] = None
    hero_position: Optional[Position] = None
    vs_position: Optional[Position] = None
    primary_action: Optional[Action] = None

    # Métadonnées enrichies (globales par défaut)
    game_format: Optional[GameFormat] = None
    variant: Optional[Variant] = None
    stack_depth: Optional[StackDepth] = None
    sizing: Optional[str] = None
    description: Optional[str] = None

    # Noms d'affichage générés
    display_name: Optional[str] = None
    display_name_short: Optional[str] = None

    # Métadonnées de traitement
    confidence: float = 0.0
    question_friendly: bool = False
    context_status: ContextStatus = ContextStatus.NEEDS_VALIDATION
    enriched_by_user: bool = False
    enrichment_date: Optional[str] = None
    version: str = "auto_v2"


class MetadataEnricher:
    """Enrichisseur automatique de métadonnées (mode web)"""

    def __init__(self, auto_config: Optional[Dict] = None):
        # Configuration par défaut pour le mode automatique
        self.default_config = auto_config or {
            'game_format': GameFormat.CASH,
            'variant': Variant.NLHE,
            'stack_depth': StackDepth.STANDARD,
            'default_table_format': TableFormat.SIXMAX
        }

    def enrich(self, standardized_metadata, ranges_data=None) -> EnrichedMetadata:
        """Enrichit les métadonnées en mode automatique"""
        print(f"[ENRICHER] Enrichissement auto: '{standardized_metadata.cleaned_name}'")

        # Créer les métadonnées enrichies
        enriched = EnrichedMetadata(
            original_name=standardized_metadata.original_name,
            cleaned_name=standardized_metadata.cleaned_name,
            table_format=standardized_metadata.table_format,
            hero_position=standardized_metadata.hero_position,
            vs_position=standardized_metadata.vs_position,
            primary_action=standardized_metadata.primary_action,
            confidence=standardized_metadata.confidence
        )

        # Appliquer les valeurs par défaut globales
        enriched.game_format = self.default_config['game_format']
        enriched.variant = self.default_config['variant']
        enriched.stack_depth = self.default_config['stack_depth']

        # Compléter le format de table si manquant
        if not enriched.table_format:
            enriched.table_format = self.default_config['default_table_format']
            print(f"[ENRICHER] Format table par défaut appliqué: {enriched.table_format.value}")

        # Améliorer la confiance selon les règles automatiques
        enriched.confidence = self._calculate_enhanced_confidence(enriched)

        # Générer les noms d'affichage
        enriched.display_name, enriched.display_name_short = self._generate_display_names(enriched)

        # Déterminer le statut du contexte pour le quiz
        enriched.context_status = self._determine_context_status(enriched, ranges_data)

        # Compatibilité avec l'ancien système
        enriched.question_friendly = (enriched.context_status == ContextStatus.QUIZ_READY)

        # Marquer les métadonnées de traitement
        enriched.enriched_by_user = False  # Mode automatique
        enriched.enrichment_date = datetime.now().isoformat()

        self._log_enrichment_results(enriched)
        return enriched

    def _determine_context_status(self, metadata: EnrichedMetadata, ranges_data) -> ContextStatus:
        """Détermine le statut du contexte selon les critères stricts du quiz"""

        # Vérifier les métadonnées obligatoires pour le quiz
        required_metadata = [
            metadata.table_format,
            metadata.hero_position,
            metadata.primary_action
        ]

        has_required_metadata = all(field is not None for field in required_metadata)

        # Vérifier qu'il y a au moins 1 range avec des mains
        if ranges_data:
            valid_ranges = [r for r in ranges_data if len(r.hands) > 0]
            has_valid_ranges = len(valid_ranges) >= 1
        else:
            has_valid_ranges = True  # On assume que les ranges seront valides

        # Confiance minimale requise
        min_confidence = metadata.confidence >= 0.5

        if has_required_metadata and has_valid_ranges and min_confidence:
            return ContextStatus.QUIZ_READY
        elif not has_required_metadata:
            return ContextStatus.NEEDS_VALIDATION
        else:
            return ContextStatus.NEEDS_VALIDATION

    def _calculate_enhanced_confidence(self, metadata: EnrichedMetadata) -> float:
        """Calcule une confiance ajustée selon les métadonnées disponibles"""

        # Si on a déjà une confiance du standardizer, on l'utilise
        if metadata.confidence > 0:
            return metadata.confidence

        # Sinon, on calcule (cas des ranges sans nom structuré)
        confidence_factors = []

        # Facteurs de base
        if metadata.hero_position:
            confidence_factors.append(0.7)
        if metadata.primary_action:
            confidence_factors.append(0.7)
        if metadata.table_format:
            confidence_factors.append(0.6)

        # Bonus pour les combinaisons logiques
        if (metadata.primary_action in [Action.CALL, Action.RAISE_3BET, Action.DEFENSE]
                and metadata.vs_position):
            confidence_factors.append(0.8)

        if (metadata.primary_action == Action.OPEN
                and metadata.hero_position in [Position.UTG, Position.CO, Position.BTN]):
            confidence_factors.append(0.7)

        # Base minimum
        if not confidence_factors:
            confidence_factors.append(0.3)

        return min(sum(confidence_factors) / len(confidence_factors), 1.0)
    def _generate_display_names(self, metadata: EnrichedMetadata) -> tuple[str, str]:
        """Génère les noms d'affichage longs et courts"""
        parts = []
        short_parts = []

        # Position héros
        if metadata.hero_position:
            parts.append(metadata.hero_position.value)
            short_parts.append(metadata.hero_position.value)

        # Action principale
        if metadata.primary_action:
            action_names = {
                Action.OPEN: "Open",
                Action.CALL: "Call",
                Action.RAISE_3BET: "3-Bet",
                Action.RAISE_4BET: "4-Bet",
                Action.FOLD: "Fold",
                Action.CHECK: "Check",
                Action.DEFENSE: "Defense"
            }
            action_shorts = {
                Action.OPEN: "Open",
                Action.CALL: "Call",
                Action.RAISE_3BET: "3B",
                Action.RAISE_4BET: "4B",
                Action.FOLD: "Fold",
                Action.CHECK: "Check",
                Action.DEFENSE: "Def"
            }

            action_str = action_names.get(metadata.primary_action, metadata.primary_action.value)
            action_short = action_shorts.get(metadata.primary_action, metadata.primary_action.value)

            parts.append(action_str)
            short_parts.append(action_short)

        # Vs position (si pertinent)
        if (metadata.vs_position and
                metadata.primary_action in [Action.CALL, Action.RAISE_3BET, Action.DEFENSE]):
            parts.append(f"vs {metadata.vs_position.value}")
            short_parts.append(f"v{metadata.vs_position.value}")

        # Stack depth (si différent du standard)
        if metadata.stack_depth and metadata.stack_depth != StackDepth.STANDARD:
            parts.append(f"({metadata.stack_depth.value})")

        # Construire les noms
        display_name = " ".join(parts) if parts else metadata.cleaned_name
        display_name_short = " ".join(short_parts) if short_parts else "Range"

        return display_name, display_name_short

    def _log_enrichment_results(self, metadata: EnrichedMetadata):
        """Log les résultats d'enrichissement"""
        print(f"[ENRICHER] Display name: '{metadata.display_name}'")
        print(f"[ENRICHER] Display short: '{metadata.display_name_short}'")
        print(f"[ENRICHER] Game format: {metadata.game_format.value}")
        print(f"[ENRICHER] Variant: {metadata.variant.value}")
        print(f"[ENRICHER] Stack depth: {metadata.stack_depth.value}")
        print(f"[ENRICHER] Confiance enrichie: {metadata.confidence:.1%}")
        print(f"[ENRICHER] Statut contexte: {metadata.context_status.value}")
        print(f"[ENRICHER] Question-friendly: {'Oui' if metadata.question_friendly else 'Non'}")


def create_auto_enricher(game_format: str = "cash", variant: str = "nlhe") -> MetadataEnricher:
    """Factory pour créer un enrichisseur avec configuration automatique"""
    config = {
        'game_format': GameFormat.CASH if game_format.lower() == "cash" else GameFormat.TOURNAMENT,
        'variant': Variant.NLHE if variant.lower() == "nlhe" else Variant.PLO,
        'stack_depth': StackDepth.STANDARD,
        'default_table_format': TableFormat.SIXMAX
    }

    return MetadataEnricher(config)


if __name__ == "__main__":
    # Test de l'enrichisseur
    from name_standardizer import NameStandardizer

    standardizer = NameStandardizer()
    enricher = create_auto_enricher()

    test_names = [
        "6max BB Defense vs CO",
        "UTG Open 100bb",
        "CO 3Bet vs BTN",
        "poker-range-1759051996644"  # Cas problématique
    ]

    for name in test_names:
        print(f"\n{'=' * 50}")
        standardized = standardizer.standardize(name)
        enriched = enricher.enrich(standardized)
        print(f"Statut final: {enriched.context_status.value}")
        print(f"Ready for quiz: {enriched.question_friendly}")