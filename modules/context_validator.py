"""
Module de validation et correction des métadonnées de contextes.
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
    "iso raise value": "ISO_VALUE", "iso value": "ISO_VALUE",
    "iso raise bluff": "ISO_BLUFF", "iso bluff": "ISO_BLUFF",
    "check": "CHECK",
}

def canon_sr(name: Optional[str]) -> str:
    """Normalise un libellé de sous-range en label canon."""
    if not name:
        return "UNKNOWN"
    key = name.strip().lower().replace("-", " ").replace("_", " ")
    return SR_CANON.get(key, name.upper())

def build_human_title_and_slug(row: Dict) -> Tuple[str, str]:
    """
    Produit un titre lisible et un slug stable à partir des colonnes déjà présentes.
    N'écrase pas display_name existant.
    """
    fmt = (row.get("table_format") or "").strip() or "5max"
    pos = (row.get("hero_position") or "").strip().upper() or "UTG"
    action = (row.get("primary_action") or "").strip().lower() or "open"
    vs_pos = (row.get("vs_position") or "").strip().upper()
    depth = (row.get("stack_depth") or "").strip() or "100bb"

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
    ctx_key = (
        "open" if action == "open" else
        (f"def-vs-open-{vs_pos.lower()}" if action in ("defense","call") and vs_pos else
         f"r3-vs-{vs_pos.lower()}" if action == "3bet" and vs_pos else
         f"r4-vs-{vs_pos.lower()}" if action == "4bet" and vs_pos else
         "custom")
    )
    slug = f"nlhe-{fmt.replace(' ', '').lower()}-{pos.lower()}-{ctx_key}-{depth.lower()}"
    slug = re.sub(r"[^a-z0-9\-\.]", "", slug)
    return human, slug

def summarize_subranges(rows: List[Dict]) -> Dict[str, int]:
    """ Agrège un résumé {label_canon: count} depuis les ranges associées. """
    summary: Dict[str, int] = {}
    for r in rows:
        canon = canon_sr(r.get("action") or r.get("name"))
        count = r.get("hand_count")
        try:
            n = int(count) if count is not None else 0
        except (TypeError, ValueError):
            n = 0
        summary[canon] = summary.get(canon, 0) + n
    return summary


class ContextValidator:
    """Gère la validation et correction des métadonnées de contextes."""

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
        'check', 'defense', 'complete', 'raise'
    ]

    # Situations types
    SITUATIONS = [
        'Premier à parler',
        'Face à ouverture',
        'Face à 3bet',
        'Face à 4bet',
        'Defense blinds',
        'Squeeze',
        'Limp derrière'
    ]

    def __init__(self, db_path: str = "../data/poker_trainer.db"):
        """
        Initialise le validateur.

        Args:
            db_path: Chemin vers la base de données SQLite
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Base de données non trouvée : {db_path}")

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

            # Récupérer les ranges associées
            cursor.execute("""
                SELECT 
                    r.id,
                    r.name,
                    r.action,
                    r.color,
                    COUNT(rh.id) as hand_count
                FROM ranges r
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                GROUP BY r.id
                ORDER BY r.name
            """, (context_id,))

            ranges = [dict(row) for row in cursor.fetchall()]

            # Ajout non intrusif : label canon pour chaque sous-range
            for r in ranges:
                r["label_canon"] = canon_sr(r.get("action") or r.get("name"))
            context["ranges"] = ranges

            # Titre humain + slug (n'écrase pas display_name)
            human, slug = build_human_title_and_slug(context)
            context["human_title"] = human
            context["slug"] = slug

            # Résumé par sous-range normalisé
            context["subranges_summary"] = summarize_subranges(ranges)

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

    def validate_and_update(
            self,
            context_id: int,
            metadata: Dict[str, Optional[str]]
    ) -> Tuple[bool, str]:
        """
        Valide et met à jour les métadonnées d'un contexte.

        Args:
            context_id: ID du contexte à mettre à jour
            metadata: Dictionnaire des métadonnées validées

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
            # Générer le display_name
            display_name = self._generate_display_name(metadata)

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
                    needs_validation = 0,
                    quiz_ready = 1,
                    confidence_score = 100
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
                context_id
            ))

            conn.commit()
            return True, f"Contexte validé avec succès : {display_name}"

        except Exception as e:
            conn.rollback()
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
