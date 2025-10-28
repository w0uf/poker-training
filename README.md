# Poker Training - Système d'entraînement de ranges

Interface web locale pour l'entraînement de ranges de poker avec pipeline intégré, validation intelligente et **système de quiz interactif avancé avec drill-down multi-étapes**.

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

#### Questions Simples
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
  - Équilibrage 80/20 entre mains IN et OUT of range
- **Questions defense** : Utilise les sous-ranges pour trouver l'action correcte
- **Boutons dynamiques contextuels** :
  - Defense : `[FOLD] [CALL] [RAISE]` (3BET → RAISE pour l'UI)
  - VS_Limpers : `[FOLD] [CALL] [ISO]` (ISO_VALUE/BLUFF → ISO pour l'UI)
  - BB check (action gratuite) : `[CHECK] [RAISE]` (pas de FOLD)
  - Open : `[FOLD] [CALL] [RAISE]`
  - Squeeze : `[FOLD] [CALL] [RAISE]`

#### Questions Drill-Down (Multi-étapes) 🎯
- **Séquences d'actions réalistes** : Simule les décisions successives d'une main
  - Exemple : Open → Face à 3bet → Face à 5bet
  - Génération basée sur les `action_sequence` des sous-ranges
- **Probabilités réalistes** :
  - 50% de questions simples (1 décision)
  - 25% de questions à 2 étapes
  - 12.5% de questions à 3 étapes
  - Jamais plus de 3 étapes pour éviter les scénarios trop complexes
- **Gestion automatique des FOLD implicites** :
  - Si une main est dans la range principale mais pas dans les sous-ranges → FOLD implicite
  - Force minimum 2 étapes pour les FOLD implicites (pédagogie)
- **Affichage progressif de l'historique** :
  - Niveau 1 : Pas d'historique (première décision)
  - Niveau 2 : Affiche `RAISE →` (décision du niveau 1)
  - Niveau 3 : Affiche `RAISE → RAISE →` (décisions des niveaux 1 et 2)
- **Badges visuels colorés** :
  - RAISE (orange), CALL (vert), FOLD (rouge), CHECK (bleu)
  - Séparés par des flèches `→` pour visualiser la séquence
- **Compteur de progression adaptatif** :
  - Compte les questions principales (pas chaque sous-étape)
  - Score calculé sur les bonnes réponses finales
- **Conditions d'arrêt intelligentes** :
  - Arrêt immédiat en cas de mauvaise réponse (erreur = fin de la séquence)
  - Arrêt à la dernière étape de la séquence prévue
  - Affichage du feedback approprié à chaque niveau

#### Interface et Feedback
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
  - Chaque sous-range possède un `action_sequence` (ex: "RAISE→RAISE" pour 4bet)
  - Les mains absentes des sous-ranges génèrent automatiquement un FOLD implicite
- **Labels canoniques** : Classification standardisée pour le quiz
  - OPEN, CALL, R3_VALUE, R3_BLUFF, R4_VALUE, R4_BLUFF, R5_ALLIN, etc.

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
│       └── quiz.html             # Interface du quiz (avec drill-down)
├── modules/
│   ├── json_parser.py            # Parsing des fichiers JSON
│   ├── name_standardizer.py      # Standardisation des noms
│   ├── metadata_enricher.py      # Enrichissement automatique
│   ├── database_manager.py       # Gestion base de données + action_sequence
│   ├── context_validator.py      # Validation des contextes
│   ├── quiz_generator.py         # Génération des questions (simple + drill-down)
│   ├── drill_down_generator.py   # Générateur de questions multi-étapes
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
  - **`action_sequence`** (TEXT) : Séquence d'actions pour cette range (ex: "RAISE→RAISE→FOLD")
- **range_hands** : Mains avec fréquences

#### Index optimisés

```sql
idx_range_hands_range_id        -- Requêtes par range
idx_range_hands_hand            -- Recherche par main
idx_ranges_context_id           -- Contextes par ID
idx_ranges_label_canon          -- Filtrage par label
idx_ranges_context_label        -- Quiz queries (context + label)
```

### Colonne action_sequence

#### Dans `range_contexts` (JSON)
Pour gérer les situations multiway complexes :

**Format DEFENSE**
```json
{
  "opener": "UTG"
}
```

**Format SQUEEZE**
```json
{
  "opener": "UTG",
  "callers": ["CO"]
}
```

**Format VS_LIMPERS**
```json
{
  "limpers": ["UTG", "CO"]
}
```

#### Dans `ranges` (TEXT)
Pour gérer les séquences drill-down :

**Format simple** : `"RAISE→RAISE→FOLD"`
- Représente une séquence de 3 actions : Open → 4bet → Fold au 5bet
- Parsé par `drill_down_generator.py` pour créer les questions multi-étapes
- Affiché progressivement dans le quiz avec des badges colorés

**Fonctions utilitaires** (dans `database_manager.py`) :
- `build_action_sequence()` : Construit le dictionnaire JSON pour les contextes
- `format_action_sequence_display()` : Génère l'affichage lisible (ex: "UTG open → CO call")
- `parse_action_sequence()` : Extrait opener/callers/limpers du JSON

### Architecture du système Drill-Down

#### Flux de génération d'une question drill-down

```
quiz_generator.py (generate_question)
    ↓
    Décide : drill_down ou simple ? (50% de probabilité)
    ↓
drill_down_generator.py (generate_drill_down_question)
    ↓
    1. Vérifie qu'il y a des sous-ranges (sinon impossible)
    2. Choisit une main (80% in-range, 20% out-range)
    3. Cherche dans quelle sous-range est la main
       ├─ Si trouvée → Utilise l'action_sequence de la sous-range
       └─ Sinon → Génère FOLD implicite (ex: "RAISE→FOLD")
    4. Parse la séquence (split sur "→")
    5. Décide combien d'étapes montrer (probabilité 50% par étape)
       ├─ Exception : FOLD implicites = toujours 2 étapes minimum
       └─ Maximum : 3 étapes pour éviter les scénarios trop longs
    6. Génère les niveaux (levels) avec questions et options
    7. Retourne la structure complète au quiz
```

#### Structure de données d'une question drill-down

```javascript
{
  type: "drill_down",
  hand: "KK",
  context_id: 3,
  context_info: { /* métadonnées du contexte */ },
  sequence: [
    { action: "RAISE", text: "Action: RAISE", type: "single" },
    { action: "RAISE", text: "Action: RAISE", type: "single" },
    { action: "CALL", text: "Action: CALL", type: "single" }
  ],
  levels: [
    {
      question: "Vous avez KK en UTG, que faites-vous ?",
      options: ["FOLD", "RAISE", "CALL"],
      correct_answer: "RAISE"
    },
    {
      question: "CO vous 3bet. Que faites-vous ?",
      options: ["FOLD", "RAISE", "CALL"],
      correct_answer: "RAISE"
    },
    {
      question: "CO 5bet all-in. Que faites-vous ?",
      options: ["FOLD", "CALL"],
      correct_answer: "CALL"
    }
  ],
  total_steps: 3,
  current_step: 1
}
```

#### Affichage dans quiz.html

Le fichier `quiz.html` utilise la fonction `displayDrillDownSequence(currentLevel)` pour afficher progressivement l'historique :

```javascript
// Niveau 0 (première question) : Pas d'historique
// Niveau 1 (deuxième question) : Affiche "RAISE →"
// Niveau 2 (troisième question) : Affiche "RAISE → RAISE →"
```

Les badges sont stylisés avec des classes CSS :
- `.quiz-action-raise` (orange)
- `.quiz-action-call` (vert)
- `.quiz-action-fold` (rouge)
- `.quiz-action-check` (bleu)

## 📚 Utilisation détaillée

### Workflow complet : de l'import au quiz

```
1. Créer vos ranges dans l'éditeur
   - https://site2wouf.fr/poker-range-editor.php
   - Définir range principale + sous-ranges (4bet, call, etc.)
   - Exporter en JSON
   ↓
2. Placer les fichiers JSON dans data/ranges/
   ↓
3. Lancer le pipeline d'import
   - Dashboard → "Import Pipeline"
   - Le système parse, standardise et enrichit automatiquement
   ↓
4. Valider les contextes ambigus (si needs_validation=1)
   - Dashboard → cliquer sur contexte à valider
   - Vérifier/corriger les métadonnées (format, positions, actions)
   - Classifier les sous-ranges avec labels canoniques
   - action_sequence construit automatiquement si possible
   ↓
5. Vérifier quiz_ready=1
   - Le contexte devient disponible pour le quiz
   - Les sous-ranges avec action_sequence permettent le drill-down
   ↓
6. Configurer le quiz
   - Sélectionner les contextes à inclure
   - Définir le nombre de questions (10-50 recommandé)
   - Le système équilibre automatiquement simple/drill-down
   ↓
7. S'entraîner avec le quiz interactif
   - Questions adaptées au contexte
   - Drill-down pour approfondir les séquences
   - Affichage progressif de l'historique des actions
   - Boutons adaptés (RAISE au lieu de 3BET, ISO au lieu de ISO_VALUE, etc.)
   - Feedback immédiat avec explications
   ↓
8. Consulter l'analyse des résultats (🚧 en développement)
   - Score global et détaillé par contexte
   - Analyse pointue des erreurs
   - Recommandations personnalisées
```

## 🎯 État du développement

### ✅ Fonctionnalités opérationnelles (v4.2)

#### Pipeline et Base de données
- ✅ Pipeline d'import automatique
- ✅ Standardisation intelligente
- ✅ Base de données complète avec index
- ✅ **Mapping contextuel (primary_action prime sur le nom de la range)**
- ✅ **Support complet du contexte SQUEEZE**
- ✅ **Support complet du contexte VS_LIMPERS** 🎉
- ✅ **Colonne action_sequence JSON** (gestion des situations multiway)
- ✅ **Colonne action_sequence TEXT dans ranges** (séquences drill-down)
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

#### Quiz - Questions Simples
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

#### Quiz - Questions Drill-Down 🎯
- ✅ **Système de drill-down multi-étapes opérationnel**
- ✅ **Génération automatique de séquences** :
  - ✅ Utilisation des action_sequence des sous-ranges (ex: "RAISE→RAISE")
  - ✅ Génération de FOLD implicites pour mains hors sous-ranges
  - ✅ Chargement correct des mains et action_sequence depuis la DB
- ✅ **Probabilités réalistes** :
  - ✅ 50% questions simples, 25% à 2 étapes, 12.5% à 3 étapes
  - ✅ Force minimum 2 étapes pour FOLD implicites (pédagogie)
  - ✅ Maximum 3 étapes pour éviter la complexité excessive
- ✅ **Affichage progressif de l'historique** :
  - ✅ Badges colorés (RAISE/CALL/FOLD/CHECK)
  - ✅ Flèches de séparation (→)
  - ✅ Affichage uniquement des actions déjà effectuées
- ✅ **Logique de progression** :
  - ✅ Arrêt en cas de mauvaise réponse
  - ✅ Compteur de questions principales (pas sous-étapes)
  - ✅ Feedback approprié à chaque niveau
- ✅ **Gestion des erreurs** :
  - ✅ Vérification de l'existence des sous-ranges
  - ✅ Fallback sur questions simples si drill-down impossible
  - ✅ Logs détaillés pour le debugging

#### Interface web
- ✅ Dashboard temps réel avec statistiques
- ✅ Interface de validation interactive
- ✅ Interface web responsive
- ✅ API REST complète

### 🚧 Améliorations prioritaires (v4.3)

#### Écran post-quiz - Analyse pointue des résultats 🎯
- 🔄 **Écran de résultats détaillés** après le quiz
  - Score global avec pourcentage de réussite
  - Score par contexte (OPEN, DEFENSE, SQUEEZE, etc.)
  - Score par type de question (simple vs drill-down)
  - Liste des erreurs avec la bonne réponse
  - **Analyse des patterns d'erreurs** :
    - Identification des faiblesses par contexte
    - Détection des types de mains problématiques (borderline, out-of-range, etc.)
    - Analyse des erreurs en drill-down (à quelle étape ?)
    - Tendances (trop tight, trop loose, confusion call/raise, etc.)
  - **Graphiques visuels** :
    - Répartition du score par contexte (camembert/barres)
    - Performance simple vs drill-down
    - Évolution de la performance au cours du quiz
    - Comparaison avec les performances précédentes
  - **Recommandations personnalisées** :
    - Suggestions d'entraînement ciblé
    - Contextes à revoir en priorité
    - Séquences drill-down problématiques
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

#### Quiz - Améliorations
- 🔄 **Éviter les doublons** : Ne pas poser deux fois la même main dans un quiz
- ⚠️ **Validation de compatibilité** : Empêcher la sélection de contextes incompatibles
- 🔄 **Mode d'entraînement configurable** :
  - Option pour désactiver temporairement le drill-down
  - Réglage du ratio simple/drill-down (actuellement 50/50)
  - Choix du nombre max d'étapes (actuellement 3)

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
- **Drill-down avancé** : Séquences incluant le post-flop

**Long terme**
- Analytics avancées avec graphiques de progression historique
- Classement et achievements
- Intégration avec trackers de poker (PT4, HM3)
- **Coach virtuel** : suggestions d'entraînement personnalisées basées sur l'historique
- **Leaderboards** : compétition entre utilisateurs
- **Drill-down complet** : Pre-flop → Flop → Turn → River

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

### Drill-down générait toujours FOLD implicite ❌ → ✅ Corrigé (v4.2)
**Problème** : Même pour les mains présentes dans les sous-ranges (ex: KK dans R4_VALUE), le système générait systématiquement "RAISE→FOLD" au lieu de la bonne séquence "RAISE→RAISE"

**Cause** :
1. `quiz_generator.py` ne chargeait pas `action_sequence` dans la requête SQL des ranges
2. Les dictionnaires des sous-ranges n'avaient donc jamais leur `action_sequence` renseignée
3. Le code vérifiait `if subrange_with_hand and subrange_with_hand.get('action_sequence'):`
4. Comme `action_sequence` était toujours `None`, ça générait un FOLD implicite pour TOUTES les mains

**Solution** :
1. Ajout de `r.action_sequence` dans le SELECT de `quiz_generator.py` ligne 95-104
2. Ajout de `'action_sequence': action_seq` dans le dictionnaire des ranges
3. Suppression du code inutile qui tentait d'ouvrir une nouvelle connexion SQLite dans `drill_down_generator.py`
4. Les mains sont maintenant correctement détectées dans leurs sous-ranges avec leur séquence

**Logs avant correction** :
```
[DRILL] Main choisie IN-RANGE: KK
[DRILL] FOLD implicite généré: RAISE→FOLD
```

**Logs après correction** :
```
[DRILL] Main choisie IN-RANGE: KK
[DRILL] ✅ Main KK trouvée dans sous-range: 4bet_value (R4_VALUE)
[DRILL] Séquence trouvée dans 4bet_value: RAISE→RAISE
```

### Drill-down affichait les mauvaises séquences ❌ → ✅ Corrigé (v4.2)
**Problème** : L'historique des actions affichait des séquences théoriques inventées (basées sur `getQuizActionSequence()`) au lieu des vraies actions du joueur

**Cause** :
1. `quiz.html` utilisait une fonction `getQuizActionSequence(labelCanon, primaryAction, rangeKey)` qui inventait des séquences basées sur des patterns génériques
2. Pour R4_BLUFF par exemple, elle générait `RAISE → RAISE → FOLD` même si la vraie séquence était différente
3. Cette fonction était copiée de `validate_context.html` où elle sert à afficher les séquences théoriques d'une range, pas l'historique réel du quiz

**Solution** :
1. Suppression complète de `getQuizActionSequence()` dans `quiz.html`
2. Création de `displayDrillDownSequence(currentLevel)` qui utilise `currentQuestion.sequence`
3. Affichage progressif : seulement les actions **déjà effectuées** (0 à currentLevel-1)
4. Simplification du CSS (suppression des groupes, slashes, etc.)

**Données maintenant utilisées** :
```javascript
currentQuestion.sequence = [
  { action: "RAISE", text: "Action: RAISE", type: "single" },
  { action: "FOLD", text: "Action: FOLD", type: "single" }
]
```

**Affichage** :
- Niveau 0 : Rien (première question)
- Niveau 1 : `RAISE →` (action du niveau 0)

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

## 💡 Notes pour les développeurs futurs

### Architecture Drill-Down : Points d'attention

1. **Chargement des données** : `quiz_generator.py` DOIT charger `action_sequence` dans la requête SQL. Sans cela, tout le système drill-down tombera en panne et générera uniquement des FOLD implicites.

2. **Séquences vs Labels** : Ne pas confondre :
   - `action_sequence` dans `ranges` (TEXT) : séquence réelle type "RAISE→RAISE→FOLD"
   - `label_canon` : classification de la range (R4_BLUFF, R4_VALUE, etc.)
   - Les séquences théoriques de `validate_context.html` ne sont PAS pour le quiz

3. **Affichage progressif** : Dans `quiz.html`, utiliser `currentQuestion.sequence` et non une fonction qui invente des séquences. L'historique doit montrer ce que le joueur a VRAIMENT fait.

4. **Probabilités** : Le système 50% par étape est dans `drill_down_generator.py` ligne 290+. Modifier avec précaution car cela impacte l'équilibre pédagogique.

5. **Mains et sous-ranges** : Si une main est dans la range principale mais pas dans les sous-ranges, c'est un FOLD implicite. C'est intentionnel (si le joueur n'a pas créé de sous-range, il ne veut pas pratiquer ce scénario).

### Debugging Tips

**Si le drill-down ne fonctionne pas :**
1. Vérifier les logs : `[DRILL] Main choisie IN-RANGE:` → doit être suivi de `✅ Main trouvée dans sous-range` OU `⚠️ FOLD implicite`
2. Vérifier que `quiz_generator.py` charge bien `action_sequence` (ligne ~97)
3. Vérifier que les sous-ranges ont bien un `action_sequence` dans la DB
4. Vérifier les logs de `drill_down_generator.py` : ils sont très verbeux exprès

**Si l'affichage de l'historique est incorrect :**
1. Console navigateur : `console.log('sequence:', currentQuestion.sequence)`
2. Vérifier que `displayDrillDownSequence()` utilise bien `.slice(0, currentLevel)`
3. Vérifier que les badges CSS sont bien définis (`.quiz-action-raise`, etc.)

### Structure des modules

**quiz_generator.py** :
- Décide entre simple et drill-down (ligne ~133)
- Charge les ranges avec `action_sequence` (ligne ~95-117)
- Appelle `drill_down_generator.py` si drill-down choisi

**drill_down_generator.py** :
- Vérifie l'existence de sous-ranges (ligne ~232)
- Sélectionne une main (ligne ~239-247)
- Cherche dans quelle sous-range est la main (ligne ~250-254)
- Génère la séquence ou FOLD implicite (ligne ~257-264)
- Calcule le nombre d'étapes (ligne ~280-297)
- Construit les niveaux (levels) pour le quiz (ligne ~299+)

**quiz.html** :
- Affiche progressivement l'historique avec `displayDrillDownSequence()` (ligne ~900+)
- Utilise `currentQuestion.sequence` fourni par le backend
- Badges colorés avec CSS (ligne ~260-290)
- Gère la progression niveau par niveau

---

**Dernière mise à jour** : 28/10/2025  
**Version** : 4.2 - Drill-down multi-étapes opérationnel avec corrections majeures

Créé avec ❤️ pour la communauté poker
