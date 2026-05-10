#!/bin/bash
# ==============================================================================
# Script de création du package portable Windows
# Poker Training — version lue depuis ./VERSION
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null | tr -d '[:space:]')
if [ -z "$VERSION" ]; then
    echo "❌ Fichier VERSION introuvable — créer un fichier VERSION à la racine"
    exit 1
fi
OUTPUT_DIR="PokerTraining-Portable-v$VERSION"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  📦 Création du package portable Windows                       ║"
echo "║  Version: $VERSION                                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Nettoyer si existe déjà
if [ -d "$OUTPUT_DIR" ]; then
    echo "🗑️  Nettoyage de l'ancien package..."
    rm -rf "$OUTPUT_DIR"
fi

# 1. Créer la structure
echo "📁 Création de la structure..."
mkdir -p "$OUTPUT_DIR/poker-training/web"
mkdir -p "$OUTPUT_DIR/poker-training/modules"
mkdir -p "$OUTPUT_DIR/poker-training/data/ranges"
mkdir -p "$OUTPUT_DIR/python"

# 2. Copier l'application
echo "📋 Copie de l'application..."
cp -r web/* "$OUTPUT_DIR/poker-training/web/" 2>/dev/null || echo "⚠️  Dossier web/ non trouvé"
cp -r modules/* "$OUTPUT_DIR/poker-training/modules/" 2>/dev/null || echo "⚠️  Dossier modules/ non trouvé"

# Copier les fichiers de données (ranges JSON uniquement, pas les BDD — elles sont créées au premier démarrage)
if [ -d "data/ranges" ]; then
    cp -r data/ranges "$OUTPUT_DIR/poker-training/data/" 2>/dev/null || echo "ℹ️  Pas de ranges à copier"
fi

# Copier VERSION dans poker-training/ pour que app.py puisse la lire (Path(__file__).parent.parent)
cp "$SCRIPT_DIR/VERSION" "$OUTPUT_DIR/poker-training/VERSION"

# 3. Créer START.bat
echo "🎬 Création de START.bat..."
cat > "$OUTPUT_DIR/START.bat" << EOFBAT
@echo off
title Poker Training v$VERSION
color 0A

cls
echo ================================================
echo.
echo   POKER TRAINING v$VERSION
echo   Entrainement de Ranges Preflop
echo.
echo ================================================
echo.
echo Demarrage du serveur...
echo.

REM Verifier que Python est present
if not exist "python\python.exe" (
    echo ERREUR: Python embarque non trouve !
    echo.
    echo Instructions:
    echo    1. Lire INSTRUCTIONS.txt
    echo    2. Telecharger Python Embeddable
    echo       https://www.python.org/downloads/windows/
    echo    3. Extraire dans le dossier "python\"
    echo    4. Installer Flask (voir INSTRUCTIONS.txt^)
    echo.
    pause
    exit /b 1
)

REM Lancer l'application
cd poker-training\web
..\..\python\python.exe app.py

REM Si erreur
if errorlevel 1 (
    echo.
    echo Erreur au demarrage !
    echo.
    echo Verifications:
    echo    - Flask est-il installe ? (voir INSTRUCTIONS.txt^)
    echo    - Le port 5000 est-il libre ?
    echo    - L'antivirus bloque-t-il python.exe ?
    echo.
)

pause
EOFBAT

# 4. Créer README.txt pour utilisateurs Windows
echo "📄 Création de README.txt..."
cat > "$OUTPUT_DIR/README.txt" << EOFREADME
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║          🃏  POKER TRAINING v$VERSION                             ║
║          Version Portable pour Windows                         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝


🚀 DÉMARRAGE RAPIDE
═══════════════════════════════════════════════════════════════

1. Double-cliquer sur START.bat

2. Une fenêtre noire s'ouvre → NE PAS LA FERMER !

3. Ouvrir votre navigateur web sur :
   → http://localhost:5000

4. C'est parti ! 🎉


📋 PREMIÈRE UTILISATION
═══════════════════════════════════════════════════════════════

1. Aller sur : http://localhost:5000/import

2. Cliquer sur "Import Pipeline"

3. Vos fichiers JSON doivent être dans :
   poker-training\data\ranges\

4. Suivre le workflow :
   Import → Validation → Configuration → Quiz !


📁 STRUCTURE DES FICHIERS
═══════════════════════════════════════════════════════════════

PokerTraining-Portable-v$VERSION/
├── START.bat                    ← LANCER L'APPLICATION
├── README.txt                   ← Ce fichier
├── INSTRUCTIONS.txt             ← Installation de Python
├── python/                      ← Python embarqué
│   └── python.exe
└── poker-training/              ← L'application
    ├── web/                     ← Serveur Flask
    ├── modules/                 ← Modules Python
    └── data/                    ← Données
        └── ranges/              ← VOS FICHIERS JSON ICI
            (les bases de données sont créées automatiquement au premier démarrage)


🎯 IMPORTER VOS RANGES
═══════════════════════════════════════════════════════════════

1. Créer vos ranges sur :
   https://site2wouf.fr/poker-range-editor.php

2. Télécharger les fichiers JSON

3. Copier les fichiers dans :
   poker-training\data\ranges\

4. Dans l'application, aller sur "Import Pipeline"


🛑 ARRÊTER L'APPLICATION
═══════════════════════════════════════════════════════════════

Option 1 : Fermer la fenêtre noire (terminal)
Option 2 : Dans la fenêtre noire, appuyer sur CTRL+C


🐛 PROBLÈMES FRÉQUENTS
═══════════════════════════════════════════════════════════════

❌ "Python embarqué non trouvé"
   → Suivre les instructions dans INSTRUCTIONS.txt
   → Python doit être dans le dossier "python\"

❌ "Port 5000 déjà utilisé"
   → Fermer toutes les applications qui utilisent ce port
   → Ou modifier le port dans poker-training\web\app.py
   → Ligne : app.run(debug=True, port=5001)

❌ "Erreur au démarrage"
   → Vérifier que Flask est installé (voir INSTRUCTIONS.txt)
   → Vérifier que l'antivirus ne bloque pas python.exe
   → Ajouter une exception dans l'antivirus si nécessaire

❌ "Pas de données dans l'historique"
   → Faire au moins un quiz complet
   → Les données s'afficheront ensuite

❌ "Erreur d'import des ranges"
   → Vérifier que les fichiers JSON sont bien formatés
   → Ils doivent venir de l'éditeur officiel
   → https://site2wouf.fr/poker-range-editor.php


📊 FONCTIONNALITÉS
═══════════════════════════════════════════════════════════════

✅ Quiz simple et drill-down multi-étapes
✅ 3 niveaux d'agressivité (LOW/MEDIUM/HIGH)
✅ Historique complet de vos sessions
✅ Graphiques de progression
✅ Stats par contexte
✅ Recommandations personnalisées
✅ Export CSV des résultats
✅ Calcul du streak (jours consécutifs)


🔗 LIENS UTILES
═══════════════════════════════════════════════════════════════

📝 Éditeur de ranges :
   https://site2wouf.fr/poker-range-editor.php

💻 GitHub :
   https://github.com/w0uf/poker-training

📧 Support :
   Ouvrir une issue sur GitHub


📄 LICENCE
═══════════════════════════════════════════════════════════════

Projet open-source sous licence libre.


═══════════════════════════════════════════════════════════════

Bon entraînement ! 🃏

Version : $VERSION
Date : $(date +%d/%m/%Y)
EOFREADME

# 5. Créer INSTRUCTIONS.txt (installation Python)
echo "📄 Création de INSTRUCTIONS.txt..."
cat > "$OUTPUT_DIR/INSTRUCTIONS.txt" << EOFINST
================================================
  POKER TRAINING v$VERSION
  Installation de Python (premiere utilisation)
================================================

Cette etape est OBLIGATOIRE uniquement si le dossier "python\" est absent.
Si START.bat fonctionne deja, vous pouvez ignorer ce fichier.


ETAPE 1 : TELECHARGER PYTHON
================================================

1. Aller sur : https://www.python.org/downloads/windows/

2. Faire defiler jusqu'a "Python 3.11.x"

3. Cliquer sur "Windows embeddable package (64-bit)"
   (fichier d'environ 10 MB, exemple : python-3.11.9-embed-amd64.zip)

4. Telecharger le fichier .zip


ETAPE 2 : INSTALLER PYTHON DANS LE DOSSIER "python\"
================================================

1. Creer le dossier "python\" dans ce dossier si absent

2. Extraire TOUT le contenu du .zip dans "python\"

3. Verifier que "python\python.exe" existe


ETAPE 3 : INSTALLER PIP
================================================

1. Telecharger get-pip.py :
   https://bootstrap.pypa.io/get-pip.py

2. Copier get-pip.py dans le dossier "python\"

3. Ouvrir une invite de commande (CMD) dans ce dossier :
   - Maintenir Shift + clic droit dans l'explorateur
   - Choisir "Ouvrir la fenetre de commandes ici"

4. Taper la commande suivante et appuyer sur Entree :
   python\python.exe python\get-pip.py


ETAPE 4 : INSTALLER FLASK
================================================

Dans la meme invite de commande, taper :

   python\python.exe -m pip install flask --target python\Lib\site-packages

Attendre la fin (environ 30 secondes).


ETAPE 5 : LANCER L'APPLICATION
================================================

Double-cliquer sur START.bat

Une fenetre noire s'ouvre : NE PAS LA FERMER.

Ouvrir votre navigateur sur : http://localhost:5000


EN CAS DE PROBLEME
================================================

"Python embarque non trouve"
   -> Verifier que python\python.exe existe (etape 2)

"Module flask not found"
   -> Recommencer l'etape 4

"Port 5000 deja utilise"
   -> Fermer les autres applications sur ce port
   -> Ou modifier le port dans poker-training\web\app.py

Antivirus bloque python.exe
   -> Ajouter une exception pour python.exe dans votre antivirus


================================================
Version : $VERSION
================================================
EOFINST

# 6. Créer un .gitignore pour le package
echo "🚫 Création de .gitignore..."
cat > "$OUTPUT_DIR/.gitignore" << 'EOFGIT'
# Python embarqué (trop volumineux pour Git)
python/

# Bases de données avec données utilisateur
poker-training/data/*.db

# Fichiers temporaires
*.pyc
__pycache__/
*.log

# OS
.DS_Store
Thumbs.db
EOFGIT

# 7. Créer un fichier VERSION
echo "$VERSION" > "$OUTPUT_DIR/VERSION"

# 8. Créer un changelog spécifique à la release portable
echo "📝 Création de CHANGELOG.txt..."
cat > "$OUTPUT_DIR/CHANGELOG.txt" << EOFCHANGELOG
═══════════════════════════════════════════════════════════════
  CHANGELOG - Poker Training Portable
═══════════════════════════════════════════════════════════════

Version $VERSION - Release ($(date +%d/%m/%Y))
────────────────────────────────────────────────────────────

🎉 PREMIÈRE VERSION PORTABLE POUR WINDOWS

✨ Nouvelles fonctionnalités :
  • Système de progression complet avec historique
  • Graphiques d'évolution des performances
  • Stats détaillées par contexte
  • Recommandations personnalisées
  • Calcul du streak (jours consécutifs)
  • Mini-graphique sur page de résultats
  • Export CSV des résultats

🎯 Quiz intelligent :
  • Questions simples et drill-down multi-étapes
  • 3 niveaux d'agressivité (LOW/MEDIUM/HIGH)
  • Feedback immédiat
  • Sauvegarde automatique

📊 Analytics :
  • Meilleur score, score moyen
  • Graphiques de progression
  • Filtres par date, score, contexte
  • Vue d'ensemble complète

🔧 Technique :
  • Version portable standalone
  • Pas d'installation Python requise
  • Double-clic pour lancer
  • Base de données SQLite


Version 4.4.2 (31/10/2025)
────────────────────────────────────────────────────────────

🐛 Corrections :
  • Skip all-in uniquement en mode HIGH
  • Arrêt automatique après all-in
  • Support complet du niveau 3


Version 4.4.0 (30/10/2025)
────────────────────────────────────────────────────────────

✨ Nouvelles fonctionnalités :
  • Système d'agressivité avec 3 niveaux
  • Widget de sélection dans l'interface
  • Configuration centralisée


Version 4.3.7 (28/10/2025)
────────────────────────────────────────────────────────────

✨ Nouvelles fonctionnalités :
  • Tracking intelligent par contexte
  • Évite les répétitions dans le même contexte


═══════════════════════════════════════════════════════════════
EOFCHANGELOG

# 9. Résumé final
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Package créé avec succès !                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Dossier créé : $OUTPUT_DIR"
echo ""
echo "📋 Fichiers créés :"
echo "   ✅ START.bat              - Lance l'application"
echo "   ✅ README.txt             - Guide utilisateur"
echo "   ✅ INSTRUCTIONS.txt       - Installation Python"
echo "   ✅ CHANGELOG.txt          - Historique des versions"
echo "   ✅ .gitignore             - Exclut Python de Git"
echo ""
echo "📁 Structure :"
echo "   📂 poker-training/        - L'application"
echo "   📂 python/                - ⚠️  À COMPLÉTER (voir INSTRUCTIONS.txt)"
echo ""
echo "🎯 Prochaines étapes :"
echo ""
echo "   1. Installer Python embarqué (voir INSTRUCTIONS.txt) :"
echo "      - Télécharger Python Embeddable"
echo "      - Extraire dans $OUTPUT_DIR/python/"
echo "      - Installer Flask"
echo ""
echo "   2. Tester :"
echo "      cd $OUTPUT_DIR"
echo "      Double-cliquer sur START.bat"
echo ""
echo "   3. Compresser en ZIP :"
echo "      zip -r $OUTPUT_DIR.zip $OUTPUT_DIR/"
echo "      ou"
echo "      7z a $OUTPUT_DIR.zip $OUTPUT_DIR/"
echo ""
echo "   4. Distribuer sur GitHub Releases ! 🚀"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
