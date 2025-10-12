"""
Module de validation et correction des métadonnées de contextes ET sous-ranges.
Gère la correction manuelle des contextes ambigus ou incomplets.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

# --- Helpers module-level : sûrs et indépendants de la classe ---

SR_CANON = {
    "open": "OPEN",
    "call": "CALL", "flat": "CALL", "complete": "CALL",
    "3bet value": "R3_VALUE", "value 3bet": "R3_VALUE", "3-bet value": "R3_VALUE",
    "3bet bluff": "R3_BLUFF", "3-bet bluff": "R3_BLUFF",
    "4bet value": "R4_VALUE", "4-bet value": "R4_VALUE",
    "4bet bluff": "R4_BLUFF", "4-bet bluff": "R4_BLUFF",
    "5bet": "R5_ALLIN", "5-bet": "R5_ALLIN", "all in": "R5_ALLIN", "allin": "R5_ALLIN",
    "iso raise value": "ISO_VALUE", "iso value": "ISO_VALUE",
    "iso raise bluff": "ISO_BLUFF", "iso bluff": "ISO_BLUFF",
    "check": "CHECK",
    "fold": "FOLD",
    "raise": "RAISE",
}

# Labels disponibles pour l'UI
SR_LABELS = {
    "OPEN": "Open",
    "CALL": "Call / Complete",
    "R3_VALUE": "3bet Value",
    "R3_BLUFF": "3bet Bluff",
    "R4_VALUE": "4bet Value",
    "R4_BLUFF": "4bet Bluff",
    "R5_ALLIN": "5bet / All-in",
    "ISO_VALUE": "Iso Value",
    "ISO_BLUFF": "Iso Bluff",
    "CHECK": "Check",
    "FOLD": "Fold",
    "RAISE": "Raise",
    "UNKNOWN": "Autre / À classifier"
}

# Cohérence : sous-ranges = réponses du héros aux réactions adverses
# Action principale = action initiale du héros
# Sous-ranges = comment le héros répond aux réactions adverses
EXPECTED_SUBRANGES = {
    "open": ["CALL", "R4_VALUE", "R4_BLUFF", "FOLD"],  # Face à 3bet après notre open
    "defense": ["CALL", "R3_VALUE", "R3_BLUFF", "FOLD"],  # Notre réponse à un open adverse
    "3bet": ["CALL", "R5_ALLIN", "FOLD"],  # Face à 4bet après notre 3bet
    "squeeze": ["CALL", "R5_ALLIN", "FOLD"],  # Face à 4bet après notre squeeze
    "4bet": ["CALL", "FOLD"],  # Face à 5bet (très rare)
    "call": [],  # Pas de sous-actions préflop après call
    "complete": ["CHECK", "RAISE", "FOLD"],  # BB face à raise SB après complete
    "check": [],  # Postflop
    "raise": ["CALL", "FOLD"],  # Face à reraise
    "fold": []  # Pas d'action après fold
}


def canon_sr(name: Optional[str]) -> str:
    """Normalise un libellé de sous-range en label canon."""
    if not name:
        return "UNKNOWN"
    key = name.strip().lower().replace("-", " ").replace("_", " ")
    return SR_CANON.get(key, "UNKNOWN")


def build_human_title_and_slug(row: Dict) -> Tuple[str, str]:
    """
    Produit un titre lisible et un slug stable à partir des colonnes déjà présentes.
    N'écrase pas display_name existant.
    """
    # Gestion sécurisée des None
    fmt = row.get("table_format")
    fmt = fmt.strip() if fmt else "5max"

    pos = row.get("hero_position")
    pos = pos.strip().upper() if pos else "UTG"

    action = row.get("primary_action")
    action = action.strip().lower() if action else "open"

    vs_pos = row.get("vs_position")
    vs_pos = vs_pos.strip().upper() if vs_pos else None

    depth = row.get("stack_depth")
    depth = depth.strip() if depth else "100bb"

    # Construction du contexte
    if action == "open":
        ctx = "Open"
    elif action in ("defense", "call") and vs_pos:
        ctx = f"Défense vs open {vs_pos}"
    elif action == "3bet" and vs_pos:
        ctx = f"3bet vs {vs_pos}"
    elif action == "4bet" and vs_pos:
        ctx = f"4bet vs {vs_pos}"
    elif action == "check":
        ctx = "Option (pot non relancé)"
    else:
        ctx = action.title() if action else "Contexte"

    human = f"{fmt} · {pos} · {ctx} · {depth}"

    # Construction du slug
    if action == "open":
        ctx_key = "open"
    elif action in ("defense", "call") and vs_pos:
        ctx_key = f"def-vs-open-{vs_pos.lower()}"
    elif action == "3bet" and vs_pos:
        ctx_key = f"r3-vs-{vs_pos.lower()}"
    elif action == "4bet" and vs_pos:
        ctx_key = f"r4-vs-{vs_pos.lower()}"
    else:
        ctx_key = "custom"

    slug = f"nlhe-{fmt.replace(' ', '').lower()}-{pos.lower()}-{ctx_key}-{depth.lower()}"
    slug = re.sub(r"[^a-z0-9\-\.]", "", slug)
    return human, slug


def summarize_subranges(rows: List[Dict]) -> Dict[str, int]:
    """ Agrège un résumé {label_canon: count} depuis les ranges associées. """
    summary: Dict[str, int] = {}
    for r in rows:
        canon = r.get("label_canon") or canon_sr(r.get("action") or r.get("name"))
        count = r.get("hand_count")
        try:
            n = int(count) if count is not None else 0
        except (TypeError, ValueError):
            n = 0
        summary[canon] = summary.get(canon, 0) + n
    return summary


def detect_inconsistencies(primary_action: str, subranges: List[Dict]) -> List[str]:
    """
    Détecte les incohérences entre l'action principale et les sous-ranges.

    Args:
        primary_action: Action principale du contexte
        subranges: Liste des sous-ranges avec leur label_canon

    Returns:
        Liste des messages d'avertissement
    """
    warnings = []

    # Gestion du cas où primary_action est None
    if not primary_action:
        warnings.append("⚠️ Action principale non définie pour ce contexte")
        return warnings

    expected = set(EXPECTED_SUBRANGES.get(primary_action.lower(), []))
    found = {sr.get("label_canon", "UNKNOWN") for sr in subranges}

    # Retirer UNKNOWN de la vérification
    found.discard("UNKNOWN")

    # Vérifier si des sous-ranges inattendus sont présents
    unexpected = found - expected
    if unexpected:
        labels = [SR_LABELS.get(u, u) for u in unexpected]
        warnings.append(
            f"ℹ️ Sous-ranges non standards pour '{primary_action}': {', '.join(labels)}. "
            f"Vérifiez qu'ils correspondent bien aux actions face aux réactions adverses."
        )

    return warnings


class ContextValidator:
    """Gère la validation et correction des métadonnées de contextes ET sous-ranges."""

    # Positions disponibles par format de table
    POSITIONS_BY_FORMAT = {
        '5max': ['UTG', 'CO', 'BTN', 'SB', 'BB'],
        '6max': ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'],
        '9max': ['UTG', 'UTG+1', 'MP', 'MP+1', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB'],
        'HU': ['BTN', 'BB']
    }

    # Actions principales disponibles
    PRIMARY_ACTIONS = [
        'open', 'call', '3bet', '4bet', 'fold',
        'check', 'defense', 'complete', 'raise', 'squeeze'
    ]

    def __init__(self, db_path: str = "../data/poker_trainer.db"):
        self.db_path = Path(db_path)
        # Ne plus lever d'exception si la base n'existe pas
        # Elle sera créée par le pipeline au premier import
        if not self.db_path.exists():
            print(f"[VALIDATOR] Base non trouvée (sera créée au premier import) : {db_path}")

    def get_context_for_validation(self, context_id: int) -> Optional[Dict]:
        """
        Récupère un contexte avec ses ranges pour validation.

        Args:
            context_id: ID du contexte à valider

        Returns:
            Dictionnaire avec les infos du contexte et ses ranges, ou None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Récupérer le contexte
            cursor.execute("""
                SELECT 
                    rc.id,
                    rc.original_name,
                    rc.display_name,
                    rc.table_format,
                    rc.hero_position,
                    rc.vs_position,
                    rc.primary_action,
                    rc.game_type,
                    rc.variant,
                    rc.stack_depth,
                    rc.stakes,
                    rc.sizing,
                    rc.confidence_score,
                    rc.needs_validation,
                    rc.quiz_ready,
                    rf.filename,
                    rf.file_path
                FROM range_contexts rc
                JOIN range_files rf ON rc.file_id = rf.id
                WHERE rc.id = ?
            """, (context_id,))

            context_row = cursor.fetchone()
            if not context_row:
                return None

            context = dict(context_row)

            # Récupérer les ranges associées SAUF la première (range principale)
            cursor.execute("""
                SELECT 
                    r.id,
                    r.name,
                    r.action,
                    r.label_canon,
                    r.color,
                    COUNT(rh.id) as hand_count
                FROM ranges r
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                  AND r.range_key != '1'  -- Exclure la range principale (index 1)
                GROUP BY r.id
                ORDER BY CAST(r.range_key AS INTEGER)
            """, (context_id,))

            ranges = [dict(row) for row in cursor.fetchall()]

            # Ajout label canon si absent ou recalcul si demandé
            for r in ranges:
                if not r.get("label_canon"):
                    r["label_canon"] = canon_sr(r.get("action") or r.get("name"))
                r["label_display"] = SR_LABELS.get(r["label_canon"], r["label_canon"])

            context["ranges"] = ranges

            # Titre humain + slug (n'écrase pas display_name)
            human, slug = build_human_title_and_slug(context)
            context["human_title"] = human
            context["slug"] = slug

            # Résumé par sous-range normalisé
            context["subranges_summary"] = summarize_subranges(ranges)

            # Détection d'incohérences
            context["warnings"] = detect_inconsistencies(
                context.get("primary_action", ""),
                ranges
            )

            # Labels disponibles pour l'édition
            context["available_labels"] = SR_LABELS

            return context

        finally:
            conn.close()

    def get_validation_candidates(self) -> List[Dict]:
        """
        Récupère tous les contextes nécessitant une validation.

        Returns:
            Liste de dictionnaires avec les contextes à valider
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT 
                    rc.id,
                    rc.original_name,
                    rc.display_name,
                    rc.table_format,
                    rc.hero_position,
                    rc.primary_action,
                    rc.confidence_score,
                    rf.filename,
                    COUNT(DISTINCT r.id) as range_count
                FROM range_contexts rc
                JOIN range_files rf ON rc.file_id = rf.id
                LEFT JOIN ranges r ON rc.id = r.context_id
                WHERE rc.needs_validation = 1 
                  AND rc.quiz_ready = 0
                GROUP BY rc.id
                ORDER BY rc.confidence_score ASC, rc.id
            """)

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def update_subrange_labels(
            self,
            range_labels: Dict[int, str]
    ) -> Tuple[bool, str]:
        """
        Met à jour les labels canoniques ET les noms des sous-ranges.

        Args:
            range_labels: Dictionnaire {range_id: label_canon}

        Returns:
            Tuple (succès, message)
        """
        # Mapping label_canon → nom lisible
        LABEL_TO_NAME = {
            "OPEN": "open",
            "CALL": "call",
            "R3_VALUE": "3bet_value",
            "R3_BLUFF": "3bet_bluff",
            "R4_VALUE": "4bet_value",
            "R4_BLUFF": "4bet_bluff",
            "R5_ALLIN": "5bet_allin",
            "ISO_VALUE": "iso_value",
            "ISO_BLUFF": "iso_bluff",
            "CHECK": "check",
            "FOLD": "fold",
            "RAISE": "raise",
            "UNKNOWN": "unknown"
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Vérifier que la colonne label_canon existe
            cursor.execute("PRAGMA table_info(ranges)")
            columns = [col[1] for col in cursor.fetchall()]

            if "label_canon" not in columns:
                # Créer la colonne si elle n'existe pas
                cursor.execute("""
                    ALTER TABLE ranges 
                    ADD COLUMN label_canon TEXT
                """)

            # Mettre à jour chaque range (label ET nom)
            for range_id, label_canon in range_labels.items():
                if label_canon not in SR_LABELS:
                    return False, f"Label invalide: {label_canon}"

                # Générer le nouveau nom
                new_name = LABEL_TO_NAME.get(label_canon, label_canon.lower())

                cursor.execute("""
                    UPDATE ranges 
                    SET label_canon = ?,
                        name = ?,
                        action = ?
                    WHERE id = ?
                """, (label_canon, new_name, new_name, range_id))

            conn.commit()
            return True, f"{len(range_labels)} sous-ranges mis à jour"

        except Exception as e:
            conn.rollback()
            return False, f"Erreur lors de la mise à jour: {str(e)}"
        finally:
            conn.close()

    def validate_and_update(
            self,
            context_id: int,
            metadata: Dict[str, Optional[str]],
            range_labels: Optional[Dict[int, str]] = None
    ) -> Tuple[bool, str]:
        """
        Valide et met à jour les métadonnées d'un contexte ET ses sous-ranges.

        Args:
            context_id: ID du contexte à mettre à jour
            metadata: Dictionnaire des métadonnées validées
            range_labels: Dictionnaire optionnel {range_id: label_canon} pour corriger les sous-ranges

        Returns:
            Tuple (succès, message)
        """
        # Validation des champs obligatoires
        required = ['table_format', 'hero_position', 'primary_action']
        missing = [f for f in required if not metadata.get(f)]

        if missing:
            return False, f"Champs obligatoires manquants : {', '.join(missing)}"

        # Vérifier cohérence format table / position
        table_format = metadata['table_format']
        hero_position = metadata['hero_position']

        if table_format not in self.POSITIONS_BY_FORMAT:
            return False, f"Format de table invalide : {table_format}"

        if hero_position not in self.POSITIONS_BY_FORMAT[table_format]:
            return False, f"Position {hero_position} invalide pour format {table_format}"

        # Vérifier vs_position si présente
        vs_position = metadata.get('vs_position')
        if vs_position and vs_position != 'N/A':
            if vs_position not in self.POSITIONS_BY_FORMAT[table_format]:
                return False, f"Position adversaire {vs_position} invalide pour format {table_format}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Mettre à jour les sous-ranges d'abord si fournis
            if range_labels:
                success, msg = self.update_subrange_labels(range_labels)
                if not success:
                    conn.rollback()
                    return False, f"Erreur sous-ranges: {msg}"

            # 🆕 Mettre à jour le label_canon de la range principale si primary_action a changé
            new_primary_action = metadata['primary_action']

            # Récupérer la range principale actuelle
            cursor.execute("""
                SELECT name, label_canon 
                FROM ranges 
                WHERE context_id = ? AND range_key = '1'
            """, (context_id,))

            main_range_result = cursor.fetchone()
            if main_range_result:
                range_name, current_label = main_range_result

                # Calculer le nouveau label_canon basé sur le primary_action
                # Import de la fonction depuis database_manager
                from database_manager import map_name_to_label_canon

                new_label = map_name_to_label_canon(range_name, '1', new_primary_action)

                if new_label and new_label != current_label:
                    cursor.execute("""
                        UPDATE ranges 
                        SET label_canon = ? 
                        WHERE context_id = ? AND range_key = '1'
                    """, (new_label, context_id))

                    print(
                        f"[VALIDATOR] Range principale mise à jour: '{current_label}' → '{new_label}' (primary_action: {new_primary_action})")

            # Générer le display_name
            display_name = self._generate_display_name(metadata)

            # Vérifier si tous les sous-ranges ont des labels valides
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ranges 
                WHERE context_id = ? 
                  AND range_key != '1'
                  AND (label_canon IS NULL OR label_canon = 'UNKNOWN' OR label_canon = '')
            """, (context_id,))

            incomplete_subranges = cursor.fetchone()[0]

            # Le contexte est quiz_ready seulement si :
            # 1. Métadonnées validées (on y est)
            # 2. TOUS les sous-ranges ont des labels valides
            quiz_ready = 1 if incomplete_subranges == 0 else 0
            needs_validation = 1 if incomplete_subranges > 0 else 0

            # Calculer le score de confiance
            if incomplete_subranges == 0:
                confidence_score = 100
            else:
                # Score partiel basé sur le % de sous-ranges complétés
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ranges 
                    WHERE context_id = ? 
                      AND range_key != '1'
                """, (context_id,))
                total_subranges = cursor.fetchone()[0]

                if total_subranges > 0:
                    completed = total_subranges - incomplete_subranges
                    confidence_score = int((completed / total_subranges) * 100)
                else:
                    confidence_score = 100

            # Mettre à jour le contexte
            cursor.execute("""
                UPDATE range_contexts
                SET 
                    table_format = ?,
                    hero_position = ?,
                    vs_position = ?,
                    primary_action = ?,
                    game_type = ?,
                    variant = ?,
                    stack_depth = ?,
                    stakes = ?,
                    sizing = ?,
                    display_name = ?,
                    needs_validation = ?,
                    quiz_ready = ?,
                    confidence_score = ?
                WHERE id = ?
            """, (
                metadata['table_format'],
                metadata['hero_position'],
                metadata.get('vs_position') or None,
                metadata['primary_action'],
                metadata.get('game_type', 'Cash Game'),
                metadata.get('variant', 'NLHE'),
                metadata.get('stack_depth', '100bb'),
                metadata.get('stakes') or None,
                metadata.get('sizing') or None,
                display_name,
                needs_validation,
                quiz_ready,
                confidence_score,
                context_id
            ))

            conn.commit()

            # Message adapté
            if quiz_ready == 1:
                subrange_msg = f" + {len(range_labels)} sous-ranges" if range_labels else ""
                return True, f"Contexte validé{subrange_msg} : {display_name}"
            else:
                return True, f"Contexte partiellement validé ({confidence_score}%) - {incomplete_subranges} sous-ranges à classifier : {display_name}"

        except Exception as e:
            conn.rollback()
            import traceback
            traceback.print_exc()
            return False, f"Erreur lors de la mise à jour : {str(e)}"

        finally:
            conn.close()
    def _generate_display_name(self, metadata: Dict[str, Optional[str]]) -> str:
        """
        Génère un nom d'affichage depuis les métadonnées validées.

        Args:
            metadata: Métadonnées du contexte

        Returns:
            Nom d'affichage formaté
        """
        parts = []

        # Format de table
        parts.append(metadata['table_format'])

        # Position héros
        parts.append(metadata['hero_position'])

        # Action
        action = metadata['primary_action'].title()
        parts.append(action)

        # Vs position si présente
        vs_pos = metadata.get('vs_position')
        if vs_pos and vs_pos != 'N/A':
            parts.append(f"vs {vs_pos}")

        # Sizing si présent
        sizing = metadata.get('sizing')
        if sizing:
            parts.append(f"({sizing})")

        return " ".join(parts)

    def mark_as_non_exploitable(self, context_id: int, reason: str = None) -> bool:
        """
        Marque un contexte comme non exploitable.

        Args:
            context_id: ID du contexte
            reason: Raison optionnelle

        Returns:
            Succès de l'opération
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE range_contexts
                SET 
                    needs_validation = 0,
                    quiz_ready = 0,
                    error_message = ?
                WHERE id = ?
            """, (reason, context_id))

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            return False

        finally:
            conn.close()