#!/usr/bin/env python3
"""
Système de validation multi-niveaux pour l'enrichissement des ranges
Valide en temps réel, par contexte, et globalement
"""

import json
import sqlite3
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Réutilise les classes de l'enrichisseur
from pathlib import Path


# ============================================================================
# VALIDATION MODELS - Structures pour la validation
# ============================================================================

class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Un problème de validation détecté"""
    level: ValidationLevel
    category: str
    message: str
    context_id: Optional[int] = None
    context_name: Optional[str] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Rapport de validation complet"""
    total_contexts: int
    validated_contexts: int
    issues: List[ValidationIssue]
    global_score: float
    context_scores: Dict[int, float]
    timestamp: str


# ============================================================================
# VALIDATORS - Validateurs spécialisés
# ============================================================================

class LogicalValidator:
    """Valide la cohérence logique des métadonnées"""

    def validate_metadata(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide un contexte et retourne les problèmes trouvés"""
        issues = []

        # Validation des positions
        issues.extend(self._validate_positions(metadata, context_name, context_id))

        # Validation action-sizing
        issues.extend(self._validate_action_sizing(metadata, context_name, context_id))

        # Validation action-vs_position
        issues.extend(self._validate_action_vs_position(metadata, context_name, context_id))

        # Validation stack depth
        issues.extend(self._validate_stack_depth(metadata, context_name, context_id))

        # Validation format cohérence
        issues.extend(self._validate_format_consistency(metadata, context_name, context_id))

        return issues

    def _validate_positions(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide les positions"""
        issues = []

        hero_pos = metadata.get('hero_position')
        vs_pos = metadata.get('vs_position')

        # Position héros obligatoire
        if not hero_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="position",
                message="Position héros manquante",
                context_id=context_id,
                context_name=context_name,
                field="hero_position",
                suggestion="Spécifier la position du joueur"
            ))

        # Héros ≠ adversaire
        if hero_pos and vs_pos and hero_pos == vs_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                category="position",
                message=f"Position héros et adversaire identiques ({hero_pos})",
                context_id=context_id,
                context_name=context_name,
                field="vs_position",
                suggestion="Vérifier qui est le héros et qui est l'adversaire"
            ))

        # Vérifier ordre logique des positions
        if hero_pos and vs_pos:
            if not self._is_position_order_logical(hero_pos, vs_pos, metadata.get('primary_action')):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="position",
                    message=f"Ordre des positions inhabituel: {hero_pos} vs {vs_pos}",
                    context_id=context_id,
                    context_name=context_name,
                    field="vs_position",
                    suggestion="Vérifier l'ordre d'action au poker"
                ))

        return issues

    def _validate_action_sizing(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide cohérence action-sizing"""
        issues = []

        action = metadata.get('primary_action')
        sizing = metadata.get('sizing')

        # Actions qui ne devraient pas avoir de sizing
        passive_actions = ['call', 'check', 'fold']
        if action in passive_actions and sizing:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="action",
                message=f"Action '{action}' avec sizing '{sizing}' (inhabituel)",
                context_id=context_id,
                context_name=context_name,
                field="sizing",
                suggestion="Les actions passives n'ont généralement pas de sizing"
            ))

        # Actions qui devraient avoir un sizing
        active_actions = ['open', '3bet', '4bet']
        if action in active_actions and not sizing:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                category="action",
                message=f"Action '{action}' sans sizing spécifié",
                context_id=context_id,
                context_name=context_name,
                field="sizing",
                suggestion="Préciser le sizing (ex: 2.5x, 3bb)"
            ))

        return issues

    def _validate_action_vs_position(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide cohérence action-vs_position"""
        issues = []

        action = metadata.get('primary_action')
        vs_pos = metadata.get('vs_position')

        # Actions réactives qui devraient avoir un vs_position
        reactive_actions = ['call', 'defense', '3bet', '4bet']
        if action in reactive_actions and not vs_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="action",
                message=f"Action réactive '{action}' sans adversaire spécifié",
                context_id=context_id,
                context_name=context_name,
                field="vs_position",
                suggestion="Spécifier contre quelle position cette action est utilisée"
            ))

        # Actions initiales qui ne devraient pas avoir de vs_position
        if action == 'open' and vs_pos:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                category="action",
                message=f"Action 'open' avec vs_position '{vs_pos}' (inhabituel)",
                context_id=context_id,
                context_name=context_name,
                field="vs_position",
                suggestion="L'open est généralement une action initiale"
            ))

        return issues

    def _validate_stack_depth(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide la stack depth"""
        issues = []

        stack = metadata.get('stack_depth')
        action = metadata.get('primary_action')

        # Stack depth obligatoire
        if not stack:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="stack",
                message="Stack depth non spécifiée",
                context_id=context_id,
                context_name=context_name,
                field="stack_depth",
                suggestion="La stack depth influence significativement les ranges"
            ))

        # Vérifier cohérence stack-action
        if stack and action:
            if stack.startswith('20-40bb') and action in ['4bet', '5bet']:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="stack",
                    message=f"Stack courte ({stack}) avec action '{action}' (rare)",
                    context_id=context_id,
                    context_name=context_name,
                    field="stack_depth",
                    suggestion="Vérifier si cette situation est réaliste"
                ))

        return issues

    def _validate_format_consistency(self, metadata: Dict, context_name: str, context_id: int) -> List[ValidationIssue]:
        """Valide la cohérence des formats"""
        issues = []

        game_format = metadata.get('game_format')
        variant = metadata.get('variant')
        table_format = metadata.get('table_format')

        # Vérifier cohérence game_format-stack_depth
        stack = metadata.get('stack_depth')
        if game_format == 'tournament' and stack and 'bb' in stack:
            try:
                bb_value = int(stack.replace('bb', '').split('-')[0])
                if bb_value > 200:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.INFO,
                        category="format",
                        message=f"Tournoi avec stack profonde ({stack})",
                        context_id=context_id,
                        context_name=context_name,
                        field="stack_depth",
                        suggestion="Vérifier si c'est en début de tournoi"
                    ))
            except:
                pass

        return issues

    def _is_position_order_logical(self, hero_pos: str, vs_pos: str, action: str) -> bool:
        """Vérifie si l'ordre des positions est logique"""
        # Ordre des positions au poker
        position_order = ['UTG', 'UTG+1', 'MP', 'MP+1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB']

        try:
            hero_idx = position_order.index(hero_pos)
            vs_idx = position_order.index(vs_pos)

            # Pour les actions réactives, le héros devrait agir après l'adversaire
            if action in ['call', '3bet', 'defense']:
                return hero_idx > vs_idx or (hero_pos in ['SB', 'BB'] and vs_pos == 'BTN')

            return True  # Autres cas considérés comme OK
        except ValueError:
            return True  # Position non reconnue, pas de validation


class GlobalValidator:
    """Valide la cohérence globale entre tous les contextes"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_global_consistency(self) -> List[ValidationIssue]:
        """Valide la cohérence globale"""
        issues = []

        contexts = self._get_all_enriched_contexts()

        if not contexts:
            return issues

        # Validation format global
        issues.extend(self._validate_global_formats(contexts))

        # Validation completeness
        issues.extend(self._validate_completeness(contexts))

        # Validation range coverage
        issues.extend(self._validate_range_coverage(contexts))

        return issues

    def _get_all_enriched_contexts(self) -> List[Dict]:
        """Récupère tous les contextes enrichis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, enriched_metadata 
                FROM range_contexts 
                WHERE json_extract(enriched_metadata, '$.enriched_by_user') = 'true'
            """)

            contexts = []
            for row in cursor.fetchall():
                contexts.append({
                    'id': row[0],
                    'name': row[1],
                    'metadata': json.loads(row[2])
                })
            return contexts

    def _validate_global_formats(self, contexts: List[Dict]) -> List[ValidationIssue]:
        """Valide la cohérence des formats globaux"""
        issues = []

        # Vérifier cohérence game_format
        game_formats = [ctx['metadata'].get('game_format') for ctx in contexts]
        unique_formats = set(filter(None, game_formats))

        if len(unique_formats) > 1:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="global",
                message=f"Formats de jeu mixtes: {', '.join(unique_formats)}",
                suggestion="Vérifier si c'est intentionnel ou erreur de saisie"
            ))

        # Vérifier cohérence variant
        variants = [ctx['metadata'].get('variant') for ctx in contexts]
        unique_variants = set(filter(None, variants))

        if len(unique_variants) > 1:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                category="global",
                message=f"Variantes mixtes: {', '.join(unique_variants)}",
                suggestion="Normal si vous jouez plusieurs variantes"
            ))

        return issues

    def _validate_completeness(self, contexts: List[Dict]) -> List[ValidationIssue]:
        """Valide la complétude des métadonnées"""
        issues = []

        # Champs essentiels
        essential_fields = ['hero_position', 'primary_action', 'stack_depth']

        for field in essential_fields:
            missing_count = sum(1 for ctx in contexts if not ctx['metadata'].get(field))
            if missing_count > 0:
                percentage = (missing_count / len(contexts)) * 100
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING if percentage > 20 else ValidationLevel.INFO,
                    category="completeness",
                    message=f"Champ '{field}' manquant dans {missing_count}/{len(contexts)} contextes ({percentage:.1f}%)",
                    suggestion=f"Compléter le champ '{field}' pour une meilleure qualité"
                ))

        return issues

    def _validate_range_coverage(self, contexts: List[Dict]) -> List[ValidationIssue]:
        """Valide la couverture des ranges (détecte les manques)"""
        issues = []

        # Analyser les positions couvertes
        positions = [ctx['metadata'].get('hero_position') for ctx in contexts]
        position_counts = {}
        for pos in positions:
            if pos:
                position_counts[pos] = position_counts.get(pos, 0) + 1

        # Détecter positions sous-représentées
        if position_counts:
            avg_count = sum(position_counts.values()) / len(position_counts)
            for pos, count in position_counts.items():
                if count < avg_count * 0.5:  # Moins de 50% de la moyenne
                    issues.append(ValidationIssue(
                        level=ValidationLevel.INFO,
                        category="coverage",
                        message=f"Position '{pos}' sous-représentée ({count} contextes)",
                        suggestion="Considérer ajouter plus de ranges pour cette position"
                    ))

        return issues


# ============================================================================
# VALIDATION MANAGER - Orchestrateur principal
# ============================================================================

class ValidationManager:
    """Gestionnaire principal du système de validation"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logical_validator = LogicalValidator()
        self.global_validator = GlobalValidator(db_path)

    def validate_single_context(self, context_id: int, metadata: Dict, context_name: str) -> Tuple[
        List[ValidationIssue], float]:
        """Valide un contexte unique"""
        issues = self.logical_validator.validate_metadata(metadata, context_name, context_id)
        score = self._calculate_context_score(metadata, issues)
        return issues, score

    def validate_all_contexts(self) -> ValidationReport:
        """Valide tous les contextes enrichis"""

        # Récupérer tous les contextes
        contexts = self._get_enriched_contexts()

        all_issues = []
        context_scores = {}

        # Valider chaque contexte
        for ctx in contexts:
            ctx_id = ctx['id']
            ctx_name = ctx['name']
            metadata = ctx['metadata']

            issues, score = self.validate_single_context(ctx_id, metadata, ctx_name)
            all_issues.extend(issues)
            context_scores[ctx_id] = score

        # Validation globale
        global_issues = self.global_validator.validate_global_consistency()
        all_issues.extend(global_issues)

        # Calculer score global
        global_score = self._calculate_global_score(context_scores, global_issues)

        return ValidationReport(
            total_contexts=len(contexts),
            validated_contexts=len([s for s in context_scores.values() if s > 0.5]),
            issues=all_issues,
            global_score=global_score,
            context_scores=context_scores,
            timestamp=datetime.now().isoformat()
        )

    def _get_enriched_contexts(self) -> List[Dict]:
        """Récupère les contextes enrichis (version robuste corrigée)"""
        with sqlite3.connect(self.db_path) as conn:
            # Essayer plusieurs critères pour trouver les contextes enrichis
            queries = [
                # Critère principal: marqué comme enrichi par utilisateur (boolean)
                """SELECT id, name, enriched_metadata 
                   FROM range_contexts 
                   WHERE json_extract(enriched_metadata, '$.enriched_by_user') = true""",

                # Critère alternatif: marqué comme enrichi (string)
                """SELECT id, name, enriched_metadata 
                   FROM range_contexts 
                   WHERE json_extract(enriched_metadata, '$.enriched_by_user') = 'true'""",

                # Critère: métadonnées non vides avec champs essentiels
                """SELECT id, name, enriched_metadata 
                   FROM range_contexts 
                   WHERE enriched_metadata != '{}' 
                   AND enriched_metadata IS NOT NULL 
                   AND enriched_metadata != ''
                   AND json_extract(enriched_metadata, '$.hero_position') IS NOT NULL""",

                # Critère: confiance > 0.5 avec métadonnées
                """SELECT id, name, enriched_metadata 
                   FROM range_contexts 
                   WHERE confidence > 0.5
                   AND enriched_metadata != '{}'
                   AND json_extract(enriched_metadata, '$.hero_position') IS NOT NULL"""
            ]

            for i, query in enumerate(queries):
                try:
                    cursor = conn.execute(query)
                    contexts = []

                    for row in cursor.fetchall():
                        try:
                            metadata = json.loads(row[2]) if row[2] else {}
                            # Vérifier que les métadonnées contiennent des données utiles
                            if metadata and metadata.get('hero_position'):
                                contexts.append({
                                    'id': row[0],
                                    'name': row[1],
                                    'metadata': metadata
                                })
                        except json.JSONDecodeError:
                            continue

                    if contexts:
                        if i > 0:  # Si on a dû utiliser un critère alternatif
                            print(f"ℹ️  Critère {i + 1} utilisé: {len(contexts)} contextes trouvés")
                        return contexts

                except Exception as e:
                    print(f"⚠️  Erreur requête {i + 1}: {e}")
                    continue

            # Si aucune requête n'a fonctionné, retourner liste vide
            print("⚠️  Aucun contexte enrichi trouvé avec tous les critères")
            return []

    def _calculate_context_score(self, metadata: Dict, issues: List[ValidationIssue]) -> float:
        """Calcule le score de qualité d'un contexte"""
        base_score = 1.0

        # Pénalités selon le niveau des problèmes
        for issue in issues:
            if issue.level == ValidationLevel.CRITICAL:
                base_score -= 0.3
            elif issue.level == ValidationLevel.ERROR:
                base_score -= 0.2
            elif issue.level == ValidationLevel.WARNING:
                base_score -= 0.1
            elif issue.level == ValidationLevel.INFO:
                base_score -= 0.05

        # Bonus pour complétude
        essential_fields = ['hero_position', 'primary_action', 'stack_depth', 'game_format', 'variant']
        completeness = sum(1 for field in essential_fields if metadata.get(field)) / len(essential_fields)

        final_score = max(0.0, base_score * completeness)
        return min(1.0, final_score)

    def _calculate_global_score(self, context_scores: Dict[int, float], global_issues: List[ValidationIssue]) -> float:
        """Calcule le score global"""
        if not context_scores:
            return 0.0

        # Score moyen des contextes
        avg_context_score = sum(context_scores.values()) / len(context_scores)

        # Pénalités globales
        global_penalty = 0.0
        for issue in global_issues:
            if issue.level == ValidationLevel.CRITICAL:
                global_penalty += 0.2
            elif issue.level == ValidationLevel.ERROR:
                global_penalty += 0.1
            elif issue.level == ValidationLevel.WARNING:
                global_penalty += 0.05

        return max(0.0, avg_context_score - global_penalty)

    def display_validation_report(self, report: ValidationReport):
        """Affiche un rapport de validation formaté"""

        print("\n" + "=" * 60)
        print("📊 RAPPORT DE VALIDATION MULTI-NIVEAUX")
        print("=" * 60)

        # Score global
        score_color = "🟢" if report.global_score > 0.8 else "🟡" if report.global_score > 0.6 else "🔴"
        print(f"\n{score_color} SCORE GLOBAL: {report.global_score:.1%}")
        print(f"📋 Contextes validés: {report.validated_contexts}/{report.total_contexts}")

        # Résumé des problèmes par niveau
        issues_by_level = {}
        for issue in report.issues:
            level = issue.level.value
            issues_by_level[level] = issues_by_level.get(level, 0) + 1

        if issues_by_level:
            print(f"\n⚠️  PROBLÈMES DÉTECTÉS:")
            for level, count in sorted(issues_by_level.items()):
                emoji = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "ℹ️"}.get(level, "❓")
                print(f"   {emoji} {level.title()}: {count}")
        else:
            print(f"\n✅ Aucun problème détecté!")

        # Top 5 des problèmes les plus critiques
        critical_issues = [i for i in report.issues if i.level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]]
        if critical_issues:
            print(f"\n🔥 PROBLÈMES PRIORITAIRES:")
            for i, issue in enumerate(critical_issues[:5], 1):
                print(f"   {i}. {issue.context_name}: {issue.message}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")

        # Contextes avec scores les plus bas
        low_score_contexts = [(ctx_id, score) for ctx_id, score in report.context_scores.items() if score < 0.7]
        if low_score_contexts:
            print(f"\n📉 CONTEXTES À REVOIR:")
            low_score_contexts.sort(key=lambda x: x[1])
            for ctx_id, score in low_score_contexts[:3]:
                ctx_name = self._get_context_name(ctx_id)
                print(f"   • {ctx_name}: {score:.1%}")

        print(f"\n🕒 Rapport généré le: {report.timestamp}")

    def _get_context_name(self, context_id: int) -> str:
        """Récupère le nom d'un contexte"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM range_contexts WHERE id = ?", (context_id,))
            row = cursor.fetchone()
            return row[0] if row else f"Contexte {context_id}"

    def interactive_validation_review(self):
        """Mode interactif pour réviser les problèmes de validation"""
        report = self.validate_all_contexts()
        self.display_validation_report(report)

        if not report.issues:
            print("\n🎉 Félicitations ! Toutes vos ranges sont parfaitement validées.")
            return

        print(f"\n🔧 MODE RÉVISION INTERACTIVE")

        # Grouper les problèmes par contexte
        issues_by_context = {}
        for issue in report.issues:
            if issue.context_id:
                if issue.context_id not in issues_by_context:
                    issues_by_context[issue.context_id] = []
                issues_by_context[issue.context_id].append(issue)

        # Proposer révision des contextes problématiques
        for ctx_id, issues in issues_by_context.items():
            ctx_name = self._get_context_name(ctx_id)
            score = report.context_scores.get(ctx_id, 0)

            if score < 0.8:  # Seuil de révision
                print(f"\n{'=' * 40}")
                print(f"📋 {ctx_name} (Score: {score:.1%})")
                print(f"{'=' * 40}")

                for issue in issues:
                    level_emoji = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "ℹ️"}
                    print(f"{level_emoji.get(issue.level.value, '❓')} {issue.message}")
                    if issue.suggestion:
                        print(f"   💡 {issue.suggestion}")

                choice = input("\n🔧 Corriger ce contexte ? (o/n/q pour quitter): ").strip().lower()
                if choice == 'q':
                    break
                elif choice == 'o':
                    print("💡 Relancez l'enrichisseur pour corriger ce contexte")


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée pour la validation"""
    print("🔍 SYSTÈME DE VALIDATION MULTI-NIVEAUX")
    print("=" * 50)

    db_path = "data/poker_trainer.db"

    if not Path(db_path).exists():
        print("❌ Base de données non trouvée!")
        print("💡 Lancez d'abord l'import et l'enrichissement")
        return

    validator = ValidationManager(db_path)

    print("Choisissez une option:")
    print("1. Rapport de validation complet")
    print("2. Révision interactive des problèmes")
    print("3. Validation en continu (mode développeur)")

    choice = input("\nVotre choix (1-3): ").strip()

    if choice == "1":
        report = validator.validate_all_contexts()
        validator.display_validation_report(report)

    elif choice == "2":
        validator.interactive_validation_review()

    elif choice == "3":
        print("🔄 Mode validation continue activé")
        print("💡 Cette fonctionnalité sera intégrée à l'enrichisseur")

    else:
        print("❌ Choix invalide")


if __name__ == "__main__":
    main()