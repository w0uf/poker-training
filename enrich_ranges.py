#!/usr/bin/env python3
"""
Enrichisseur interactif console V4 pour les ranges de poker
Génère des display_name et display_name_short pour les questions
"""

import json
import re
import os  # ← Ajouter cet import
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Réutilise les classes du système d'import
import sqlite3
from pathlib import Path

# Détection du mode web
WEB_MODE = os.getenv('POKER_WEB_MODE') == '1'

if WEB_MODE:
    print(f"🌐 MODE WEB : Enrichissement automatique activé")
# ============================================================================
# ENRICHMENT MODELS - Structures pour l'enrichissement V4
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
class EnrichedMetadataV4:
    """Métadonnées enrichies V4 avec display_name"""
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

    # Nouveaux V4
    display_name: Optional[str] = None
    display_name_short: Optional[str] = None
    question_friendly: bool = False
    version: str = "v4"


# ============================================================================
# ANALYZER - Analyseur de métadonnées avancé V4
# ============================================================================

class AdvancedRangeAnalyzerV4:
    """Analyseur avancé V4 pour extraire plus d'informations"""

    def __init__(self):
        # Patterns de positions avec variations et ordre de priorité
        self.position_patterns = {
            # UTG et variations
            r'\bUTG\+?1?\b|\bUnder[\s_]?the[\s_]?Gun\+?1?\b': Position.UTG1,
            r'\bUTG\b(?!\+)|\bUnder[\s_]?the[\s_]?Gun\b(?!\+)': Position.UTG,

            # MP et variations
            r'\bMP\+?1?\b|\bMiddle[\s_]?Position\+?1?\b|\bMid[\s_]?Position\+?1?\b': Position.MP1,
            r'\bMP\b(?!\+)|\bMiddle[\s_]?Position\b(?!\+)|\bMid[\s_]?Position\b(?!\+)': Position.MP,

            # Autres positions
            r'\bLJ\b|\bLojack\b|\bLo[\s_]?Jack\b': Position.LJ,
            r'\bHJ\b|\bHijack\b|\bHi[\s_]?Jack\b': Position.HJ,
            r'\bCO\b|\bCutoff\b|\bCut[\s_]?off\b': Position.CO,
            r'\bBTN\b|\bBU\b|\bButton\b': Position.BTN,
            r'\bSB\b|\bSmall[\s_]?Blind\b': Position.SB,
            r'\bBB\b|\bBig[\s_]?Blind\b': Position.BB,
        }

        # Patterns d'actions avec gestion français/anglais et encodage
        self.action_patterns = {
            # Défense (français et anglais) - PRIORITÉ ÉLEVÉE
            r'\bD[éeèÉÃ©Ã¨]fense?\b|\bDefend\b|\bDefending\b|\bDef\b': Action.DEFENSE,

            # Open
            r'\bOpen\b|\bOpening\b|\bRFI\b|\bRaise[\s_]?First[\s_]?In\b': Action.OPEN,

            # Call
            r'\bCall\b|\bCalling\b|\bFlat\b': Action.CALL,

            # 3Bet/4Bet
            r'\b3[\s_-]?[Bb]et\b|\bReraise\b|\bThree[\s_]?Bet\b': Action.RAISE_3BET,
            r'\b4[\s_-]?[Bb]et\b|\bFour[\s_]?Bet\b': Action.RAISE_4BET,

            # Autres
            r'\bFold\b|\bFolding\b': Action.FOLD,
            r'\bCheck\b|\bChecking\b': Action.CHECK,
        }

        # Patterns de structure "vs"
        self.vs_patterns = [
            r'\bvs\b',
            r'\bv\b',
            r'\bcontre\b',
            r'\bface\b',
            r'\bversus\b',
            r'\bagainst\b'
        ]

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

    def clean_encoding_issues(self, text: str) -> str:
        """Nettoie les problèmes d'encoding courants"""
        replacements = {
            'DÃ©fense': 'Défense',
            'DÃ©f': 'Déf',
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã ': 'à',
            'â€™': "'",
            'â€œ': '"',
            'â€': '"'
        }

        cleaned = text
        for bad, good in replacements.items():
            cleaned = cleaned.replace(bad, good)

        return cleaned

    def analyze_context_name(self, context_name: str) -> EnrichedMetadataV4:
        """Analyse approfondie du nom de contexte avec gestion d'encoding"""
        metadata = EnrichedMetadataV4()
        confidence_factors = []

        # Nettoyer l'encoding d'abord
        cleaned_name = self.clean_encoding_issues(context_name)
        print(f"🔍 Analyse: '{context_name}' → '{cleaned_name}'")

        # Analyser les positions avec logique "vs"
        positions_analysis = self._analyze_positions_with_vs(cleaned_name)

        if positions_analysis['hero_position']:
            metadata.hero_position = positions_analysis['hero_position']
            confidence_factors.append(positions_analysis['hero_confidence'])

        if positions_analysis['vs_position']:
            metadata.vs_position = positions_analysis['vs_position']
            confidence_factors.append(positions_analysis['vs_confidence'])

        # Analyser les actions avec priorité pour "défense"
        action_analysis = self._analyze_actions_prioritized(cleaned_name)
        if action_analysis['action']:
            metadata.primary_action = action_analysis['action']
            confidence_factors.append(action_analysis['confidence'])

        # Calculer confiance globale
        metadata.confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        return metadata

    def _analyze_positions_with_vs(self, context_name: str) -> Dict:
        """Analyse les positions avec logique 'vs' améliorée"""
        result = {
            'hero_position': None,
            'vs_position': None,
            'hero_confidence': 0.0,
            'vs_confidence': 0.0
        }

        # Trouver toutes les positions
        positions_found = []
        for pattern, position in self.position_patterns.items():
            matches = list(re.finditer(pattern, context_name, re.IGNORECASE))
            for match in matches:
                positions_found.append({
                    'position': position,
                    'start': match.start(),
                    'end': match.end(),
                    'match': match.group()
                })

        if not positions_found:
            return result

        # Chercher structure "vs"
        vs_match = None
        for vs_pattern in self.vs_patterns:
            match = re.search(vs_pattern, context_name, re.IGNORECASE)
            if match:
                vs_match = {'start': match.start(), 'end': match.end(), 'keyword': match.group()}
                break

        if len(positions_found) == 1:
            # Une seule position = héros
            result['hero_position'] = positions_found[0]['position']
            result['hero_confidence'] = 0.7

        elif len(positions_found) >= 2 and vs_match:
            # Logique avec "vs": avant = héros, après = adversaire
            vs_position = vs_match['start']

            before_vs = [p for p in positions_found if p['end'] <= vs_position]
            after_vs = [p for p in positions_found if p['start'] >= vs_match['end']]

            if before_vs:
                result['hero_position'] = before_vs[-1]['position']  # Dernière avant vs
                result['hero_confidence'] = 0.9

            if after_vs:
                result['vs_position'] = after_vs[0]['position']  # Première après vs
                result['vs_confidence'] = 0.9

        elif len(positions_found) >= 2:
            # Plusieurs positions sans "vs" - heuristique
            result['hero_position'] = positions_found[0]['position']
            result['hero_confidence'] = 0.5

        return result

    def _analyze_actions_prioritized(self, context_name: str) -> Dict:
        """Analyse les actions avec priorité pour défense"""
        result = {
            'action': None,
            'confidence': 0.0
        }

        # Priorité spéciale pour "défense"
        defense_patterns = [
            r'\bD[éeèÉÃ©Ã¨]fense?\b',
            r'\bDefend\b',
            r'\bDefending\b',
            r'\bDef\b'
        ]

        for pattern in defense_patterns:
            if re.search(pattern, context_name, re.IGNORECASE):
                result['action'] = Action.DEFENSE
                result['confidence'] = 0.9
                return result

        # Autres actions par ordre de priorité
        priority_actions = [
            (r'\bOpen\b|\bOpening\b|\bRFI\b', Action.OPEN, 0.8),
            (r'\b3[\s_-]?[Bb]et\b|\bReraise\b', Action.RAISE_3BET, 0.7),
            (r'\b4[\s_-]?[Bb]et\b', Action.RAISE_4BET, 0.7),
            (r'\bCall\b|\bCalling\b', Action.CALL, 0.6),
            (r'\bFold\b|\bFolding\b', Action.FOLD, 0.6),
            (r'\bCheck\b|\bChecking\b', Action.CHECK, 0.6),
        ]

        for pattern, action, confidence in priority_actions:
            if re.search(pattern, context_name, re.IGNORECASE):
                result['action'] = action
                result['confidence'] = confidence
                break

        return result


