# Poker Training - Système d'entraînement de ranges

Interface web locale pour l'entraînement de ranges de poker avec pipeline intégré, validation intelligente et génération de quiz.

## 🎯 Vue d'ensemble

**poker-training** est un système complet permettant d'importer, valider et utiliser des ranges de poker pour l'entraînement. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées, validées et préparées pour le quiz.

## ✨ Fonctionnalités principales

### Pipeline d'import automatique
- Import et parsing des fichiers JSON
- Standardisation intelligente des noms et positions
- Enrichissement automatique des métadonnées
- Détection des contextes nécessitant validation

### Système de validation avancé
- **Validation des métadonnées de contexte** : format de table, positions, actions
- **Classification des sous-ranges** : labels canoniques pour chaque range
- **Détection d'incohérences** : vérification de la cohérence action/sous-ranges
- **Score de confiance** : calculé selon le % de sous-ranges classifiés
- **Mise à jour JSON source** : synchronisation automatique des validations
- **Renommage automatique** : normalisation des noms de fichiers selon le slug

### Architecture hiérarchique des ranges
- **Range principale** : Action initiale (open, defense, 3bet, etc.)
- **Sous-ranges** : Réponses aux réactions adverses (call, 4bet, fold, etc.)
- **Labels canoniques** : Classification standardisée pour le quiz

### Interface web moderne
- Dashboard temps réel avec statistiques
- Interface de validation interactive
- Gestion des erreurs avec feedback visuel
- API REST complète

## 📦 Installation

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

## 🚀 Démarrage rapide

```bash
# 1. Placer vos fichiers JSON dans data/ranges/
cp mes_ranges/*.json data/ranges/

# 2. Lancer l'interface web
cd web/
python app.py

# 3. Accéder à l'interface
# http://localhost:5000

# 4. Importer les ranges via "Import Pipeline"

# 5. Valider les contextes nécessitant validation
# http://localhost:5000/validate?id=<context_id>
```

## 🏗️ Architecture

### Structure du projet

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite principale
│   └── ranges/                   # Fichiers JSON des ranges
├── web/
│   ├── app.py                    # Serveur Flask + API REST
│   └── templates/
│       ├── dashboard.html        # Dashboard principal
│       └── validate_context.html # Interface de validation
├── modules/
│   ├── json_parser.py            # Parsing des fichiers JSON
│   ├── name_standardizer.py      # Standardisation des noms
│   ├── metadata_enricher.py      # Enrichissement automatique
│   ├── database_manager.py       # Gestion base de données
│   ├── context_validator.py      # Validation des contextes
│   ├── pipeline_runner.py        # Orchestrateur principal
│   └── quiz_action_mapper.py     # Mapping actions pour quiz
├── integrated_pipeline.py        # Point d'entrée pipeline
└── README.md
```

### Base de données SQLite

#### Tables principales

- **range_files** : Fichiers importés avec hash et timestamps
- **range_contexts** : Contextes avec métadonnées enrichies
  - Colonnes dédiées : `table_format`, `hero_position`, `primary_action`, etc.
  - Statuts : `needs_validation`, `quiz_ready`, `confidence_score`
- **ranges** : Ranges individuelles avec classification
  - `range_key` : Position dans le fichier (1=principale, 2+=sous-ranges)
  - `label_canon` : Label standardisé (CALL, R4_VALUE, R4_BLUFF, etc.)
  - `name` : Nom lisible pour affichage
- **range_hands** : Mains avec fréquences

#### Index optimisés

```sql
idx_range_hands_range_id        -- Requêtes par range
idx_range_hands_hand            -- Recherche par main
idx_ranges_context_id           -- Contextes par ID
idx_ranges_label_canon          -- Filtrage par label
idx_ranges_context_label        -- Quiz queries (context + label)
```

## 🎲 Structure des ranges

### Architecture hiérarchique

```
Fichier JSON : "5max_utg_open.json"
├── Range 1 (principale) : OPEN
│   ├── AA, KK, QQ, ...
│   └── [Action initiale du héros]
├── Range 2 (sous-range) : CALL
│   ├── AQs, JJ, TT, ...
│   └── [Face à 3bet → call]
├── Range 3 (sous-range) : R4_VALUE
│   ├── AA, KK
│   └── [Face à 3bet → 4bet value]
└── Range 4 (sous-range) : R4_BLUFF
    ├── A5s
    └── [Face à 3bet → 4bet bluff]
