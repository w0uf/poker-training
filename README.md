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
- **Statistiques détaillées** : score, progression, résultats finaux

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
│   └── [Mains à open depuis UTG]
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── AQs, JJ, TT, ...
│   └── [Face à 3bet adverse → call]
├── Range 3 (sous-range) : label_canon='R4_VALUE'
│   ├── AA, KK, QQ
│   └── [Face à 3bet adverse → 4bet value]
└── Range 4 (sous-range) : label_canon='R4_BLUFF'
    ├── A5s, A4s
    └── [Face à 3bet adverse → 4bet bluff]
```

#### Exemple 2 : Range de DEFENSE

```
Fichier JSON : "nlhe-5max-co-defense-vs-utg-100bb.json"
├── Range 1 (principale) : label_canon='DEFENSE'
│   ├── AA, KK, QQ, JJ, TT, 99, 88, 77, AKs, AQs, KQs, JTs, ...
│   └── [TOUTES les mains jouables = union de call + 3bet]
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── 88, 77, AQs, KQs, JTs, ...
│   └── [Face à open UTG → call]
├── Range 3 (sous-range) : label_canon='R3_VALUE'
│   ├── AA, KK, QQ, JJ, TT, AKs
│   └── [Face à open UTG → 3bet value]
└── Range 4 (sous-range) : label_canon='R3_BLUFF'
    ├── A5s, A4s, A3s
    └── [Face à open UTG → 3bet bluff]
```

**⚠️ Important pour les ranges de defense :**
- La range principale (range_key='1') contient **TOUTES** les mains non-fold (union complète)
- Les sous-ranges définissent les **actions spécifiques** (CALL, 3BET)
- Le quiz utilise `_find_subrange_action()` pour chercher dans les sous-ranges
- L'action 3BET est convertie en **RAISE** pour l'affichage UI (plus clair pour l'utilisateur)

#### Exemple 3 : Range de SQUEEZE ✅

```
Fichier JSON : "nlhe-5max-btn-squeeze-100bb.json"
Métadonnées: primary_action='squeeze', action_sequence='{"opener":"UTG","callers":["CO"]}'

├── Range 1 (principale) : label_canon='SQUEEZE'
│   ├── AA, KK, QQ, JJ, AKs, AQs, ...
│   └── [Toutes les mains à squeeze depuis BTN vs UTG open + CO call]
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── 88, 77, JTs, ...
│   └── [Overcall le call de CO]
├── Range 3 (sous-range) : label_canon='R3_VALUE'
│   ├── AA, KK, QQ, JJ, AKs
│   └── [Squeeze value]
└── Range 4 (sous-range) : label_canon='R3_BLUFF'
    ├── A5s, A4s, A3s
    └── [Squeeze bluff]
```

**Note importante pour SQUEEZE :**
- Le `label_canon='SQUEEZE'` est normalisé vers `'RAISE'` dans `poker_constants.py`
- Ceci permet d'afficher "RAISE" dans l'UI plutôt que le terme technique "SQUEEZE"
- L'`action_sequence` JSON stocke opener et callers pour générer la question contextuelle

#### Exemple 4 : Range VS_LIMPERS ✅

```
Fichier JSON : "nlhe-6max-btn-vs_limpers-100bb.json"
Métadonnées: primary_action='vs_limpers', limpers='UTG,CO', action_sequence='{"limpers":["UTG","CO"]}'

├── Range 1 (principale) : label_canon='RAISE' ou 'ISO'
│   ├── AA, KK, QQ, JJ, TT, 99, AKs, AQs, KQs, ...
│   └── [Toutes les mains jouables face aux limpers]
├── Range 2 (sous-range) : label_canon='CALL'
│   ├── 88, 77, 66, KQo, JTo, 98s, ...
│   └── [Overlimper derrière les limpers]
├── Range 3 (sous-range) : label_canon='ISO_VALUE'
│   ├── AA, KK, QQ, JJ, TT, 99, AKs, AQs, AJs
│   └── [Iso raise value]
└── Range 4 (sous-range) : label_canon='ISO_BLUFF'
    ├── A5s, A4s, A3s, K9s, K8s, Q9s, J9s, T9s, 98s, 87s
    └── [Iso raise bluff]
