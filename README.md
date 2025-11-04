# 🃏 Poker Training - Entraînement de Ranges Preflop

> **Version Beta 4.5.0** - Système d'entraînement interactif avec suivi de progression

Interface web locale pour s'entraîner sur les ranges de poker avec quiz intelligent, questions multi-étapes et analytics de progression.

---

## ✨ Fonctionnalités

### 🎯 Système de Quiz Intelligent
- **Questions simples** : Test direct de vos ranges
- **Questions drill-down** : Séquences réalistes (Open → 3bet → 4bet → 5bet)
- **Agressivité configurable** : 3 niveaux (LOW/MEDIUM/HIGH)
- **Feedback immédiat** avec statistiques temps réel

### 📊 Suivi de Progression
- **Historique complet** : Toutes vos sessions sauvegardées
- **Graphiques de progression** : Visualisez votre évolution
- **Stats par contexte** : Identifiez vos points forts et faibles
- **Recommandations personnalisées** : Conseils adaptés à vos résultats
- **Calcul du streak** : Jours d'entraînement consécutifs

### 🎚️ Paramètres d'Entraînement
- **Choix des contextes** : Open, Defense, Squeeze, VS Limpers
- **Nombre de questions** : Personnalisable
- **Niveau d'agressivité** : Adapté à votre progression

### 📈 Analytics
- Meilleur score, score moyen, total sessions
- Graphiques d'évolution sur le temps
- Filtres par date, score et contexte
- Export CSV des résultats

---

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip

### Installation rapide

```bash
# 1. Cloner le repository
git clone https://github.com/w0uf/poker-training.git
cd poker-training

# 2. Créer environnement virtuel
python3 -m venv mon_env
source mon_env/bin/activate  # Linux/Mac
# ou
mon_env\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install flask

# 4. Créer la structure de données
mkdir -p data/ranges
```

---

## 📖 Démarrage rapide

```bash
# 1. Placer vos fichiers JSON de ranges dans data/ranges/
# (Créés avec l'éditeur : https://site2wouf.fr/poker-range-editor.php)

# 2. Lancer l'application
cd web/
python app.py

# 3. Ouvrir votre navigateur
# → http://localhost:5000

# 4. Suivre le workflow
# Import Pipeline → Validation → Configuration Quiz → Entraînement !
```

---

## 🎮 Utilisation

### Workflow complet

```
1. Import des Ranges
   ↓
   Éditeur web → JSON → data/ranges/ → Import Pipeline
   
2. Validation
   ↓
   Vérification des contextes → Activation pour le quiz
   
3. Configuration
   ↓
   Sélection contextes + nombre de questions + agressivité
   
4. Entraînement
   ↓
   Quiz interactif avec drill-down
   
5. Résultats
   ↓
   Analyse détaillée + recommandations
   
6. Progression
   ↓
   Historique complet + graphiques + stats
```

### Pages principales

- **`/`** : Accueil avec statistiques globales
- **`/import`** : Import des fichiers JSON
- **`/quiz-setup`** : Configuration du quiz
- **`/quiz`** : Session d'entraînement
- **`/quiz-result`** : Résultats détaillés avec progression
- **`/history`** : Historique complet avec analytics

---

## 🏗️ Architecture

### Structure du projet

```
poker-training/
├── data/
│   ├── poker_trainer.db          # Base SQLite principale
│   ├── quiz_history.db            # Historique des sessions
│   └── ranges/                    # Fichiers JSON importés
├── web/
│   ├── app.py                     # Serveur Flask + API
│   └── templates/                 # Interfaces HTML
│       ├── index.html             # Accueil
│       ├── quiz-setup.html        # Configuration
│       ├── quiz.html              # Interface quiz
│       ├── quiz-result.html       # Résultats + progression
│       └── history.html           # Historique complet
├── modules/
│   ├── quiz_generator.py          # Génération questions
│   ├── drill_down_generator.py    # Questions multi-étapes
│   ├── hand_selector.py           # Sélection intelligente
│   ├── quiz_history_manager.py    # Gestion historique 🆕
│   ├── aggression_settings.py     # Configuration agressivité
│   └── ...
└── README.md
```

### Base de données

**poker_trainer.db** : Ranges et contextes
- `range_files` : Fichiers importés
- `range_contexts` : Contextes validés
- `ranges` : Ranges avec séquences
- `range_hands` : Mains avec fréquences

**quiz_history.db** 🆕 : Suivi de progression
- `quiz_sessions` : Sessions complétées
- `quiz_answers` : Réponses détaillées

---

## 🎯 Niveaux d'agressivité

| Niveau | Drill-down | Séquences longues | All-in | Usage |
|--------|-----------|-------------------|--------|-------|
| 🟢 **LOW** | 50% | 30% | Rare | Débutants |
| 🟡 **MEDIUM** | 70% | 60% | Modéré | Standard |
| 🔴 **HIGH** | 100% | 100% | Fréquent | Avancés |