# ============================================================================
# DISPLAY NAME GENERATOR - Générateur de noms d'affichage V4
# ============================================================================

class DisplayNameGeneratorV4:
    """Générateur de noms d'affichage pour les questions"""

    def generate_display_names(self, metadata: EnrichedMetadataV4, context_name: str) -> Tuple[str, str]:
        """Génère display_name (long) et display_name_short (court)"""

        # Construire le nom long
        parts = []

        # Format de jeu (si différent du défaut)
        if metadata.game_format and metadata.game_format != GameFormat.CASH:
            parts.append(metadata.game_format.value.title())

        # Position héros
        if metadata.hero_position:
            parts.append(metadata.hero_position.value)

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
            action_str = action_names.get(metadata.primary_action, metadata.primary_action.value)
            parts.append(action_str)

        # Vs position (si pertinent)
        if metadata.vs_position and metadata.primary_action in [Action.CALL, Action.RAISE_3BET, Action.DEFENSE]:
            parts.append(f"vs {metadata.vs_position.value}")

        # Stack depth (si différent du standard)
        if metadata.stack_depth and metadata.stack_depth != StackDepth.STANDARD:
            parts.append(f"({metadata.stack_depth.value})")

        # Construire le nom long
        if parts:
            display_name = " ".join(parts)
        else:
            # Fallback sur le nom du contexte original
            display_name = self._clean_context_name(context_name)

        # Générer le nom court
        display_name_short = self._generate_short_name(metadata)

        return display_name, display_name_short

    def _clean_context_name(self, context_name: str) -> str:
        """Nettoie le nom du contexte pour l'affichage"""
        # Supprimer les extensions, caractères spéciaux, etc.
        cleaned = re.sub(r'\.[a-zA-Z0-9]+$', '', context_name)  # Extensions
        cleaned = re.sub(r'[_-]+', ' ', cleaned)  # Underscores et tirets
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Espaces multiples
        return cleaned.title()

    def _generate_short_name(self, metadata: EnrichedMetadataV4) -> str:
        """Génère un nom court pour l'affichage compact"""
        parts = []

        # Position (abrégée)
        if metadata.hero_position:
            parts.append(metadata.hero_position.value)

        # Action (abrégée)
        if metadata.primary_action:
            action_shorts = {
                Action.OPEN: "Open",
                Action.CALL: "Call",
                Action.RAISE_3BET: "3B",
                Action.RAISE_4BET: "4B",
                Action.FOLD: "Fold",
                Action.CHECK: "Check",
                Action.DEFENSE: "Def"
            }
            parts.append(action_shorts.get(metadata.primary_action, metadata.primary_action.value))

        # Vs position (si pertinent)
        if metadata.vs_position and metadata.primary_action in [Action.CALL, Action.RAISE_3BET, Action.DEFENSE]:
            parts.append(f"v{metadata.vs_position.value}")

        return " ".join(parts) if parts else "Range"