```

**Note importante pour VS_LIMPERS :**
- Le `label_canon` de la range principale peut être 'RAISE' (générique) ou 'ISO' (si 'iso' dans le nom)
- Les actions ISO_VALUE et ISO_BLUFF sont normalisées vers `'ISO'` pour l'UI
- L'`action_sequence` JSON stocke la liste des limpers : `{"limpers": ["UTG", "CO"]}`
- Question générée : "Table 6max, vous êtes BTN avec 100bb. UTG et CO limpent. Vous avez XX. Que faites-vous ?"
- Options : `[FOLD, CALL, ISO]` ou `[FOLD, CALL, RAISE]` selon la normalisation

### Labels canoniques

#### Actions principales
- **OPEN** : Range d'ouverture
- **DEFENSE** : Range de defense (contient toutes les mains jouables)
- **SQUEEZE** : Range de squeeze (multiway, vs open + call)
- **RAISE** : Raise générique (utilisé pour vs_limpers)
- **ISO** : Iso raise (vs limpers)
- **CALL** : Call / Complete / Flat / Overlimper
- **CHECK** : Check
- **FOLD** : Fold

#### Actions de relance
- **R3_VALUE** : 3bet Value (normalisé en 3BET, affiché comme RAISE en defense)
- **R3_BLUFF** : 3bet Bluff (normalisé en 3BET, affiché comme RAISE en defense)
- **R4_VALUE** : 4bet Value (normalisé en 4BET pour le quiz)
- **R4_BLUFF** : 4bet Bluff (normalisé en 4BET pour le quiz)
- **R5_ALLIN** : 5bet / All-in

#### Actions vs limpers
- **ISO_RAISE** : Iso raise générique (normalisé en ISO pour le quiz)
- **ISO_VALUE** : Iso raise Value (normalisé en ISO pour le quiz)
- **ISO_BLUFF** : Iso raise Bluff (normalisé en ISO pour le quiz)

### Logique de validation et mapping

**Mapping contextuel avec priorité au primary_action**

```python
def map_name_to_label_canon(name: str, range_key: str, primary_action: str = None):
    if range_key == '1':  # Range principale
        # PRIORITÉ : Le contexte prime sur le nom !
        if primary_action:
            if 'defense' in primary_action.lower():
                return 'DEFENSE'
            elif 'squeeze' in primary_action.lower():
                return 'SQUEEZE'  # ✅ Squeeze détecté
            elif 'vs_limpers' in primary_action.lower():
                if 'iso' in name.lower():
                    return 'ISO'
                return 'RAISE'  # ✅ VS_Limpers détecté
            elif 'open' in primary_action.lower():
                return 'OPEN'
        
        # Sinon mapping classique basé sur le nom
        # Ordre important : squeeze AVANT 3bet !
        if 'squeeze' in name.lower() or 'squezze' in name.lower():
            return 'SQUEEZE'
        elif 'iso' in name.lower() or 'limper' in name.lower():
            return 'ISO'
        elif 'open' in name.lower():
            return 'OPEN'
        # ...
```

**Action principale du héros → Sous-ranges = Réponses aux réactions adverses**

| Action principale | Réaction adverse | Sous-ranges attendus |
|-------------------|------------------|---------------------|
| OPEN | Face à 3bet | CALL, R4_VALUE, R4_BLUFF, FOLD |
| DEFENSE | Réponse à open | CALL, R3_VALUE, R3_BLUFF, FOLD |
| SQUEEZE | Face à 4bet | CALL, R5_ALLIN, FOLD |
| VS_LIMPERS | Face à un iso raise adverse | CALL, ISO_VALUE, ISO_BLUFF, FOLD |
| 3BET / SQUEEZE | Face à 4bet | CALL, R5_ALLIN, FOLD |
| 4BET | Face à 5bet | CALL, FOLD |

## 🎮 Système de Quiz Interactif

### Configuration du Quiz

**Page de setup** : `http://localhost:5000/quiz-setup`

