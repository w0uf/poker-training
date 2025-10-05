#!/usr/bin/env python3
"""
Module de gestion de la base de données SQLite
Gère la persistance des contextes, ranges et mains avec transactions sécurisées
Version mise à jour avec colonnes individuelles pour métadonnées
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import asdict
from quiz_action_mapper import QuizActionMapper

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
                """)

                print(f"[DB] Base de données initialisée: {self.db_path}")

        except Exception as e:
            print(f"[DB] Erreur initialisation base: {e}")
            raise

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

                # 2. Sauvegarder le contexte avec métadonnées en colonnes individuelles
                cursor.execute("""
                    INSERT INTO range_contexts
                    (file_id, original_name, display_name, cleaned_name,
                     table_format, hero_position, vs_position, primary_action,
                     game_type, variant, stack_depth, stakes, sizing,
                     confidence_score, needs_validation, quiz_ready, error_message,
                     description, enriched_by_user, enrichment_date, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    enriched_metadata.original_name,
                    enriched_metadata.display_name,
                    enriched_metadata.cleaned_name,
                    enriched_metadata.table_format.value if enriched_metadata.table_format else None,
                    enriched_metadata.hero_position.value if enriched_metadata.hero_position else None,
                    enriched_metadata.vs_position.value if enriched_metadata.vs_position else None,
                    enriched_metadata.primary_action.value if enriched_metadata.primary_action else None,
                    enriched_metadata.game_format.value if enriched_metadata.game_format else 'Cash Game',
                    enriched_metadata.variant.value if enriched_metadata.variant else 'NLHE',
                    enriched_metadata.stack_depth.value if enriched_metadata.stack_depth else '100bb',
                    None,  # stakes (non utilisé pour l'instant)
                    enriched_metadata.sizing,
                    int(enriched_metadata.confidence*100),
                    1 if not enriched_metadata.question_friendly and enriched_metadata.confidence < 80 else 0,
                    1 if enriched_metadata.question_friendly else 0,
                    None,  # error_message
                    enriched_metadata.description,
                    1 if enriched_metadata.enriched_by_user else 0,
                    enriched_metadata.enrichment_date,
                    enriched_metadata.version
                ))
                context_id = cursor.lastrowid

                # 3. Sauvegarder les ranges
                for i, range_data in enumerate(parsed_context.ranges, 1):
                    # Détecter l'action quiz
                    quiz_action = QuizActionMapper.detect(range_data.name)
                    cursor.execute("""
                        INSERT INTO ranges
                        (context_id, range_key, name, action, color,quiz_action)
                        VALUES (?, ?, ?, ?, ?,?)
                    """, (
                        context_id,
                        str(i),
                        range_data.name,
                        range_data.name,  # action = name pour l'instant
                        range_data.color,
                        quiz_action
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

                print(f"[DB] Contexte '{enriched_metadata.display_name}' sauvegardé avec succès (ID: {context_id})")
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

                # Compter les fichiers
                cursor.execute("SELECT COUNT(*) FROM range_files")
                stats['total_files'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_files WHERE status = 'imported'")
                stats['imported_files'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM range_files WHERE status = 'error'")
                stats['error_files'] = cursor.fetchone()[0]

                # Compter les contextes
                cursor.execute("SELECT COUNT(*) FROM range_contexts")
                stats['total_contexts'] = cursor.fetchone()[0]

                # Compter les contextes prêts pour quiz
                cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE quiz_ready = 1")
                stats['question_ready_contexts'] = cursor.fetchone()[0]

                # Compter les contextes nécessitant validation
                cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE needs_validation = 1")
                stats['needs_validation'] = cursor.fetchone()[0]

                # Compter les ranges et mains
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
                # Calculer le hash du fichier
                content = json_file.read_text(encoding='utf-8')
                file_hash = hashlib.md5(content.encode()).hexdigest()

                # Vérifier s'il existe déjà en DB
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
                # Supprimer les anciens contextes et leurs données associées
                cursor = conn.execute("""
                    SELECT id FROM range_contexts 
                    WHERE file_id IN (SELECT id FROM range_files WHERE filename = ?)
                """, (filename,))

                context_ids = [row[0] for row in cursor.fetchall()]

                for context_id in context_ids:
                    # Les CASCADE dans les FK s'occupent de supprimer ranges et range_hands
                    conn.execute("DELETE FROM range_contexts WHERE id = ?", (context_id,))

                # Supprimer le fichier
                conn.execute("DELETE FROM range_files WHERE filename = ?", (filename,))

                return True

        except Exception as e:
            print(f"[DB] Erreur nettoyage ancien import '{filename}': {e}")
            return False


if __name__ == "__main__":
    # Test du database manager
    db = DatabaseManager()
    stats = db.get_import_stats()
    print("Stats actuelles:", stats)