```

### Labels canoniques

#### Actions principales
- **OPEN** : Range d'ouverture
- **CALL** : Call / Complete / Flat
- **CHECK** : Check
- **FOLD** : Fold
- **RAISE** : Raise générique

#### Actions de relance
- **R3_VALUE** : 3bet Value
- **R3_BLUFF** : 3bet Bluff
- **R4_VALUE** : 4bet Value
- **R4_BLUFF** : 4bet Bluff
- **R5_ALLIN** : 5bet / All-in

#### Actions spécifiques
- **ISO_VALUE** : Iso raise Value
- **ISO_BLUFF** : Iso raise Bluff

### Logique de validation

**Action principale du héros → Sous-ranges = Réponses aux réactions adverses**

| Action principale | Réaction adverse | Sous-ranges attendus |
|-------------------|------------------|---------------------|
| OPEN | Face à 3bet | CALL, R4_VALUE, R4_BLUFF, FOLD |
| DEFENSE | Réponse à open | CALL, R3_VALUE, R3_BLUFF, FOLD |
| 3BET / SQUEEZE | Face à 4bet | CALL, R5_ALLIN, FOLD |
| 4BET | Face à 5bet | CALL, FOLD |

## 🔍 Pipeline d'import

### Étapes du traitement

1. **Parsing JSON** : Extraction des ranges et mains
2. **Standardisation** : Détection automatique des métadonnées
   - Format de table (5max, 6max, 9max, HU)
   - Position héros (UTG, CO, BTN, etc.)
   - Action principale (open, defense, 3bet, etc.)
   - Position adversaire si applicable
3. **Enrichissement** : Ajout des métadonnées par défaut
   - Type de jeu : Cash Game
   - Variante : NLHE
   - Stack depth : 100bb
4. **Calcul de confiance** : Score basé sur la qualité de la détection
5. **Sauvegarde** : Persistance en base de données

### Exemple de détection

```
Nom du fichier : "5max open utg.json"
↓
Détection automatique :
- table_format: "5max"
- hero_position: "UTG"  
- primary_action: "open"
- confidence_score: 85%
- needs_validation: 1 (si < 80%)
```

## ✅ Système de validation

### Interface de validation

Accessible via `http://localhost:5000/validate?id=<context_id>`

#### Fonctionnalités

1. **Validation des métadonnées du contexte**
   - Format de table (dropdown)
   - Position héros (boutons)
   - Action principale (boutons)
   - Position adversaire (optionnel)
   - Stack depth, variante, stakes, sizing

2. **Classification des sous-ranges**
   - Table interactive avec toutes les sous-ranges
   - Sélection du label canonique pour chaque range
   - Indication visuelle des modifications (rouge)
   - Compteur de modifications en temps réel

3. **Détection d'incohérences**
   - Vérification cohérence action/sous-ranges
   - Warnings informatifs (pas bloquants)
   - Suggestions de correction

4. **Actions disponibles**
   - ✅ **Valider et sauvegarder** : Met à jour la base
   - 📝 **Mettre à jour le JSON source** : Synchronise le fichier
   - 📁 **Renommer le fichier** : Normalise selon le slug
   - 🗑️ **Marquer non exploitable** : Exclut du quiz

### Score de confiance

```python
# Calcul automatique
if tous_les_sous_ranges_classés:
    confidence_score = 100%
    quiz_ready = True
else:
    completed = sous_ranges_classés / total_sous_ranges
    confidence_score = completed * 100
    needs_validation = True
```

### Slug et renommage

Chaque contexte génère un slug unique :

```
Format : nlhe-{format}-{position}-{action}-{depth}
Exemple : nlhe-5max-utg-open-100bb
```

Renommage automatique :
```
"5max open utg.json" → "nlhe-5max-utg-open-100bb.json"
```

## 📊 API REST

### Routes principales

#### Import et pipeline
- `POST /api/import_pipeline` : Lance le pipeline complet
- `GET /api/debug/db` : Statistiques de la base

#### Dashboard
- `GET /api/dashboard/contexts` : Liste des contextes
- `GET /api/dashboard/stats` : Statistiques globales

#### Validation
- `GET /api/validation/candidates` : Contextes à valider
- `GET /api/validation/context/<id>` : Détails d'un contexte
- `POST /api/validation/validate/<id>` : Valide un contexte
- `POST /api/validation/update-subranges` : Met à jour les labels
- `POST /api/validation/ignore/<id>` : Marque comme non exploitable
- `POST /api/validation/rename-file/<id>` : Renomme selon le slug
- `GET /api/validation/stats` : Stats de validation

#### Quiz (en développement)
- `GET /api/quiz/check` : Vérifie les contextes prêts

### Exemple d'utilisation

```python
# Valider un contexte avec ses sous-ranges
POST /api/validation/validate/1
{
    "table_format": "5max",
    "hero_position": "UTG",
    "primary_action": "open",
    "vs_position": "N/A",
    "stack_depth": "100bb",
    "range_labels": {
        "2": "CALL",
        "3": "R4_VALUE",
        "4": "R4_BLUFF"
    },
    "update_json": true
}
```

## 🎮 Génération de quiz (à venir)

### Vue SQL optimisée