1. **Sélection des contextes** : Checkbox pour chaque contexte `quiz_ready`
2. **Nombre de questions** : Slider de 5 à 50 questions
3. **Lancement** : Génération instantanée des questions

### Sélection intelligente des mains

Le système privilégie les **mains borderline** (à la frontière de la range) pour un entraînement optimal :

```python
def smart_hand_choice(in_range, out_of_range, is_in_range=True):
    """
    Sélectionne une main en privilégiant les borderlines.
    
    Borderline IN : Mains juste à l'intérieur de la range
    Borderline OUT : Mains juste à l'extérieur de la range
    
    Pondération :
    - 60% borderlines (décisions difficiles)
    - 40% aléatoires (pour couvrir toute la range)
    """
```

**Exemple de détection de borderlines :**
```
IN-RANGE : [..., ATs(90), A9s(87), A8s(84), ...]
OUT-RANGE : [..., A7s(78), A6s(74), A5s(71), ...]

→ Borderlines IN : ATs, A9s, A8s (proches de la frontière)
→ Borderlines OUT : A7s, A6s, A5s (juste exclus)

→ Le quiz pose plus souvent ces mains difficiles !
```

### Types de Questions

#### Question Simple - OPEN
```
Contexte : Table 5max, vous êtes UTG avec 100bb
Main affichée : AJs
Question : Vous avez AJs. Que faites-vous ?

Boutons disponibles : [FOLD] [CALL] [RAISE]
Réponse correcte : RAISE (range principale label_canon='OPEN')
```

#### Question Simple - DEFENSE ✅
```
Contexte : Table 5max, vous êtes CO avec 100bb
Main affichée : KQs
Question : UTG ouvre. Vous avez KQs. Que faites-vous ?

Boutons disponibles : [FOLD] [CALL] [RAISE]
Réponse correcte : CALL (trouvée dans sous-range label_canon='CALL')

Logique :
1. Main KQs est IN-RANGE (dans range principale DEFENSE)
2. Appel de _find_subrange_action(KQs, sous_ranges)
3. Trouve KQs dans sous-range "call" → retourne 'CALL'
4. Conversion 3BET → RAISE pour l'affichage (si applicable)
```

#### Question Simple - SQUEEZE ✅
```
Contexte : Table 5max, vous êtes BTN avec 100bb
Main affichée : AQs
Question : UTG ouvre, CO call. Vous avez AQs. Que faites-vous ?

Boutons disponibles : [FOLD] [CALL] [RAISE]
Réponse correcte : RAISE (range principale label_canon='SQUEEZE' normalisé vers RAISE)

Logique :
1. label_canon='SQUEEZE' est normalisé vers 'RAISE' dans poker_constants.py
2. action_sequence='{"opener":"UTG","callers":["CO"]}' génère la question contextuelle
3. Les options affichent RAISE (plus clair que SQUEEZE pour l'utilisateur)
```

#### Question Simple - VS_LIMPERS ✅
```
Contexte : Table 6max, vous êtes BTN avec 100bb
Main affichée : KQs
Question : UTG et CO limpent. Vous avez KQs. Que faites-vous ?

Boutons disponibles : [FOLD] [CALL] [ISO]
Réponse correcte : ISO (trouvée dans sous-range label_canon='ISO_VALUE' normalisé vers ISO)

Logique :
1. action_sequence='{"limpers":["UTG","CO"]}' génère la question
2. Main KQs est IN-RANGE (dans range principale)
3. _find_subrange_action(KQs, sous_ranges) trouve KQs dans "iso_value"
4. Normalisation : ISO_VALUE → ISO pour l'affichage
5. Format question : "UTG et CO limpent" (détecté depuis action_sequence)
```

