# 🃏 Poker Training – Importeur de Ranges

Ce projet est un **importeur et gestionnaire de ranges de poker** en Python.  
Il scanne un dossier de fichiers JSON exportés depuis [poker-range-editor](https://site2wouf.fr/poker-range-editor.php) , les parse et les stocke dans une base **SQLite**.  
Chaque contexte de range est enrichi avec des métadonnées (positions détectées, actions, confiance).



## 🎯 But du script
`poker-training.py` est un **importeur modulaire** de ranges de poker.  
Il parcourt un dossier (`data/ranges/`), lit des **fichiers JSON** exportés depuis ton éditeur de ranges, et **stocke** les données dans une **base SQLite** (`data/poker_trainer.db`).  
Le script **détecte** automatiquement un **contexte** (positions, action) et calcule un **score de confiance**.

---

## 🧱 Ce que fait exactement le script
- Crée les répertoires `data/` et `data/ranges/` s’ils n’existent pas.
- Scanne `data/ranges/` pour trouver tous les `*.json`.
- Pour chaque JSON :
  - calcule un **hash MD5** pour savoir si le fichier a changé (sinon, l’ignore),
  - **parse** la structure (via `JSONRangeParser`),
  - **insère** en base : le fichier, le **contexte**, les **ranges** et les **mains**,
  - affiche un **résumé** (nb de ranges, nb de mains, confiance, etc.).
- En fin d’exécution, affiche un **résumé global** de la base (tous les contextes).

---

## 🧩 Architecture interne (dans `poker-training.py`)
- **Models (dataclasses)**  
  - `RangeFile` : fichier importé (nom, hash, dates, statut).  
  - `RangeContext` : contexte global (ex. « Défense BB vs Open CO ») + métadonnées détectées.  
  - `Range` : une range (ex. « Call », « 3Bet Value »).  
  - `RangeHand` : une main + fréquence (actuellement 1.0 par défaut).
- **Base de données (SQLite)**  
  - `SQLiteRangeRepository` crée les tables et expose des méthodes `save_...` et `get_all_contexts()`.
  - Tables : `range_files`, `range_contexts`, `ranges`, `range_hands` (+ index).
- **Parsers**  
  - `RangeParser` (interface).  
  - `JSONRangeParser` : attend un JSON structuré avec `data.ranges` (métadonnées par range) et `data.values` (mapping *main → ids de ranges*).  
    - `_extract_context_name()` : essaie de déduire un nom de contexte (depuis le 1er range ou le nom de fichier).  
    - `_analyze_context()` : détecte positions/actions par regex (`UTG`, `MP`, `CO`, `BTN/BU`, `SB`, `BB`, `open`, `call`, `3bet`, `4bet`, `fold`, `défense`) et calcule un **score de confiance**.  
- **Importer**  
  - `RangeImporter` orchestre l’ensemble : scan, parse, insert, mapping des mains vers la bonne range, résumé.  
- **Script principal**  
  - Définit `ranges_dir = "data/ranges"` et `db_path = "data/poker_trainer.db"`.  
  - Appelle `RangeImporter.import_all_ranges()` puis `show_database_summary()`.

---

## 📦 Format JSON attendu (exemple minimal)
```json
{
  "data": {
    "ranges": {
      "1": { "name": "Call", "color": "#0033ff" },
      "2": { "name": "3Bet Value", "color": "#ff0000" },
      "3": { "name": "3Bet Bluff", "color": "#ff6a00" }
    },
    "values": {
      "AQo": [3],
      "ATs": [2],
      "JJ":  [2],
      "A5s": [3],
      "KJs": [1]
    }
  }
}
```
- `data.ranges` : dictionnaire **clé → objet range** ; la *clé* (ex. `"1"`) sert de **range_key**.  
- `data.values` : **main → [liste des clés de ranges]**. Exemple : `"AQo": [3]` signifie que *AQo* appartient à la range `"3"` (ici « 3Bet Bluff »).

---

## ⚙️ Installation & exécution
```bash
git clone https://github.com/w0uf/poker-training.git
cd poker-training

# optionnel : environnement virtuel
python3 -m venv venv
source venv/bin/activate

# lancer
python poker-training.py
```
- Place tes fichiers JSON dans `data/ranges/` avant d’exécuter le script.

---

## 🗄️ Base SQLite
- Fichier : `data/poker_trainer.db` (créé automatiquement).  
- Résumé des tables :
  - **range_files** : nom du fichier, hash MD5, dates, statut.  
  - **range_contexts** : un contexte par fichier (JSON d’origine + métadonnées parses + confiance).  
  - **ranges** : chaque range (nom, couleur, `range_key`).  
  - **range_hands** : chaque main associée à une range, avec `frequency` (1.0 par défaut).

---

enrich_ranges.py — Enrichisseur interactif (V4)

But : compléter les métadonnées des contextes importés en base (SQLite) et générer des noms d’affichage (display_name) prêts pour la création de questions d’entraînement.

Prérequis

Avoir déjà importé au moins un fichier JSON avec poker-training.py (ce qui crée data/poker_trainer.db).

Python ≥ 3.10.

Ce que fait le script

Liste les contextes trouvés dans range_contexts.

Pose des questions globales (format de jeu, variante, format de table).

Pour chaque contexte :

détection avancée automatique (positions, action, stack, etc.),

questions ciblées pour compléter/corriger,

propose plusieurs display_name (long et court),

enregistre le tout dans enriched_metadata avec un marqueur de version v4 et question_friendly (booléen).

Fournit des menus pour :

enrichir, 2) voir un résumé global V4, 3) lister les display_name créés, 4) debug des métadonnées V4.

Lancer

python enrich_ranges.py


Si la base n’existe pas encore, lance d’abord :

python poker-training.py


Menu

Enrichissement interactif – guide pas à pas (questions globales puis par contexte).

Résumé des enrichissements – totaux, part des contextes V4, prêts pour questions, confiance moyenne.

Liste des noms d’affichage – affiche display_name et display_name_short pour tous les contextes V4.

Debug métadonnées – imprime le JSON enriched_metadata V4 (utile pour du troubleshooting).

Quitter.

Champs stockés (enriched_metadata, V4)

game_format, variant, table_format

hero_position, vs_position, primary_action, stack_depth, sizing

description, confidence, enriched_by_user, enrichment_date

Nouveaux V4 : display_name, display_name_short, question_friendly, version: "v4"

Bon à savoir

Les booléens (ex. question_friendly) sont normalisés à la lecture ('true', true, 1 → True).

Le résumé et les listes V4 utilisent json_extract (extension JSON de SQLite, fournie avec Python standard).

Le score confidence passe à 1.0 après enrichissement manuel.

Workflow recommandé

python poker-training.py → import des JSON (création/MAJ DB)

python enrich_ranges.py → enrichissement V4 + display_name

(optionnel) exploiter display_name pour générer/nommer des questions dans un module de training.
