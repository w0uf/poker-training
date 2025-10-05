#!/usr/bin/env python3
"""
Orchestrateur principal du pipeline intégré
Traite chaque contexte de A à Z dans une seule boucle
"""

from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# Ajouter le répertoire modules au path si nécessaire
sys.path.append(str(Path(__file__).parent))

from json_parser import JSONRangeParser, scan_json_files
from name_standardizer import NameStandardizer
from metadata_enricher import MetadataEnricher, create_auto_enricher
from database_manager import DatabaseManager


class PipelineResult:
    """Résultat du pipeline pour un contexte"""

    def __init__(self, filename: str):
        self.filename = filename
        self.success = False
        self.steps_completed = []
        self.error_message = ""
        self.context_name = ""
        self.question_ready = False


class IntegratedPipeline:
    """Pipeline intégré pour traitement complet des contextes"""

    def __init__(self, ranges_dir: str = "data/ranges", db_path: str = "data/poker_trainer.db"):
        self.ranges_dir = Path(ranges_dir)
        self.db_path = db_path

        # Initialiser les composants
        self.parser = JSONRangeParser()
        self.standardizer = NameStandardizer()
        self.enricher = create_auto_enricher()
        self.db_manager = DatabaseManager(db_path)

        print(f"[PIPELINE] Initialisé - Répertoire: {self.ranges_dir}")

    def run_complete_pipeline(self) -> Dict[str, Any]:
        """Exécute le pipeline complet sur tous les fichiers"""
        print(f"[PIPELINE] Démarrage du pipeline intégré")

        # Vérifier le répertoire source
        if not self.ranges_dir.exists():
            return {
                'success': False,
                'error': f'Répertoire {self.ranges_dir} introuvable',
                'results': []
            }

        # Scanner les fichiers à traiter
        files_to_process = self.db_manager.get_files_to_process(self.ranges_dir)

        if not files_to_process:
            print(f"[PIPELINE] Aucun nouveau fichier à traiter")
            return {
                'success': True,
                'message': 'Aucun nouveau fichier à traiter',
                'results': [],
                'stats': self.db_manager.get_import_stats()
            }

        print(f"[PIPELINE] {len(files_to_process)} fichiers à traiter")

        # Traiter chaque fichier
        results = []
        success_count = 0
        error_count = 0

        for json_file in files_to_process:
            print(f"\n{'=' * 60}")
            print(f"[PIPELINE] Traitement: {json_file.name}")
            print(f"{'=' * 60}")

            result = self.process_single_file(json_file)
            results.append(result)

            if result.success:
                success_count += 1
                print(f"[PIPELINE] ✅ Succès: {json_file.name}")
            else:
                error_count += 1
                print(f"[PIPELINE] ❌ Échec: {json_file.name} - {result.error_message}")

        # Résumé final
        total_processed = len(files_to_process)
        print(f"\n{'=' * 60}")
        print(f"[PIPELINE] RÉSUMÉ FINAL")
        print(f"{'=' * 60}")
        print(f"Total traités: {total_processed}")
        print(f"Succès: {success_count}")
        print(f"Erreurs: {error_count}")

        # Statistiques finales
        final_stats = self.db_manager.get_import_stats()
        print(f"Contextes prêts pour quiz: {final_stats.get('question_ready_contexts', 0)}")

        return {
            'success': error_count == 0,
            'message': f'{success_count} fichiers traités avec succès, {error_count} erreurs',
            'results': results,
            'stats': final_stats
        }

    def process_single_file(self, json_file: Path) -> PipelineResult:
        """Traite un seul fichier de A à Z"""
        result = PipelineResult(json_file.name)

        try:
            # Étape 1: Parsing JSON
            print(f"[PIPELINE] Étape 1: Parsing JSON")
            parsed_context = self.parser.parse_file(json_file)

            if not parsed_context:
                result.error_message = "Échec parsing JSON"
                self.db_manager.mark_context_error(json_file.name, result.error_message)
                return result

            result.steps_completed.append("parsing")
            result.context_name = parsed_context.context_name
            print(f"[PIPELINE] ✅ Parsing réussi: {len(parsed_context.ranges)} ranges")

            # Étape 2: Standardisation
            print(f"[PIPELINE] Étape 2: Standardisation")
            standardized_metadata = self.standardizer.standardize(parsed_context.context_name)

            result.steps_completed.append("standardization")
            print(f"[PIPELINE] ✅ Standardisation réussie - Confiance: {standardized_metadata.confidence:.1%}")

            # Étape 3: Enrichissement
            print(f"[PIPELINE] Étape 3: Enrichissement")
            enriched_metadata = self.enricher.enrich(standardized_metadata, parsed_context.ranges)

            result.steps_completed.append("enrichment")
            result.question_ready = enriched_metadata.question_friendly
            print(f"[PIPELINE] ✅ Enrichissement réussi - Question-ready: {enriched_metadata.question_friendly}")

            # Étape 4: Sauvegarde en base
            print(f"[PIPELINE] Étape 4: Sauvegarde base de données")

            # Nettoyer les anciens imports du même fichier s'ils existent
            self.db_manager.cleanup_old_imports(json_file.name)

            # Sauvegarder le nouveau contexte
            if self.db_manager.save_context_complete(parsed_context, enriched_metadata):
                result.steps_completed.append("database")
                result.success = True
                print(f"[PIPELINE] ✅ Sauvegarde réussie")
            else:
                result.error_message = "Échec sauvegarde base de données"
                print(f"[PIPELINE] ❌ Échec sauvegarde")

        except Exception as e:
            result.error_message = f"Erreur inattendue: {str(e)}"
            print(f"[PIPELINE] ❌ Erreur: {e}")

            # Marquer en erreur dans la base
            self.db_manager.mark_context_error(json_file.name, result.error_message)

        return result

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Récupère le statut actuel du pipeline"""
        stats = self.db_manager.get_import_stats()

        # Ajouter des informations sur les fichiers disponibles
        all_json_files = scan_json_files(self.ranges_dir)
        files_to_process = self.db_manager.get_files_to_process(self.ranges_dir)

        return {
            'ranges_directory': str(self.ranges_dir),
            'ranges_directory_exists': self.ranges_dir.exists(),
            'total_json_files': len(all_json_files),
            'files_to_process': len(files_to_process),
            'database_stats': stats,
            'ready_for_quiz': stats.get('question_ready_contexts', 0) > 0
        }


def run_web_mode_pipeline() -> Dict[str, Any]:
    """Point d'entrée pour le mode web"""
    # Définir les variables d'environnement pour le mode web
    os.environ['POKER_WEB_MODE'] = '1'

    pipeline = IntegratedPipeline()
    return pipeline.run_complete_pipeline()


if __name__ == "__main__":
    # Mode console - pour tests
    import argparse

    parser = argparse.ArgumentParser(description='Pipeline intégré poker training')
    parser.add_argument('--ranges-dir', default='../data/ranges', help='Répertoire des fichiers JSON')
    parser.add_argument('--db-path', default='../data/poker_trainer.db', help='Chemin base de données')
    parser.add_argument('--status', action='store_true', help='Afficher le statut seulement')

    args = parser.parse_args()

    pipeline = IntegratedPipeline(args.ranges_dir, args.db_path)

    if args.status:
        status = pipeline.get_pipeline_status()
        print("\n=== STATUT PIPELINE ===")
        for key, value in status.items():
            print(f"{key}: {value}")
    else:
        result = pipeline.run_complete_pipeline()
        print(f"\nRésultat final: {result['success']}")
        if not result['success']:
            print(f"Erreur: {result.get('error', 'Erreurs multiples')}")