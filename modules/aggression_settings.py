#!/usr/bin/env python3
"""
Configuration de l'agressivité de la table pour le quiz
🎚️ Contrôle les probabilités de drill-down, profondeur, et actions du vilain
"""

# 🎚️ PARAMÈTRES D'AGRESSIVITÉ DE LA TABLE
# Contrôle le comportement du vilain et la profondeur des séquences

AGGRESSION_SETTINGS = {
    'low': {
        # 🟢 TABLE PASSIVE
        # - Peu de drill-down
        # - Séquences courtes
        # - Peu d'all-in
        # - Peu de 5bet
        'use_drill_down_prob': 0.5,           # 50% de questions drill-down
        'drill_depth_continue_prob': 0.3,     # 30% de continuer à l'étape suivante
        'villain_allin_prob_level2': 0.2,     # 20% all-in (80% 5bet sizing)
        'villain_skip_allin_level1': 0.0,     # 0% all-in direct (jamais de skip)
        'villain_5bet_prob': 0.3,             # 30% de 5bet après notre 4bet
        'description': 'Table passive - Séquences courtes, peu d\'all-in',
        'villain_allin_prob_level3': 0.0
    },
    
    'medium': {
        # 🟡 TABLE STANDARD
        # - Mix équilibré drill-down/simple
        # - Séquences moyennes
        # - All-in modéré
        # - 5bet modéré
        'use_drill_down_prob': 0.7,           # 70% de questions drill-down
        'drill_depth_continue_prob': 0.6,     # 60% de continuer à l'étape suivante
        'villain_allin_prob_level2': 0.5,     # 50% all-in (50% 5bet sizing)
        'villain_skip_allin_level1': 0.0,     # 0% all-in direct (jamais de skip)
        'villain_5bet_prob': 0.5,             # 50% de 5bet après notre 4bet
        'villain_allin_prob_level3': 0.1,
        'description': 'Table standard - Mix équilibré'
    },
    
    'high': {
        # 🔴 TABLE ULTRA-AGRESSIVE
        # - Maximum de drill-down
        # - Séquences longues (3 étapes)
        # - Beaucoup d'all-in
        # - Beaucoup de 5bet
        # - 🆕 Skip possibles (all-in direct)
        'use_drill_down_prob': 1.0,           # 100% de questions drill-down
        'drill_depth_continue_prob': 1.0,     # 100% de continuer (max 3 étapes)
        'villain_allin_prob_level2': 0.8,     # 80% all-in (20% 5bet sizing)
        'villain_skip_allin_level1': 0.15,    # 15% all-in direct (skip 3bet)
        'villain_5bet_prob': 0.7,             # 70% de 5bet après notre 4bet
        'villain_allin_prob_level3': 0.5,
        'description': 'Table ultra-agressive - Séquences longues, beaucoup d\'all-in, skips possibles'
    }
}

def get_aggression_settings(level='medium'):
    """
    Récupère les paramètres d'agressivité pour un niveau donné
    
    Args:
        level: 'low', 'medium', ou 'high'
        
    Returns:
        Dict des paramètres d'agressivité
    """
    return AGGRESSION_SETTINGS.get(level, AGGRESSION_SETTINGS['medium'])

def get_aggression_description(level='medium'):
    """
    Récupère la description d'un niveau d'agressivité
    
    Args:
        level: 'low', 'medium', ou 'high'
        
    Returns:
        Description textuelle
    """
    settings = get_aggression_settings(level)
    return settings.get('description', 'Niveau standard')

# 🎯 DISTRIBUTION ATTENDUE DES QUESTIONS

# LOW (Table passive) :
# - 50% questions simples, 50% drill-down
# - Parmi drill-down : 70% à 1 étape, 21% à 2 étapes, 9% à 3 étapes
# - Résultat : Séquences courtes, prévisibles

# MEDIUM (Table standard) :
# - 30% questions simples, 70% drill-down
# - Parmi drill-down : 40% à 1 étape, 36% à 2 étapes, 24% à 3 étapes
# - Résultat : Mix équilibré

# HIGH (Table ultra-agressive) :
# - 0% questions simples, 100% drill-down
# - Parmi drill-down : Toujours 3 étapes si possible
# - 15% de skip all-in direct (niveau 1)
# - 80% d'all-in au niveau 2
# - Résultat : Pression maximale, situations extrêmes
