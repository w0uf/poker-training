#!/usr/bin/env python3
"""
Enrichisseur interactif console pour les ranges de poker
Analyse les métadonnées et pose des questions pour les compléter
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Réutilise les classes du système d'import
import sqlite3
from pathlib import Path


# ============================================================================
# ENRICHMENT MODELS - Structures pour l'enrichissement
# ============================================================================

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


class StackDepth(Enum):
    SHORT = "20-40bb"
    MID = "50-75bb"
    STANDARD = "100bb"
    DEEP = "150bb+"
    VARIABLE = "variable"


class TableFormat(Enum):
    FIVEMAX = "5max"
    SIXMAX = "6max"
    NINEMAX = "9max"
    HEADSUP = "heads-up"


class GameFormat(Enum):
    CASH = "cash game"
    TOURNAMENT = "tournament"
    SNG = "sit & go"
    SPIN = "spin & go"


class Variant(Enum):
    NLHE = "No Limit Hold'em"
    PLO = "Pot Limit Omaha"
    PLO5 = "5-Card PLO"


@dataclass
class EnrichedMetadata:
    """Métadonnées enrichies pour une range"""
    # Contexte de jeu
    game_format: Optional[GameFormat] = None
    variant: Optional[Variant] = None
    table_format: Optional[TableFormat] = None

    # Situation de jeu
    hero_position: Optional[Position] = None
    vs_position: Optional[Position] = None
    primary_action: Optional[Action] = None
    stack_depth: Optional[StackDepth] = None
    sizing: Optional[str] = None

    # Métadonnées
    description: Optional[str] = None
    confidence: float = 0.0
    enriched_by_user: bool = False
    enrichment_date: Optional[str] = None


# ============================================================================
# ANALYZER - Analyseur de métadonnées avancé
# ============================================================================

class AdvancedRangeAnalyzer:
    """Analyseur avancé pour extraire plus d'informations"""

    def __init__(self):
        self.position_patterns = {
            r'\bUTG\+?1?\b': Position.UTG1,
            r'\bUTG\b': Position.UTG,
            r'\bMP\+?1?\b': Position.MP1,
            r'\bMP\b': Position.MP,
            r'\bLJ\b': Position.LJ,
            r'\bHJ\b': Position.HJ,
            r'\bCO\b': Position.CO,
            r'\bBTN\b|\bBU\b|\bButton\b': Position.BTN,
            r'\bSB\b|\bSmall[\s_]?Blind\b': Position.SB,
            r'\bBB\b|\bBig[\s_]?Blind\b': Position.BB,
        }

        self.action_patterns = {
            r'\bOpen\b|\bOpening\b|\bRFI\b': Action.OPEN,
            r'\bCall\b|\bCalling\b': Action.CALL,
            r'\b3[Bb]et\b|\b3-bet\b|\bReraise\b': Action.RAISE_3BET,
            r'\b4[Bb]et\b|\b4-bet\b': Action.RAISE_4BET,
            r'\bFold\b|\bFolding\b': Action.FOLD,
            r'\bCheck\b|\bChecking\b': Action.CHECK,
            r'\bD[éeè]fense?\b|\bDefend\b|\bDefending\b': Action.DEFENSE,
        }

        self.stack_patterns = {
            r'\b20bb\b|\bshort\b': StackDepth.SHORT,
            r'\b50bb\b|\b75bb\b|\bmid\b': StackDepth.MID,
            r'\b100bb\b|\bstandard\b': StackDepth.STANDARD,
            r'\b150bb\b|\b200bb\b|\bdeep\b': StackDepth.DEEP,
        }

        self.table_patterns = {
            r'\b5[\s-]?max\b|\b5m\b': TableFormat.FIVEMAX,
            r'\b6[\s-]?max\b|\b6m\b': TableFormat.SIXMAX,
            r'\b9[\s-]?max\b|\b9m\b|\bfull[\s-]?ring\b': TableFormat.NINEMAX,
            r'\bhu\b|\bheads[\s-]?up\b': TableFormat.HEADSUP,
        }

        self.game_patterns = {
            r'\bcash\b|\bcg\b|\bnl\d+\b': GameFormat.CASH,
            r'\btournament\b|\btourney\b|\bmtt\b': GameFormat.TOURNAMENT,
            r'\bsng\b|\bsit[\s&]go\b': GameFormat.SNG,
            r'\bspin\b|\bhyper\b': GameFormat.SPIN,
        }

        self.variant_patterns = {
            r'\bnlhe\b|\bhold[\s\']?em\b|\btexas\b': Variant.NLHE,
            r'\bplo\b|\bomaha\b': Variant.PLO,
            r'\b5[\s-]?card\b.*\bplo\b|\bplo5\b': Variant.PLO5,
        }

    def analyze_context_name(self, context_name: str) -> EnrichedMetadata:
        """Analyse approfondie du nom de contexte"""
        metadata = EnrichedMetadata()
        confidence_factors = []

        # Analyser les positions
        positions_found = []
        for pattern, position in self.position_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                positions_found.append(position)

        # Logique pour position vs vs_position
        if len(positions_found) == 1:
            metadata.hero_position = positions_found[0]
            confidence_factors.append(0.8)
        elif len(positions_found) >= 2:
            # Chercher "vs" pour déterminer l'ordre
            if re.search(r'\bvs\b|\bv\b|\bcontre\b', context_name, re.IGNORECASE):
                parts = re.split(r'\bvs\b|\bv\b|\bcontre\b', context_name, flags=re.IGNORECASE)
                if len(parts) == 2:
                    # Première partie = hero, deuxième = adversaire
                    for pattern, position in self.position_patterns.items():
                        if re.search(pattern, parts[0], re.IGNORECASE):
                            metadata.hero_position = position
                            break
                    for pattern, position in self.position_patterns.items():
                        if re.search(pattern, parts[1], re.IGNORECASE):
                            metadata.vs_position = position
                            break
                    confidence_factors.append(0.9)

        # Analyser les actions
        for pattern, action in self.action_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata.primary_action = action
                confidence_factors.append(0.7)
                break

        # Analyser stack depth
        for pattern, stack in self.stack_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata.stack_depth = stack
                confidence_factors.append(0.6)
                break

        # Analyser format de table
        for pattern, table_format in self.table_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata.table_format = table_format
                confidence_factors.append(0.5)
                break

        # Analyser format de jeu
        for pattern, game_format in self.game_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata.game_format = game_format
                confidence_factors.append(0.4)
                break

        # Analyser variante
        for pattern, variant in self.variant_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata.variant = variant
                confidence_factors.append(0.3)
                break

        # Calculer confiance
        metadata.confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        return metadata


