#!/usr/bin/env python3
"""
Script pour identifier les fichiers JSON corrompus
"""

import json
import os
from pathlib import Path


def check_json_files(directory="data/ranges"):
    """Vérifie tous les fichiers JSON dans un dossier"""

    ranges_dir = Path(directory)

    if not ranges_dir.exists():
        print(f"Dossier {ranges_dir} n'existe pas")
        return

    json_files = list(ranges_dir.glob("*.json"))

    if not json_files:
        print(f"Aucun fichier JSON trouvé dans {ranges_dir}")
        return

    print(f"Vérification de {len(json_files)} fichiers JSON...")
    print("=" * 60)

    valid_files = []
    invalid_files = []

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)

            print(f"✅ {file_path.name}")
            valid_files.append(file_path.name)

        except json.JSONDecodeError as e:
            print(f"❌ {file_path.name}")
            print(f"   Erreur: {e}")
            print(f"   Ligne {e.lineno}, colonne {e.colno}")
            invalid_files.append(file_path.name)

        except Exception as e:
            print(f"⚠️  {file_path.name}")
            print(f"   Erreur lecture: {e}")
            invalid_files.append(file_path.name)

    print("\n" + "=" * 60)
    print(f"Résumé:")
    print(f"✅ Fichiers valides: {len(valid_files)}")
    print(f"❌ Fichiers invalides: {len(invalid_files)}")

    if invalid_files:
        print(f"\nFichiers à corriger:")
        for filename in invalid_files:
            print(f"  - {filename}")

    return valid_files, invalid_files


def fix_common_json_issues(file_path):
    """Essaie de corriger automatiquement des erreurs JSON communes"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Corrections communes
        fixes_made = []

        # Remplacer les virgules en fin d'objet/array
        if ',}' in content:
            content = content.replace(',}', '}')
            fixes_made.append("Virgules superflues avant }")

        if ',]' in content:
            content = content.replace(',]', ']')
            fixes_made.append("Virgules superflues avant ]")

        # Ajouter des guillemets manquants (basique)
        # Cette partie est plus complexe et nécessiterait une analyse plus fine

        if fixes_made:
            backup_path = str(file_path) + ".backup"
            # Faire une sauvegarde
            with open(backup_path, 'w', encoding='utf-8') as f:
                with open(file_path, 'r', encoding='utf-8') as orig:
                    f.write(orig.read())

            # Écrire la version corrigée
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Vérifier que c'est maintenant valide
            try:
                json.loads(content)
                print(f"✅ {file_path.name} corrigé automatiquement")
                print(f"   Corrections: {', '.join(fixes_made)}")
                print(f"   Sauvegarde: {backup_path}")
                return True
            except:
                # Restaurer la sauvegarde si ça ne marche pas
                with open(backup_path, 'r', encoding='utf-8') as f:
                    with open(file_path, 'w', encoding='utf-8') as orig:
                        orig.write(f.read())
                print(f"❌ Impossible de corriger automatiquement {file_path.name}")
                return False

        return False

    except Exception as e:
        print(f"Erreur lors de la tentative de correction: {e}")
        return False


def main():
    print("🔍 VÉRIFICATEUR DE FICHIERS JSON")
    print("=" * 40)

    # Vérifier les fichiers
    valid, invalid = check_json_files()

    # Proposer des corrections automatiques
    if invalid:
        print(f"\n🔧 Tentative de correction automatique...")

        for filename in invalid:
            file_path = Path("data/ranges") / filename
            print(f"\nTraitement de {filename}...")
            fix_common_json_issues(file_path)

        # Re-vérifier après corrections
        print(f"\n🔍 Re-vérification après corrections...")
        valid_after, invalid_after = check_json_files()

        if len(invalid_after) < len(invalid):
            print(f"🎉 {len(invalid) - len(invalid_after)} fichier(s) corrigé(s)!")

    print(f"\n💡 Une fois tous les fichiers corrigés, relancez l'import!")


if __name__ == "__main__":
    main()