**Configuration** : Dans l'interface de setup du quiz

---

## 📊 API Endpoints

### Quiz
- `POST /api/quiz/generate` - Génère un nouveau quiz
- `POST /api/quiz/submit-answer` - Sauvegarde une réponse
- `POST /api/quiz/end-session/:id` - Termine une session

### Progression 🆕
- `GET /api/quiz/progression` - Toutes les sessions + stats globales
- `GET /api/quiz/session/:id` - Détails d'une session
- `GET /api/quiz/user-stats` - Statistiques utilisateur
- `GET /api/quiz/recent-sessions` - Sessions récentes

### Ranges
- `POST /api/import-from-folder` - Import des fichiers JSON
- `GET /api/contexts` - Liste des contextes disponibles

---

## 🐛 Résolution de problèmes

### L'application ne démarre pas
```bash
# Vérifier que Flask est installé
pip list | grep -i flask

# Vérifier le fichier app.py
python app.py
# Devrait afficher : "🚀 Démarrage Flask..."
```

### Aucune donnée dans l'historique
```bash
# Vérifier que la base existe
ls -la data/quiz_history.db

# Faire au moins un quiz complet
# Les données apparaîtront ensuite
```

### Erreur d'import des ranges
```bash
# Vérifier le format JSON
# Les fichiers doivent venir de l'éditeur web officiel
# https://site2wouf.fr/poker-range-editor.php
```

### Port 5000 déjà utilisé
```python
# Dans app.py, changer le port :
app.run(debug=True, host='0.0.0.0', port=5001)  # ← 5001
```

---

## 📝 Changelog

### v4.5.0 - Beta Release (04/11/2025)
🎉 **Nouvelle version majeure avec système de progression complet**

#### ✨ Nouvelles fonctionnalités
- 📊 **Système de progression complet**
  - Historique de toutes les sessions
  - Graphiques d'évolution
  - Stats par contexte
  - Mini-graphique sur page de résultats
  
- 📈 **Page d'historique dédiée**
  - Vue d'ensemble avec 6 indicateurs clés
  - Graphique de progression complet
  - Filtres (date, score, contexte)
  - Liste complète des sessions
  - Calcul du streak (jours consécutifs)
  
- 💾 **Sauvegarde automatique**
  - Base de données séparée pour l'historique
  - Chaque réponse sauvegardée en temps réel
  - Export CSV disponible

#### 🔧 Améliorations techniques
- API `/api/quiz/progression` pour récupérer les données
- `QuizHistoryManager` pour gérer l'historique
- Architecture séparée pour performance optimale

#### 🎨 Interface
- Section "Votre progression" sur page de résultats
- Design moderne avec graphiques en Canvas natif
- Responsive mobile complet

### v4.4.2 (31/10/2025)
- 🐛 Correction du skip all-in en mode MEDIUM
- 🐛 Arrêt automatique après all-in
- 🐛 Support complet du niveau 3

### v4.4.0 (30/10/2025)
- ✨ Système d'agressivité avec 3 niveaux
- ✨ Widget de sélection dans l'interface
- ⚙️ Configuration centralisée

### v4.3.7 (28/10/2025)
- ✨ Tracking intelligent par contexte
- 🐛 Évite les répétitions dans le même contexte

### v4.3.6 (27/10/2025)
- ✨ Position Vilain cohérente
- ✨ Historique narratif fluide

---

## 🤝 Contribution

Les contributions sont bienvenues ! 

**Guidelines** :
- Suivre PEP 8
- Ajouter des docstrings
- Tester avant de soumettre
- Mettre à jour le CHANGELOG

---

## 🔗 Liens utiles

- [Éditeur de ranges web](https://site2wouf.fr/poker-range-editor.php)
- [Repository GitHub](https://github.com/w0uf/poker-training)
- [Documentation Flask](https://flask.palletsprojects.com/)

---

## 📄 Licence

Projet sous licence libre.

---

## 💡 Notes pour la Beta

### Ce qui fonctionne parfaitement ✅
- Import et validation des ranges
- Quiz simple et drill-down
- Paramètres d'agressivité
- Sauvegarde automatique des sessions
- Système de progression complet
- Graphiques et analytics
- Export des résultats

### Retours attendus 🎯
- Pertinence des recommandations
- Clarté de l'interface historique
- Performance avec 50+ sessions
- Bugs éventuels sur différents navigateurs

### Comment signaler un bug
1. Ouvrir une issue sur GitHub
2. Préciser la version (4.5.0)
3. Décrire les étapes pour reproduire
4. Joindre une capture d'écran si possible

---

**Dernière mise à jour** : 04/11/2025  
**Version actuelle** : 4.5.0 Beta

Créé avec ❤️ pour la communauté poker

---

## 🎯 Prochaines étapes (Post-Beta)

- Mode révision espacée (spaced repetition)
- Contextes 3-way et 4-way
- Drill-down post-flop
- Coach virtuel avec IA
- Application mobile

*À discuter selon les retours de la beta !*
