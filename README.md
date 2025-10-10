# Poker Training - Système d'entraînement de ranges

Interface web locale pour l'entraînement de ranges de poker avec pipeline intégré, validation intelligente et **système de quiz interactif**.

## 🎯 Vue d'ensemble

**poker-training** est un système complet permettant d'importer, valider et utiliser des ranges de poker pour l'entraînement. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées, validées et utilisées dans un quiz interactif.

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

### Système de Quiz Interactif ✨ NOUVEAU
- **Configuration flexible** : sélection des contextes et nombre de questions
- **Questions simples** : action principale (ex: "Avec AJs en UTG, que faites-vous ?")
- **Questions conditionnelles** : réponses aux réactions adverses (ex: "Vous open JJ, CO 3bet...")
- **Interface immersive** : table de poker virtuelle avec affichage des cartes
- **Boutons dynamiques** : FOLD, CALL, RAISE, 4-BET, etc. selon le contexte
- **Feedback immédiat** : indication correcte/incorrecte avec explications
- **Statistiques détaillées** : score, progression, résultats finaux

### Architecture hiérarchique des ranges
- **Range principale** : Action initiale (open, defense, 3bet, etc.)
- **Sous-ranges** : Réponses aux réactions adverses (call, 4bet, fold, etc.)
- **Labels canoniques** : Classification standardisée pour le quiz

### Interface web moderne
- Dashboard temps réel avec statistiques
- Interface de validation interactive
- Système de quiz avec progression
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

# 6. Lancer le quiz !
# Cliquer sur "🎯 Lancer le Quiz" dans le dashboard
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
│       ├── validate_context.html # Interface de validation
│       ├── quiz_setup.html       # Configuration du quiz
│       └── quiz.html             # Interface du quiz
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
5. **Vérification quiz_ready** : Le contexte est prêt si toutes les ranges ont des `label_canon` valides
6. **Sauvegarde** : Persistance en base de données

### Exemple de détection

```
Nom du fichier : "5max open utg.json"
↓
Détection automatique :
- table_format: "5max"
- hero_position: "UTG"  
- primary_action: "open"
- confidence_score: 100%
- quiz_ready: 1 (si tous les label_canon sont définis)
- needs_validation: 0
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

### Score de confiance et quiz_ready

```python
# Calcul automatique
if range_principale_sans_label OR sous_ranges_sans_labels:
    quiz_ready = 0
    needs_validation = 1
elif tous_les_labels_définis:
    quiz_ready = 1
    needs_validation = 0
    confidence_score = 100%
else:
    completed = sous_ranges_ok / total_sous_ranges
    confidence_score = completed * 100
    needs_validation = 1
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

## 🎮 Système de Quiz Interactif

### Configuration du Quiz

**Page de setup** : `http://localhost:5000/quiz-setup`

1. **Sélection des contextes** : Checkbox pour chaque contexte `quiz_ready`
2. **Nombre de questions** : Slider de 5 à 50 questions
3. **Lancement** : Génération instantanée des questions

### Types de Questions

#### Question Simple (60%)
```
Contexte : Table 5max, vous êtes UTG avec 100bb
Main affichée : AJs
Question : Vous avez AJs.

Boutons disponibles : [OPEN] [FOLD] [CALL]
Réponse correcte : OPEN (range principale)
```

#### Question Conditionnelle (40%)
```
Contexte : Table 5max, vous êtes UTG avec 100bb
Main affichée : JJ
Question : Vous ouvrez avec JJ, un adversaire relance.

Boutons disponibles : [CALL] [4-BET] [FOLD]
Réponse correcte : CALL (sous-range 2)
```

### Interface du Quiz

- **Table de poker virtuelle** : Fond vert réaliste avec effet feutre
- **Affichage des cartes** : Animation de distribution des cartes
- **Contexte visible** : Table format, position, stack depth
- **Boutons d'action** : 
  - Dynamiques selon les options disponibles
  - Couleurs distinctes (FOLD rouge, CALL bleu, RAISE orange, etc.)
  - Désactivés après réponse
- **Feedback immédiat** :
  - ✅ Correct : fond vert avec encouragement
  - ❌ Incorrect : fond rouge avec bonne réponse
- **Progression** :
  - Barre de progression visuelle
  - Score en temps réel (bonnes/total)
  - Numéro de question actuelle

### Écran de Résultats

- **Score final** : Pourcentage de réussite (grande taille)
- **Statistiques détaillées** :
  - Total de questions répondues
  - Nombre de réponses correctes
  - Nombre de réponses incorrectes
- **Actions** :
  - 🔄 Recommencer (nouveau quiz)
  - 🏠 Retour au dashboard

### Génération des Questions

Le système génère intelligemment les questions :

```python
# Algorithme de génération
for i in range(question_count):
    context = random.choice(selected_contexts)
    
    # 60% questions simples, 40% conditionnelles
    if random() < 0.6 OR pas_de_sous_ranges:
        question = generate_simple_question()
        # Utilise la range principale (range_key='1')
    else:
        question = generate_conditional_question()
        # Utilise une sous-range aléatoire (range_key>'1')
    
    # Filtrage automatique des questions invalides
    if question.has_valid_label_canon:
        add_to_quiz(question)
```

