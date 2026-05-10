#!/bin/bash
# ==============================================================================
# Script de release — Poker Training
# Usage : bash release.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Lire la version
VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]')
if [ -z "$VERSION" ]; then
    echo "❌ Fichier VERSION introuvable ou vide"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🚀 Release Poker Training v$VERSION"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Vérifier que git est dispo
if ! command -v git &>/dev/null; then
    echo "⚠️  git non disponible — le tag ne sera pas créé"
    GIT_OK=false
else
    GIT_OK=true
fi

if [ "$GIT_OK" = true ]; then
    # Vérifier les modifications non committées
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "⚠️  Des modifications non committées existent :"
        git status --short
        echo ""
        read -rp "Continuer quand même ? [o/N] " confirm
        [[ "$confirm" != "o" && "$confirm" != "O" ]] && { echo "Annulé."; exit 0; }
        echo ""
    fi

    # Vérifier que le tag n'existe pas déjà
    if git tag -l "v$VERSION" | grep -q "v$VERSION"; then
        echo "❌ Le tag v$VERSION existe déjà en local"
        echo "   Mets à jour VERSION avec le prochain numéro puis relance"
        exit 1
    fi

    echo "📋 Résumé :"
    echo "   Version : v$VERSION"
    echo "   Commit  : $(git rev-parse --short HEAD)"
    echo "   Branche : $(git branch --show-current)"
else
    echo "📋 Version : v$VERSION"
fi

echo ""
read -rp "Créer le tag git v$VERSION et packager ? [o/N] " confirm
[[ "$confirm" != "o" && "$confirm" != "O" ]] && { echo "Annulé."; exit 0; }

# Tag git
if [ "$GIT_OK" = true ]; then
    echo ""
    echo "🏷️  Création du tag v$VERSION..."
    git tag -a "v$VERSION" -m "Release v$VERSION"
    echo "✅ Tag créé localement"
fi

# Build package Windows
echo ""
echo "📦 Lancement du packaging Windows..."
bash create_portable_windows.sh
echo ""

# Push du tag
if [ "$GIT_OK" = true ]; then
    read -rp "Pousser le tag v$VERSION sur origin ? [o/N] " push
    if [[ "$push" == "o" || "$push" == "O" ]]; then
        git push origin "v$VERSION"
        echo "✅ Tag poussé sur origin"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Release v$VERSION terminée !                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Prochaines étapes :"
echo "  1. Tester  : PokerTraining-Portable-v$VERSION/"
echo "  2. Zipper  : zip -r PokerTraining-Portable-v$VERSION.zip PokerTraining-Portable-v$VERSION/"
echo "  3. Bump    : éditer VERSION avec le prochain numéro (ex: 4.7.0)"
echo ""
