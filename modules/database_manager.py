#!/usr/bin/env python3
"""
Module de gestion de la base de données SQLite
Gère la persistance des contextes, ranges et mains avec transactions sécurisées
Version 4.1 :
- Amélioration détection automatique + validation cohérence positions
- Support limpers_count pour vs_limpers
- Validations optionnelles (ranges génériques permises)
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from dataclasses import asdict
from quiz_action_mapper import QuizActionMapper


def map_name_to_label_canon(name: str, range_key: str, primary_action: str = None) -> str:
    """
    Mappe un nom de range vers un label_canon standardisé.

    Args:
        name: Nom de la range (ex: 'open_utg', 'call', '4bet_value')
        range_key: Clé de la range ('1' pour principale, autre pour sous-ranges)
        primary_action: Action principale du contexte (ex: 'defense', 'open', 'squeeze')

    Returns:
        Label canonique (OPEN, CALL, R4_VALUE, DEFENSE, SQUEEZE, etc.)
    """
    if not name:
        return None

    name_lower = name.lower()

    # Pour la range principale (range_key='1')
    if range_key == '1':
        # 🎯 PRIORITÉ 1 : Utiliser primary_action du contexte
        if primary_action:
            primary_lower = primary_action.lower()

            if primary_lower == 'defense':
                return 'DEFENSE'
            elif primary_lower == 'open':
                return 'OPEN'
            elif primary_lower == 'squeeze':
                return 'SQUEEZE'
            elif primary_lower == 'vs_limpers':
                if 'iso' in name_lower:
                    return 'ISO'
                return 'RAISE'
            elif primary_lower == 'check':
                return 'CHECK'

        # 🎯 PRIORITÉ 2 : Analyser le nom si primary_action absent/ambigu
        # Ordre important : squeeze AVANT 3bet !
        if 'squeeze' in name_lower or 'squezze' in name_lower:
            return 'SQUEEZE'
        elif 'open' in name_lower:
            return 'OPEN'
        elif 'defense' in name_lower or 'defend' in name_lower:
            return 'DEFENSE'
        elif '3bet' in name_lower or '3-bet' in name_lower:
            return '3BET'
        elif '4bet' in name_lower:
            return '4BET'
        elif 'iso' in name_lower or 'limper' in name_lower:
            return 'ISO'
        elif 'call' in name_lower:
            return 'CALL'
        elif 'raise' in name_lower:
            return 'RAISE'
        elif 'check' in name_lower:
            return 'CHECK'
        else:
            # Fallback : utiliser QuizActionMapper
            from quiz_action_mapper import QuizActionMapper
            quiz_action = QuizActionMapper.detect(name)
            if quiz_action and quiz_action != 'UNKNOWN':
                return quiz_action
            return None

    # Pour les sous-ranges, mapping standard (inchangé)
    if 'call' in name_lower or 'overcall' in name_lower:
        return 'CALL'
    elif '4bet' in name_lower or '4-bet' in name_lower:
        if 'value' in name_lower:
            return 'R4_VALUE'
        elif 'bluff' in name_lower:
            return 'R4_BLUFF'
        else:
            return '4BET'
    elif '3bet' in name_lower or '3-bet' in name_lower or 'squeeze' in name_lower:
        if 'value' in name_lower:
            return 'R3_VALUE'
        elif 'bluff' in name_lower:
            return 'R3_BLUFF'
        else:
            return '3BET'
    elif '5bet' in name_lower or 'allin' in name_lower or 'all-in' in name_lower:
        return 'R5_ALLIN'
    elif 'iso' in name_lower:
        if 'value' in name_lower:
            return 'ISO_VALUE'
        elif 'bluff' in name_lower:
            return 'ISO_BLUFF'
        else:
            return 'ISO'
    elif 'check' in name_lower:
        return 'CHECK'
    elif 'raise' in name_lower:
        return 'RAISE'
    else:
        return None


def generate_action_sequence(label_canon: str, primary_action: str, range_key: str) -> str:
    """
    Génère la séquence d'actions pour le quiz à partir du label_canon et du contexte.

    Args:
        label_canon: Label canonique (OPEN, CALL, R4_VALUE, etc.)
        primary_action: Action principale du contexte (open, defense, squeeze, vs_limpers)
        range_key: Clé de la range ('1' pour principale, autre pour sous-ranges)

    Returns:
        Séquence d'actions sous forme de string (ex: "RAISE→CALL", "RAISE→RAISE→RAISE/CALL")
    """
    if not label_canon or label_canon == 'UNKNOWN' or label_canon == 'None':
        return None

    # Range principale : généralement pas de quiz direct
    if range_key == '1':
        return None

    # Logique selon le contexte
    if primary_action == 'open':
        # Sous-ranges face à un 3bet (on a déjà open avant)
        if label_canon == 'CALL':
            return 'RAISE→CALL'
        elif label_canon == 'R4_VALUE':
            return 'RAISE→RAISE→RAISE/CALL'
        elif label_canon == 'R4_BLUFF':
            return 'RAISE→RAISE→FOLD'
        elif label_canon == 'FOLD':
            return 'RAISE→FOLD'

    elif primary_action == 'defense':
        # Sous-ranges en défense (face à une ouverture)
        if label_canon == 'CALL':
            return 'CALL'
        elif label_canon in ('R3_VALUE', 'R4_VALUE'):
            return 'RAISE→RAISE/CALL'
        elif label_canon in ('R3_BLUFF', 'R4_BLUFF'):
            return 'RAISE→FOLD'
        elif label_canon == 'FOLD':
            return 'FOLD'

    elif primary_action == 'squeeze':
        # Squeeze : face à open + call(s)
        if label_canon == 'CALL':
            return 'CALL'
        elif label_canon == 'R4_VALUE':
            return 'RAISE→RAISE/CALL'
        elif label_canon == 'R4_BLUFF':
            return 'RAISE→FOLD'
        elif label_canon == 'FOLD':
            return 'FOLD'

    elif primary_action == 'vs_limpers':
        # Face à limpers
        if label_canon in ('OPEN', 'RAISE', 'ISO_RAISE', 'ISO_VALUE', 'ISO_BLUFF', 'ISO'):
            return 'RAISE'
        elif label_canon == 'CALL':
            return 'CALL'
        elif label_canon == 'FOLD':
            return 'FOLD'

    return None


class DatabaseManager:
    """Gestionnaire de base de données pour les ranges de poker"""

    def __init__(self, db_path: str = "data/poker_trainer.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Créer les tables si elles n'existent pas
        self.init_database()

    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Créer les tables selon le nouveau schéma
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS range_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        file_path TEXT,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(filename, file_hash)
                    );

                    CREATE TABLE IF NOT EXISTS range_contexts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER,

                        -- Noms et identification
                        original_name TEXT NOT NULL,
                        display_name TEXT,
                        cleaned_name TEXT,

                        -- Métadonnées de jeu (colonnes individuelles)
                        table_format TEXT,
                        hero_position TEXT,
                        vs_position TEXT,
                        primary_action TEXT,
                        action_sequence TEXT,  -- 🆕 JSON pour séquences multiway
                        game_type TEXT DEFAULT 'Cash Game',
                        variant TEXT DEFAULT 'NLHE',
                        stack_depth TEXT DEFAULT '100bb',
                        stakes TEXT,
                        sizing TEXT,

                        -- Statuts et validation
                        confidence_score INTEGER DEFAULT 0,
                        needs_validation INTEGER DEFAULT 0,
                        quiz_ready INTEGER DEFAULT 0,
                        error_message TEXT,

                        -- Métadonnées d'enrichissement
                        description TEXT,
                        enriched_by_user INTEGER DEFAULT 0,
                        enrichment_date TEXT,
                        version TEXT DEFAULT '1.0',

                        -- Timestamps
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (file_id) REFERENCES range_files (id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS ranges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        context_id INTEGER NOT NULL,
                        range_key TEXT NOT NULL,
                        name TEXT NOT NULL,
                        action TEXT,
                        label_canon TEXT,
                        action_sequence TEXT,
                        color TEXT,
                        quiz_action TEXT,  
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (context_id) REFERENCES range_contexts (id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS range_hands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        range_id INTEGER NOT NULL,
                        hand TEXT NOT NULL,
                        frequency REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (range_id) REFERENCES ranges (id) ON DELETE CASCADE
                    );

                    -- Index pour optimiser les requêtes
                    CREATE INDEX IF NOT EXISTS idx_range_hands_range_id ON range_hands(range_id);
                    CREATE INDEX IF NOT EXISTS idx_range_hands_hand ON range_hands(hand);
                    CREATE INDEX IF NOT EXISTS idx_ranges_context_id ON ranges(context_id);
                    CREATE INDEX IF NOT EXISTS idx_contexts_needs_validation ON range_contexts(needs_validation);
                    CREATE INDEX IF NOT EXISTS idx_contexts_quiz_ready ON range_contexts(quiz_ready);
                    CREATE INDEX IF NOT EXISTS idx_ranges_label_canon ON ranges(label_canon);
                    CREATE INDEX IF NOT EXISTS idx_ranges_context_label ON ranges(context_id, label_canon);
                    CREATE INDEX IF NOT EXISTS idx_ranges_action_sequence ON ranges(action_sequence);
                """)

                # Vérifier et appliquer migrations si nécessaire
                self._apply_migrations(conn)

                print(f"[DB] Base de données initialisée: {self.db_path}")

        except Exception as e:
            print(f"[DB] Erreur initialisation base: {e}")
            raise

    def _apply_migrations(self, conn):
        """Applique les migrations nécessaires"""
        cursor = conn.cursor()

        # Récupérer les colonnes existantes
        cursor.execute("PRAGMA table_info(range_contexts)")
        columns = {row[1] for row in cursor.fetchall()}

        migrations_applied = []

        # Migration : Ajouter action_sequence si absente
        if 'action_sequence' not in columns:
            cursor.execute("""
                ALTER TABLE range_contexts 
                ADD COLUMN action_sequence TEXT
            """)
            migrations_applied.append("action_sequence ajouté à range_contexts")

        # 🆕 Migration : Ajouter action_sequence dans ranges si absente
        cursor.execute("PRAGMA table_info(ranges)")
        ranges_columns = {row[1] for row in cursor.fetchall()}

        if 'action_sequence' not in ranges_columns:
            cursor.execute("""
                ALTER TABLE ranges 
                ADD COLUMN action_sequence TEXT
            """)
            migrations_applied.append("action_sequence ajouté à ranges")

            # Créer l'index si la colonne vient d'être ajoutée
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ranges_action_sequence 
                ON ranges(action_sequence)
            """)
            migrations_applied.append("index action_sequence créé sur ranges")

        if migrations_applied:
            conn.commit()
            for migration in migrations_applied:
                print(f"[DB] 🔄 Migration appliquée : {migration}")

    # ============================================================================
    # 🆕 MÉTHODES POUR GÉRER action_sequence (JSON)
    # ============================================================================

    def parse_action_sequence(self, action_sequence_json: Optional[str]) -> Optional[Dict]:
        """
        Parse le JSON action_sequence depuis la base de données

        Args:
            action_sequence_json: Chaîne JSON depuis la DB

        Returns:
            Dictionnaire Python ou None
        """
        if not action_sequence_json:
            return None

        try:
            return json.loads(action_sequence_json)
        except json.JSONDecodeError:
            return None

    def serialize_action_sequence(self, action_sequence: Optional[Dict]) -> Optional[str]:
        """
        Sérialise un dictionnaire action_sequence en JSON

        Args:
            action_sequence: Dictionnaire Python

        Returns:
            Chaîne JSON pour la DB ou None
        """
        if not action_sequence:
            return None

        return json.dumps(action_sequence, ensure_ascii=False)

    def build_action_sequence(
            self,
            primary_action: str,
            opener: Optional[str] = None,
            callers: Optional[List[str]] = None,
            callers_count: Optional[Union[int, str]] = None,
            limpers: Optional[List[str]] = None,
            limpers_count: Optional[Union[int, str]] = None
    ) -> Optional[Dict]:
        """
        Construit un dictionnaire action_sequence selon le contexte

        Version 4.1 : Support limpers_count

        Args:
            primary_action: 'open', 'defense', 'squeeze', 'vs_limpers'
            opener: Position de l'ouvreur (pour defense, squeeze)
            callers: Liste des positions ayant callé (pour squeeze)
            limpers: Liste des positions ayant limpé (pour vs_limpers)
            limpers_count: Nombre de limpers (int ou "3+") - NOUVEAU

        Returns:
            Dictionnaire structuré ou None
        """
        if not primary_action:
            return None

        primary_action_lower = primary_action.lower()

        if primary_action_lower == 'open':
            return None  # Pas besoin d'action_sequence pour open simple

        elif primary_action_lower == 'defense':
            if not opener:
                return None
            return {"opener": opener}


        elif primary_action_lower == 'squeeze':

            result = {}

            # Opener toujours présent si fourni

            if opener:
                result["opener"] = opener

            # Ajouter callers si fournis

            if callers:
                result["callers"] = callers if isinstance(callers, list) else [callers]

            # NOUVEAU : Ajouter callers_count si fourni

            if callers_count is not None:

                if isinstance(callers_count, str):

                    result["callers_count"] = callers_count  # Pour "2+", etc.

                else:

                    result["callers_count"] = int(callers_count)

            return result if result else None

        elif primary_action_lower == 'vs_limpers':
            result = {}

            # Ajouter limpers si fournis
            if limpers:
                result["limpers"] = limpers if isinstance(limpers, list) else [limpers]

            # Ajouter limpers_count si fourni
            if limpers_count is not None:
                # Convertir en int si possible, sinon garder string ("3+")
                if isinstance(limpers_count, str):
                    result["limpers_count"] = limpers_count
                else:
                    result["limpers_count"] = int(limpers_count)

            # Si aucun des deux → None
            if not result:
                return None

            return result

        return None

    def format_action_sequence_display(self, action_sequence: Optional[Dict]) -> str:
        """
        Formate action_sequence pour l'affichage humain

        Version 4.1 : Support limpers_count

        Args:
            action_sequence: Dictionnaire action_sequence

        Returns:
            Chaîne lisible (ex: "vs UTG open + SB call", "vs 2 limpers")
        """
        if not action_sequence:
            return ""

        parts = []

        if "opener" in action_sequence:
            parts.append(f"vs {action_sequence['opener']} open")

            if "callers" in action_sequence:
                callers = action_sequence['callers']
                if callers:
                    caller_str = " + ".join(callers)
                    parts.append(f"+ {caller_str} call")

        elif "limpers" in action_sequence or "limpers_count" in action_sequence:
            limpers = action_sequence.get('limpers')
            limpers_count = action_sequence.get('limpers_count')

            # Priorité 1 : Positions spécifiques
            if limpers:
                limper_str = " + ".join(limpers)
                parts.append(f"vs {limper_str} limp")

            # Priorité 2 : Count seulement
            elif limpers_count:
                if isinstance(limpers_count, str) and '+' in limpers_count:
                    parts.append(f"vs {limpers_count} limpers")
                else:
                    parts.append(f"vs {limpers_count} limper(s)")

        return " ".join(parts)

    def detect_action_sequence_from_name(
            self,
            context_name: str,
            primary_action: Optional[str] = None,
            hero_position: Optional[str] = None
    ) -> Optional[Dict]:
        """
        🆕 Détecte automatiquement action_sequence depuis le nom du contexte.

        Version 4.1 :
        - Meilleurs patterns regex pour nom de fichier
        - Exclusion du hero des positions détectées
        - Support limpers_count ("2 limpers", "3+ limpers")
        - Support de multiples formats de noms

        Args:
            context_name: Nom du contexte (ex: "squeeze_btn_vs_utg_co.json")
            primary_action: Action principale détectée
            hero_position: Position du hero (pour l'exclure des détections)

        Returns:
            Dictionnaire action_sequence ou None
        """
        if not context_name or not primary_action:
            return None

        import re
        context_lower = context_name.lower()
        primary_lower = primary_action.lower()

        # =========================================================================
        # SQUEEZE : Détecter opener + callers
        # =========================================================================
        if primary_lower == 'squeeze':
            # Pattern 1 : "vs UTG+CO" ou "vs UTG + CO"
            match = re.search(r'vs\s+(\w+)\s*[+\s]+\s*(\w+)', context_name, re.IGNORECASE)
            if match:
                opener = match.group(1).upper()
                caller = match.group(2).upper()

                # Vérifier que ce sont des positions valides
                valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'LJ', 'HJ', 'UTG+1', 'MP+1']
                if opener in valid_positions and caller in valid_positions:
                    # Exclure hero si détecté
                    callers = [caller] if caller != hero_position else []
                    if callers and opener != hero_position:
                        return {
                            "opener": opener,
                            "callers": callers
                        }

            # Pattern 2 : "squeeze_vs_utg_co" (dans nom de fichier)
            match = re.search(r'squeeze[_\s]+vs[_\s]+(\w+)[_\s]+(\w+)', context_lower)
            if match:
                opener = match.group(1).upper()
                caller = match.group(2).upper()

                valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'LJ', 'HJ', 'UTG+1', 'MP+1']
                if opener in valid_positions and caller in valid_positions:
                    callers = [caller] if caller != hero_position else []
                    if callers and opener != hero_position:
                        return {
                            "opener": opener,
                            "callers": callers
                        }

            # Pattern 3 : Recherche de toutes les positions (fallback)
            positions = re.findall(r'\b(UTG\+?\d?|MP\+?\d?|LJ|HJ|CO|BTN|SB|BB)\b', context_name, re.IGNORECASE)
            if len(positions) >= 2:
                # Exclure hero
                positions = [p.upper() for p in positions if p.upper() != hero_position]
                if len(positions) >= 2:
                    return {
                        "opener": positions[0],
                        "callers": positions[1:]
                    }

        # =========================================================================
        # VS_LIMPERS : Détecter limpers + limpers_count
        # =========================================================================
        elif primary_lower == 'vs_limpers' or 'limp' in context_lower:
            result = {}

            # Pattern 1 : Détecter nombre "2 limpers", "3+ limpers"
            count_match = re.search(r'(\d+)\+?\s*limpers?', context_lower)
            if count_match:
                count_str = count_match.group(0)
                if '+' in count_str:
                    result["limpers_count"] = count_match.group(1) + "+"
                else:
                    result["limpers_count"] = int(count_match.group(1))

            # Pattern 2 : "vs_limpers_utg_co" (dans nom de fichier)
            match = re.search(r'(?:vs[_\s]*)?limpers?[_\s]+(.+?)(?:\.|$)', context_lower)
            if match:
                limpers_str = match.group(1)
                # Extraire les positions
                positions = re.findall(r'(UTG\+?\d?|MP\+?\d?|LJ|HJ|CO|BTN|SB|BB)', limpers_str.upper())
                if positions:
                    # Exclure hero
                    limpers = [p for p in positions if p != hero_position]
                    if limpers:
                        result["limpers"] = limpers

            # Pattern 3 : "UTG limp + CO limp"
            if not result.get("limpers"):
                match = re.findall(r'(\w+)\s+limp', context_lower)
                if match:
                    positions = [p.upper() for p in match]
                    valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'LJ', 'HJ', 'UTG+1', 'MP+1']
                    limpers = [p for p in positions if p in valid_positions and p != hero_position]
                    if limpers:
                        result["limpers"] = limpers

            # Pattern 4 : Extraire toutes les positions (fallback)
            if not result.get("limpers") and not result.get("limpers_count"):
                positions = re.findall(r'\b(UTG\+?\d?|MP\+?\d?|LJ|HJ|CO|BTN|SB|BB)\b', context_name, re.IGNORECASE)
                if positions:
                    # Exclure hero
                    limpers = [p.upper() for p in positions if p.upper() != hero_position]
                    if limpers:
                        result["limpers"] = limpers

            return result if result else None

        # =========================================================================
        # DEFENSE : Détecter opener
        # =========================================================================
        elif primary_lower == 'defense':
            # Pattern 1 : "vs UTG" ou "vs_utg"
            match = re.search(r'vs[_\s]+(\w+)', context_lower)
            if match:
                opener = match.group(1).upper()
                valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'LJ', 'HJ', 'UTG+1', 'MP+1']
                if opener in valid_positions and opener != hero_position:
                    return {"opener": opener}

            # Pattern 2 : "defense_co_vs_utg" (hero_vs_opener dans nom fichier)
            match = re.search(r'defense[_\s]+(\w+)[_\s]+vs[_\s]+(\w+)', context_lower)
            if match:
                # group(1) est hero, group(2) est opener
                opener = match.group(2).upper()
                valid_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'LJ', 'HJ', 'UTG+1', 'MP+1']
                if opener in valid_positions and opener != hero_position:
                    return {"opener": opener}

        return None

    # ============================================================================
    # MÉTHODES CRUD EXISTANTES (modifiées pour action_sequence)
    # ============================================================================

    def check_file_exists(self, filename: str, file_hash: str) -> bool:
        """Vérifie si un fichier a déjà été importé avec le même hash"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM range_files 
                WHERE filename = ? AND file_hash = ?
            """, (filename, file_hash))
            return cursor.fetchone() is not None

    def save_context_complete(self, parsed_context, enriched_metadata) -> bool:
        """Sauvegarde complète d'un contexte avec toutes ses données"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Sauvegarder le fichier source
                cursor.execute("""
                    INSERT OR REPLACE INTO range_files 
                    (filename, file_hash, file_path, status, created_at, updated_at)
                    VALUES (?, ?, ?, 'imported', datetime('now'), datetime('now'))
                """, (
                    parsed_context.filename,
                    parsed_context.file_hash,
                    parsed_context.source_path
                ))
                file_id = cursor.lastrowid

                # ========================================================================
                # 🆕 VERSION 4.1 : Détection avec priorité metadata + validation optionnelle
                # ========================================================================

                primary_action_value = enriched_metadata.primary_action.value if enriched_metadata.primary_action else None
                hero_position_value = enriched_metadata.hero_position.value if enriched_metadata.hero_position else None
                table_format_value = enriched_metadata.table_format.value if enriched_metadata.table_format else None

                action_sequence_dict = None
                error_message = None

                # ====================================================================
                # PRIORITÉ 1 : Metadata du JSON (si présentes)
                # ====================================================================

                if primary_action_value == 'squeeze':
                    # Chercher opener et callers dans les metadata
                    opener = parsed_context.metadata.get('opener')
                    callers_str = parsed_context.metadata.get('callers', '')
                    callers = [c.strip() for c in callers_str.split(',') if c.strip()] if callers_str else []

                    if opener and callers:
                        action_sequence_dict = {
                            "opener": opener,
                            "callers": callers
                        }
                        print(f"[DB] 🎯 Action sequence depuis metadata: opener={opener}, callers={callers}")

                elif primary_action_value == 'vs_limpers':
                    # Chercher limpers dans les metadata
                    limpers_str = parsed_context.metadata.get('limpers', '')
                    limpers = [l.strip() for l in limpers_str.split(',') if l.strip()] if limpers_str else []

                    # 🆕 Chercher limpers_count
                    limpers_count = parsed_context.metadata.get('limpers_count')

                    # Construire action_sequence si au moins un est fourni
                    if limpers or limpers_count:
                        action_sequence_dict = {}
                        if limpers:
                            action_sequence_dict["limpers"] = limpers
                        if limpers_count:
                            action_sequence_dict["limpers_count"] = limpers_count

                        print(f"[DB] 🎯 Action sequence depuis metadata: {action_sequence_dict}")

                elif primary_action_value == 'defense':
                    # Chercher opener dans les metadata
                    opener = parsed_context.metadata.get('opener')
                    if opener:
                        action_sequence_dict = {"opener": opener}
                        print(f"[DB] 🎯 Action sequence depuis metadata: opener={opener}")

                # ====================================================================
                # PRIORITÉ 2 : Détection depuis nom de fichier/contexte
                # ====================================================================

                if not action_sequence_dict:
                    action_sequence_dict = self.detect_action_sequence_from_name(
                        enriched_metadata.original_name,
                        primary_action_value,
                        hero_position_value
                    )
                    if action_sequence_dict:
                        print(f"[DB] 🔍 Action sequence détectée depuis nom: {action_sequence_dict}")

                # ====================================================================
                # VALIDATION DE COHÉRENCE (si action_sequence détecté)
                # ====================================================================

                if action_sequence_dict and hero_position_value and table_format_value:
                    from position_validator import validate_position_consistency

                    is_valid, validation_error = validate_position_consistency(
                        primary_action=primary_action_value,
                        hero_position=hero_position_value,
                        table_format=table_format_value,
                        opener=action_sequence_dict.get('opener'),
                        callers=action_sequence_dict.get('callers'),
                        limpers=action_sequence_dict.get('limpers'),
                        limpers_count=action_sequence_dict.get('limpers_count')
                    )

                    if not is_valid:
                        print(f"[DB] ❌ ERREUR cohérence positions: {validation_error}")
                        # Invalider action_sequence
                        action_sequence_dict = None
                        # Stocker l'erreur pour affichage
                        error_message = f"Incohérence positions: {validation_error}"
                    else:
                        print(f"[DB] ✅ Validation positions OK")

                # ====================================================================
                # 🆕 Si pas d'action_sequence → Range générique (OK aussi !)
                # ====================================================================

                if not action_sequence_dict:
                    if primary_action_value in ['defense', 'squeeze', 'vs_limpers']:
                        print(f"[DB] ℹ️  Range générique {primary_action_value} (sans positions vilains spécifiques)")

                # ====================================================================
                # Sérialiser et préparer pour sauvegarde
                # ====================================================================

                action_sequence_json = self.serialize_action_sequence(action_sequence_dict)

                if action_sequence_json:
                    display = self.format_action_sequence_display(action_sequence_dict)
                    print(f"[DB] 💾 Action sequence validée : {display}")

                # 2. Sauvegarder le contexte avec métadonnées en colonnes individuelles
                cursor.execute("""
                    INSERT INTO range_contexts
                    (file_id, original_name, display_name, cleaned_name,
                     table_format, hero_position, vs_position, primary_action, action_sequence,
                     game_type, variant, stack_depth, stakes, sizing,
                     confidence_score, needs_validation, quiz_ready, error_message,
                     description, enriched_by_user, enrichment_date, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    enriched_metadata.original_name,
                    enriched_metadata.display_name,
                    enriched_metadata.cleaned_name,
                    table_format_value,
                    hero_position_value,
                    enriched_metadata.vs_position.value if enriched_metadata.vs_position else None,
                    primary_action_value,
                    action_sequence_json,  # 🆕 Sauvegarder le JSON
                    enriched_metadata.game_format.value if enriched_metadata.game_format else 'Cash Game',
                    enriched_metadata.variant.value if enriched_metadata.variant else 'NLHE',
                    enriched_metadata.stack_depth.value if enriched_metadata.stack_depth else '100bb',
                    None,  # stakes (non utilisé pour l'instant)
                    enriched_metadata.sizing,
                    int(enriched_metadata.confidence * 100),
                    1,  # needs_validation = 1 par défaut (sera recalculé après)
                    0,  # quiz_ready = 0 par défaut (sera recalculé après)
                    error_message,  # 🆕 Stocker error_message si validation échoue
                    enriched_metadata.description,
                    1 if enriched_metadata.enriched_by_user else 0,
                    enriched_metadata.enrichment_date,
                    enriched_metadata.version
                ))
                context_id = cursor.lastrowid

                # 3. Sauvegarder les ranges
                for i, range_data in enumerate(parsed_context.ranges, 1):
                    range_key = str(i)

                    # Déterminer le label_canon
                    # Priorité 1 : Utiliser label_canon du JSON si présent
                    label_canon = None
                    if hasattr(range_data, 'label_canon') and range_data.label_canon:
                        label_canon = range_data.label_canon

                    # Priorité 2 : Mapper depuis le name 🆕 en passant primary_action
                    if not label_canon or label_canon == 'None' or label_canon == '':
                        label_canon = map_name_to_label_canon(range_data.name, range_key, primary_action_value)

                    # Détecter l'action quiz (pour compatibilité)
                    quiz_action = QuizActionMapper.detect(range_data.name)

                    # 🎮 Générer la séquence d'actions pour le drill down
                    action_sequence = generate_action_sequence(label_canon, primary_action_value, range_key)
                    print("=" * 80)
                    print(f"🔥🔥🔥 APPEL generate_action_sequence")
                    print(f"   label_canon={label_canon}")
                    print(f"   primary_action={primary_action_value}")
                    print(f"   range_key={range_key}")
                    action_sequence = generate_action_sequence(label_canon, primary_action_value, range_key)
                    print(f"   RÉSULTAT action_sequence={action_sequence}")
                    print("=" * 80)

                    print(
                        f"[DB] Range {range_key}: name='{range_data.name}', primary_action='{primary_action_value}' → label_canon='{label_canon}', action_sequence='{action_sequence}'")

                    cursor.execute("""
                        INSERT INTO ranges
                        (context_id, range_key, name, action, color, quiz_action, label_canon, action_sequence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context_id,
                        range_key,
                        range_data.name,
                        range_data.name,
                        range_data.color,
                        quiz_action,
                        label_canon,
                        action_sequence
                    ))
                    range_id = cursor.lastrowid

                    # 4. Sauvegarder les mains pour cette range
                    for hand, range_keys in range_data.hands.items():
                        # Calculer la fréquence
                        frequency = 1.0 if i in range_keys else 0.0

                        if frequency > 0:
                            cursor.execute("""
                                INSERT INTO range_hands
                                (range_id, hand, frequency)
                                VALUES (?, ?, ?)
                            """, (range_id, hand, frequency))

                # 5. ✅ VÉRIFICATION FINALE : Le contexte est-il vraiment prêt pour le quiz ?

                # 🆕 ÉTAPE 1 : Vérifier les MÉTADONNÉES du contexte
                metadata_valid = True
                metadata_issues = []

                if not enriched_metadata.table_format or enriched_metadata.table_format.value == 'N/A':
                    metadata_valid = False
                    metadata_issues.append("table_format manquant")

                if not enriched_metadata.hero_position or enriched_metadata.hero_position.value == 'N/A':
                    metadata_valid = False
                    metadata_issues.append("hero_position manquant")

                if not enriched_metadata.primary_action or enriched_metadata.primary_action.value == 'N/A':
                    metadata_valid = False
                    metadata_issues.append("primary_action manquant")

                # Si métadonnées invalides → validation requise
                if not metadata_valid:
                    print(
                        f"[DB] ⚠️ Métadonnées incomplètes pour '{enriched_metadata.display_name}': {', '.join(metadata_issues)}")
                    cursor.execute("""
                        UPDATE range_contexts
                        SET quiz_ready = 0,
                            needs_validation = 1,
                            confidence_score = 0
                        WHERE id = ?
                    """, (context_id,))
                    print(
                        f"[DB] Contexte '{enriched_metadata.display_name}' sauvegardé (ID: {context_id}) - ⚠️ Nécessite validation (métadonnées incomplètes)")
                    return True

                # ÉTAPE 2 : Vérifier la range PRINCIPALE (range_key='1')
                cursor.execute("""
                    SELECT label_canon 
                    FROM ranges 
                    WHERE context_id = ? 
                      AND range_key = '1'
                """, (context_id,))

                main_range_result = cursor.fetchone()
                main_range_label = main_range_result[0] if main_range_result else None

                # Si la range principale n'a pas de label_canon valide → validation requise
                if not main_range_label or main_range_label == 'None' or main_range_label == '':
                    print(f"[DB] ⚠️ Range principale sans label_canon pour contexte '{enriched_metadata.display_name}'")
                    cursor.execute("""
                        UPDATE range_contexts
                        SET quiz_ready = 0,
                            needs_validation = 1,
                            confidence_score = 0
                        WHERE id = ?
                    """, (context_id,))
                    print(
                        f"[DB] Contexte '{enriched_metadata.display_name}' sauvegardé (ID: {context_id}) - ⚠️ Nécessite validation (range principale sans label)")
                    return True

                # ÉTAPE 3 : Vérifier les sous-ranges (range_key != '1')
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ranges 
                    WHERE context_id = ? 
                      AND range_key != '1'
                      AND (label_canon IS NULL OR label_canon = '' OR label_canon = 'UNKNOWN' OR label_canon = 'None')
                """, (context_id,))

                incomplete_subranges = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ranges 
                    WHERE context_id = ? 
                      AND range_key != '1'
                """, (context_id,))

                total_subranges = cursor.fetchone()[0]

                # Calculer quiz_ready et needs_validation
                if total_subranges == 0:
                    # Pas de sous-ranges : contexte simple
                    # Métadonnées OK (vérifié ci-dessus) + Range principale OK (vérifié ci-dessus) → prêt !
                    quiz_ready = 1
                    needs_validation = 0
                    confidence_score = 100
                elif incomplete_subranges == 0:
                    # Tous les sous-ranges ont des labels : prêt pour le quiz !
                    quiz_ready = 1
                    needs_validation = 0
                    confidence_score = 100
                else:
                    # Des sous-ranges manquent de labels : nécessite validation
                    quiz_ready = 0
                    needs_validation = 1
                    completed = total_subranges - incomplete_subranges
                    confidence_score = int((completed / total_subranges) * 100)

                # 6. Mettre à jour le contexte avec les valeurs finales
                cursor.execute("""
                    UPDATE range_contexts
                    SET quiz_ready = ?,
                        needs_validation = ?,
                        confidence_score = ?
                    WHERE id = ?
                """, (quiz_ready, needs_validation, confidence_score, context_id))

                # Log du résultat
                if quiz_ready:
                    status_msg = "✅ Prêt pour le quiz"
                elif total_subranges > 0:
                    status_msg = f"⚠️ Nécessite validation ({incomplete_subranges}/{total_subranges} sous-ranges à classifier)"
                else:
                    status_msg = "⚠️ Nécessite validation (métadonnées à compléter)"

                print(f"[DB] Contexte '{enriched_metadata.display_name}' sauvegardé (ID: {context_id}) - {status_msg}")

                return True

        except Exception as e:
            print(f"[DB] Erreur sauvegarde contexte '{parsed_context.context_name}': {e}")
            import traceback
            traceback.print_exc()
            return False

    def mark_context_error(self, filename: str, error_message: str) -> bool:
        """Marque un contexte comme en erreur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE range_files 
                    SET status = 'error', error_message = ?, updated_at = datetime('now')
                    WHERE filename = ?
                """, (error_message, filename))

                print(f"[DB] Fichier '{filename}' marqué en erreur: {error_message}")
                return True

        except Exception as e:
            print(f"[DB] Erreur marquage erreur pour '{filename}': {e}")
            return False

    def get_import_stats(self) -> Dict[str, int]:
        """Récupère les statistiques d'import"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                cursor.execute("SELECT COUNT(*) FROM range_files")
                stats['total_files'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_files WHERE status = 'imported'")
                stats['imported_files'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_files WHERE status = 'error'")
                stats['error_files'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_contexts")
                stats['total_contexts'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE quiz_ready = 1")
                stats['question_ready_contexts'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE needs_validation = 1")
                stats['needs_validation'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM ranges")
                stats['total_ranges'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_hands")
                stats['total_hands'] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            print(f"[DB] Erreur récupération stats: {e}")
            return {}

    def get_files_to_process(self, ranges_dir: Path) -> List[Path]:
        """Récupère la liste des fichiers JSON à traiter (nouveaux ou modifiés)"""
        import hashlib

        files_to_process = []

        for json_file in ranges_dir.glob("*.json"):
            try:
                content = json_file.read_text(encoding='utf-8')
                file_hash = hashlib.md5(content.encode()).hexdigest()

                if not self.check_file_exists(json_file.name, file_hash):
                    files_to_process.append(json_file)
                else:
                    print(f"[DB] Fichier '{json_file.name}' déjà importé (hash identique)")

            except Exception as e:
                print(f"[DB] Erreur vérification fichier '{json_file.name}': {e}")
                continue

        return files_to_process

    def cleanup_old_imports(self, filename: str) -> bool:
        """Nettoie les anciens imports du même fichier"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id FROM range_contexts 
                    WHERE file_id IN (SELECT id FROM range_files WHERE filename = ?)
                """, (filename,))

                context_ids = [row[0] for row in cursor.fetchall()]

                for context_id in context_ids:
                    conn.execute("DELETE FROM range_contexts WHERE id = ?", (context_id,))

                conn.execute("DELETE FROM range_files WHERE filename = ?", (filename,))

                return True

        except Exception as e:
            print(f"[DB] Erreur nettoyage ancien import '{filename}': {e}")
            return False


if __name__ == "__main__":
    db = DatabaseManager()
    stats = db.get_import_stats()
    print("Stats actuelles:", stats)