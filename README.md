# Poker Training



Interface web locale pour l'entraînement de ranges de poker avec import automatique et standardisation intelligente.

## Vue d'ensemble

**poker-training** est une interface web locale permettant d'importer, standardiser et s'entraîner sur des ranges de poker. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées et standardisées pour l'entraînement.

## Fonctionnalités

- Import automatique de fichiers JSON avec détection de changements
- Interface web Flask avec dashboard temps réel
- Standardisation intelligente des noms et positions
- Analyse automatique des métadonnées (positions, actions)
- Architecture modulaire extensible
- Base SQLite optimisée avec index

## Installation

### Prérequis

- Python 3.8+
- pip

### Installation rapide

```bash
# Cloner le repository
git clone https://github.com/w0uf/poker-training.git
cd poker-training

# Créer environnement virtuel
python3 -m venv mon_env
source mon_env/bin/activate

# Installer dépendances
pip install flask pathlib

# Créer structure de données
mkdir -p data/ranges
```

## Démarrage rapide

```bash
# 1. Placer vos fichiers JSON dans data/ranges/
cp mes_ranges/*.json data/ranges/

# 2. Import automatique
python poker_training.py

# 3. Standardisation (optionnel)
python range_name_standardizer.py

# 4. Interface web
cd web/
python app.py

# 5. Accéder à l'interface
# http://localhost:5000
```

## Architecture

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite principale
│   └── ranges/                   # Répertoire des fichiers JSON
├── web/
│   ├── app.py                    # Serveur Flask principal
│   └── templates/                # Interface utilisateur
├── poker_training.py             # Import des ranges
├── range_name_standardizer.py    # Standardisation
├── enrich_ranges.py              # Enrichissement métadonnées
└── questions.py                  # Génération de questions
```

## Système d'import

### Format JSON supporté

```json
{
  "data": {
    "ranges": {
      "1": { "name": "Call", "color": "#4CAF50" },
      "2": { "name": "3Bet", "color": "#F44336" }
    },
    "values": {
      "AKo": [1, 2],
      "AQs": [1]
    }
  }
}
```

### Fonctionnalités d'import

- **Détection de changements**: Hash MD5 pour éviter les réimports inutiles
- **Parsing intelligent**: Extraction automatique des métadonnées
- **Gestion d'erreurs**: Logs détaillés et validation
- **Architecture extensible**: Support futur pour GTO+, PIOSolver

## Standardisation automatique

### Positions détectées par format

- **5max**: UTG, CO, BTN, SB, BB
- **6max**: UTG, MP, CO, BTN, SB, BB  
- **9max**: UTG, UTG+1, MP, MP+1, LJ, HJ, CO, BTN, SB, BB
- **Heads-up**: BTN, BB

### Actions standardisées

- **Primaires**: call, fold, 3bet_value, 3bet_bluff, 4bet_value, 4bet_bluff
- **Spéciales**: squeeze_value, squeeze_bluff, open_raise, defense
- **Support**: check, shove, limp

### Exemples d'analyse

```
"5 Max-défense BB vs UTG"  → hero: BB, vs: UTG, action: defense
"CO Open 100bb"           → hero: CO, action: open
"3Bet vs BTN steal"        → action: 3bet, vs: BTN
```

## Base de données

### Structure SQLite

- `range_files`: Fichiers importés avec hash et timestamps
- `range_contexts`: Contextes de jeu avec métadonnées
- `ranges`: Ranges individuelles avec actions
- `range_hands`: Mains avec fréquences

### Index optimisés

- Requêtes par range: `idx_range_hands_range_id`
- Recherche par main: `idx_range_hands_hand`

## Interface web

### Pages disponibles

- **Dashboard**: Statistiques et aperçu général
- **Import**: Interface d'import avec logs temps réel
- **Enrichissement**: Gestion des métadonnées (en développement)

### API REST

L'interface expose des endpoints pour l'intégration externe (documentation à venir).

## État du développement

### Composants fonctionnels

- Système d'import modulaire avec Repository pattern
- Interface web Flask avec templates responsive  
- Standardiseur sécurisé avec validation complète
- Base de données avec relations optimisées
- Analyse automatique des métadonnées

### En développement

- Enrichissement V4 des métadonnées
- Intégration web complète
- Système de génération de questions
- Tests d'intégration

## Workflow de développement

```
JSON Sources → Import → Base SQLite → Standardisation → Enrichissement → Questions → Entraînement
```

## Contribution

Ce projet utilise les bonnes pratiques suivantes :

- **Repository pattern** pour l'accès aux données
- **Factory pattern** pour les parsers extensibles
- **Type hints** systématiques
- **Validation robuste** à chaque étape
- **Gestion d'erreurs** avec rollback automatique
- **Documentation** des fonctions critiques

## Sessions de développement planifiées

### Prochaines étapes

1. **Tests d'intégration Flask**: Validation du workflow complet via interface web
2. **Correction encodage UTF-8**: Standardisation sur tout le projet
3. **Enrichissement V4**: Interface web pour les métadonnées
4. **Génération de questions**: Pipeline complet d'entraînement

## Support

Pour les questions techniques ou les contributions, créez une issue sur GitHub.

## Licence

Projet sous licence libre - voir [LICENSE](LICENSE) pour plus de détails.

---

**Dernière mise à jour**: 25/09/2025 - Standardiseur sécurisé validé
