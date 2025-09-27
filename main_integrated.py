#!/usr/bin/env python3
"""
Script principal pour le nouveau workflow intégré
Architecture: poker-training/main_integrated.py

Workflow: JSON → Import (standardisation + enrichissement) → Validation
Prépare pour: Module Questions (étape suivante)
"""

import argparse
import sys
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('poker_training.log')
    ]
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Vérifie les dépendances et l'état du projet"""
    issues = []

    # Vérification de la structure des répertoires
    required_dirs = ['data', 'data/ranges', 'web', 'web/templates']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Répertoire manquant: {dir_path}")

    # Vérification des modules Python
    try:
        import flask
    except ImportError:
        issues.append("Flask non installé: pip install flask")

    # Vérification des modules existants
    modules_status = {}
    try:
        import range_name_standardizer
        modules_status['standardizer'] = '✅ Disponible'
    except ImportError:
        modules_status['standardizer'] = '⚠️  Non trouvé (fallback utilisé)'

    try:
        import enrich_ranges
        modules_status['enricher'] = '✅ Disponible'
    except ImportError:
        modules_status['enricher'] = '⚠️  Non trouvé (fallback utilisé)'

    return issues, modules_status


def setup_project():
    """Configuration initiale du projet"""
    print("🔧 Configuration du projet...")

    # Création des répertoires nécessaires
    dirs_to_create = [
        'data',
        'data/ranges',
        'web',
        'web/templates',
        'web/static',
        'logs'
    ]

    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {dir_path}")

    # Création d'un fichier de configuration
    config_content = """# Configuration Poker Training Pipeline Intégré
# Généré automatiquement

[database]
path = data/poker_trainer.db

[import]
directory = data/ranges/
backup_on_import = true

[pipeline]
version = 2.0_integrated
use_existing_modules = true
fallback_on_error = true

[web]
host = 0.0.0.0
port = 5000
debug = true
"""

    with open('config.ini', 'w') as f:
        f.write(config_content)

    print("   ✓ config.ini créé")
    print("✅ Configuration terminée")


def run_import_pipeline(directory: str = "data/ranges/"):
    """Exécute le pipeline d'import intégré"""
    try:
        from integrated_import_v2 import IntegratedImportPipeline

        print("🚀 Lancement du pipeline d'import intégré...")
        pipeline = IntegratedImportPipeline()

        # Exécution
        results = pipeline.process_directory(directory)

        # Résumé
        total = len(results)
        compatible = sum(1 for r in results.values() if r.is_compatible)

        print(f"\n📊 Import terminé: {compatible}/{total} contextes compatibles")
        return True, results

    except ImportError:
        print("❌ Module pipeline non trouvé. Exécutez d'abord: python integrated_import_v2.py")
        return False, {}
    except Exception as e:
        print(f"❌ Erreur lors de l'import: {e}")
        return False, {}


def start_web_interface():
    """Lance l'interface web"""
    try:
        print("🌐 Démarrage de l'interface web...")

        # Import et lancement de Flask
        from web.app_integrated import app
        app.run(debug=True, host='0.0.0.0', port=5000)

    except ImportError:
        print("❌ Interface web non trouvée. Vérifiez le fichier web/app_integrated.py")
    except Exception as e:
        print(f"❌ Erreur interface web: {e}")


def show_status():
    """Affiche l'état actuel du projet"""
    print("📋 ÉTAT DU PROJET POKER TRAINING")
    print("=" * 50)

    # Vérification des dépendances
    issues, modules_status = check_dependencies()

    print("🔧 Modules existants:")
    for module, status in modules_status.items():
        print(f"   {status} {module}")

    print(f"\n📁 Structure projet:")
    structure_ok = len(issues) == 0
    print(f"   {'✅' if structure_ok else '❌'} Répertoires: {'OK' if structure_ok else 'Issues détectées'}")

    if issues:
        print("\n⚠️  Issues à résoudre:")
        for issue in issues:
            print(f"   - {issue}")

    # État de la base de données
    db_path = Path("data/poker_trainer.db")
    print(f"\n💾 Base de données: {'✅ Existe' if db_path.exists() else '❌ Absente'}")

    # Contextes disponibles
    ranges_dir = Path("data/ranges")
    if ranges_dir.exists():
        json_files = list(ranges_dir.glob("*.json"))
        print(f"📄 Fichiers JSON: {len(json_files)} trouvés")
    else:
        print("📄 Fichiers JSON: Répertoire data/ranges/ absent")

    print(f"\n🎯 Étapes suivantes:")
    print(f"   1. ✅ Pipeline intégré (JSON → Import → Validation)")
    print(f"   2. 🔄 Module Questions (en préparation)")
    print(f"   3. 🎮 Interface d'entraînement (à venir)")


def main():
    """Point d'entrée principal avec gestion des arguments"""
    parser = argparse.ArgumentParser(
        description="Poker Training - Pipeline Intégré v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main_integrated.py status              # Afficher l'état
  python main_integrated.py setup               # Configuration initiale  
  python main_integrated.py import              # Lancer l'import
  python main_integrated.py web                 # Interface web
  python main_integrated.py workflow            # Pipeline complet
        """
    )

    parser.add_argument('command',
                        choices=['status', 'setup', 'import', 'web', 'workflow'],
                        help='Commande à exécuter')

    parser.add_argument('--directory', '-d',
                        default='data/ranges/',
                        help='Répertoire des fichiers JSON (défaut: data/ranges/)')

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Mode verbose')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("🎯 POKER TRAINING - PIPELINE INTÉGRÉ v2.0")
    print("=" * 50)

    # Exécution selon la commande
    if args.command == 'status':
        show_status()

    elif args.command == 'setup':
        setup_project()
        print("\n💡 Prochaine étape: python main_integrated.py import")

    elif args.command == 'import':
        success, results = run_import_pipeline(args.directory)
        if success:
            print("\n💡 Prochaine étape: python main_integrated.py web")
        else:
            print("\n💡 Résolvez les erreurs puis relancez l'import")

    elif args.command == 'web':
        start_web_interface()

    elif args.command == 'workflow':
        print("🔄 Exécution du workflow complet...\n")

        # 1. Vérification
        issues, _ = check_dependencies()
        if issues:
            print("❌ Résolvez d'abord les dépendances avec: python main_integrated.py setup")
            return

        # 2. Import
        success, results = run_import_pipeline(args.directory)
        if not success:
            print("❌ Échec de l'import, arrêt du workflow")
            return

        # 3. Proposition interface web
        compatible_count = sum(1 for r in results.values() if r.is_compatible)
        if compatible_count > 0:
            print(f"\n✅ Workflow terminé ! {compatible_count} contextes prêts")
            print("💡 Lancez l'interface web: python main_integrated.py web")
        else:
            print("\n⚠️  Aucun contexte compatible trouvé. Vérifiez vos fichiers JSON.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)