# ============================================================================
# CONSOLE ENRICHER - Interface console interactive
# ============================================================================

class ConsoleRangeEnricher:
    """Interface console pour enrichir les métadonnées des ranges"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.analyzer = AdvancedRangeAnalyzer()

    def run_interactive_enrichment(self):
        """Lance l'enrichissement interactif"""
        print("🃏 ENRICHISSEMENT INTERACTIF DES RANGES")
        print("=" * 50)

        # Récupérer les contextes non enrichis
        contexts = self._get_contexts_to_enrich()

        if not contexts:
            print("✅ Tous les contextes sont déjà enrichis!")
            return

        print(f"📋 {len(contexts)} contextes à enrichir")

        # Afficher aperçu des contextes
        print(f"\n📊 APERÇU DES CONTEXTES À ENRICHIR:")
        for i, context in enumerate(contexts[:5], 1):  # Afficher les 5 premiers
            print(f"   {i}. {context['name']}")
        if len(contexts) > 5:
            print(f"   ... et {len(contexts) - 5} autres")

        # Questions préliminaires GLOBALES
        print(f"\n🎮 QUESTIONS PRÉLIMINAIRES GLOBALES")
        print("Ces paramètres s'appliqueront à TOUS vos contextes:")
        global_metadata = self._ask_global_preliminary_questions()

        print(f"\n✅ Paramètres globaux définis!")
        print(f"   🎮 Format: {global_metadata.game_format.value}")
        print(f"   🃏 Variante: {global_metadata.variant.value}")
        if global_metadata.table_format:
            print(f"   🪑 Table: {global_metadata.table_format.value}")

        # Confirmer le démarrage de l'enrichissement
        start = input(f"\n🚀 Commencer l'enrichissement des {len(contexts)} contextes ? (o/n): ").strip().lower()
        if not start.startswith('o'):
            print("❌ Enrichissement annulé")
            return

        enriched_count = 0

        for i, context in enumerate(contexts, 1):
            print(f"\n{'=' * 60}")
            print(f"📋 CONTEXTE {i}/{len(contexts)}")
            print(f"{'=' * 60}")

            try:
                if self._enrich_single_context(context, global_metadata):
                    enriched_count += 1

                # Demander si continuer
                if i < len(contexts):
                    choice = input("\n➡️  Continuer avec le suivant ? (o/n/q pour quitter): ").strip().lower()
                    if choice == 'q':
                        break
                    elif choice == 'n':
                        print("⏸️  Enrichissement interrompu")
                        break

            except KeyboardInterrupt:
                print("\n⏸️  Enrichissement interrompu par l'utilisateur")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                continue

        print(f"\n🎉 ENRICHISSEMENT TERMINÉ")
        print(f"✅ {enriched_count} contextes enrichis")

    def _get_contexts_to_enrich(self) -> List[Dict]:
        """Récupère les contextes qui ont besoin d'enrichissement"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, parsed_metadata, enriched_metadata, confidence
                FROM range_contexts
                WHERE json_extract(enriched_metadata, '$.enriched_by_user') IS NULL
                   OR json_extract(enriched_metadata, '$.enriched_by_user') = 'false'
                ORDER BY confidence ASC
            """)

            contexts = []
            for row in cursor.fetchall():
                contexts.append({
                    'id': row[0],
                    'name': row[1],
                    'parsed_metadata': json.loads(row[2]) if row[2] else {},
                    'enriched_metadata': json.loads(row[3]) if row[3] else {},
                    'confidence': row[4]
                })

            return contexts

    def _enrich_single_context(self, context: Dict, global_metadata: EnrichedMetadata) -> bool:
        """Enrichit un contexte unique avec les métadonnées globales"""

        context_name = context['name']
        print(f"📋 Contexte: '{context_name}'")
        print(f"🎯 Confiance automatique: {context['confidence']:.1%}")

        # Afficher les ranges contenues dans ce contexte
        self._display_context_ranges(context['id'])

        # Confirmer que c'est le bon contexte
        confirm = input(f"\n✅ Enrichir ce contexte ? (o/n): ").strip().lower()
        if not confirm.startswith('o'):
            print("⏭️  Contexte ignoré")
            return False

        # Analyse avancée du contexte spécifique
        metadata = self.analyzer.analyze_context_name(context_name)

        # Appliquer les métadonnées globales
        metadata.game_format = global_metadata.game_format
        metadata.variant = global_metadata.variant

        # Pour le format de table : utiliser global si défini, sinon demander
        if global_metadata.table_format:
            metadata.table_format = global_metadata.table_format
        # Sinon, garder ce qui a été détecté automatiquement (peut être None)

        # Afficher ce qui a été détecté + global
        print(f"\n🔍 ANALYSE (GLOBAL + AUTOMATIQUE):")
        self._display_detected_metadata(metadata)

        # Poser des questions pour compléter SEULEMENT les éléments spécifiques au contexte
        print(f"\n❓ QUESTIONS SPÉCIFIQUES À CE CONTEXTE:")
        enhanced_metadata = self._ask_context_specific_questions(metadata, context_name, global_metadata)

        # Demander confirmation finale
        print(f"\n📝 RÉSUMÉ DES MÉTADONNÉES:")
        self._display_final_metadata(enhanced_metadata)

        save = input("\n💾 Sauvegarder ces métadonnées ? (o/n): ").strip().lower()

        if save.startswith('o'):
            self._save_enriched_metadata(context['id'], enhanced_metadata)
            print("✅ Métadonnées sauvegardées!")
            return True
        else:
            print("❌ Métadonnées non sauvegardées")
            return False

    def _display_context_ranges(self, context_id: int):
        """Affiche les ranges contenues dans ce contexte"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, color, 
                       (SELECT COUNT(*) FROM range_hands WHERE range_id = ranges.id) as hand_count
                FROM ranges 
                WHERE context_id = ?
                ORDER BY range_key
            """, (context_id,))

            ranges = cursor.fetchall()

            if ranges:
                print(f"\n📊 RANGES CONTENUES DANS CE CONTEXTE:")
                for name, color, hand_count in ranges:
                    print(f"   🎯 {name} ({hand_count} mains) - {color}")
            else:
                print(f"\n⚠️  Aucune range trouvée dans ce contexte")

    def _ask_global_preliminary_questions(self) -> EnrichedMetadata:
        """Pose les questions préliminaires globales pour TOUS les contextes"""
        metadata = EnrichedMetadata()

        print("Ces informations s'appliqueront à tous vos contextes de ranges.\n")

        # Format de jeu (essentiel)
        metadata.game_format = self._ask_game_format("Format de jeu principal pour vos ranges ?")

        # Variante (essentiel)
        metadata.variant = self._ask_variant("Variante de poker ?")

        # Format de table (important, avec possibilité de variable)
        print(f"\n🪑 Format de table par défaut ?")
        formats = list(TableFormat)
        formats.append("variable")  # Option spéciale

        for i, fmt in enumerate(formats, 1):
            if isinstance(fmt, TableFormat):
                print(f"   {i}. {fmt.value}")
            else:
                print(f"   {i}. Variable (spécifique par contexte)")

        while True:
            try:
                choice = input("Votre choix (1-5): ").strip()
                choice_idx = int(choice) - 1
                if choice_idx == len(formats) - 1:  # Variable choisi
                    metadata.table_format = None  # Sera demandé par contexte
                    break
                elif 0 <= choice_idx < len(formats) - 1:
                    metadata.table_format = formats[choice_idx]
                    break
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

        return metadata
        """Affiche les métadonnées détectées automatiquement"""

        def status_icon(value):
            return "✅" if value else "❓"

        print(
            f"   {status_icon(metadata.hero_position)} Position héros: {metadata.hero_position.value if metadata.hero_position else 'non détectée'}")
        print(
            f"   {status_icon(metadata.vs_position)} Vs position: {metadata.vs_position.value if metadata.vs_position else 'non détectée'}")
        print(
            f"   {status_icon(metadata.primary_action)} Action: {metadata.primary_action.value if metadata.primary_action else 'non détectée'}")
        print(
            f"   {status_icon(metadata.stack_depth)} Stack depth: {metadata.stack_depth.value if metadata.stack_depth else 'non détectée'}")
        print(
            f"   {status_icon(metadata.table_format)} Format table: {metadata.table_format.value if metadata.table_format else 'non détecté'}")

    def _ask_context_specific_questions(self, metadata: EnrichedMetadata, context_name: str,
                                        global_metadata: EnrichedMetadata) -> EnrichedMetadata:
        """Pose des questions spécifiques au contexte (pas les globales déjà posées)"""

        # Format de table (seulement si pas défini globalement)
        if not global_metadata.table_format and not metadata.table_format:
            metadata.table_format = self._ask_table_format("Format de table pour ce contexte ?")
        elif not global_metadata.table_format and metadata.table_format:
            confirm = input(f"   Format table '{metadata.table_format.value}' détecté. Correct ? (o/n): ")
            if not confirm.strip().lower().startswith('o'):
                metadata.table_format = self._ask_table_format("Format de table ?")

        # Position héros
        if not metadata.hero_position:
            metadata.hero_position = self._ask_position("Quelle est votre position pour cette range ?")
        else:
            confirm = input(f"   Position héros '{metadata.hero_position.value}' correcte ? (o/n): ")
            if not confirm.strip().lower().startswith('o'):
                metadata.hero_position = self._ask_position("Quelle est votre position ?")

        # Vs position (seulement si pertinent)
        if metadata.primary_action in [Action.CALL, Action.RAISE_3BET, Action.DEFENSE]:
            if not metadata.vs_position:
                vs_needed = input(f"   Cette range est-elle face à une position spécifique ? (o/n): ")
                if vs_needed.strip().lower().startswith('o'):
                    metadata.vs_position = self._ask_position("Face à quelle position ?")
            else:
                confirm = input(f"   Vs position '{metadata.vs_position.value}' correcte ? (o/n): ")
                if not confirm.strip().lower().startswith('o'):
                    metadata.vs_position = self._ask_position("Face à quelle position ?")

        # Action principale
        if not metadata.primary_action:
            metadata.primary_action = self._ask_action("Quelle est l'action principale de cette range ?")
        else:
            confirm = input(f"   Action '{metadata.primary_action.value}' correcte ? (o/n): ")
            if not confirm.strip().lower().startswith('o'):
                metadata.primary_action = self._ask_action("Quelle est l'action principale ?")

        # Stack depth
        if not metadata.stack_depth:
            metadata.stack_depth = self._ask_stack_depth("Quelle stack depth pour cette range ?")
        else:
            confirm = input(f"   Stack depth '{metadata.stack_depth.value}' correcte ? (o/n): ")
            if not confirm.strip().lower().startswith('o'):
                metadata.stack_depth = self._ask_stack_depth("Quelle stack depth ?")

        # Sizing (si pertinent)
        if metadata.primary_action in [Action.OPEN, Action.RAISE_3BET, Action.RAISE_4BET]:
            sizing = input(f"   Sizing utilisé (ex: 2.5x, 3bb, pot) ou Enter pour passer: ").strip()
            if sizing:
                metadata.sizing = sizing

        # Description optionnelle
        description = input(f"   Description optionnelle (Enter pour passer): ").strip()
        if description:
            metadata.description = description

        # Marquer comme enrichi par l'utilisateur
        metadata.enriched_by_user = True
        metadata.enrichment_date = datetime.now().isoformat()
        metadata.confidence = 1.0  # Confiance maximale après enrichissement manuel

        return metadata

    def _ask_position(self, question: str) -> Optional[Position]:
        """Demande de choisir une position"""
        print(f"\n🎯 {question}")
        positions = list(Position)

        for i, pos in enumerate(positions, 1):
            print(f"   {i:2d}. {pos.value}")

        while True:
            try:
                choice = input("Votre choix (1-10) ou 's' pour passer: ").strip()
                if choice.lower() == 's':
                    return None

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(positions):
                    return positions[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def _ask_action(self, question: str) -> Optional[Action]:
        """Demande de choisir une action"""
        print(f"\n⚡ {question}")
        actions = list(Action)

        for i, action in enumerate(actions, 1):
            print(f"   {i}. {action.value}")

        while True:
            try:
                choice = input("Votre choix (1-7) ou 's' pour passer: ").strip()
                if choice.lower() == 's':
                    return None

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(actions):
                    return actions[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def _ask_stack_depth(self, question: str) -> Optional[StackDepth]:
        """Demande de choisir une stack depth"""
        print(f"\n💰 {question}")
        stacks = list(StackDepth)

        for i, stack in enumerate(stacks, 1):
            print(f"   {i}. {stack.value}")

        while True:
            try:
                choice = input("Votre choix (1-5) ou 's' pour passer: ").strip()
                if choice.lower() == 's':
                    return None

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(stacks):
                    return stacks[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def _ask_game_format(self, question: str) -> Optional[GameFormat]:
        """Demande le format de jeu"""
        print(f"\n🎮 {question}")
        formats = list(GameFormat)

        for i, fmt in enumerate(formats, 1):
            print(f"   {i}. {fmt.value}")

        while True:
            try:
                choice = input("Votre choix (1-4): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(formats):
                    return formats[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def _ask_variant(self, question: str) -> Optional[Variant]:
        """Demande la variante de poker"""
        print(f"\n🃏 {question}")
        variants = list(Variant)

        for i, variant in enumerate(variants, 1):
            print(f"   {i}. {variant.value}")

        while True:
            try:
                choice = input("Votre choix (1-3): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(variants):
                    return variants[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")
        """Demande le format de table"""
        print(f"\n🪑 {question}")
        formats = list(TableFormat)

        for i, fmt in enumerate(formats, 1):
            print(f"   {i}. {fmt.value}")

        while True:
            try:
                choice = input("Votre choix (1-5) ou 's' pour passer: ").strip()
                if choice.lower() == 's':
                    return None

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(formats):
                    return formats[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def _display_final_metadata(self, metadata: EnrichedMetadata):
        """Affiche le résumé final des métadonnées"""

        def format_value(value):
            return value.value if hasattr(value, 'value') else (value or 'non spécifié')

        print(f"   🎮 Format jeu: {format_value(metadata.game_format)}")
        print(f"   🃏 Variante: {format_value(metadata.variant)}")
        print(f"   🪑 Format table: {format_value(metadata.table_format)}")
        print(f"   📍 Position héros: {format_value(metadata.hero_position)}")
        print(f"   🆚 Vs position: {format_value(metadata.vs_position)}")
        print(f"   ⚡ Action: {format_value(metadata.primary_action)}")
        print(f"   💰 Stack depth: {format_value(metadata.stack_depth)}")

        if metadata.sizing:
            print(f"   💵 Sizing: {metadata.sizing}")

        if metadata.description:
            print(f"   📝 Description: {metadata.description}")

    def _save_enriched_metadata(self, context_id: int, metadata: EnrichedMetadata):
        """Sauvegarde les métadonnées enrichies en base"""

        # Convertir en dictionnaire
        metadata_dict = {
            'game_format': metadata.game_format.value if metadata.game_format else None,
            'variant': metadata.variant.value if metadata.variant else None,
            'table_format': metadata.table_format.value if metadata.table_format else None,
            'hero_position': metadata.hero_position.value if metadata.hero_position else None,
            'vs_position': metadata.vs_position.value if metadata.vs_position else None,
            'primary_action': metadata.primary_action.value if metadata.primary_action else None,
            'stack_depth': metadata.stack_depth.value if metadata.stack_depth else None,
            'sizing': metadata.sizing,
            'description': metadata.description,
            'confidence': metadata.confidence,
            'enriched_by_user': metadata.enriched_by_user,
            'enrichment_date': metadata.enrichment_date
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE range_contexts 
                SET enriched_metadata = ?, confidence = ?
                WHERE id = ?
            """, (json.dumps(metadata_dict), metadata.confidence, context_id))

    def show_enrichment_summary(self):
        """Affiche un résumé des enrichissements"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN json_extract(enriched_metadata, '$.enriched_by_user') = 'true' THEN 1 ELSE 0 END) as enriched,
                    AVG(confidence) as avg_confidence
                FROM range_contexts
            """)

            row = cursor.fetchone()
            total, enriched, avg_confidence = row

            print(f"\n📊 RÉSUMÉ D'ENRICHISSEMENT:")
            print(f"📋 Total contextes: {total}")
            print(f"✅ Enrichis: {enriched}")
            print(f"❓ Restants: {total - enriched}")
            print(f"🎯 Confiance moyenne: {avg_confidence:.1%}")


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée principal"""

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord le script d'import: python import_ranges.py")
        return

    enricher = ConsoleRangeEnricher(db_path)

    # Afficher résumé initial
    enricher.show_enrichment_summary()

    # Lancer enrichissement interactif
    start = input("\n🚀 Lancer l'enrichissement interactif ? (o/n): ").strip().lower()

    if start.startswith('o'):
        enricher.run_interactive_enrichment()

        # Afficher résumé final
        enricher.show_enrichment_summary()

    print("\n👋 À bientôt!")


if __name__ == "__main__":
    main()