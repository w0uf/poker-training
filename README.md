# Poker Training - Système d'entraînement de ranges

Interface web locale pour l'entraînement de ranges de poker avec pipeline intégré, validation intelligente et **système de quiz interactif avancé**.

## 🎯 Vue d'ensemble

**poker-training** est un système complet permettant d'importer, valider et utiliser des ranges de poker pour l'entraînement. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées, validées et utilisées dans un quiz interactif intelligent.

## ✨ Fonctionnalités principales

### Pipeline d'import automatique
- Import et parsing des fichiers JSON
- Standardisation intelligente des noms et positions
- Enrichissement automatique des métadonnées
- **Mapping contextuel prioritaire** : Le `primary_action` du contexte prime sur le nom de la range
- **Support complet des contextes multiway** : Squeeze (✅), vs_limpers (✅)
- **Action_sequence JSON** : Gestion des situations complexes (opener + callers, limpers multiples)
- Détection des contextes nécessitant validation
- **Validation stricte des métadonnées** avant `quiz_ready=1`

### Système de validation avancé
- **Validation des métadonnées de contexte** : format de table, positions, actions
- **Classification des sous-ranges** : labels canoniques pour chaque range
- **Détection d'incohérences** : vérification de la cohérence action/sous-ranges
- **Score de confiance** : calculé selon le % de sous-ranges classifiés
- **Mise à jour JSON source** : synchronisation automatique des validations
- **Renommage automatique** : normalisation des noms de fichiers selon le slug
- **Mise à jour du label_canon de la range principale** : Synchronisé avec le `primary_action`
- **Construction automatique d'action_sequence** : Détection depuis le nom du contexte

### Système de Quiz Interactif Intelligent ✨
- **Configuration flexible** : sélection des contextes et nombre de questions
- **Questions contextuelles** : adaptation du texte selon le type de situation
  - Open : "Vous avez XX en UTG, que faites-vous ?"
  - Defense : "UTG ouvre. Vous avez XX en CO, que faites-vous ?"
  - Squeeze : "UTG ouvre, CO call. Vous avez XX en BTN, que faites-vous ?"
  - VS_Limpers : "UTG limp, CO limp. Vous avez XX en BTN, que faites-vous ?"
  - 4bet : "Vous ouvrez, CO 3bet. Vous avez XX, que faites-vous ?"
- **Sélection intelligente des mains** :
  - Détection automatique des mains borderline (à la frontière de la range)
  - Pondération vers les décisions difficiles pour un entraînement ciblé
  - Équilibrage 50/50 entre mains IN et OUT of range