#### Question Simple - BB CHECK
```
Contexte : Table 6max, vous êtes BB avec 100bb
Main affichée : 72o
Question : Personne n'a ouvert. Vous avez 72o. Que faites-vous ?

Boutons disponibles : [CHECK] [RAISE]
(Pas de FOLD car action gratuite !)
```

### Interface du Quiz

- **Table de poker virtuelle** : Fond vert réaliste avec effet feutre
- **Affichage des cartes** : Animation de distribution des cartes
- **Contexte visible** : Table format, position, stack depth
- **Questions contextuelles** : Texte adapté selon open/defense/squeeze/vs_limpers/4bet/etc.
- **Boutons d'action dynamiques** :
  - Adaptation selon le contexte (defense = RAISE au lieu de 3BET)
  - VS_Limpers = ISO au lieu de ISO_VALUE/BLUFF
  - BB check = pas de FOLD (action gratuite)
  - DEFENSE ne s'affiche jamais comme bouton (c'est un label technique)
  - Couleurs distinctes (FOLD rouge, CALL bleu, RAISE orange, ISO violet, etc.)
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
        
        # Sélection intelligente avec borderlines
        hand = smart_hand_choice(in_range, out_range, is_in_range=True)
        
        # Pour DEFENSE : trouve l'action dans les sous-ranges
        if label_canon == 'DEFENSE':
            correct_answer = _find_subrange_action(hand, ranges)
            # Conversion 3BET → RAISE pour l'UI
            if correct_answer == '3BET':
                correct_answer = 'RAISE'
        else:
            correct_answer = normalize_action(label_canon)
    else:
        question = generate_conditional_question()
        # Utilise une sous-range aléatoire (range_key>'1')
    
    # Filtrage automatique des questions invalides
    if question.has_valid_label_canon:
        add_to_quiz(question)
```

### Format des questions selon action_sequence

Le texte de la question est généré automatiquement depuis `action_sequence` :

```python
def _format_question(context, hand):
    action_seq = context.get('action_sequence')  # Dict Python parsé depuis JSON
    
    if primary_action == 'defense':
        opener = action_seq.get('opener', 'UTG')
        parts.append(f"{opener} ouvre")
    
    elif primary_action == 'squeeze':
        opener = action_seq.get('opener', 'UTG')
        callers = action_seq.get('callers', [])
        
        parts.append(f"{opener} ouvre")
        
        if len(callers) == 1:
            parts.append(f"{callers[0]} call")
        else:
            caller_str = ", ".join(callers[:-1]) + f" et {callers[-1]}"
            parts.append(f"{caller_str} callent")
    
    elif primary_action == 'vs_limpers':
        limpers = action_seq.get('limpers', [])
        
        if len(limpers) == 1:
            parts.append(f"{limpers[0]} limp")
        else:
            limper_str = ", ".join(limpers[:-1]) + f" et {limpers[-1]}"
            parts.append(f"{limper_str} limpent")
```

### Fonction _find_subrange_action()

Pour les contextes de defense et vs_limpers, cette fonction trouve l'action correcte :

```python
def _find_subrange_action(hand, ranges):
    """
    Trouve l'action correcte pour une main dans un contexte defense/vs_limpers.
    Cherche dans les sous-ranges (range_key > 1).
    
    Returns:
        'CALL', '3BET', 'ISO', etc. (action normalisée)
        Note : 3BET sera converti en RAISE, ISO_VALUE en ISO dans _generate_simple_question
    """
    for r in ranges:
        if r['range_key'] != '1' and hand in r['hands']:
            label = r.get('label_canon')
            if label:
                return normalize_action(label)
    
    return None  # Main non trouvée (erreur de cohérence)
