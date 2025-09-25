Poker Training

Interface web locale pour travailler et s’entraîner sur des ranges de poker.

Statut : Import et Dashboard OK · Standardisation OK (CLI) · Enrichissement en cours · Génération de questions à faire
Dernière mise à jour : 25/09/2025

Vue d’ensemble

Interface Flask : dashboard, import, statistiques en temps réel

Pipeline de données : JSON → Import → Standardisation → Enrichissement → Questions

Base SQLite : stockage normalisé des ranges et métadonnées

Compatibilité : fichiers JSON générés via Poker Range Editor

Architecture du projet

poker-training/
├── data/
│ ├── poker_trainer.db # Base SQLite
│ └── ranges/ # Fichiers JSON
├── web/
│ ├── app.py # Serveur Flask
│ └── templates/ # HTML (dashboard, import, enrich, base)
├── poker_training.py # Import et mise à jour depuis data/ranges
├── enrich_ranges.py # Enrichissement métadonnées (CLI)
├── range_name_standardizer.py # Standardisation noms/contexte/actions
├── questions.py # Génération de questions (WIP)
├── valid_system.py # Validation système
├── debug-validation.py # Outils de debug
└── test.py # Tests ponctuels

Base de données

range_files : fichiers importés (hash, timestamps)

range_contexts : contextes de jeu (ex. "Défense BB vs UTG")

ranges : sous-ranges (ex. "Call", "3Bet")

range_hands : mains et fréquences (ex. "AKo": 1.0)

Index optimisés pour recherche rapide (idx_range_hands_range_id, idx_range_hands_hand).

Standardisation

Script : range_name_standardizer.py

Normalise les noms de contextes et actions

Sécurisé : écriture atomique, backup horodaté, rollback en cas d’erreur

Actions détectées : call, fold, 3bet_value, 3bet_bluff, 4bet_value, 4bet_bluff, squeeze_value, squeeze_bluff, open_raise, defense, check, shove, limp

Positions :

5-max : UTG, CO, BTN, SB, BB

6-max : UTG, MP, CO, BTN, SB, BB

9-max : UTG, UTG1, MP, MP1, LJ, HJ, CO, BTN, SB, BB

HU : BTN, BB

Enrichissement

Script : enrich_ranges.py

Ajoute des métadonnées (positions, actions, score de confiance)

Corrige les problèmes d’encodage UTF-8 (Ã©, ðŸ…, etc.) via clean_encoding_issues()

Formats de données

Exemple JSON d’entrée (éditeur externe) :

{
"data": {
"ranges": {
"1": { "name": "Call", "color": "#4CAF50" },
"2": { "name": "3Bet", "color": "#F44336" },
"3": { "name": "Fold", "color": "#9E9E9E" }
},
"values": {
"AKo": [1, 2],
"AQs": [1],
"72o": [3]
}
}
}

Analyse automatique de contexte :

"5 Max-défense BB vs UTG" → hero=BB, vs=UTG, action=defense

"CO Open 100bb" → hero=CO, action=open

"3Bet vs BTN steal" → action=3bet, vs=BTN

Installation

python3 -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt

requirements.txt
Flask

sqlite3 et pathlib sont inclus dans la bibliothèque standard Python.

Démarrage rapide
1) Import initial des ranges

python poker_training.py

2) Lancer l’interface web

cd web
python app.py

→ http://localhost:5000
Workflow recommandé

Créer les ranges dans l’éditeur → exporter en JSON (5_Max-defense_BB_vs_UTG.json)

Déposer les fichiers dans data/ranges/

Importer : python poker_training.py (détection automatique des changements)

Standardiser (optionnel) : python range_name_standardizer.py

Enrichir (optionnel) : python enrich_ranges.py

S’entraîner : interface web (questions en cours de développement)

État du projet

✅ Interface Flask (dashboard, import, stats)

✅ Import JSON (parser modulaire + détection changements)

✅ Standardisation (CLI stable)

🔄 Enrichissement (CLI OK, intégration web en cours)

🚧 Génération de questions (pipeline défini, pas encore implémenté)

Prochaines étapes

Intégrer enrichissement/standardisation dans Flask

Nettoyer l’encodage UTF-8 sur tout le projet

Développer le système de questions et l’interface d’entraînement
