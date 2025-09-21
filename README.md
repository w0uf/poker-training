# 🃏 Poker Training – Importeur de Ranges

Ce projet est un **importeur et gestionnaire de ranges de poker** en Python.  
Il scanne un dossier de fichiers JSON exportés depuis ton éditeur de ranges, les parse et les stocke dans une base **SQLite**.  
Chaque contexte de range est enrichi avec des métadonnées (positions détectées, actions, confiance).

---

## ✨ Fonctionnalités
- Scan automatique du dossier `data/ranges/`
- Import des fichiers JSON de ranges
- Détection des contextes (positions, actions) avec un score de confiance
- Stockage dans une base **SQLite** (`data/poker_trainer.db`)
- Résumé en console : nb de ranges, nb de mains, contexte détecté
- Extensible : possibilité d’ajouter d’autres parsers (GTO+, PioSolver, …)

---

## 📂 Structure du projet et modules

### `poker-training.py`
Script principal.  
- Scanne `data/ranges/` pour trouver les fichiers JSON.  
- Utilise la classe `RangeImporter` pour parser et insérer en base SQLite.  
- Affiche un résumé détaillé en console (contextes, ranges, mains, score confiance).  

### `range_name_standardizer.py`
- Normalise la notation des ranges (par ex. `ATs+` → `ATs, A9s, …`).  
- Garantit une compatibilité totale avec l’export de l’éditeur de ranges.  

### `enrich_ranges.py`
- Déploie les notations compressées en liste complète de mains.  
- Tag chaque main avec son bucket (Call, 3Bet Value, Bluff, etc.).  

### `valid_system.py`
- Vérifie la cohérence d’un système de ranges complet.  
- Détecte recouvrements (même main dans plusieurs buckets), incohérences, pourcentages anormaux.  

### `questions.py`
- Génère des questions d’entraînement (ex: “BB vs CO open : AQo ?”).  
- Supporte QCM et saisie libre.  
- Peut pondérer les questions selon les erreurs passées.  

### `debug-validation.py`
- Script de test rapide.  
- Vérifie qu’un pack JSON dans `data/ranges/` peut être importé correctement et sans incohérence.  

### `data/`
- Contient les fichiers JSON de ranges à importer.  
- Contient également la base SQLite `poker_trainer.db` après exécution.

---

## ⚙️ Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/w0uf/poker-training.git
cd poker-training
```

### 2. Créer l’environnement
Python 3.10+ recommandé.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # si fichier ajouté plus tard
```

### 3. Préparer les données
- Placez vos fichiers JSON de ranges dans `data/ranges/`.

---

## ▶️ Utilisation

Exécuter le script principal :
```bash
python poker-training.py
```

Exemple de sortie :
```
🃏 IMPORTEUR DE RANGES POKER
==================================================
🔍 Scan du dossier: data/ranges
📁 3 fichiers JSON trouvés
📥 Import de BB_vs_CO.json...
✅ BB_vs_CO.json importé:
   📋 Contexte: Défense BB vs Open CO
   🎯 3 ranges
   🃏 280 mains
   📊 Confiance: 85.0%
```

---

## 🗄️ Base de données

- **Fichier** : `data/poker_trainer.db`
- **Tables** :
  - `range_files` → suivi des fichiers importés
  - `range_contexts` → contexte global d’un fichier
  - `ranges` → chaque range (Call, 3Bet Value, …)
  - `range_hands` → chaque main et fréquence

---

## 🚀 Roadmap

- Ajouter CLI avec `argparse` ou `typer` (choix du dossier, DB…)
- Gérer les fréquences partielles (< 1.0)
- Support d’autres formats de ranges (PioSolver, GTO+)
- Export vers CSV/JSON pour analyse externe
- Interface web (Flask/Streamlit) pour visualiser les ranges importées

---

## 📜 Licence
TBD (MIT recommandé).
