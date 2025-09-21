#!/usr/bin/env python3
"""
Système d'import modulaire pour ranges de poker
Structure: models -> parsers -> database -> import script
"""

import os
import json
import hashlib
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


# ============================================================================
# MODELS - Structures de données
# ============================================================================

@dataclass
class RangeFile:
    """Représente un fichier de range importé"""
    id: Optional[int]
    filename: str
    file_hash: str
    imported_at: datetime
    last_modified: datetime
    status: str  # 'imported', 'error', 'updated'


@dataclass
class RangeContext:
    """Contexte global d'un fichier de ranges (ex: Défense CO vs Open MP)"""
    id: Optional[int]
    file_id: int
    name: str
    original_data: Dict  # JSON original complet
    parsed_metadata: Dict  # Métadonnées extraites automatiquement
    enriched_metadata: Dict  # Métadonnées enrichies par l'utilisateur
    confidence: float  # 0.0 à 1.0


@dataclass
class Range:
    """Une range spécifique (ex: Call, 3Bet Value)"""
    id: Optional[int]
    context_id: int
    range_key: str  # "1", "2", "3" du JSON original
    name: str
    color: str
    range_type: str = "action"


@dataclass
class RangeHand:
    """Une main dans une range avec sa fréquence"""
    id: Optional[int]
    range_id: int
    hand: str
    frequency: float = 1.0


# ============================================================================
# DATABASE - Couche d'accès aux données
# ============================================================================

class RangeRepository(ABC):
    """Interface abstraite pour l'accès aux données"""

    @abstractmethod
    def save_range_file(self, range_file: RangeFile) -> int:
        pass

    @abstractmethod
    def get_range_file_by_name(self, filename: str) -> Optional[RangeFile]:
        pass

    @abstractmethod
    def save_range_context(self, context: RangeContext) -> int:
        pass

    @abstractmethod
    def save_range(self, range_obj: Range) -> int:
        pass

    @abstractmethod
    def save_range_hand(self, range_hand: RangeHand) -> int:
        pass

    @abstractmethod
    def get_all_contexts(self) -> List[RangeContext]:
        pass


