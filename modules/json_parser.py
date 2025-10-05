#!/usr/bin/env python3
"""
Module d'extraction et parsing des fichiers JSON de ranges
Extrait les données brutes des fichiers pour traitement ultérieur
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RangeData:
    """Structure pour une range extraite"""
    name: str
    color: str
    hands: Dict[str, List[int]]  # main -> liste des range_keys


@dataclass
class ParsedContext:
    """Contexte parsé depuis un fichier JSON"""
    filename: str
    file_hash: str
    context_name: str
    ranges: List[RangeData]
    source_path: str


class JSONRangeParser:
    """Parser pour les fichiers JSON de ranges"""

    def __init__(self):
        self.supported_formats = ['range_editor', 'pio', 'gto+']

    def parse_file(self, file_path: Path) -> Optional[ParsedContext]:
        """Parse un fichier JSON et retourne le contexte extrait"""
        try:
            print(f"[PARSER] Analyse de {file_path.name}")

            # Lire le fichier et calculer le hash
            content = file_path.read_text(encoding='utf-8')
            file_hash = hashlib.md5(content.encode()).hexdigest()

            # Parser le JSON
            data = json.loads(content)

            # Détecter le format et extraire
            if self._is_range_editor_format(data):
                return self._parse_range_editor(file_path, file_hash, data)
            elif self._is_pio_format(data):
                return self._parse_pio(file_path, file_hash, data)
            else:
                print(f"[PARSER] Format non supporté pour {file_path.name}")
                return None

        except json.JSONDecodeError as e:
            print(f"[PARSER] Erreur JSON dans {file_path.name}: {e}")
            return None
        except Exception as e:
            print(f"[PARSER] Erreur lors du parsing de {file_path.name}: {e}")
            return None

    def _is_range_editor_format(self, data: Dict) -> bool:
        """Détecte le format range editor"""
        return (isinstance(data, dict) and
                'data' in data and
                isinstance(data['data'], dict) and
                'ranges' in data['data'] and
                'values' in data['data'])

    def _is_pio_format(self, data: Dict) -> bool:
        """Détecte le format PIO (à implémenter selon besoin)"""
        return False  # Placeholder

    def _parse_range_editor(self, file_path: Path, file_hash: str, data: Dict) -> ParsedContext:
        """Parse le format range editor"""
        range_data = data['data']
        ranges_def = range_data['ranges']
        values = range_data['values']

        # Extraire le nom du contexte (nom du fichier sans extension)
        context_name = file_path.stem

        # Créer les ranges
        ranges = []
        for range_key, range_info in ranges_def.items():
            range_hands = {}

            # Extraire les mains pour cette range
            for hand, range_keys in values.items():
                if int(range_key) in range_keys:
                    range_hands[hand] = range_keys

            ranges.append(RangeData(
                name=range_info['name'],
                color=range_info['color'],
                hands=range_hands
            ))

        return ParsedContext(
            filename=file_path.name,
            file_hash=file_hash,
            context_name=context_name,
            ranges=ranges,
            source_path=str(file_path)
        )

    def _parse_pio(self, file_path: Path, file_hash: str, data: Dict) -> ParsedContext:
        """Parse le format PIO (placeholder)"""
        # À implémenter selon les spécifications PIO
        pass

    def get_all_hands_from_ranges(self, ranges: List[RangeData]) -> List[str]:
        """Extrait toutes les mains uniques de toutes les ranges"""
        all_hands = set()
        for range_data in ranges:
            all_hands.update(range_data.hands.keys())
        return sorted(list(all_hands))


def scan_json_files(directory: Path) -> List[Path]:
    """Scanne un répertoire pour les fichiers JSON"""
    if not directory.exists():
        print(f"[PARSER] Répertoire {directory} introuvable")
        return []

    json_files = list(directory.glob("*.json"))
    print(f"[PARSER] {len(json_files)} fichiers JSON trouvés")
    return json_files


if __name__ == "__main__":
    # Test du parser
    parser = JSONRangeParser()
    test_dir = Path("../data/ranges")

    files = scan_json_files(test_dir)
    for file_path in files[:3]:  # Test sur les 3 premiers
        result = parser.parse_file(file_path)
        if result:
            print(f"Contexte: {result.context_name}")
            print(f"Ranges: {len(result.ranges)}")
            for r in result.ranges:
                print(f"  - {r.name}: {len(r.hands)} mains")
        print()