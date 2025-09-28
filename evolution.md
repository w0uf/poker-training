# Spécifications du système de quiz poker

## Context et objectif

Le système génère des quiz de situations poker réalistes basés sur des ranges importées. L'utilisateur doit prendre des décisions binaires ou multiples dans des situations complètes.

## Format de quiz cible

**Structure** : Situation complète + décision à prendre

**Exemple** : 
> "Vous êtes sur une table 6max, position CO. Personne n'a ouvert avant vous. Vous touchez K♥ T♣"
> 
> Actions possibles : **RAISE** | **FOLD**

## Critères d'exploitabilité des contextes

### Métadonnées obligatoires (bloquantes)

- **Format de table** : détermine les positions disponibles
- **Position héros** : situe le joueur dans la situation  
- **Action/Situation** : définit le contexte de décision

### Métadonnées optionnelles

- **Stack depth** : défaut 100bb si non spécifié
- **Limites** : NL10, NL25, etc.
- **Position adversaire** : si action face à quelqu'un
- **Sizing** : 2.5x, 3bb, pot, etc.

### Structure de ranges minimale

- Au moins 1 range avec des mains définies
- Actions cohérentes avec le contexte

## Positions par format de table

| Format | Positions disponibles |
|--------|----------------------|
| 5max   | UTG, CO, BTN, SB, BB |
| 6max   | UTG, MP, CO, BTN, SB, BB |
| 9max   | UTG, UTG+1, MP, MP+1, LJ, HJ, CO, BTN, SB, BB |
| HU     | BTN, BB |

## Actions de quiz

**Actions de base** :
- RAISE (inclut open, 3bet, 4bet)
- CALL 
- FOLD
- CHECK (quand possible)

**Mapping contexte → actions** :
- "Open UTG" → RAISE vs FOLD
- "BB Defense vs CO" → CALL vs FOLD (vs RAISE si 3bet)
- "SB Complete" → CALL vs FOLD vs RAISE

## Workflow de validation

### 1. Import automatique
- Parsing JSON
- Détection automatique des métadonnées depuis le nom de fichier
- Marquage des contextes problématiques

### 2. Interface de validation
Pour les contextes incomplets ou ambigus :

```
Fichier : poker-range-1759051996644.json
Ranges : Range principale, Sous-range 1, Sous-range 2

Métadonnées requises :
Format table* : [5max] [6max] [9max] [HU]     ← Obligatoire
Position* : [UTG] [CO] [BTN] [BB]             ← Adapté au format
Situation* : [Premier à parler] [Face à ouverture] ← Obligatoire

Métadonnées optionnelles :
Stack depth : [20bb] [50bb] [100bb] [200bb+] [Standard]
Vs position : [UTG] [CO] [BTN] [N/A]

[Valider et sauvegarder] [Ignorer ce fichier]
```

### 3. Statuts de contexte

- **quiz_ready** : Toutes métadonnées obligatoires présentes
- **non_exploitable** : JSON valide mais métadonnées insuffisantes  
- **error** : Problème technique (JSON corrompu, etc.)

## Interface dynamique

L'interface doit adapter les choix selon les sélections :
- Positions disponibles selon le format de table
- Actions possibles selon la situation
- Validation cohérente des combinaisons

## Validation technique

```python
def is_quiz_exploitable(metadata, ranges_data):
    required = ['table_format', 'hero_position', 'primary_action']
    has_metadata = all(metadata.get(field) for field in required)
    has_ranges = len([r for r in ranges_data if r.hands]) >= 1
    return has_metadata and has_ranges
```

## Architecture modulaire

- **json_parser** : Extraction des ranges
- **name_standardizer** : Détection automatique des métadonnées
- **metadata_enricher** : Application des valeurs par défaut
- **validation_interface** : Correction manuelle des cas ambigus
- **quiz_generator** : Création des questions depuis les contextes validés

Cette approche permet de traiter automatiquement les cas clairs tout en offrant un contrôle utilisateur pour les cas complexes ou ambigus.