# ============================================================================
# CONSOLE ENRICHER V4 - Interface console interactive
# ============================================================================

class ConsoleRangeEnricherV4:
    """Interface console V4 pour enrichir les métadonnées des ranges"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.analyzer = AdvancedRangeAnalyzerV4()
        self.display_generator = DisplayNameGeneratorV4()

    def run_interactive_enrichment_v4(self):
        """Lance l'enrichissement interactif V4"""
        print("🃏 ENRICHISSEMENT INTERACTIF V4 DES RANGES")
        print("=" * 50)

        # Récupérer les contextes à enrichir
        contexts = self._get_contexts_to_enrich_v4()

        if not contexts:
            print("✅ Tous les contextes sont déjà enrichis V4!")
            return

        print(f"📋 {len(contexts)} contextes à enrichir en V4")

        # Afficher aperçu des contextes
        print(f"\n📊 APERÇU DES CONTEXTES À ENRICHIR:")
        for i, context in enumerate(contexts[:5], 1):
            print(f"   {i}. {context['name']}")
        if len(contexts) > 5:
            print(f"   ... et {len(contexts) - 5} autres")

        # Questions préliminaires GLOBALES
        print(f"\n🎮 QUESTIONS PRÉLIMINAIRES GLOBALES V4")
        print("Ces paramètres s'appliqueront à TOUS vos contextes:")
        global_metadata = self._ask_global_preliminary_questions_v4()

        print(f"\n✅ Paramètres globaux V4 définis!")
        print(f"   🎮 Format: {global_metadata.game_format.value}")
        print(f"   🃏 Variante: {global_metadata.variant.value}")
        if global_metadata.table_format:
            print(f"   🪑 Table: {global_metadata.table_format.value}")

        # Confirmer le démarrage
        start = input(f"\n🚀 Commencer l'enrichissement V4 des {len(contexts)} contextes ? (o/n): ").strip().lower()
        if not start.startswith('o'):
            print("❌ Enrichissement V4 annulé")
            return

        enriched_count = 0

        for i, context in enumerate(contexts, 1):
            print(f"\n{'=' * 60}")
            print(f"📋 CONTEXTE {i}/{len(contexts)} (V4)")
            print(f"{'=' * 60}")

            try:
                if self._enrich_single_context_v4(context, global_metadata):
                    enriched_count += 1

                # Demander si continuer
                if i < len(contexts):
                    choice = input("\n➡️  Continuer avec le suivant ? (o/n/q pour quitter): ").strip().lower()
                    if choice == 'q':
                        break
                    elif choice == 'n':
                        print("⏸️  Enrichissement V4 interrompu")
                        break

            except KeyboardInterrupt:
                print("\n⏸️  Enrichissement V4 interrompu par l'utilisateur")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                continue

        print(f"\n🎉 ENRICHISSEMENT V4 TERMINÉ")
        print(f"✅ {enriched_count} contextes enrichis en V4")

    def _get_contexts_to_enrich_v4(self) -> List[Dict]:
        """Récupère les contextes qui ont besoin d'enrichissement V4"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, parsed_metadata, enriched_metadata, confidence
                FROM range_contexts
                WHERE json_extract(enriched_metadata, '$.version') != 'v4'
                   OR json_extract(enriched_metadata, '$.version') IS NULL
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

    def _ask_global_preliminary_questions_v4(self) -> EnrichedMetadataV4:
        """Pose les questions préliminaires globales V4"""
        metadata = EnrichedMetadataV4()
        if WEB_MODE:
            # Mode web - valeurs par défaut automatiques
            print("🌐 MODE WEB : Application des paramètres par défaut")
            metadata.game_format = GameFormat.CASH
            metadata.variant = Variant.NLHE
            metadata.table_format = TableFormat.SIXMAX
            print(f"   🎮 Format: {metadata.game_format.value}")
            print(f"   🃏 Variante: {metadata.variant.value}")
            print(f"   🪑 Table: {metadata.table_format.value}")
            return metadata

        # Mode interactif normal...
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

    def _enrich_single_context_v4(self, context: Dict, global_metadata: EnrichedMetadataV4) -> bool:
        """Enrichit un contexte unique avec les métadonnées globales V4"""

        context_name = context['name']
        print(f"📋 Contexte: '{context_name}'")
        print(f"🎯 Confiance automatique: {context['confidence']:.1%}")

        # Afficher les ranges contenues dans ce contexte
        self._display_context_ranges(context['id'])

        # Confirmer que c'est le bon contexte
        confirm = input(f"\n✅ Enrichir ce contexte en V4 ? (o/n): ").strip().lower()
        if not confirm.startswith('o'):
            print("⏭️  Contexte ignoré")
            return False

        # Analyse avancée du contexte spécifique
        metadata = self.analyzer.analyze_context_name(context_name)

        # Appliquer les métadonnées globales
        metadata.game_format = global_metadata.game_format
        metadata.variant = global_metadata.variant

        # Format de table
        if global_metadata.table_format:
            metadata.table_format = global_metadata.table_format

        # Afficher ce qui a été détecté + global
        print(f"\n🔍 ANALYSE V4 (GLOBAL + AUTOMATIQUE):")
        self._display_detected_metadata_v4(metadata)

        # Poser des questions pour compléter
        print(f"\n❓ QUESTIONS SPÉCIFIQUES À CE CONTEXTE V4:")
        enhanced_metadata = self._ask_context_specific_questions_v4(metadata, context_name, global_metadata)

        # Générer les noms d'affichage
        display_name, display_name_short = self.display_generator.generate_display_names(enhanced_metadata,
                                                                                         context_name)
        enhanced_metadata.display_name = display_name
        enhanced_metadata.display_name_short = display_name_short

        # Marquer comme prêt pour les questions si complet
        enhanced_metadata.question_friendly = self._is_question_friendly(enhanced_metadata)

        # Demander confirmation finale
        print(f"\n📝 RÉSUMÉ DES MÉTADONNÉES V4:")
        self._display_final_metadata_v4(enhanced_metadata)

        save = input("\n💾 Sauvegarder ces métadonnées V4 ? (o/n): ").strip().lower()

        if save.startswith('o'):
            self._save_enriched_metadata_v4(context['id'], enhanced_metadata)
            print("✅ Métadonnées V4 sauvegardées!")
            return True
        else:
            print("❌ Métadonnées V4 non sauvegardées")
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

    def _display_detected_metadata_v4(self, metadata: EnrichedMetadataV4):
        """Affiche les métadonnées détectées automatiquement V4"""

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

    def _ask_context_specific_questions_v4(self, metadata: EnrichedMetadataV4, context_name: str,
                                           global_metadata: EnrichedMetadataV4) -> EnrichedMetadataV4:
        """Pose des questions spécifiques au contexte V4"""

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

        # Marquer comme enrichi par l'utilisateur V4
        metadata.enriched_by_user = True
        metadata.enrichment_date = datetime.now().isoformat()
        metadata.confidence = 1.0
        metadata.version = "v4"

        return metadata

    def _is_question_friendly(self, metadata: EnrichedMetadataV4) -> bool:
        """Détermine si le contexte est prêt pour la génération de questions"""
        required_fields = [
            metadata.hero_position,
            metadata.primary_action,
            metadata.game_format,
            metadata.variant
        ]
        return all(field is not None for field in required_fields)

    def _display_final_metadata_v4(self, metadata: EnrichedMetadataV4):
        """Affiche le résumé final des métadonnées V4"""

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

        print(f"\n🏷️  NOMS D'AFFICHAGE GÉNÉRÉS:")
        print(f"   📋 Display Name: '{metadata.display_name}'")
        print(f"   🔤 Display Short: '{metadata.display_name_short}'")
        print(f"   ❓ Question-friendly: {'✅' if metadata.question_friendly else '❌'}")

    def _save_enriched_metadata_v4(self, context_id: int, metadata: EnrichedMetadataV4):
        """Sauvegarde les métadonnées enrichies V4 en base"""
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
            'enrichment_date': metadata.enrichment_date,
            'display_name': metadata.display_name,
            'display_name_short': metadata.display_name_short,
            'question_friendly': metadata.question_friendly,
            'version': metadata.version
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE range_contexts 
                SET enriched_metadata = ?, confidence = ?
                WHERE id = ?
            """, (json.dumps(metadata_dict), metadata.confidence, context_id))

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

    def _ask_table_format(self, question: str) -> Optional[TableFormat]:
        """Demande le format de table"""
        print(f"\n🪑 {question}")
        formats = list(TableFormat)

        for i, fmt in enumerate(formats, 1):
            print(f"   {i}. {fmt.value}")

        while True:
            try:
                choice = input("Votre choix (1-4) ou 's' pour passer: ").strip()
                if choice.lower() == 's':
                    return None

                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(formats):
                    return formats[choice_idx]
                else:
                    print("❌ Choix invalide!")
            except ValueError:
                print("❌ Veuillez entrer un nombre!")

    def show_enrichment_summary_v4(self):
        """Affiche un résumé des enrichissements V4"""
        with sqlite3.connect(self.db_path) as conn:
            # Normaliser les booléens pour la compatibilité
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE 
                        WHEN json_extract(enriched_metadata, '$.version') = 'v4' THEN 1 
                        ELSE 0 
                    END) as v4_contexts,
                    SUM(CASE 
                        WHEN json_extract(enriched_metadata, '$.version') = 'v4' 
                         AND (json_extract(enriched_metadata, '$.question_friendly') = 'true'
                              OR json_extract(enriched_metadata, '$.question_friendly') = true
                              OR json_extract(enriched_metadata, '$.question_friendly') = 1) THEN 1 
                        ELSE 0 
                    END) as question_ready,
                    AVG(confidence) as avg_confidence
                FROM range_contexts
            """)

            row = cursor.fetchone()
            total, v4_contexts, question_ready, avg_confidence = row

            print(f"\n📊 RÉSUMÉ D'ENRICHISSEMENT V4:")
            print(f"📋 Total contextes: {total}")
            print(f"✅ Enrichis V4: {v4_contexts}")
            print(f"❓ Prêts pour questions: {question_ready}")
            print(f"❌ Restants: {total - v4_contexts}")
            print(f"🎯 Confiance moyenne: {avg_confidence:.1%}")

    def list_display_names_v4(self):
        """Liste tous les noms d'affichage V4 créés"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, 
                       json_extract(enriched_metadata, '$.display_name') as display_name,
                       json_extract(enriched_metadata, '$.display_name_short') as display_short,
                       json_extract(enriched_metadata, '$.question_friendly') as question_friendly
                FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.version') = 'v4'
                  AND json_extract(enriched_metadata, '$.display_name') IS NOT NULL
                ORDER BY name
            """)

            contexts = cursor.fetchall()

            if not contexts:
                print("❌ Aucun nom d'affichage V4 trouvé")
                return

            print(f"\n🏷️  NOMS D'AFFICHAGE V4 ({len(contexts)} contextes)")
            print("=" * 60)

            for name, display_name, display_short, question_friendly in contexts:
                # Normaliser le booléen
                is_question_friendly = str(question_friendly).lower() in ['true', '1', 'yes']
                friendly_icon = "✅" if is_question_friendly else "❌"

                print(f"\n📋 Contexte: {name}")
                print(f"   🏷️  Display Name: '{display_name}'")
                print(f"   🔤 Display Short: '{display_short}'")
                print(f"   ❓ Question Ready: {friendly_icon}")

    def debug_v4_metadata(self):
        """Debug des métadonnées V4 pour troubleshooting"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, enriched_metadata
                FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.version') = 'v4'
                ORDER BY name
                LIMIT 5
            """)

            contexts = cursor.fetchall()

            if not contexts:
                print("❌ Aucun contexte V4 trouvé pour debug")
                return

            print(f"\n🐛 DEBUG MÉTADONNÉES V4 (échantillon de {len(contexts)})")
            print("=" * 60)

            for ctx_id, name, metadata_str in contexts:
                print(f"\n📋 [{ctx_id}] {name}")
                print("-" * 40)

                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    print(json.dumps(metadata, indent=2, ensure_ascii=False))
                except json.JSONDecodeError as e:
                    print(f"❌ Erreur JSON: {e}")
                    print(f"Raw: {metadata_str}")


# ============================================================================
# MENU INTERFACE - Interface menu principal
# ============================================================================

def show_main_menu():
    """Affiche le menu principal"""
    print("\n" + "=" * 50)
    print("🃏 ENRICHISSEUR DE RANGES V4")
    print("=" * 50)
    print("1. 🚀 Enrichissement interactif")
    print("2. 📊 Résumé des enrichissements")
    print("3. 🏷️  Liste des noms d'affichage")
    print("4. 🐛 Debug métadonnées V4")
    print("5. 🚪 Quitter")
    print("=" * 50)


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée principal"""

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord le script d'import: python poker-training.py")
        return

    enricher = ConsoleRangeEnricherV4(db_path)

    while True:
        show_main_menu()

        try:
            choice = input("\nVotre choix (1-5): ").strip()

            if choice == "1":
                enricher.run_interactive_enrichment_v4()

            elif choice == "2":
                enricher.show_enrichment_summary_v4()

            elif choice == "3":
                enricher.list_display_names_v4()

            elif choice == "4":
                enricher.debug_v4_metadata()

            elif choice == "5":
                print("\n👋 À bientôt!")
                break

            else:
                print("❌ Choix invalide!")

        except KeyboardInterrupt:
            print("\n\n👋 À bientôt!")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            print("💡 Continuer avec le menu principal...")


if __name__ == "__main__":
    main()