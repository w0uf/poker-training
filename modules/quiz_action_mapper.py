#!/usr/bin/env python3
"""Module de mapping des ranges vers les actions de quiz"""


class QuizActionMapper:
    """Détecte et mappe les actions de quiz depuis les noms de ranges"""

    RAISE = 'raise'
    CALL = 'call'
    FOLD = 'fold'
    CHECK = 'check'

    KEYWORDS = {
        RAISE: ['raise', 'open', '3bet', '4bet', 'squeeze', '3-bet', '4-bet',
                'relance', 'surrelance', 'iso'],
        CALL: ['call', 'limp', 'complete', 'defense', 'défense'],
        FOLD: ['fold', 'couche', 'passe'],
        CHECK: ['check', 'parole']
    }

    @classmethod
    def detect(cls, text: str):
        """Détecte l'action quiz depuis un texte"""
        if not text:
            return None

        text_lower = text.lower()

        for action, keywords in cls.KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return action

        return None