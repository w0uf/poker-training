# 🎲 Guide : Modifier les Probabilités de Drill Down

## 📍 Où se trouve le paramètre ?

**Fichier :** `modules/drill_down_generator.py`  
**Ligne :** 291

## 🎯 Valeurs possibles

### 1. Mode PRODUCTION (50% par étape) - RECOMMANDÉ
```python
if random.random() < 0.5:  # 50% de chance de continuer
```

**Distribution sur 100 questions :**
- ~50 avec 1 étape
- ~25 avec 2 étapes
- ~12-13 avec 3 étapes

**Réaliste pour le poker !** ✅

### 2. Mode TEST (100% - toujours continuer)
```python
if random.random() < 1.0:  # 100% de chance de continuer
```

**Distribution sur 100 questions :**
- 0 avec 1 étape
- 0 avec 2 étapes
- ~100 avec 3 étapes (maximum)

**Utile pour tester que toutes les étapes fonctionnent !** 🧪

### 3. Mode RARE (25% par étape)
```python
if random.random() < 0.25:  # 25% de chance de continuer
```

**Distribution sur 100 questions :**
- ~75 avec 1 étape
- ~18-19 avec 2 étapes
- ~6-7 avec 3 étapes

**Encore plus réaliste (3bet moins fréquents) !** 🎯

## 🚀 Installation

### Pour tester avec 100% (toutes les étapes)

```bash
cd /home/wouf/pCloudDrive/PycharmProjects/poker-training

# Utiliser la version TEST
cp drill_down_generator_TEST_100.py modules/drill_down_generator.py

# Supprimer cache
rm -rf modules/__pycache__

# Redémarrer Flask
```

### Pour revenir à 50% (normal)

Éditez `modules/drill_down_generator.py` ligne 291 :

```python
# Changer de :
if random.random() < 1.0:  # TEST

# À :
if random.random() < 0.5:  # PRODUCTION
```

Puis :
```bash
rm -rf modules/__pycache__
# Redémarrer Flask
```

## 📊 Logs attendus selon le mode

### Mode 50% (normal)
```
[DRILL] Séquence complète: 3 étapes → on en fait: 1  (50%)
[DRILL] Séquence complète: 3 étapes → on en fait: 2  (25%)
[DRILL] Séquence complète: 3 étapes → on en fait: 3  (12.5%)
```

### Mode 100% (test)
```
[DRILL] Séquence complète: 3 étapes → on en fait: 3  (100% !)
[DRILL] Séquence complète: 2 étapes → on en fait: 2  (100% !)
[DRILL] Séquence complète: 3 étapes → on en fait: 3  (100% !)
```

## 💡 Recommandations

### Pour TESTER les drill down complets :
✅ Utiliser **100%** temporairement

### Pour PRODUCTION (entraînement réel) :
✅ Utiliser **50%** (ou même 25% pour plus de réalisme)

### Pour FOLD implicites :
⚠️ **Toujours 2 étapes** (forcé automatiquement, pas de changement nécessaire)

## 🎯 Note importante

Les **FOLD implicites** (main dans range principale mais pas dans sous-ranges) sont **TOUJOURS** affichés en 2 étapes minimum, **indépendamment** de ce paramètre.

Exemple : ATo dans `open_utg` mais pas dans `call/4bet` :
- Étape 1 : "Vous avez ATo" → RAISE
- Étape 2 : "CO vous 3bet" → FOLD (forcé à 100%)

## 🧪 Test rapide

Après avoir mis à 100%, générez 10 questions et vérifiez les logs :

```bash
# Tous les drill down devraient afficher "→ on en fait: 3" (ou 2 pour FOLD implicites)
```

Si vous voyez toujours "→ on en fait: 1", vérifiez :
1. Le fichier a bien été modifié
2. Le cache __pycache__ a été supprimé
3. Flask a été redémarré

## ✅ Fichiers disponibles

1. **drill_down_generator_TEST_100.py** : Version 100% pour tests
2. Modifiez manuellement pour 50% ou 25%

Bons tests ! 🚀
