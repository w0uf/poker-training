# Poker Training

Interface web locale pour travailler des ranges au poker.

## Vue d'ensemble

Le projet **poker-training** est une interface web locale permettant de travailler et d'entraîner des ranges de poker. Les ranges sont créées en format JSON via l'outil externe [Poker Range Editor](https://site2wouf.fr/poker-range-editor.php) puis importées dans l'application pour l'entraînement.

## Architecture du projet

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite principale
│   └── ranges/                   # Répertoire des fichiers JSON
│       ├── 5_Max-defense_BB_vs_steal.json
│       ├── 5 Max-défense BB vs steal.json
│       └── [autres fichiers ranges...]
├── web/
│   ├── app.py                    # Serveur Flask principal
│   └── templates/
│       ├── dashboard.html        # Page d'accueil avec stats
│       ├── import.html           # Interface d'import
│       ├── enrich.html          # Interface d'enrichissement
│       └── template.html        # Template de base
├── poker_training.py             # Script d'import des ranges
├── enrich_ranges.py              # Script d'enrichissement métadonnées
├── questions.py                  # Système de génération de questions
├── debug-validation.py           # Outils de debug
├── range_name_standardizer.py    # Standardisation noms de ranges
├── valid_system.py               # Validation système
└── test.py                       # Tests
```

## Composants principaux

### 1. Interface Web (Flask)
- **Serveur**: `web/app.py`
- **URL locale**: http://localhost:5000
- **Pages**:
  - Dashboard: Statistiques temps réel
  - Import: Import automatique des ranges JSON
  - Enrichissement: Gestion des métadonnées

### 2. Système d'import (`poker_training.py`)
- Import automatique des fichiers JSON depuis `data/ranges/`
- Parsing et validation des ranges
- Stockage en base SQLite

### 3. Base de données SQLite (`data/poker_trainer.db`)
Structure des tables principales:
- `range_files`: Fichiers importés
- `range_contexts`: Contextes de jeu
- `ranges`: Ranges individuelles
- `range_hands`: Mains dans chaque range

### 4. Système d'enrichissement (`enrich_ranges.py`)
- Analyse automatique des métadonnées à partir des noms
- Génération de noms d'affichage
- Interface console interactive (V4)

## État actuel du projet

### ✅ Fonctionnel
- Interface web Flask opérationnelle
- Import automatique des ranges JSON
- Base SQLite avec 5 tables
- 15 contextes importés avec succès
- Dashboard avec statistiques temps réel
- Interface d'import avec logs

### 🔄 En développement
- Système d'enrichissement des métadonnées (V4)
- Interface web pour l'enrichissement
- Génération automatique de questions

### ❌ Problèmes identifiés
- 1 fichier JSON corrompu (corruption externe)
- Problèmes d'encodage UTF-8 dans `enrich_ranges.py`
- Interface d'enrichissement pas encore intégrée à Flask

## Source des données

Les ranges sont créées via l'outil externe:
**https://site2wouf.fr/poker-range-editor.php**

Format de sortie: fichiers JSON avec structure standardisée pour les ranges de poker.

## Installation et démarrage

```bash
# Activer l'environnement virtuel
source mon_env/bin/activate

# Lancer l'interface web
cd web/
python app.py

# Accéder à l'interface
# http://localhost:5000
```

## Utilisation

1. **Créer des ranges** avec l'éditeur en ligne
2. **Sauvegarder** les fichiers JSON dans `data/ranges/`
3. **Importer** via l'interface web ou le script
4. **Enrichir** les métadonnées pour l'entraînement
5. **S'entraîner** avec les questions générées

---

*README en construction - Projet en développement actif*
