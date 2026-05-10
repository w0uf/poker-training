# Changelog — Poker Training

## [4.6.0] - 2026-05-10

### Interface
- Refonte complète de l'UI : thème dark poker (charbon + or + tapis vert) appliqué à toutes les pages
- Nouveau système CSS partagé (`web/static/poker.css`) — design system cohérent avec variables CSS
- Cartes de quiz redessinées avec couleurs de suites améliorées (♠♥♦♣)
- `quiz.html`, `quiz_setup.html`, `dashboard.html` — redessinés en premier
- `quiz-result.html`, `history.html`, `orphans.html` — thème appliqué
- `import.html`, `enrich.html`, `validate_context.html` — thème appliqué
- `dashboard_simple.html`, `template.html`, `quiz_setup_aggression_widget.html` — thème appliqué

### Corrections
- Validation contexte : la range principale (range_key=1) n'apparaît plus dans le tableau des sous-ranges
- Quiz résultats : positions (héros + adversaire) maintenant affichées dans la section "Erreurs à réviser"
- Quiz résultats : `villain_position` sauvegardé dans `quizResults` pour les questions drill-down

### Workflow
- Fichier `VERSION` centralisé — source unique de vérité pour le numéro de version
- `create_portable_windows.sh` lit `VERSION` automatiquement
- `release.sh` — script de release : tag git + packaging en une commande

---

## [4.5.0] - 2025-11-04

### Nouvelles fonctionnalités
- Système de progression complet avec historique (base SQLite séparée `quiz_history.db`)
- Page historique avec graphiques d'évolution des performances
- Stats détaillées par contexte
- Recommandations personnalisées basées sur les erreurs
- Calcul du streak (jours consécutifs d'entraînement)
- Mini-graphique sur la page de résultats
- Export CSV des résultats de session
- Sessions Flask pour le suivi (`session_id`)

### Quiz
- Questions simples et drill-down multi-étapes
- 3 niveaux d'agressivité de table : LOW / MEDIUM / HIGH
- Feedback immédiat avec explication
- Sauvegarde automatique des réponses en base
- Première version portable standalone pour Windows (START.bat)

---

## [4.4.2] - 2025-10-31

### Corrections
- Skip all-in uniquement activé en mode HIGH
- Arrêt automatique de la séquence après un all-in
- Support complet du niveau 3 drill-down

---

## [4.4.0] - 2025-10-30

### Nouvelles fonctionnalités
- Système d'agressivité de table avec 3 niveaux configurables
- Widget de sélection dans l'interface quiz setup
- Configuration centralisée dans `quiz_generator.py`

---

## [4.3.7] - 2025-10-28

### Corrections
- Tracking des mains utilisées par contexte (évite les répétitions dans un même contexte)
- Fix boucle infinie lors de la génération de quiz sur contexte unique

---

## [4.3.5] - 2025-10-27

### Corrections
- Fix dépassement du nombre de questions demandé (drill-down trop long)
- Force question simple quand il reste moins de 3 places dans le quota

---

## [4.3.0] - 2025-10-25

### Nouvelles fonctionnalités
- Système drill-down multi-étapes (séquences de betting complètes)
- Détection automatique des conflits entre ranges
- Page de validation des contextes importés (`/validate`)
- Gestion des fichiers orphelins (`/orphans`)
- Reconstruction JSON depuis la base de données

---

## [4.0.0] - 2025-10-15

### Nouvelles fonctionnalités
- Première version du quiz interactif
- Import automatique de fichiers JSON de ranges
- Détection et parsing des métadonnées (position, action, format de table)
- Base de données SQLite pour la persistance
- Interface web Flask
