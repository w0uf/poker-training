# Poker Training 28092025

Interface web locale pour l'entraînement de ranges de poker avec pipeline intégré automatique.

## Vue d'ensemble

**poker-training** est une interface web locale permettant d'importer, standardiser et enrichir automatiquement des ranges de poker. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées et standardisées pour l'entraînement.

## Fonctionnalités

- Pipeline intégré automatique : import → standardisation → enrichissement en une seule opération
- Interface web Flask avec dashboard temps réel
- Architecture modulaire extensible
- Standardisation intelligente des noms et positions
- Enrichissement automatique des métadonnées (mode web sans interaction)
- Base SQLite optimisée avec index
- Analyse automatique des métadonnées (positions, actions)

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
pip install flask

# Créer structure de données
mkdir -p data/ranges
```

## Démarrage rapide

```bash
# 1. Placer vos fichiers JSON dans data/ranges/
cp mes_ranges/*.json data/ranges/

# 2. Lancer l'interface web
cd web/
python app.py

# 3. Accéder à l'interface
# http://localhost:5000

# 4. Cliquer sur "Import Pipeline" pour traitement complet
```

Le pipeline intégré traite automatiquement tous les aspects : import, standardisation des noms, enrichissement des métadonnées, et sauvegarde. Les contextes prêts pour l'entraînement sont immédiatement disponibles.

## Architecture

### Structure actuelle

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite principale
│   └── ranges/                   # Répertoire des fichiers JSON
├── web/
│   ├── app.py                    # Serveur Flask principal
│   └── templates/
│       └── dashboard.html        # Interface utilisateur principale
├── modules/                      # Architecture modulaire
│   ├── json_parser.py            # Extraction données JSON
│   ├── name_standardizer.py      # Standardisation noms et positions
│   ├── metadata_enricher.py      # Enrichissement automatique
│   ├── database_manager.py       # Gestion base de données
│   └── pipeline_runner.py        # Orchestrateur principal
├── integrated_pipeline.py        # Point d'entrée pipeline intégré
└── README.md
```

### Fichiers obsolètes

Les fichiers suivants ne sont plus utilisés avec l'architecture modulaire :
- `poker_training.py` (remplacé par le pipeline intégré)
- `range_name_standardizer.py` (remplacé par le module)
- `enrich_ranges.py` (remplacé par le module)
- `questions.py` (en cours de refactoring)
- Templates non utilisés : `import.html`, `enrich.html`, etc.

## Pipeline intégré

### Fonctionnement

Le pipeline traite chaque contexte de A à Z dans une seule boucle :

1. **Parsing JSON** : Extraction des ranges depuis les fichiers
2. **Standardisation** : Détection automatique des positions, actions, formats de table
3. **Enrichissement** : Ajout des métadonnées globales et génération des noms d'affichage
4. **Sauvegarde** : Persistance complète en base de données

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

### Fonctionnalités automatiques

- **Détection intelligente** : Positions, actions, formats de table
- **Enrichissement automatique** : Métadonnées par défaut (Cash Game, NLHE, 6max, 100bb)
- **Gestion d'erreurs** : Les contextes problématiques sont marqués en erreur
- **Architecture extensible** : Support futur pour GTO+, PIOSolver

## Standardisation automatique

### Positions détectées par format

- **5max**: UTG, CO, BTN, SB, BB
- **6max**: UTG, MP, CO, BTN, SB, BB  
- **9max**: UTG, UTG+1, MP, MP+1, LJ, HJ, CO, BTN, SB, BB
- **Heads-up**: BTN, BB

### Actions standardisées

- **Primaires**: open, call, 3bet, 4bet, fold, check, defense
- **Détection prioritaire** pour "defense" (gestion français/anglais)

### Exemples d'analyse

```
"5max open utg"     → table: 5max, hero: UTG, action: open
"BB Defense vs CO"  → hero: BB, vs: CO, action: defense
"CO 3Bet vs BTN"    → hero: CO, vs: BTN, action: 3bet
```

## Base de données

### Structure SQLite (auto-créée)

- `range_files`: Fichiers importés avec hash et timestamps
- `range_contexts`: Contextes de jeu avec métadonnées enrichies
- `ranges`: Ranges individuelles avec actions et couleurs
- `range_hands`: Mains avec fréquences

### Index optimisés

- Requêtes par range: `idx_range_hands_range_id`
- Recherche par main: `idx_range_hands_hand`
- Contextes par ID: `idx_ranges_context_id`

## Interface web

### Dashboard principal

- **Statistiques temps réel** : Fichiers, contextes, ranges, mains
- **Import Pipeline** : Bouton unique pour traitement complet
- **État des contextes** : Confiance et prêt pour quiz
- **Feedback visuel** : Progression et résultats en temps réel

### API REST

- `/api/import_pipeline` : Lance le pipeline complet
- `/api/debug/db` : Statistiques de base de données
- `/api/dashboard/contexts` : Liste des contextes avec métadonnées
- `/api/quiz/check` : Vérification de l'état pour le quiz (en développement)

## Test du pipeline standalone

```bash
# Test direct du pipeline
python integrated_pipeline.py

# Test avec statut seulement
python modules/pipeline_runner.py --status
```

## État du développement

### Composants fonctionnels

- Pipeline intégré avec architecture modulaire
- Interface web Flask responsive
- Standardiseur avec détection robuste
- Enrichisseur automatique (mode web)
- Base de données auto-créée avec relations optimisées
- Gestion d'erreurs avec continuité de traitement

### En développement

- Module questions (génération de quiz)
- Interface de validation pour cas ambigus
- Support formats supplémentaires (PIO, GTO+)
- Tests d'intégration complets

## Workflow de développement

```
JSON Sources → Pipeline intégré → Contextes question-ready
```

### Pipeline unifié

Le pipeline traite automatiquement chaque fichier JSON pour :
- **Import** et parsing des données
- **Standardisation** des noms selon le format détecté
- **Enrichissement** avec métadonnées par défaut
- **Validation** et marquage question-friendly
- **Sauvegarde** complète en base

### Résultat par contexte

- **Question-ready** : Contexte prêt pour l'entraînement
- **Erreur** : Contexte non exploitable (avec message d'erreur)

## Architecture modulaire

### Principes de conception

- **Responsabilité unique** : Chaque module a un rôle spécifique
- **Faible couplage** : Modules indépendants et réutilisables
- **Gestion d'erreurs** : Robustesse avec rollback automatique
- **Type hints** : Code auto-documenté
- **Tests unitaires** : Validation par composant

### Évolution

L'architecture modulaire facilite :
- Ajout de nouveaux formats d'import
- Amélioration des algorithmes de détection
- Intégration de nouvelles sources de données
- Tests et debugging ciblés

## Support

Pour les questions techniques ou les contributions, créez une issue sur GitHub.

## Licence

Projet sous licence libre - voir [LICENSE](LICENSE) pour plus de détails.

---

**Dernière mise à jour**: 28/09/2025 - Pipeline intégré opérationnel