class SQLiteRangeRepository(RangeRepository):
    """Implémentation SQLite du repository"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialise les tables de la base de données"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS range_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    imported_at TIMESTAMP NOT NULL,
                    last_modified TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'imported'
                );

                CREATE TABLE IF NOT EXISTS range_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    original_data TEXT NOT NULL,  -- JSON
                    parsed_metadata TEXT NOT NULL,  -- JSON
                    enriched_metadata TEXT NOT NULL,  -- JSON
                    confidence REAL NOT NULL DEFAULT 0.0,
                    FOREIGN KEY (file_id) REFERENCES range_files (id)
                );

                CREATE TABLE IF NOT EXISTS ranges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id INTEGER NOT NULL,
                    range_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    range_type TEXT NOT NULL DEFAULT 'action',
                    FOREIGN KEY (context_id) REFERENCES range_contexts (id)
                );

                CREATE TABLE IF NOT EXISTS range_hands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    range_id INTEGER NOT NULL,
                    hand TEXT NOT NULL,
                    frequency REAL NOT NULL DEFAULT 1.0,
                    FOREIGN KEY (range_id) REFERENCES ranges (id)
                );

                CREATE INDEX IF NOT EXISTS idx_range_hands_range_id ON range_hands(range_id);
                CREATE INDEX IF NOT EXISTS idx_range_hands_hand ON range_hands(hand);
            """)

    def save_range_file(self, range_file: RangeFile) -> int:
        """Sauvegarde un fichier de range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO range_files 
                (filename, file_hash, imported_at, last_modified, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                range_file.filename,
                range_file.file_hash,
                range_file.imported_at.isoformat(),
                range_file.last_modified.isoformat(),
                range_file.status
            ))
            return cursor.lastrowid

    def get_range_file_by_name(self, filename: str) -> Optional[RangeFile]:
        """Récupère un fichier par son nom"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, filename, file_hash, imported_at, last_modified, status
                FROM range_files WHERE filename = ?
            """, (filename,))

            row = cursor.fetchone()
            if row:
                return RangeFile(
                    id=row[0],
                    filename=row[1],
                    file_hash=row[2],
                    imported_at=datetime.fromisoformat(row[3]),
                    last_modified=datetime.fromisoformat(row[4]),
                    status=row[5]
                )
            return None

    def save_range_context(self, context: RangeContext) -> int:
        """Sauvegarde un contexte de range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO range_contexts 
                (file_id, name, original_data, parsed_metadata, enriched_metadata, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                context.file_id,
                context.name,
                json.dumps(context.original_data),
                json.dumps(context.parsed_metadata),
                json.dumps(context.enriched_metadata),
                context.confidence
            ))
            return cursor.lastrowid

    def save_range(self, range_obj: Range) -> int:
        """Sauvegarde une range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO ranges 
                (context_id, range_key, name, color, range_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                range_obj.context_id,
                range_obj.range_key,
                range_obj.name,
                range_obj.color,
                range_obj.range_type
            ))
            return cursor.lastrowid

    def save_range_hand(self, range_hand: RangeHand) -> int:
        """Sauvegarde une main dans une range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO range_hands (range_id, hand, frequency)
                VALUES (?, ?, ?)
            """, (range_hand.range_id, range_hand.hand, range_hand.frequency))
            return cursor.lastrowid

    def get_all_contexts(self) -> List[RangeContext]:
        """Récupère tous les contextes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, file_id, name, original_data, parsed_metadata, 
                       enriched_metadata, confidence
                FROM range_contexts
            """)

            contexts = []
            for row in cursor.fetchall():
                contexts.append(RangeContext(
                    id=row[0],
                    file_id=row[1],
                    name=row[2],
                    original_data=json.loads(row[3]),
                    parsed_metadata=json.loads(row[4]),
                    enriched_metadata=json.loads(row[5]),
                    confidence=row[6]
                ))
            return contexts


# ============================================================================
# PARSERS - Analyseurs de fichiers
# ============================================================================

class RangeParser(ABC):
    """Interface abstraite pour les parsers de ranges"""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: str) -> Tuple[RangeContext, List[Range], List[RangeHand]]:
        pass


class JSONRangeParser(RangeParser):
    """Parser pour les fichiers JSON de votre éditeur de ranges"""

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith('.json')

    def parse(self, file_path: str) -> Tuple[RangeContext, List[Range], List[RangeHand]]:
        """Parse un fichier JSON de ranges"""

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraire le nom du contexte principal (heuristique)
        context_name = self._extract_context_name(data, file_path)

        # Analyser automatiquement le contexte
        parsed_metadata = self._analyze_context(context_name, data)

        # Créer le contexte
        context = RangeContext(
            id=None,
            file_id=0,  # Sera mis à jour lors de la sauvegarde
            name=context_name,
            original_data=data,
            parsed_metadata=parsed_metadata,
            enriched_metadata={},  # Vide initialement
            confidence=parsed_metadata.get('confidence', 0.0)
        )

        # Parser les ranges
        ranges = []
        range_hands = []

        ranges_data = data.get('data', {}).get('ranges', {})
        values_data = data.get('data', {}).get('values', {})

        for range_key, range_info in ranges_data.items():
            range_obj = Range(
                id=None,
                context_id=0,  # Sera mis à jour lors de la sauvegarde
                range_key=range_key,
                name=range_info.get('name', f'Range {range_key}'),
                color=range_info.get('color', '#000000'),
                range_type='action'
            )
            ranges.append(range_obj)

        # Parser les mains de chaque range
        for hand, range_ids in values_data.items():
            for range_id in range_ids:
                range_hand = RangeHand(
                    id=None,
                    range_id=0,  # Sera mis à jour avec l'ID réel
                    hand=hand,
                    frequency=1.0
                )
                # Stocker temporairement la clé de range pour mapping
                range_hand._temp_range_key = str(range_id)
                range_hands.append(range_hand)

        return context, ranges, range_hands

    def _extract_context_name(self, data: Dict, file_path: str) -> str:
        """Extrait le nom du contexte principal"""

        # Chercher dans les ranges un nom qui semble être le contexte principal
        ranges = data.get('data', {}).get('ranges', {})

        if ranges:
            # Prendre le premier range comme base du contexte
            first_range = list(ranges.values())[0]
            name = first_range.get('name', '')

            # Nettoyer le nom pour en faire un contexte
            if any(word in name.lower() for word in ['vs', 'contre', 'face']):
                # C'est déjà un contexte (ex: "Défense CO vs Open MP")
                return name
            else:
                # C'est une action, utiliser le nom du fichier
                return Path(file_path).stem

        # Fallback: nom du fichier
        return Path(file_path).stem

    def _analyze_context(self, context_name: str, data: Dict) -> Dict:
        """Analyse automatique du contexte"""

        import re

        metadata = {}
        confidence_factors = []

        # Patterns pour détecter les positions
        position_patterns = {
            r'\bUTG\+?1?\b': 'UTG+1',
            r'\bUTG\b': 'UTG',
            r'\bMP\+?1?\b': 'MP+1',
            r'\bMP\b': 'MP',
            r'\bLJ\b': 'LJ',
            r'\bHJ\b': 'HJ',
            r'\bCO\b': 'CO',
            r'\bBTN\b|\bBU\b': 'BTN',
            r'\bSB\b': 'SB',
            r'\bBB\b': 'BB',
        }

        # Patterns pour les actions
        action_patterns = {
            r'\bOpen\b|\bOpening\b|\bRFI\b': 'open',
            r'\bCall\b|\bCalling\b': 'call',
            r'\b3[Bb]et\b|\b3-bet\b': '3bet',
            r'\b4[Bb]et\b|\b4-bet\b': '4bet',
            r'\bFold\b|\bFolding\b': 'fold',
            r'\bD[éeè]fense?\b|\bDefend\b': 'defense',
        }

        # Analyser les positions dans le nom
        positions_found = []
        for pattern, position in position_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                positions_found.append(position)

        if len(positions_found) >= 1:
            metadata['hero_position'] = positions_found[0]
            confidence_factors.append(0.8)

            if len(positions_found) >= 2:
                # Détecter vs_position
                if re.search(r'\bvs\b|\bv\b|\bcontre\b', context_name, re.IGNORECASE):
                    parts = re.split(r'\bvs\b|\bv\b|\bcontre\b', context_name, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        metadata['vs_position'] = positions_found[1]
                        confidence_factors.append(0.9)

        # Analyser les actions
        for pattern, action in action_patterns.items():
            if re.search(pattern, context_name, re.IGNORECASE):
                metadata['primary_action'] = action
                confidence_factors.append(0.7)
                break

        # Analyser les ranges pour détecter les types d'actions
        ranges = data.get('data', {}).get('ranges', {})
        action_types = []
        for range_info in ranges.values():
            name = range_info.get('name', '').lower()
            if 'call' in name:
                action_types.append('call')
            elif '3bet' in name or 'raise' in name:
                action_types.append('3bet')
            elif 'fold' in name:
                action_types.append('fold')

        if action_types:
            metadata['action_types'] = list(set(action_types))
            confidence_factors.append(0.6)

        # Calculer confiance globale
        metadata['confidence'] = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        metadata['detected_at'] = datetime.now().isoformat()

        return metadata


class ParserFactory:
    """Factory pour obtenir le bon parser selon le type de fichier"""

    def __init__(self):
        self.parsers = [
            JSONRangeParser(),
            # Ici on pourra ajouter d'autres parsers
            # GTOPlusParser(),
            # PIOSolverParser(),
        ]

    def get_parser(self, file_path: str) -> Optional[RangeParser]:
        """Retourne le parser approprié pour le fichier"""
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None


# ============================================================================
# IMPORT SCRIPT - Script principal d'import
# ============================================================================

class RangeImporter:
    """Importe les fichiers de ranges dans la base de données"""

    def __init__(self, ranges_dir: str, db_path: str):
        self.ranges_dir = Path(ranges_dir)
        self.repository = SQLiteRangeRepository(db_path)
        self.parser_factory = ParserFactory()

    def import_all_ranges(self):
        """Importe tous les fichiers du dossier ranges/"""
        print(f"🔍 Scan du dossier: {self.ranges_dir}")

        if not self.ranges_dir.exists():
            print(f"❌ Dossier {self.ranges_dir} n'existe pas")
            return

        json_files = list(self.ranges_dir.glob("*.json"))
        print(f"📁 {len(json_files)} fichiers JSON trouvés")

        if not json_files:
            print("ℹ️  Aucun fichier JSON à importer")
            return

        imported_count = 0
        error_count = 0

        for file_path in json_files:
            try:
                if self.import_range_file(file_path):
                    imported_count += 1
                else:
                    print(f"⏭️  {file_path.name} déjà à jour")
            except Exception as e:
                print(f"❌ Erreur import {file_path.name}: {e}")
                error_count += 1

        print(f"\n📊 RÉSUMÉ D'IMPORT:")
        print(f"✅ Importés: {imported_count}")
        print(f"⏭️  Déjà à jour: {len(json_files) - imported_count - error_count}")
        print(f"❌ Erreurs: {error_count}")

    def import_range_file(self, file_path: Path) -> bool:
        """Importe un fichier de range. Retourne True si importé, False si déjà à jour"""

        # Calculer hash pour détecter changements
        file_hash = self._calculate_file_hash(file_path)
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Vérifier si déjà importé
        existing = self.repository.get_range_file_by_name(file_path.name)
        if existing and existing.file_hash == file_hash:
            return False

        # Parser le fichier
        parser = self.parser_factory.get_parser(str(file_path))
        if not parser:
            raise ValueError(f"Aucun parser disponible pour {file_path.name}")

        print(f"📥 Import de {file_path.name}...")
        context, ranges, range_hands = parser.parse(str(file_path))

        # Sauvegarder en base
        range_file = RangeFile(
            id=existing.id if existing else None,
            filename=file_path.name,
            file_hash=file_hash,
            imported_at=datetime.now(),
            last_modified=file_mtime,
            status='imported'
        )

        file_id = self.repository.save_range_file(range_file)
        context.file_id = file_id
        context_id = self.repository.save_range_context(context)

        # Mapper les ranges par leur clé pour les mains
        range_key_to_id = {}

        for range_obj in ranges:
            range_obj.context_id = context_id
            range_id = self.repository.save_range(range_obj)
            range_key_to_id[range_obj.range_key] = range_id

        # Sauvegarder les mains avec les bons IDs de range
        hands_count = 0
        for range_hand in range_hands:
            if hasattr(range_hand, '_temp_range_key'):
                range_key = range_hand._temp_range_key
                if range_key in range_key_to_id:
                    range_hand.range_id = range_key_to_id[range_key]
                    self.repository.save_range_hand(range_hand)
                    hands_count += 1

        print(f"✅ {file_path.name} importé:")
        print(f"   📋 Contexte: {context.name}")
        print(f"   🎯 {len(ranges)} ranges")
        print(f"   🃏 {hands_count} mains")
        print(f"   📊 Confiance: {context.confidence:.1%}")

        return True

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcule le hash MD5 du fichier"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def show_database_summary(self):
        """Affiche un résumé de ce qui est en base"""
        contexts = self.repository.get_all_contexts()

        print(f"\n📊 CONTENU DE LA BASE DE DONNÉES:")
        print(f"📁 {len(contexts)} contextes importés\n")

        for context in contexts:
            print(f"📋 {context.name}")
            print(f"   🎯 Confiance: {context.confidence:.1%}")

            if context.parsed_metadata:
                meta = context.parsed_metadata
                if 'hero_position' in meta:
                    print(f"   📍 Position: {meta['hero_position']}")
                if 'vs_position' in meta:
                    print(f"   🆚 Vs: {meta['vs_position']}")
                if 'action_types' in meta:
                    print(f"   ⚡ Actions: {', '.join(meta['action_types'])}")
            print()


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Point d'entrée principal"""
    print("🃏 IMPORTEUR DE RANGES POKER")
    print("=" * 50)

    # Configuration
    ranges_dir = "data/ranges"
    db_path = "data/poker_trainer.db"

    # Créer les dossiers si nécessaire
    Path("data").mkdir(exist_ok=True)
    Path(ranges_dir).mkdir(exist_ok=True)

    # Lancer l'import
    importer = RangeImporter(ranges_dir, db_path)
    importer.import_all_ranges()

    # Afficher résumé
    importer.show_database_summary()

    print("\n🎉 Import terminé!")
    print(f"📁 Base de données: {db_path}")
    print("💡 Placez vos fichiers JSON dans le dossier 'data/ranges/' et relancez ce script")


if __name__ == "__main__":
    main()