```

### Normalisation des Actions

Les actions sont normalisées pour éviter les doublons :

```python
ACTION_NORMALIZATION = {
    'R3_VALUE': '3BET',
    'R3_BLUFF': '3BET',
    'R4_VALUE': '4BET',
    'R4_BLUFF': '4BET',
    'R5_ALLIN': 'ALLIN',
    'ISO_VALUE': 'ISO',      # ✅ VS_Limpers
    'ISO_BLUFF': 'ISO',      # ✅ VS_Limpers
    'ISO_RAISE': 'ISO',      # ✅ VS_Limpers
    'SQUEEZE': 'RAISE',      # ✅ Squeeze normalise vers RAISE pour l'UI
}
```

### Génération des options de réponse

Les options s'adaptent intelligemment au contexte :

```python
def _generate_action_options(correct_answer, main_range_action, context):
    options = []
    
    # 1. Toujours la bonne réponse
    options.append(correct_answer)
    
    # 2. FOLD ou CHECK selon le contexte
    if context['hero_position'] == 'BB' and 'check' in context['primary_action']:
        options.append('CHECK')  # Pas de FOLD si action gratuite
    else:
        options.append('FOLD')
    
    # 3. Pour DEFENSE, ne JAMAIS ajouter 'DEFENSE' comme option
    #    (c'est un label technique, pas une action jouable)
    if main_range_action and main_range_action != 'DEFENSE':
        if main_range_action not in options:
            options.append(main_range_action)
    
    # 4. Distracteurs intelligents selon le contexte
    if 'defense' in context['primary_action']:
        distractors = ['CALL', 'RAISE']  # ✅ RAISE au lieu de 3BET
    elif 'squeeze' in context['primary_action']:
        distractors = ['CALL']
    elif 'vs_limpers' in context['primary_action']:
        distractors = ['CALL', 'ISO']  # ✅ Options pour vs_limpers
    # ...
    
    return sort_actions(options)
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
- `POST /api/quiz/question` : Obtient la prochaine question

## 🧪 Tests et debugging

### Routes de debug

```
http://localhost:5000/debug_structure     # Structure de la DB
http://localhost:5000/debug_all_contexts  # Liste tous les contextes
http://localhost:5000/debug_metadata      # Métadonnées détaillées
```

### Vérification de la base

```python
import sqlite3
conn = sqlite3.connect('data/poker_trainer.db')
cursor = conn.cursor()

# Vérifier le mapping contextuel
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
   - S'entraîner
   - Consulter les résultats
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
- ✅ **Statistiques et résultats détaillés**

#### Interface web
- ✅ Dashboard temps réel avec statistiques
- ✅ Interface de validation interactive
- ✅ Interface web responsive

### 🚧 Améliorations prioritaires (v4.1)

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
- 📊 **Statistiques par contexte** : Taux de réussite par type de situation

#### Fonctionnalités générales
- 📊 Statistiques de progression détaillées
- 🔁 Système de révision espacée
- 📤 Export des résultats en CSV/JSON
- 📱 Interface mobile optimisée
- 🎨 Thèmes personnalisables

### 🔮 Roadmap (v5.0+)

**Moyen terme**
- Support formats additionnels (PIO, GTO+)
- Mode hors-ligne complet
- Synchronisation cloud (optionnel)
- Partage de ranges entre utilisateurs
- **Contextes 3-way et 4-way** (plusieurs callers, plusieurs limpers)

**Long terme**
- Analytics avancées avec graphiques
- Mode entraînement vs mode examen
- Timer par question (optionnel)
- Classement et achievements
- Intégration avec trackers de poker

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

---

**Dernière mise à jour** : 15/01/2025  
**Version** : 4.0 - Support complet VS_LIMPERS + action_sequence JSON

Créé avec ❤️ pour la communauté poker
