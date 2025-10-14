#!/usr/bin/env python3
"""
Module de gestion de la base de données SQLite
Gère la persistance des contextes, ranges et mains avec transactions sécurisées
Version mise à jour avec colonnes individuelles pour métadonnées + action_sequence JSON
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
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
                return 'SQUEEZE'  # 🎯 CORRECTION : squeeze → SQUEEZE
            elif primary_lower == 'vs_limpers':
                if 'iso' in name_lower:
                    return 'ISO'
                return 'RAISE'
            elif primary_lower == 'check':
                return 'CHECK'

        # 🎯 PRIORITÉ 2 : Analyser le nom si primary_action absent/ambigu
        # Ordre important : squeeze AVANT 3bet !
        if 'squeeze' in name_lower or 'squezze' in name_lower:  # 🎯 Gérer la faute d'orthographe
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

                        FOREIGN KEY (file_id) REFERENCES range_files (id)
                    );

                    CREATE TABLE IF NOT EXISTS ranges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        context_id INTEGER NOT NULL,
                        range_key TEXT NOT NULL,
                        name TEXT NOT NULL,
                        action TEXT,
                        label_canon TEXT,
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
            limpers: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Construit un dictionnaire action_sequence selon le contexte

        Args:
            primary_action: 'open', 'defense', 'squeeze', 'vs_limpers'
            opener: Position de l'ouvreur (pour defense, squeeze)
            callers: Liste des positions ayant callé (pour squeeze)
            limpers: Liste des positions ayant limpé (pour vs_limpers)

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
            if not opener or not callers:
                return None
            return {
                "opener": opener,
                "callers": callers if isinstance(callers, list) else [callers]
            }

        elif primary_action_lower == 'vs_limpers':
            if not limpers:
                return None
            return {
                "limpers": limpers if isinstance(limpers, list) else [limpers]
            }

        return None

    def format_action_sequence_display(self, action_sequence: Optional[Dict]) -> str:
        """
        Formate action_sequence pour l'affichage humain

        Args:
            action_sequence: Dictionnaire action_sequence

        Returns:
            Chaîne lisible (ex: "vs UTG open + SB call")
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

        elif "limpers" in action_sequence:
            limpers = action_sequence['limpers']
            if limpers:
                limper_str = " + ".join(limpers)
                parts.append(f"vs {limper_str} limp")

        return " ".join(parts)

    def detect_action_sequence_from_name(
            self,
            context_name: str,
            primary_action: Optional[str] = None
    ) -> Optional[Dict]:
        """
        🆕 Détecte automatiquement action_sequence depuis le nom du contexte

        Args:
            context_name: Nom du contexte (ex: "squeeze BB vs UTG+SB")
            primary_action: Action principale détectée

        Returns:
            Dictionnaire action_sequence ou None
        """
        if not context_name or not primary_action:
            return None

        import re
        context_lower = context_name.lower()
        primary_lower = primary_action.lower()

        # Pattern pour squeeze : "vs POSITION + POSITION"
        if primary_lower == 'squeeze':
            # Chercher "vs UTG+SB" ou "vs CO + BTN"
            match = re.search(r'vs\s+(\w+)\s*[+\s]+\s*(\w+)', context_name, re.IGNORECASE)
            if match:
                opener = match.group(1).upper()
                caller = match.group(2).upper()
                return {
                    "opener": opener,
                    "callers": [caller]
                }

        # Pattern pour vs_limpers : "limp" + positions
        elif primary_lower == 'vs_limpers' or 'limp' in context_lower:
            # Extraire toutes les positions mentionnées
            positions = re.findall(r'\b(UTG|MP|CO|BTN|SB|BB|LJ|HJ)\b', context_name, re.IGNORECASE)
            if positions:
                return {
                    "limpers": [p.upper() for p in positions]
                }

        # Pattern pour defense : "vs POSITION open"
        elif primary_lower == 'defense':
            match = re.search(r'vs\s+(\w+)', context_name, re.IGNORECASE)
            if match:
                opener = match.group(1).upper()
                return {
                    "opener": opener
                }

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

                # 🆕 Détecter ou construire action_sequence
                primary_action_value = enriched_metadata.primary_action.value if enriched_metadata.primary_action else None

                # Essayer de détecter depuis le nom
                action_sequence_dict = self.detect_action_sequence_from_name(
                    enriched_metadata.original_name,
                    primary_action_value
                )

                # Sérialiser en JSON si détecté
                action_sequence_json = self.serialize_action_sequence(action_sequence_dict)

                if action_sequence_json:
                    display = self.format_action_sequence_display(action_sequence_dict)
                    print(f"[DB] 🎯 Action sequence détectée : {display}")

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
                    enriched_metadata.table_format.value if enriched_metadata.table_format else None,
                    enriched_metadata.hero_position.value if enriched_metadata.hero_position else None,
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
                    None,  # error_message
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

                    print(
                        f"[DB] Range {range_key}: name='{range_data.name}', primary_action='{primary_action_value}' → label_canon='{label_canon}'")

                    cursor.execute("""
                        INSERT INTO ranges
                        (context_id, range_key, name, action, color, quiz_action, label_canon)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context_id,
                        range_key,
                        range_data.name,
                        range_data.name,
                        range_data.color,
                        quiz_action,
                        label_canon
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