- **Questions defense** : Utilise les sous-ranges pour trouver l'action correcte
- **Boutons dynamiques contextuels** :
  - Defense : `[FOLD] [CALL] [RAISE]` (3BET → RAISE pour l'UI)
  - VS_Limpers : `[FOLD] [CALL] [ISO]` (ISO_VALUE/BLUFF → ISO pour l'UI)
  - BB check (action gratuite) : `[CHECK] [RAISE]` (pas de FOLD)
  - Open : `[FOLD] [CALL] [RAISE]`
  - Squeeze : `[FOLD] [CALL] [RAISE]`
- **Interface immersive** : table de poker virtuelle avec affichage des cartes
- **Feedback immédiat** : indication correcte/incorrecte avec explications
- **Statistiques en temps réel** : score, progression, distribution des questions par contexte

### Architecture hiérarchique des ranges
- **Range principale (range_key='1')** : 
  - **Pour OPEN** : Contient uniquement les mains à open
  - **Pour DEFENSE** : Contient TOUTES les mains jouables (union call + 3bet)
  - **Pour SQUEEZE** : Contient TOUTES les mains à squeeze
  - **Pour VS_LIMPERS** : Contient TOUTES les mains jouables (overlimper + iso raise)
- **Sous-ranges (range_key > '1')** : Actions spécifiques (réponses aux réactions adverses)
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
│   ├── database_manager.py       # Gestion base de données + action_sequence
│   ├── context_validator.py      # Validation des contextes
│   ├── quiz_generator.py         # Génération des questions
│   ├── hand_selector.py          # Sélection intelligente des mains
│   ├── poker_constants.py        # Constantes et mappings
│   ├── pipeline_runner.py        # Orchestrateur principal
│   └── quiz_action_mapper.py     # Mapping actions pour quiz
├── integrated_pipeline.py        # Point d'entrée pipeline
└── README.md
```

### Base de données SQLite

#### Tables principales

- **range_files** : Fichiers importés avec hash et timestamps
- **range_contexts** : Contextes avec métadonnées enrichies
  - Colonnes dédiées : `table_format`, `hero_position`, `primary_action`, `action_sequence`, etc.
  - **`action_sequence`** (TEXT, JSON) : Stocke les séquences multiway
  - Statuts : `needs_validation`, `quiz_ready`, `confidence_score`
- **ranges** : Ranges individuelles avec classification
  - `range_key` : Position dans le fichier (1=principale, 2+=sous-ranges)
  - `label_canon` : Label standardisé (OPEN, CALL, DEFENSE, SQUEEZE, ISO, etc.)
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

### Colonne action_sequence (JSON)

Pour gérer les situations multiway complexes, la colonne `action_sequence` stocke les informations sous forme JSON :

#### Format DEFENSE
```json
{
  "opener": "UTG"
}
```

#### Format SQUEEZE
```json
{
  "opener": "UTG",
  "callers": ["CO"]
}
```

#### Format VS_LIMPERS
```json
{
  "limpers": ["UTG", "CO"]
}
```

**Fonctions utilitaires** (dans `database_manager.py`) :
- `build_action_sequence()` : Construit le dictionnaire
- `serialize_action_sequence()` : Convertit en JSON pour la DB
- `parse_action_sequence()` : Parse le JSON depuis la DB
- `format_action_sequence_display()` : Format pour affichage ("vs UTG open + CO call")
- `detect_action_sequence_from_name()` : Détection automatique depuis le nom du contexte

## 🎲 Structure des ranges

### Architecture hiérarchique

#### Exemple 1 : Range d'OPEN

```
Fichier JSON : "nlhe-5max-utg-open-100bb.json"
├── Range 1 (principale) : label_canon='OPEN'
│   ├── AA, KK, QQ, JJ, TT, 99, AKs, AQs, ...
│   └── Action : OPEN (première de parole)
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── QQ, JJ, TT (call si 3bet)
│   └── Action conditionnelle : vs 3BET après notre OPEN
├── Range 3 (sous-range) : label_canon='R4_VALUE'
│   ├── AA, KK (4bet value)
│   └── Action conditionnelle : vs 3BET après notre OPEN
└── Range 4 (sous-range) : label_canon='R4_BLUFF'
    ├── A5s (4bet bluff)
    └── Action conditionnelle : vs 3BET après notre OPEN
```

**Quiz** : "UTG avec AKs → OPEN ?" 
- Question simple (niveau 1)
- Options : `[FOLD, CALL, OPEN]`
- Sous-ranges = réponses futures SI 3bet

---

#### Exemple 2 : Range de DEFENSE

```
Fichier JSON : "nlhe-5max-bb-defense-vs-utg-100bb.json"
├── Range 1 (principale) : label_canon='DEFENSE'
│   ├── Union de TOUTES les mains jouables
│   ├── AA, KK, ..., 66, AQs, KQs, ...
│   └── Action : Variable selon la main (CALL ou 3BET)
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── 99, 88, 77, AQs, KQs, QJs, ...
│   └── Action : CALL face à l'open UTG
└── Range 3 (sous-range) : label_canon='3BET'
    ├── AA, KK, QQ, JJ, TT, AKs, ...
    └── Action : 3BET face à l'open UTG
```

**Quiz** : "UTG ouvre, BB avec KQs → ?" 
- Question de decision (niveau 1)
- Système cherche dans les sous-ranges :
  - KQs dans Range 2 (CALL) → Réponse = CALL
- Options : `[FOLD, CALL, RAISE]` (pas de DEFENSE comme option)

---

#### Exemple 3 : Range de SQUEEZE

```
Fichier JSON : "nlhe-5max-bb-squeeze-vs-utg-co-100bb.json"
└── Metadata JSON :
    {
      "primary_action": "squeeze",
      "opener": "UTG",
      "callers": ["CO"]
    }
├── Range 1 (principale) : label_canon='SQUEEZE'
│   ├── AA, KK, QQ, JJ, AKs, AQs, ...
│   └── Action : SQUEEZE face à UTG open + CO call
└── action_sequence (DB) :
    {
      "opener": "UTG",
      "callers": ["CO"]
    }
```

**Quiz** : "UTG ouvre, CO call, BB avec AQs → ?" 
- Question squeeze (niveau 1)
- Options : `[FOLD, CALL, RAISE]`
- Texte généré depuis action_sequence

---

#### Exemple 4 : Range VS_LIMPERS

```
Fichier JSON : "nlhe-5max-bb-vs-limpers-utg-mp-100bb.json"
└── Metadata JSON :
    {
      "primary_action": "vs_limpers",
      "limpers": ["UTG", "MP"]
    }
├── Range 1 (principale) : label_canon='ISO'
│   ├── AA, KK, QQ, AKs, AQs, ...
│   └── Action : ISO RAISE
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── 77, 66, 55, ATs, KJs, ...
│   └── Action : OVERLIMPER
└── action_sequence (DB) :
    {
      "limpers": ["UTG", "MP"]
    }
```

**Quiz** : "UTG limp, MP limp, BB avec 88 → ?" 
- Question vs_limpers (niveau 1)
- Options : `[FOLD, CALL, ISO]`
- Texte généré depuis action_sequence

## 🎮 Fonctionnement du Quiz

### Phase 1 : Setup
1. Utilisateur sélectionne les contextes (OPEN, DEFENSE, SQUEEZE, etc.)
2. Choisit le nombre de questions
3. Lance le quiz

### Phase 2 : Génération des questions
1. Pour chaque question :
   - Sélection aléatoire d'un contexte parmi ceux choisis
   - Détection automatique des mains borderline (seuil) dans ce contexte
   - Choix intelligent : 50% IN-range / 50% OUT-range
   - Pondération vers les mains difficiles (borderline)
2. Génération du texte contextuel adapté
3. Construction des options de réponse appropriées
4. Comptage de la distribution des questions par contexte

### Phase 3 : Questions
1. Affichage de la question avec :
   - Contexte visuel (table de poker)
   - Cartes de la main
   - Texte adapté à la situation
   - Boutons d'action contextuels
2. Validation de la réponse
3. Feedback immédiat avec explication
4. Progression vers la question suivante

### Phase 4 : Résultats (en cours de développement 🚧)
1. **Écran de résultats détaillés** (workflow futur) :
   - Score global et par contexte
   - Analyse pointue des erreurs
   - Identification des patterns de faiblesse
   - Suggestions d'amélioration personnalisées
   - Graphiques de progression
   - Export des résultats

### Gestion des contextes spéciaux

#### Contexte DEFENSE
- La range principale contient **toutes** les mains jouables
- Le système interroge les sous-ranges pour déterminer CALL vs 3BET
- Fonction `_find_subrange_action()` dédiée

#### Contexte SQUEEZE
- Texte adapté : "X ouvre, Y call, vous avez Z..."
- Action_sequence utilisé pour générer le texte
- Options : `[FOLD, CALL, RAISE]` (pas de SQUEEZE comme option)

#### Contexte VS_LIMPERS
- Texte adapté : "X limp, Y limp, vous avez Z..."
- Options : `[FOLD, CALL, ISO]` (ISO = ISO_VALUE/BLUFF normalisé)

#### BB Check
- Pas d'option FOLD (action gratuite)
- Options : `[CHECK, RAISE]` uniquement

## 📊 Diagnostic et Debug

### Vérifier le mapping des ranges principales

```python
import sqlite3
conn = sqlite3.connect('data/poker_trainer.db')
cursor = conn.cursor()

# Afficher toutes les ranges principales avec leur label_canon
cursor.execute("""
    SELECT rc.display_name, rc.primary_action, r.name, r.label_canon
    FROM ranges r
    JOIN range_contexts rc ON r.context_id = rc.id
    WHERE r.range_key = '1'
""")
for row in cursor.fetchall():
    print(f"{row[0]} | {row[1]} | {row[2]} → {row[3]}")

# Vérifier les contextes prêts pour le quiz
cursor.execute("""
    SELECT id, display_name, quiz_ready, needs_validation
    FROM range_contexts
    WHERE quiz_ready = 1
""")
print(cursor.fetchall())

# Vérifier les action_sequence
cursor.execute("""
    SELECT display_name, primary_action, action_sequence
    FROM range_contexts
    WHERE action_sequence IS NOT NULL
""")
for row in cursor.fetchall():
    print(f"{row[0]} | {row[1]} | {row[2]}")
```

## 📈 Workflow complet

```
1. Créer ranges dans l'éditeur web
   ↓
2. Exporter JSON → data/ranges/
   (Inclure les label_canon dans le JSON pour éviter la validation manuelle)
   (Inclure les metadata pour un mapping optimal)
   (Pour squeeze : inclure opener/callers dans metadata)
   (Pour vs_limpers : inclure limpers="UTG,CO" dans metadata)
   ↓
3. Lancer Import Pipeline
   ↓
4. Vérification automatique stricte :
   - Métadonnées valides ? (table_format, hero_position, primary_action)
   - Range principale a un label_canon ?
   - Toutes les sous-ranges ont des labels ?
   - Mapping contextuel correct ? (squeeze → SQUEEZE, vs_limpers → RAISE/ISO)
   - Action_sequence construite automatiquement si détectable
   - Si NON → needs_validation=1
   ↓
5. Si needs_validation=1, valider les contextes:
   - Corriger métadonnées si nécessaire
   - Ajouter opener/callers/limpers si manquant
   - Le label_canon de la range principale est automatiquement mis à jour
   - Classifier tous les sous-ranges
   - Action_sequence est construite automatiquement
   - Renommer fichier selon slug
   - Mettre à jour JSON source
   ↓
6. Contextes prêts (quiz_ready=1)
   ↓
7. Lancer le quiz !
   - Sélectionner contextes (open, defense, squeeze, vs_limpers, etc.)
   - Choisir nombre de questions
   - Questions intelligentes avec mains borderline
   - Texte adapté au contexte (utilise action_sequence pour squeeze/vs_limpers)
   - Boutons adaptés (RAISE au lieu de 3BET, ISO au lieu de ISO_VALUE, etc.)
   - S'entraîner avec feedback immédiat
   ↓
8. Consulter l'analyse des résultats (🚧 en développement)
   - Score global et détaillé par contexte
   - Analyse pointue des erreurs
   - Recommandations personnalisées
```

## 🎯 État du développement

### ✅ Fonctionnalités opérationnelles (v4.0)

#### Pipeline et Base de données
- ✅ Pipeline d'import automatique
- ✅ Standardisation intelligente
- ✅ Base de données complète avec index
- ✅ **Mapping contextuel (primary_action prime sur le nom de la range)**
- ✅ **Support complet du contexte SQUEEZE**
- ✅ **Support complet du contexte VS_LIMPERS** 🎉
- ✅ **Colonne action_sequence JSON** (gestion des situations multiway)
- ✅ Validation stricte des métadonnées avant quiz_ready=1

#### Validation
- ✅ Système de validation complet
- ✅ Classification des sous-ranges
- ✅ Détection d'incohérences
- ✅ Score de confiance automatique
- ✅ Mise à jour JSON synchronisée
- ✅ Renommage automatique des fichiers
- ✅ Mise à jour automatique du label_canon de la range principale
- ✅ Construction automatique d'action_sequence depuis le nom ou metadata

#### Quiz
- ✅ **Système de quiz interactif complet**
- ✅ **Questions simples et conditionnelles**
- ✅ **Interface immersive type table de poker**
- ✅ **Sélection intelligente des mains avec détection de borderlines**
- ✅ **Questions contextuelles adaptées (defense, open, squeeze, vs_limpers, 4bet, etc.)**
- ✅ **Gestion spéciale des ranges DEFENSE avec _find_subrange_action()**
- ✅ **Support complet SQUEEZE** (mapping correct, normalisation vers RAISE)
- ✅ **Support complet VS_LIMPERS** (détection limpers, questions adaptées, options ISO)
- ✅ **Boutons dynamiques selon le contexte**
  - ✅ BB check = pas de FOLD (action gratuite)
  - ✅ Defense = RAISE au lieu de 3BET pour l'UI
  - ✅ VS_Limpers = ISO au lieu de ISO_VALUE/BLUFF
  - ✅ DEFENSE ne s'affiche jamais comme option (label technique)
- ✅ **Statistiques en temps réel** : Distribution des questions par contexte
- ✅ **Évitement de questions redondantes** : Limitation des options à 3 max
- ✅ **Compteur de progression** avec feedback immédiat

#### Interface web
- ✅ Dashboard temps réel avec statistiques
- ✅ Interface de validation interactive
- ✅ Interface web responsive
- ✅ API REST complète

### 🚧 Améliorations prioritaires (v4.1)

#### Écran post-quiz - Analyse pointue des résultats 🎯
- 🔄 **Écran de résultats détaillés** après le quiz
  - Score global avec pourcentage de réussite
  - Score par contexte (OPEN, DEFENSE, SQUEEZE, etc.)
  - Liste des erreurs avec la bonne réponse
  - **Analyse des patterns d'erreurs** :
    - Identification des faiblesses par contexte
    - Détection des types de mains problématiques (borderline, out-of-range, etc.)
    - Tendances (trop tight, trop loose, confusion call/raise, etc.)
  - **Graphiques visuels** :
    - Répartition du score par contexte (camembert/barres)
    - Évolution de la performance au cours du quiz
    - Comparaison avec les performances précédentes
  - **Recommandations personnalisées** :
    - Suggestions d'entraînement ciblé
    - Contextes à revoir en priorité
    - Conseils stratégiques basés sur les erreurs
  - **Export des résultats** :
    - Export CSV/JSON pour analyse externe
    - Sauvegarde de l'historique des quiz
    - Comparaison des performances dans le temps

#### Context Validator - Performance au premier import
- 🔄 **Détection intelligente au premier import**
  - Détecter automatiquement opener/callers/limpers depuis le nom du fichier
  - Construire action_sequence dès l'import si possible
  - Réduire le besoin de validation manuelle
- 🔄 **Validation cohérence positions**
  - Pour SQUEEZE : vérifier que opener ≠ callers
  - Pour VS_LIMPERS : vérifier que hero ≠ limpers
  - Alertes si incohérence détectée

#### Slug et renommage automatique
- 🔄 **Mise à jour du slug à chaque changement de metadata**
  - Recalcul automatique si table_format, hero_position ou primary_action change
  - Proposition de renommer le fichier JSON source
  - Historique des modifications

#### Quiz
- 🔄 **Éviter les doublons** : Ne pas poser deux fois la même main dans un quiz
- 🎯 **Questions à tiroirs** : Décomposer les questions conditionnelles en 2 étapes
- ⚠️ **Validation de compatibilité** : Empêcher la sélection de contextes incompatibles
- 📊 **Statistiques par contexte** : Taux de réussite par type de situation (intégré dans l'écran post-quiz)

#### Fonctionnalités générales
- 📊 Système de progression avec historique
- 🔁 Système de révision espacée (basé sur les erreurs fréquentes)
- 📱 Interface mobile optimisée
- 🎨 Thèmes personnalisables

### 🔮 Roadmap (v5.0+)

**Moyen terme**
- Support formats additionnels (PIO, GTO+)
- Mode hors-ligne complet
- Synchronisation cloud (optionnel)
- Partage de ranges entre utilisateurs
- **Contextes 3-way et 4-way** (plusieurs callers, plusieurs limpers)
- **Mode entraînement vs mode examen** avec timer
- **Système de révision intelligente** (spaced repetition basé sur les erreurs)

**Long terme**
- Analytics avancées avec graphiques de progression historique
- Classement et achievements
- Intégration avec trackers de poker (PT4, HM3)
- **Coach virtuel** : suggestions d'entraînement personnalisées basées sur l'historique
- **Leaderboards** : compétition entre utilisateurs

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

## 🐛 Problèmes connus et solutions

### SQUEEZE affichait 'DEFENSE' comme option ❌ → ✅ Corrigé (v3.6)
**Problème** : Le contexte squeeze générait `['FOLD', 'CALL', 'DEFENSE']` au lieu de `['FOLD', 'CALL', 'RAISE']`

**Cause** : 
1. `label_canon='None'` pour la range principale du squeeze
2. `map_name_to_label_canon()` ne gérait pas correctement le cas squeeze
3. L'action 'DEFENSE' s'ajoutait comme option

**Solution** :
1. Correction du mapping : `primary_action='squeeze'` → `label_canon='SQUEEZE'`
2. Ordre de détection : chercher 'squeeze' AVANT '3bet' dans le nom
3. Gestion de la faute d'orthographe : 'squezze' détecté aussi
4. Normalisation : `ACTION_NORMALIZATION['SQUEEZE'] = 'RAISE'`
5. Filtrage : DEFENSE ne s'ajoute jamais comme option (c'est un label technique)

### Defense affichait '3BET' au lieu de 'RAISE' ❌ → ✅ Corrigé (v3.5)
**Problème** : Les options affichaient `['FOLD', 'CALL', '3BET']` au lieu de `['FOLD', 'CALL', 'RAISE']`

**Cause** : Le terme "3BET" est trop technique pour l'utilisateur final

**Solution** :
1. Conversion contextuelle : Si `primary_action='defense'` et `correct_answer='3BET'` → `correct_answer='RAISE'`
2. Distracteurs adaptés : `_get_contextual_distractors('defense')` retourne `['CALL', 'RAISE']`

### Trop de boutons pour contexte OPEN ❌ → ✅ Corrigé (v3.8)
**Problème** : Les sous-ranges (4BET, CALL) apparaissaient comme options pour les questions simples

**Cause** : Les sous-ranges sont des réponses conditionnelles (niveau 2), pas des options pour la décision initiale

**Solution** :
1. Limitation stricte : maximum 3 options par question
2. Les sous-ranges ne sont plus utilisées comme distracteurs pour les questions simples
3. Seuls les distracteurs génériques contextuels sont ajoutés (FOLD, CALL, RAISE)

### Distribution inégale des contextes ❌ → ✅ Corrigé (v3.9)
**Problème** : Certains contextes généraient beaucoup plus de questions que d'autres

**Cause** : Manque de visibilité sur la distribution réelle des questions générées

**Solution** :
1. Ajout d'un compteur par contexte dans la génération
2. Logs détaillés de la distribution : `[QUIZ] 📊 Distribution des questions: Contexte 1: 8, Contexte 2: 7`
3. Permet d'identifier les contextes qui échouent systématiquement

---

**Dernière mise à jour** : 23/10/2025  
**Version** : 4.1-dev - Préparation écran post-quiz avec analyse pointue des résultats

Créé avec ❤️ pour la communauté poker
