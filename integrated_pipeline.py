#!/usr/bin/env python3
"""
Script principal du pipeline intégré
Point d'entrée pour Flask et pour l'exécution autonome
"""

import sys
from pathlib import Path

# Ajouter le répertoire modules au path
modules_dir = Path(__file__).parent / "modules"
sys.path.insert(0, str(modules_dir))

from pipeline_runner import run_web_mode_pipeline, IntegratedPipeline


def main():
    """Point d'entrée principal"""
    try:
        # Lancer le pipeline en mode web
        result = run_web_mode_pipeline()

        # Afficher le résumé
        if result['success']:
            print(f"[SUCCESS] Pipeline terminé: {result['message']}")
            stats = result.get('stats', {})
            print(f"[STATS] Contextes prêts pour quiz: {stats.get('question_ready_contexts', 0)}")
        else:
            print(f"[ERROR] Pipeline échoué: {result.get('error', 'Erreur inconnue')}")
            return 1

        return 0

    except Exception as e:
        print(f"[FATAL] Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)