### Normalisation des Actions

Les actions sont normalisées pour éviter les doublons :

```python
R3_VALUE, R3_BLUFF → 3BET
R4_VALUE, R4_BLUFF → 4BET
R5_ALLIN → ALLIN
ISO_VALUE, ISO_BLUFF → ISO
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

#### Quiz
- `GET /api/quiz/check` : Vérifie les contextes prêts
- `GET /api/quiz/available-contexts` : Liste des contextes `quiz_ready`
- `GET /api/quiz/generate` : Génère les questions du quiz

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

# Générer un quiz
GET /api/quiz/generate?contexts=1,2,3&count=10
→ Retourne 10 questions aléatoires depuis les contextes 1, 2 et 3
```

## 🔧 Format JSON supporté

### Structure attendue

```json
{
  "version": "1.0",
  "timestamp": "2025-10-09T14:41:30.166Z",
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
      },
      "3": {
        "name": "4bet_value",
        "color": "#ff0000",
        "label_canon": "R4_VALUE"
      }
    },
    "values": {
      "AA": [1, 2, 3],
      "KK": [1, 2, 3],
      "AKs": [1, 2],
      "JJ": [1, 2]
    },
    "maxIndex": 3
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
- **data.ranges** : Définition des ranges avec **label_canon obligatoire**
- **data.values** : Affectation des mains aux ranges
- **metadata** : Métadonnées du contexte (ajoutées lors de la validation)

⚠️ **Important** : Pour qu'un contexte soit `quiz_ready=1`, **tous les label_canon** doivent être définis dans le JSON ou via l'interface de validation.

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
    WHERE label_canon IS NOT NULL
    GROUP BY label_canon
""")
print(cursor.fetchall())

# Vérifier les contextes prêts pour le quiz
cursor.execute("""
    SELECT id, display_name, quiz_ready
    FROM range_contexts
    WHERE quiz_ready = 1
""")
print(cursor.fetchall())
```

## 📈 Workflow complet

```
1. Créer ranges dans l'éditeur web
   ↓
2. Exporter JSON → data/ranges/
   (Inclure les label_canon dans le JSON pour éviter la validation manuelle)
   ↓
3. Lancer Import Pipeline
   ↓
4. Si needs_validation=1, valider les contextes:
   - Corriger métadonnées si nécessaire
   - Classifier tous les sous-ranges
   - Renommer fichier selon slug
   - Mettre à jour JSON source
   ↓
5. Contextes prêts (quiz_ready=1)
   ↓
6. Lancer le quiz !
   - Sélectionner contextes
   - Choisir nombre de questions
   - S'entraîner
   - Consulter les résultats
```

## 🎯 État du développement

### ✅ Fonctionnalités opérationnelles

- ✅ Pipeline d'import automatique
- ✅ Standardisation intelligente
- ✅ Base de données complète avec index
- ✅ Interface web responsive
- ✅ Système de validation complet
- ✅ Classification des sous-ranges
- ✅ Détection d'incohérences
- ✅ Score de confiance automatique
- ✅ Mise à jour JSON synchronisée
- ✅ Renommage automatique des fichiers
- ✅ **Système de quiz interactif complet**
- ✅ **Questions simples et conditionnelles**
- ✅ **Interface immersive type table de poker**
- ✅ **Statistiques et résultats détaillés**

### 🚧 Améliorations prévues

#### Quiz
- 🔄 **Éviter les doublons** : Ne pas poser deux fois la même main
- 🎯 **Questions à tiroirs** : Décomposer les questions conditionnelles en 2 étapes :
  - Étape 1 : Action principale (0.5 point)
  - Étape 2 : Réponse à la réaction (0.5 point)
  - Exemple : "Vous avez JJ en UTG" → "Vous open" → "CO 3bet, que faites-vous ?"
- ⚠️ **Validation de compatibilité** : Empêcher la sélection de contextes incompatibles (ex: défense BB vs open UTG + open UTG)

#### Fonctionnalités générales
- 📊 Statistiques de progression par contexte
- 🔁 Système de révision espacée
- 📤 Export des résultats en CSV/JSON
- 📱 Interface mobile optimisée
- 🎨 Thèmes personnalisables

### 🔮 Roadmap

- Support formats additionnels (PIO, GTO+)
- Mode hors-ligne complet
- Synchronisation cloud (optionnel)
- Partage de ranges entre utilisateurs
- Analytics avancées avec graphiques
- Mode entraînement vs mode examen
- Timer par question (optionnel)
- Classement et achievements

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
- [Repository GitHub](https://github.com/w0uf/poker-training)

---

**Dernière mise à jour** : 09/10/2025  
**Version** : 3.0 - Système de quiz interactif opérationnel

Créé avec ❤️ pour la communauté poker