```sql
-- Vue prête pour le quiz
CREATE VIEW v_quiz_ranges_detailed AS
SELECT 
    r.id, r.name, r.label_canon,
    rc.display_name, rc.table_format, rc.hero_position,
    rh.hand
FROM ranges r
JOIN range_contexts rc ON r.context_id = rc.id
JOIN range_hands rh ON r.id = rh.range_id
WHERE rc.quiz_ready = 1;
```

### Exemples de questions

#### Question simple
```
Contexte : 5max UTG Open 100bb
Main : AJs
Question : Quelle action ?
Réponses : A) Open  B) Fold
Réponse correcte : A (label_canon = OPEN)
```

#### Question conditionnelle
```
Contexte : 5max UTG Open 100bb
Main : JJ
Situation : Vous open JJ, CO 3bet.
Question : Quelle action ?
Réponses : A) Call  B) 4bet Value  C) 4bet Bluff  D) Fold
Réponse correcte : A (label_canon = CALL)
```

## 🔧 Format JSON supporté

### Structure attendue

```json
{
  "version": "1.0",
  "timestamp": "2025-10-06T14:41:30.166Z",
  "source": {
    "url": "https://site2wouf.fr/poker-range-editor.php",
    "tool": "Poker Range Grid"
  },
  "data": {
    "ranges": {
      "1": {
        "name": "open_utg",
        "color": "#1eff00",
        "label_canon": "OPEN"
      },
      "2": {
        "name": "call",
        "color": "#002aff",
        "label_canon": "CALL"
      }
    },
    "values": {
      "AA": [1, 2],
      "KK": [1, 2],
      "AKs": [1, 2],
      "AQs": [1, 2],
      "JJ": [2]
    },
    "maxIndex": 2
  },
  "metadata": {
    "table_format": "5max",
    "hero_position": "UTG",
    "primary_action": "open",
    "stack_depth": "100bb",
    "validated": true,
    "validated_by_user": true
  }
}
```

### Sections du JSON

- **source** : Métadonnées de l'outil source
- **data.ranges** : Définition des ranges avec labels
- **data.values** : Affectation des mains aux ranges
- **metadata** : Métadonnées du contexte (ajoutées lors de la validation)

## 🧪 Tests et debugging

### Routes de debug

```
http://localhost:5000/debug_structure     # Structure de la DB
http://localhost:5000/debug_all_contexts  # Liste tous les contextes
http://localhost:5000/debug_metadata      # Métadonnées détaillées
```

### Test du pipeline standalone

```bash
# Test complet
python integrated_pipeline.py

# Test avec statut uniquement
python modules/pipeline_runner.py --status

# Test d'un module spécifique
python modules/name_standardizer.py
```

### Vérification de la base

```python
import sqlite3
conn = sqlite3.connect('data/poker_trainer.db')
cursor = conn.cursor()

# Vérifier la structure
cursor.execute("PRAGMA table_info(ranges)")
print(cursor.fetchall())

# Statistiques des labels
cursor.execute("""
    SELECT label_canon, COUNT(*) 
    FROM ranges 
    GROUP BY label_canon
""")
print(cursor.fetchall())
```

## 📈 Workflow complet

```
1. Créer ranges dans l'éditeur web
   ↓
2. Exporter JSON → data/ranges/
   ↓
3. Lancer Import Pipeline
   ↓
4. Valider les contextes (needs_validation=1)
   - Corriger métadonnées si nécessaire
   - Classifier tous les sous-ranges
   - Renommer fichier selon slug
   - Mettre à jour JSON source
   ↓
5. Contextes prêts (quiz_ready=1)
   ↓
6. Générer et utiliser le quiz (à venir)
```

## 🎯 État du développement

### ✅ Fonctionnalités opérationnelles

- Pipeline d'import automatique
- Standardisation intelligente
- Base de données complète avec index
- Interface web responsive
- Système de validation complet
- Classification des sous-ranges
- Détection d'incohérences
- Score de confiance automatique
- Mise à jour JSON synchronisée
- Renommage automatique des fichiers

### 🚧 En développement

- Générateur de quiz interactif
- Statistiques de progression
- Système de révision espacée
- Export des résultats
- Support formats additionnels (PIO, GTO+)

### 🔮 Roadmap

- Interface mobile responsive
- Mode hors-ligne
- Synchronisation cloud (optionnel)
- Partage de ranges entre utilisateurs
- Analytics avancées

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

## 📝 Licence

Projet sous licence libre - voir [LICENSE](LICENSE) pour plus de détails.

## 🔗 Liens utiles

- [Éditeur de ranges web](https://site2wouf.fr/poker-range-editor.php)
- [Documentation Python](https://docs.python.org/3/)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Dernière mise à jour** : 07/10/2025
**Version** : 2.0 - Système de validation complet opérationnel

Créé avec ❤️ pour la communauté poker
