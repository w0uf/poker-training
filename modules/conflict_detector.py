#!/usr/bin/env python3
"""
Détecteur de conflits entre contextes pour le système de quiz.

Un conflit existe quand plusieurs contextes génèrent des questions
identiques (mêmes métadonnées affichées) mais avec des réponses différentes.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict

# Imports locaux
from poker_constants import normalize_action
from drill_down_generator import RANGE_STRUCTURE


class ConflictDetector:
    """Détecte les conflits de réponses entre contextes"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "poker_trainer.db"
        self.db_path = Path(db_path)

    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def detect_conflicts(self, context_ids: List[int]) -> Dict:
        """
        Détecte tous les conflits entre les contextes sélectionnés.

        Args:
            context_ids: Liste des IDs de contextes sélectionnés

        Returns:
            Dict avec les conflits groupés par métadonnées identiques
            {
                'metadata_key': {
                    'contexts': [ctx1, ctx2],
                    'conflicts_by_level': {
                        0: {'AKo': {1: 'RAISE', 2: 'CALL'}},
                        1: {'AKs': {1: 'RAISE', 2: 'CALL'}}
                    },
                    'total_conflicts': 5
                }
            }
        """
        if len(context_ids) < 2:
            return {}  # Pas de conflit possible

        conn = self.get_connection()
        try:
            # 1. Charger tous les contextes
            contexts = self._load_contexts(conn, context_ids)
            if len(contexts) < 2:
                return {}

            # 2. Grouper par métadonnées visibles
            groups = self._group_by_displayed_metadata(contexts)

            # 3. Détecter les conflits dans chaque groupe
            all_conflicts = {}
            for metadata_key, group_contexts in groups.items():
                if len(group_contexts) < 2:
                    continue  # Pas de conflit possible

                # Charger les ranges pour ce groupe
                contexts_with_ranges = self._load_ranges_for_contexts(conn, group_contexts)

                # Détecter les conflits
                group_conflicts = self._detect_conflicts_in_group(contexts_with_ranges)

                if group_conflicts:
                    all_conflicts[metadata_key] = group_conflicts

            return all_conflicts

        finally:
            conn.close()

    def _load_contexts(self, conn, context_ids: List[int]) -> List[Dict]:
        """Charge les contextes depuis la BDD"""
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(context_ids))
        cursor.execute(f"""
            SELECT 
                id, display_name, table_format, hero_position, 
                primary_action, stack_depth, action_sequence
            FROM range_contexts 
            WHERE id IN ({placeholders}) AND quiz_ready = 1
        """, context_ids)

        contexts = []
        for row in cursor.fetchall():
            ctx = dict(row)
            # Parser action_sequence si présent
            if ctx.get('action_sequence'):
                try:
                    ctx['action_sequence'] = json.loads(ctx['action_sequence'])
                except:
                    ctx['action_sequence'] = None
            contexts.append(ctx)

        return contexts

    def _load_ranges_for_contexts(self, conn, contexts: List[Dict]) -> List[Dict]:
        """Charge les ranges pour chaque contexte"""
        cursor = conn.cursor()

        for ctx in contexts:
            cursor.execute("""
                SELECT 
                    r.id, r.range_key, r.name, r.label_canon,
                    GROUP_CONCAT(DISTINCT rh.hand) as hands
                FROM ranges r
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                WHERE r.context_id = ?
                GROUP BY r.id
                ORDER BY r.range_key
            """, (ctx['id'],))

            ranges = []
            for row in cursor.fetchall():
                hands_str = row[4]
                if hands_str:
                    ranges.append({
                        'id': row[0],
                        'range_key': row[1],
                        'name': row[2],
                        'label_canon': row[3],
                        'hands': set(hands_str.split(','))
                    })

            ctx['ranges'] = ranges

        return contexts

    def _group_by_displayed_metadata(self, contexts: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Groupe les contextes par métadonnées visibles identiques.

        Returns:
            Dict {metadata_key: [ctx1, ctx2, ...]}
        """
        groups = defaultdict(list)

        for ctx in contexts:
            key = self._get_displayed_metadata_key(ctx)
            groups[key].append(ctx)

        # Retourner seulement les groupes avec 2+ contextes
        return {k: v for k, v in groups.items() if len(v) >= 2}

    def _get_displayed_metadata_key(self, context: Dict) -> str:
        """
        Génère une clé unique basée sur les métadonnées visibles dans la question.

        Returns:
            String représentant les métadonnées (ex: "6max|BTN|100bb|defense|CO")
        """
        action_seq_key = self._extract_action_sequence_key(context)

        # Convertir en string pour utiliser comme clé de dict
        parts = [
            context['table_format'],
            context['hero_position'],
            context['stack_depth'],
            context['primary_action'],
            str(action_seq_key) if action_seq_key else 'GENERIC'
        ]

        return '|'.join(parts)

    def _extract_action_sequence_key(self, context: Dict) -> Optional[Tuple]:
        """
        Extrait la partie de action_sequence qui influence le texte visible.

        Returns:
            None si range générique, sinon un tuple avec les détails
        """
        if not context.get('action_sequence'):
            return None  # Range générique

        seq = context['action_sequence']
        primary = context['primary_action']

        if primary == 'defense':
            opener = seq.get('opener')
            return ('opener', opener) if opener else None

        elif primary == 'squeeze':
            opener = seq.get('opener')
            callers = seq.get('callers', [])
            if opener or callers:
                return ('squeeze', opener, tuple(sorted(callers)))
            return None

        elif primary == 'vs_limpers':
            limpers = seq.get('limpers', [])
            return ('limpers', tuple(sorted(limpers))) if limpers else None

        return None

    def _detect_conflicts_in_group(self, contexts: List[Dict]) -> Optional[Dict]:
        """
        Détecte les conflits de réponses dans un groupe de contextes.

        Args:
            contexts: Liste de contextes avec ranges chargées

        Returns:
            Dict avec les conflits ou None si aucun conflit
        """
        conflicts_by_level = {}

        # Explorer toutes les séquences d'actions possibles
        all_sequences = self._get_all_sequences_in_group(contexts)

        for sequence in all_sequences:
            level = len(sequence) - 1

            # Trouver toutes les mains à ce niveau
            all_hands = self._get_all_hands_at_sequence(contexts, sequence)

            for hand in all_hands:
                # Récupérer l'action dans chaque contexte
                actions = {}
                for ctx in contexts:
                    action = self._get_action_at_sequence(ctx, hand, sequence)
                    if action is not None:  # Séquence valide pour cette main
                        actions[ctx['id']] = action

                # Conflit si actions différentes
                unique_actions = set(actions.values())
                if len(unique_actions) > 1:
                    if level not in conflicts_by_level:
                        conflicts_by_level[level] = {}
                    conflicts_by_level[level][hand] = actions

        if not conflicts_by_level:
            return None

        # Compter le total de conflits
        total = sum(len(hands) for hands in conflicts_by_level.values())

        return {
            'contexts': [{'id': ctx['id'], 'name': ctx['display_name']} for ctx in contexts],
            'conflicts_by_level': conflicts_by_level,
            'total_conflicts': total
        }

    def _get_all_sequences_in_group(self, contexts: List[Dict]) -> Set[Tuple]:
        """
        Retourne toutes les séquences d'actions possibles dans ce groupe.

        Returns:
            Set de tuples représentant les séquences
            Ex: {(('initial', 'RAISE'),), (('initial', 'RAISE'), ('3bet', 'RAISE'))}
        """
        sequences = set()

        for ctx in contexts:
            ranges = ctx.get('ranges', [])

            for r in ranges:
                label = r['label_canon']
                if label in RANGE_STRUCTURE:
                    structure = RANGE_STRUCTURE[label]
                    actions = structure.get('actions', [])

                    # Construire les séquences progressives
                    for i in range(len(actions)):
                        sequence = tuple(actions[:i+1])
                        sequences.add(sequence)

        # Toujours inclure le niveau 0
        sequences.add((('initial', 'RAISE'),))

        return sequences

    def _get_all_hands_at_sequence(self, contexts: List[Dict], sequence: Tuple) -> Set[str]:
        """
        Retourne toutes les mains présentes dans au moins un contexte à cette séquence.

        Args:
            contexts: Liste de contextes
            sequence: Séquence d'actions à vérifier

        Returns:
            Set de mains (ex: {'AKs', 'AKo', 'QQ'})
        """
        all_hands = set()

        for ctx in contexts:
            ranges = ctx.get('ranges', [])

            for r in ranges:
                label = r['label_canon']

                # Vérifier si ce range correspond à cette séquence
                if self._range_matches_sequence(label, sequence):
                    all_hands.update(r['hands'])

        return all_hands

    def _range_matches_sequence(self, range_label: str, sequence: Tuple) -> bool:
        """
        Vérifie si un range correspond à une séquence d'actions.

        Args:
            range_label: Label du range (ex: 'OPEN', 'R4_VALUE')
            sequence: Séquence d'actions (ex: (('initial', 'RAISE'), ('3bet', 'RAISE')))

        Returns:
            True si le range peut répondre à cette séquence
        """
        if range_label not in RANGE_STRUCTURE:
            # Range simple (OPEN, CALL, FOLD)
            normalized = normalize_action(range_label)
            if len(sequence) == 1 and sequence[0] == ('initial', 'RAISE'):
                return normalized == 'RAISE' or range_label == 'OPEN'
            return False

        structure = RANGE_STRUCTURE[range_label]
        range_actions = structure.get('actions', [])

        # Vérifier si la séquence correspond aux actions du range
        # Ex: R4_VALUE a [('initial', 'RAISE'), ('3bet', 'RAISE'), ('all-in', 'CALL')]
        # Séquence (('initial', 'RAISE'), ('3bet', 'RAISE')) → Match niveau 2
        if len(sequence) <= len(range_actions):
            return tuple(range_actions[:len(sequence)]) == sequence

        return False

    def _get_action_at_sequence(self, context: Dict, hand: str, sequence: Tuple) -> Optional[str]:
        """
        Retourne l'action qu'une main doit prendre à une séquence donnée.

        Args:
            context: Contexte avec ranges
            hand: Main à vérifier
            sequence: Séquence d'actions (ex: (('initial', 'RAISE'), ('3bet', 'RAISE')))

        Returns:
            Action ('RAISE', 'CALL', 'FOLD') ou None si séquence impossible
        """
        ranges = context.get('ranges', [])
        level = len(sequence) - 1

        # Niveau 0 : action initiale
        if level == 0:
            return self._get_level_0_action(hand, ranges)

        # Niveau 1+ : drill-down
        for r in ranges:
            label = r['label_canon']

            if label not in RANGE_STRUCTURE:
                continue

            structure = RANGE_STRUCTURE[label]
            range_actions = structure.get('actions', [])

            # Vérifier si ce range correspond à la séquence
            if len(sequence) <= len(range_actions):
                if tuple(range_actions[:len(sequence)]) == sequence:
                    # Cette main est-elle dans ce range ?
                    if hand in r['hands']:
                        # L'action est le dernier élément de la séquence
                        return sequence[-1][1]  # RAISE, CALL, ou FOLD

        # Si la main n'est dans aucun range pour cette séquence → FOLD implicite
        return 'FOLD'

    def _get_level_0_action(self, hand: str, ranges: List[Dict]) -> str:
        """
        Retourne l'action au niveau 0 (action initiale) pour une main.

        Args:
            hand: Main à vérifier
            ranges: Liste des ranges du contexte

        Returns:
            Action normalisée ('RAISE', 'CALL', 'FOLD')
        """
        # Chercher dans les ranges avec priorité
        for r in ranges:
            if hand in r['hands']:
                label = r['label_canon']
                normalized = normalize_action(label)

                # Si c'est un range simple, retourner l'action
                if normalized and normalized != 'DEFENSE':
                    return normalized

                # Si c'est DEFENSE, chercher dans les sous-ranges
                if normalized == 'DEFENSE':
                    subrange_action = self._find_subrange_action(hand, ranges)
                    if subrange_action:
                        # Conversion 3BET → RAISE pour l'UI
                        return 'RAISE' if subrange_action == '3BET' else subrange_action

        # Main pas dans les ranges → FOLD implicite
        return 'FOLD'

    def _find_subrange_action(self, hand: str, ranges: List[Dict]) -> Optional[str]:
        """
        Trouve l'action dans les sous-ranges (pour DEFENSE).

        Args:
            hand: Main à chercher
            ranges: Liste des ranges

        Returns:
            Action normalisée ou None
        """
        # Chercher dans les sous-ranges (range_key != '1')
        for r in ranges:
            if r['range_key'] != '1' and hand in r['hands']:
                label = r.get('label_canon')
                if label and label != 'None' and label != '':
                    normalized = normalize_action(label)
                    if normalized:
                        return normalized

        return None


# Fonction utilitaire pour app.py
def detect_context_conflicts(context_ids: List[int], db_path: str = None) -> Dict:
    """
    Fonction wrapper pour détecter les conflits.

    Args:
        context_ids: Liste des IDs de contextes sélectionnés
        db_path: Chemin vers la BDD (optionnel)

    Returns:
        Dict avec les conflits détectés
    """
    detector = ConflictDetector(db_path)
    return detector.detect_conflicts(context_ids)