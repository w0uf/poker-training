# Poker Training - Système d'entraînement de ranges

Interface web locale pour l'entraînement de ranges de poker avec système de quiz interactif avancé et questions drill-down multi-étapes.

## 🎯 Vue d'ensemble

**poker-training** permet d'importer et d'utiliser des ranges de poker pour l'entraînement. Les ranges sont créées via l'[éditeur de ranges](https://site2wouf.fr/poker-range-editor.php) puis automatiquement analysées, validées et utilisées dans un quiz interactif intelligent.

## ✨ Fonctionnalités principales

### Pipeline d'import automatique
- Import et parsing des fichiers JSON
- Standardisation intelligente des noms et positions
- Enrichissement automatique des métadonnées
- Support complet des contextes : Open, Defense, Squeeze, VS_Limpers
- Validation stricte avant activation pour le quiz

### Système de Quiz Interactif ✨

#### Questions Simples
- Configuration flexible : sélection des contextes et nombre de questions
- Questions contextuelles adaptées à chaque situation
- **🆕 v4.3.7 : Tracking intelligent par contexte** - Une main peut apparaître dans différents contextes (situations d'apprentissage différentes)
- Sélection intelligente avec détection des mains borderline
- Boutons dynamiques selon le contexte (RAISE au lieu de 3BET, ISO pour vs_limpers, etc.)
- Feedback immédiat avec statistiques en temps réel

#### Questions Drill-Down (Multi-étapes) 🎯
- **Séquences réalistes** : Simule les décisions successives (Open → 3bet → 4bet → 5bet/all-in)
- **🆕 v4.3.6 : Position du Vilain cohérente** - Même adversaire sur toute la séquence
- **🆕 v4.3.6 : Historique narratif fluide** - Texte naturel reprenant l'histoire de la main
- **Gestion automatique des FOLD implicites** - Si une main n'est pas dans les sous-ranges, elle fold
- **Affichage progressif** avec feedback adapté à chaque niveau

#### 🎚️ Paramètre d'agressivité de la table (✅ v4.4.0)

Contrôle l'agressivité des adversaires et la profondeur des séquences :

| Niveau | Drill-down | Profondeur | All-in L2 | All-in L3 | 5bet | Usage |
|--------|-----------|------------|-----------|-----------|------|-------|
| 🟢 **LOW** | 50% | 30% | 20% | 0% | 30% | Débutants |
| 🟡 **MEDIUM** | 70% | 60% | 50% | 10% | 50% | Standard |
| 🔴 **HIGH** | 100% | 100% | 80% | 50% | 70% | Avancés |

**Configuration** : Fichier `aggression_settings.py` avec paramètres centralisés

**Résultat** :
- **LOW** : Séquences courtes (1-2 étapes), peu d'all-in
- **MEDIUM** : Équilibré, bon pour l'entraînement général
- **HIGH** : Séquences longues (3 étapes), beaucoup d'all-in

### Architecture des ranges
- **Range principale** : Contient toutes les mains jouables dans le contexte
- **Sous-ranges** : Actions spécifiques avec séquences (ex: "RAISE→RAISE" pour 4bet)
- **FOLD implicites** : Mains absentes des sous-ranges foldent automatiquement
- **Labels canoniques** : Classification standardisée (OPEN, CALL, R3_VALUE, R4_BLUFF, etc.)

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

# 2. Lancer l'interface web
cd web/
python app.py

# 3. Accéder à http://localhost:5000

# 4. Importer via "Import Pipeline"

# 5. Valider les contextes si nécessaire

# 6. Lancer le quiz !
```

## 🏗️ Architecture

### Structure du projet

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite
│   └── ranges/                   # Fichiers JSON
├── web/
│   ├── app.py                    # Serveur Flask + API
│   └── templates/                # Interfaces HTML
├── modules/
│   ├── quiz_generator.py         # Génération questions
│   ├── drill_down_generator.py   # Questions multi-étapes
│   ├── hand_selector.py          # Sélection intelligente
│   ├── aggression_settings.py    # Configuration agressivité 🆕 v4.4.0
│   └── ... (autres modules)
└── README.md
```

### Base de données SQLite

#### Tables principales
- **range_files** : Fichiers importés avec métadonnées
- **range_contexts** : Contextes avec validation et action_sequence (JSON pour multiway)
- **ranges** : Ranges individuelles avec labels et action_sequence (TEXT pour drill-down)
- **range_hands** : Mains avec fréquences

#### Colonne action_sequence

**Dans `range_contexts` (JSON)** - Gestion multiway :
```json
{"opener": "UTG", "callers": ["CO"]}  // Squeeze
{"limpers": ["UTG", "CO"]}            // VS_Limpers
```

**Dans `ranges` (TEXT)** - Séquences drill-down :
```
"RAISE→RAISE→FOLD"  // Open → 4bet → Fold au 5bet
```

### Workflow drill-down

```
1. quiz_generator.py décide : simple ou drill-down ?
   ↓
2. drill_down_generator.py :
   - Vérifie les sous-ranges
   - Sélectionne une main (évite répétitions par contexte)
   - Cherche dans quelle sous-range → sinon FOLD implicite
   - Génère position Vilain fixe (v4.3.6)
   - Construit séquence narrative (v4.3.6)
   - Utilise probabilités selon niveau d'agressivité (v4.4.0)
   ↓
3. quiz.html affiche progressivement avec historique narratif
```

## 📚 Workflow complet

```
Éditeur web → JSON → data/ranges/ → Import Pipeline
    ↓
Validation (si nécessaire) → quiz_ready=1
    ↓
Configuration Quiz (contextes + nombre + agressivité)
    ↓
Entraînement avec drill-down et tracking intelligent
```

## 🎯 État du développement

### ✅ Fonctionnalités opérationnelles (v4.4.2)

- ✅ Pipeline d'import complet
- ✅ Support tous contextes (Open, Defense, Squeeze, VS_Limpers)
- ✅ Quiz simple et drill-down multi-étapes
- ✅ **Paramètre d'agressivité** avec 3 niveaux configurables (v4.4.0)
- ✅ Position Vilain cohérente et historique narratif (v4.3.6)
- ✅ Tracking intelligent des mains par contexte (v4.3.7)
- ✅ Gestion correcte des all-in dans les séquences (v4.4.2)
- ✅ Interface web responsive avec statistiques temps réel

### 🚧 Améliorations prioritaires (v4.5+)

- 🔄 **Écran post-quiz détaillé** :
  - Score par contexte et type de question
  - Analyse des patterns d'erreurs
  - Recommandations personnalisées
  - Export des résultats
  
- 🔄 **Affinage des labels poker** :
  - Clarification VALUE/BLUFF
  - Documentation stratégique
  - Simplification si redondance

- 🔄 **Mode d'entraînement configurable** :
  - Désactivation drill-down temporaire
  - Choix du ratio simple/drill-down
  - Nombre max d'étapes personnalisable

### 🔮 Roadmap (v5.0+)

- Analytics avancées avec progression historique
- Mode révision espacée (spaced repetition)
- Contextes 3-way et 4-way
- Drill-down post-flop
- Coach virtuel avec suggestions personnalisées

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créer une branche (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

**Guidelines** :
- Suivre PEP 8
- Ajouter des docstrings
- Tester avant de soumettre
- Mettre à jour la documentation

## 📝 Changelog

### v4.4.2 (31/10/2025)
- 🐛 **Correction Bug #1** : Skip all-in uniquement en mode HIGH (15% de probabilité)
- 🐛 **Correction Bug #2** : Arrêt automatique de la séquence après all-in
- 🐛 **Correction Bug #3** : Support complet du niveau 3 avec all-in
- 📚 Documentation complète des bugs et correctifs

### v4.4.0 (30/10/2025)
- ✨ **Système d'agressivité** avec 3 niveaux (LOW/MEDIUM/HIGH)
- ✨ Widget de sélection dans l'interface
- ⚙️ Configuration centralisée dans `aggression_settings.py`
- 📊 Probabilités paramétrables pour chaque niveau

### v4.3.7 (28/10/2025)
- ✨ Tracking intelligent des mains par contexte
- 🐛 Évite les répétitions dans le même contexte
- 📝 Permission de réutiliser une main dans un contexte différent

### v4.3.6 (27/10/2025)
- ✨ Position du Vilain cohérente dans les séquences
- ✨ Historique narratif fluide (texte naturel au lieu de badges)
- 🎨 Amélioration de l'UX drill-down

### v4.0.0 (20/10/2025)
- ✨ Système de drill-down multi-niveaux
- ✨ Support des séquences 3bet/4bet/5bet/all-in
- ✨ FOLD implicites automatiques

## 🐛 Problèmes connus résolus

### ✅ All-in Skip en mode MEDIUM (v4.4.2)
**Problème** : All-in direct généré en MEDIUM au lieu de HIGH uniquement  
**Correction** : Vérification de `villain_skip_allin_level1` avec probabilité 15% en HIGH

### ✅ Séquence continue après all-in (v4.4.2)
**Problème** : Le système générait un niveau suivant après un all-in  
**Correction** : Détection d'all-in avec `break` pour arrêter la boucle

### ✅ Pas d'all-in au niveau 3 (v4.4.2)
**Problème** : Le niveau 3 n'était pas géré pour les all-in  
**Correction** : Ajout du cas niveau 3 dans `_get_villain_reaction_at_level()`

### ✅ Position Vilain incohérente (v4.3.6)
**Problème** : Position changeait à chaque étape  
**Correction** : Génération fixe UNE SEULE FOIS au début

### ✅ Historique avec badges (v4.3.6)
**Problème** : Affichage technique peu naturel  
**Correction** : Texte narratif fluide en français

### ✅ Répétition des mêmes mains (v4.3.7)
**Problème** : Plusieurs questions sur la même main dans un contexte  
**Correction** : Tracking par contexte avec `used_hands_by_context`

## 💡 Notes pour développeurs

### Points d'attention Drill-Down

1. **Chargement données** : `quiz_generator.py` DOIT charger `action_sequence` dans la requête SQL
2. **Position Vilain** : Générée UNE SEULE FOIS et stockée dans `context['villain_position_fixed']`
3. **Historique narratif** : Utiliser `displayDrillDownSequence()` avec `currentQuestion.sequence`
4. **Tracking mains** : PAR CONTEXTE (dict) et non global - permet apprentissage différencié
5. **Agressivité** : Configuration dans `aggression_settings.py`, utilisée par les deux générateurs

### Debugging Tips

**Drill-down ne fonctionne pas :**
- Vérifier logs : `[DRILL] Main choisie IN-RANGE:` suivi de `✅ Main trouvée` ou `⚠️ FOLD implicite`
- Vérifier que `action_sequence` est chargé (ligne ~97 de `quiz_generator.py`)

**Historique incorrect :**
- Console : `console.log('sequence:', currentQuestion.sequence)`
- Vérifier que `displayDrillDownSequence()` utilise `.slice(0, currentLevel)`

**Répétitions de mains :**
- Vérifier logs : `[QUIZ GEN] 🎲 Main utilisée: XX dans contexte Y`
- Vérifier que `used_hands_by_context` est bien un dict

**All-in mal géré :**
- Vérifier le niveau d'agressivité sélectionné
- Vérifier les probabilités dans `aggression_settings.py`
- Vérifier que `is_allin` est détecté et traité avec `break`

### Structure des modules

- **quiz_generator.py** : Décide simple/drill-down, charge ranges, gère tracking
- **drill_down_generator.py** : Génère séquences, position Vilain fixe, utilise agressivité
- **aggression_settings.py** : 🆕 v4.4.0 - Configuration centralisée des probabilités
- **quiz.html** : Affiche historique narratif progressif
- **app.py** : Maintient `used_hands_by_context`, passe paramètres

## 📄 Licence

Projet sous licence libre - voir [LICENSE](LICENSE) pour plus de détails.

## 🔗 Liens utiles

- [Éditeur de ranges web](https://site2wouf.fr/poker-range-editor.php)
- [Documentation Python](https://docs.python.org/3/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Repository GitHub](https://github.com/w0uf/poker-training)

---

**Dernière mise à jour** : 31/10/2025  
**Version actuelle** : 4.4.2

Créé avec ❤️ pour la communauté poker
