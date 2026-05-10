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

# Copier les bases de données vides (templates)
if [ -d "data" ]; then
    cp -r data/*.db "$OUTPUT_DIR/poker-training/data/" 2>/dev/null || echo "ℹ️  Pas de base de données à copier"
fi

# 3. Créer START.bat
echo "🎬 Création de START.bat..."
cat > "$OUTPUT_DIR/START.bat" << EOFBAT
@echo off
title Poker Training v$VERSION
color 0A

cls
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║          🃏  POKER TRAINING v$VERSION                             ║
echo ║          Entrainement de Ranges Preflop                       ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🚀 Demarrage du serveur...
echo.

REM Vérifier que Python est présent
if not exist "python\python.exe" (
    echo ❌ ERREUR: Python embarque non trouve !
    echo.
    echo 📝 Instructions:
    echo    1. Telecharger Python Embeddable depuis:
    echo       https://www.python.org/downloads/windows/
    echo    2. Chercher "Windows embeddable package (64-bit)"
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
    echo ❌ Erreur au demarrage !
    echo.
    echo 💡 Verifications:
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
    └── data/                    ← Bases de données
        ├── poker_trainer.db
        ├── quiz_history.db
        └── ranges/              ← VOS FICHIERS JSON ICI


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
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     INSTRUCTIONS D'INSTALLATION - PYTHON EMBARQUÉ              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

⚠️ CES INSTRUCTIONS SONT POUR LE CRÉATEUR DU PACKAGE
   Les utilisateurs finaux n'ont qu'à double-cliquer sur START.bat


📦 ÉTAPE 1 : TÉLÉCHARGER PYTHON EMBEDDABLE
═══════════════════════════════════════════════════════════════

1. Aller sur : https://www.python.org/downloads/windows/

2. Chercher "Windows embeddable package (64-bit)"
   Version recommandée : Python 3.11.x

3. Télécharger le fichier (environ 10 MB)
   Exemple : python-3.11.6-embed-amd64.zip


📂 ÉTAPE 2 : EXTRAIRE DANS LE DOSSIER PYTHON/
═══════════════════════════════════════════════════════════════

1. Créer le dossier "python\" s'il n'existe pas

2. Extraire TOUT le contenu du .zip dans ce dossier

3. Vérifier que vous avez :
   python\
   ├── python.exe       ← Important !
   ├── python311.dll
   ├── pythonw.exe
   └── ... autres fichiers


📦 ÉTAPE 3 : INSTALLER PIP
═══════════════════════════════════════════════════════════════

1. Télécharger get-pip.py depuis :
   https://bootstrap.pypa.io/get-pip.py

2. Copier get-pip.py dans le dossier python\

3. Ouvrir un terminal (CMD) dans PokerTraining-Portable-vX.X.X\

4. Exécuter :
   python\python.exe python\get-pip.py


🔧 ÉTAPE 4 : INSTALLER FLASK
═══════════════════════════════════════════════════════════════

Dans le même terminal, exécuter :

python\python.exe -m pip install flask --target python\Lib\site-packages

Attendre la fin de l'installation (quelques secondes).


✅ ÉTAPE 5 : VÉRIFIER L'INSTALLATION
═══════════════════════════════════════════════════════════════

1. Double-cliquer sur START.bat

2. Si le serveur démarre → C'est bon ! ✅

3. Sinon, vérifier :
   - python\python.exe existe
   - python\Lib\site-packages\flask\ existe
   - Pas d'erreur dans le terminal


📦 ÉTAPE 6 : CRÉER LE ZIP FINAL
═══════════════════════════════════════════════════════════════

1. Fermer l'application (si elle tourne)

2. Sélectionner TOUT le dossier PokerTraining-Portable-vX.X.X\

3. Clic droit → Envoyer vers → Dossier compressé

   OU avec 7-Zip :
   7z a PokerTraining-Portable-v$VERSION.zip PokerTraining-Portable-v$VERSION\

4. Le fichier final devrait faire environ 80-120 MB


🚀 ÉTAPE 7 : DISTRIBUER
═══════════════════════════════════════════════════════════════

Option 1 : GitHub Releases
   - Créer une nouvelle release
   - Uploader le .zip
   - Ajouter le changelog

Option 2 : Hébergement direct
   - Uploader sur votre serveur
   - Partager le lien

Option 3 : Les deux
   - GitHub pour les développeurs
   - Hébergement pour les utilisateurs


📋 CHECKLIST FINALE
═══════════════════════════════════════════════════════════════

Avant de distribuer, vérifier :

☐ python\python.exe existe et fonctionne
☐ Flask est installé (python\Lib\site-packages\flask\)
☐ START.bat lance l'application sans erreur
☐ http://localhost:5000 affiche l'interface
☐ README.txt est clair et complet
☐ Le .zip se décompresse correctement
☐ Test sur un autre PC Windows si possible


💡 CONSEILS
═══════════════════════════════════════════════════════════════

- Testez sur Windows 10 ET Windows 11
- Testez avec l'antivirus activé
- Vérifiez que le port 5000 n'est pas bloqué
- Ajoutez un .gitignore pour python/ (fichiers volumineux)


🐛 EN CAS DE PROBLÈME
═══════════════════════════════════════════════════════════════

Erreur pip :
   → Télécharger get-pip.py manuellement
   → https://bootstrap.pypa.io/get-pip.py

Erreur Flask :
   → Installer avec --no-deps d'abord :
     python\python.exe -m pip install flask --no-deps --target python\Lib\site-packages
   → Puis installer les dépendances une par une

Antivirus bloque :
   → Ajouter python.exe aux exceptions
   → Ou signer le .exe avec un certificat (avancé)


═══════════════════════════════════════════════════════════════

Version : $VERSION
Dernière mise à jour : $(date +%d/%m/%Y)
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
