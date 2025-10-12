from flask import Flask, render_template, jsonify, request
import subprocess
import os
import sys
import sqlite3
import json
from pathlib import Path
import re
from datetime import datetime
import random
# Ajouter au début de app.py, après les imports

# ============================================
# CONSTANTES POKER
# ============================================

# Liste complète des 169 mains de poker
ALL_POKER_HANDS = [
    # Paires
    'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
    # Suited
    'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
    'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s',
    'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'J4s', 'J3s', 'J2s',
    'T9s', 'T8s', 'T7s', 'T6s', 'T5s', 'T4s', 'T3s', 'T2s',
    '98s', '97s', '96s', '95s', '94s', '93s', '92s',
    '87s', '86s', '85s', '84s', '83s', '82s',
    '76s', '75s', '74s', '73s', '72s',
    '65s', '64s', '63s', '62s',
    '54s', '53s', '52s',
    '43s', '42s',
    '32s',
    # Offsuit
    'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
    'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'K6o', 'K5o', 'K4o', 'K3o', 'K2o',
    'QJo', 'QTo', 'Q9o', 'Q8o', 'Q7o', 'Q6o', 'Q5o', 'Q4o', 'Q3o', 'Q2o',
    'JTo', 'J9o', 'J8o', 'J7o', 'J6o', 'J5o', 'J4o', 'J3o', 'J2o',
    'T9o', 'T8o', 'T7o', 'T6o', 'T5o', 'T4o', 'T3o', 'T2o',
    '98o', '97o', '96o', '95o', '94o', '93o', '92o',
    '87o', '86o', '85o', '84o', '83o', '82o',
    '76o', '75o', '74o', '73o', '72o',
    '65o', '64o', '63o', '62o',
    '54o', '53o', '52o',
    '43o', '42o',
    '32o'
]

# Force relative des mains (100 = meilleure, 1 = pire)
HAND_STRENGTH = {
    # Paires premium (100-90)
    'AA': 100, 'KK': 99, 'QQ': 98, 'JJ': 97, 'TT': 96,
    '99': 91, '88': 87, '77': 83, '66': 79, '55': 75,
    '44': 71, '33': 67, '22': 63,

    # Broadways suited (95-85)
    'AKs': 95, 'AQs': 94, 'AJs': 92, 'ATs': 90, 'KQs': 88,
    'KJs': 86, 'QJs': 84, 'JTs': 82,

    # Broadways offsuit (93-80)
    'AKo': 93, 'AQo': 89, 'AJo': 85, 'ATo': 81,
    'KQo': 80, 'KJo': 78, 'KTo': 76, 'QJo': 74, 'QTo': 72, 'JTo': 70,

    # Suited connectors et Ax suited (80-60)
    'A9s': 80, 'A8s': 78, 'A7s': 76, 'A6s': 74, 'A5s': 73,
    'A4s': 72, 'A3s': 71, 'A2s': 70,
    'T9s': 69, '98s': 68, '87s': 67, '76s': 66, '65s': 65,
    '54s': 64, 'K9s': 63, 'KTs': 77, 'Q9s': 62, 'QTs': 75,
    'J9s': 61,

    # Offsuit semi-connectés (60-40)
    'A9o': 60, 'A8o': 58, 'A7o': 56, 'A6o': 54, 'A5o': 53,
    'A4o': 52, 'A3o': 51, 'A2o': 50,
    'K9o': 49, 'Q9o': 48, 'J9o': 47, 'T9o': 46,
    '98o': 45, '87o': 44, '76o': 43, '65o': 42, '54o': 41,

    # Suited moyen-faibles (55-35)
    'K8s': 55, 'K7s': 53, 'K6s': 51, 'K5s': 49, 'K4s': 47, 'K3s': 45, 'K2s': 43,
    'Q8s': 54, 'Q7s': 52, 'Q6s': 50, 'Q5s': 48, 'Q4s': 46, 'Q3s': 44, 'Q2s': 42,
    'J8s': 53, 'J7s': 51, 'J6s': 49, 'J5s': 47, 'J4s': 45, 'J3s': 43, 'J2s': 41,
    'T8s': 52, 'T7s': 50, 'T6s': 48, 'T5s': 46, 'T4s': 44, 'T3s': 42, 'T2s': 40,
    '97s': 51, '96s': 49, '95s': 47, '94s': 45, '93s': 43, '92s': 41,
    '86s': 50, '85s': 48, '84s': 46, '83s': 44, '82s': 42,
    '75s': 49, '74s': 47, '73s': 45, '72s': 40,
    '64s': 48, '63s': 46, '62s': 44,
    '53s': 47, '52s': 45,
    '43s': 46, '42s': 44,
    '32s': 43,

    # Offsuit faibles (40-1)
    'K8o': 38, 'K7o': 36, 'K6o': 34, 'K5o': 32, 'K4o': 30, 'K3o': 28, 'K2o': 26,
    'Q8o': 37, 'Q7o': 35, 'Q6o': 33, 'Q5o': 31, 'Q4o': 29, 'Q3o': 27, 'Q2o': 25,
    'J8o': 36, 'J7o': 34, 'J6o': 32, 'J5o': 30, 'J4o': 28, 'J3o': 26, 'J2o': 24,
    'T8o': 35, 'T7o': 33, 'T6o': 31, 'T5o': 29, 'T4o': 27, 'T3o': 25, 'T2o': 23,
    '97o': 34, '96o': 32, '95o': 30, '94o': 28, '93o': 26, '92o': 22,
    '86o': 33, '85o': 31, '84o': 29, '83o': 27, '82o': 21,
    '75o': 32, '74o': 30, '73o': 28, '72o': 1,  # Pire main
    '64o': 31, '63o': 29, '62o': 20,
    '54o': 30, '53o': 28, '52o': 19,
    '43o': 29, '42o': 18,
    '32o': 17
}
app = Flask(__name__)

# Ratio de questions avec mains aléatoires vs borderline
QUIZ_RANDOM_RATIO = 0.70              # 70% aléatoire, 30% borderline
BORDERLINE_PROXIMITY_THRESHOLD = 12   # Distance max pour être borderline OUT


def smart_hand_choice(in_range_hands, out_range_hands, is_in_range):
    """
    Choisit une main avec équilibre configurable entre aléatoire et borderline.

    Args:
        in_range_hands: Mains dans la range
        out_range_hands: Mains hors de la range
        is_in_range: True si on veut une main IN, False si OUT

    Returns:
        Une main choisie intelligemment
    """
    target_hands = list(in_range_hands) if is_in_range else list(out_range_hands)

    if not target_hands:
        return None

    # Tirer un dé : aléatoire ou borderline ?
    if random.random() < QUIZ_RANDOM_RATIO:
        # 🎲 Choix purement ALÉATOIRE (70% du temps)
        hand = random.choice(target_hands)
        print(f"[CHOICE] Aléatoire {'IN' if is_in_range else 'OUT'}: {hand}")
        return hand
    else:
        # 🎯 Choix BORDERLINE (30% du temps)
        borderline_in, borderline_out = get_borderline_hands(
            in_range_hands,
            out_range_hands,
            BORDERLINE_PROXIMITY_THRESHOLD
        )

        borderline_hands = borderline_in if is_in_range else borderline_out

        if borderline_hands:
            hand = random.choice(borderline_hands)
            print(f"[CHOICE] Borderline {'IN' if is_in_range else 'OUT'}: {hand}")
            return hand
        else:
            # Fallback : aléatoire si pas de borderline
            hand = random.choice(target_hands)
            print(f"[CHOICE] Fallback aléatoire {'IN' if is_in_range else 'OUT'}: {hand}")
            return hand
def sort_actions(actions):
    """
    Trie les actions dans un ordre logique et constant.
    Ordre : FOLD → CHECK → CALL → RAISE → OPEN → ISO → 3BET → 4BET → ALLIN
    """
    if not actions:
        return []

    action_order = {
        'FOLD': 1,
        'CHECK': 2,
        'CALL': 3,
        'RAISE': 4,
        'OPEN': 5,
        'ISO': 6,
        '3BET': 7,
        '4BET': 8,
        'ALLIN': 9
    }

    return sorted(actions, key=lambda x: action_order.get(x, 999))


def get_borderline_hands(in_range_hands, out_range_hands, proximity_threshold=12):
    """
    Identifie les vrais borderlines :
    - IN : mains aux frontières de la range (trous en dessous/dessus)
    - OUT : mains proches d'une main IN

    Args:
        in_range_hands: Mains dans la range
        out_range_hands: Mains hors de la range
        proximity_threshold: Distance max pour être "proche"

    Returns:
        (borderline_in, borderline_out)
    """
    if not in_range_hands or not out_range_hands:
        return list(in_range_hands), list(out_range_hands)

    # Calculer les forces
    strengths_in = {h: HAND_STRENGTH.get(h, 50) for h in in_range_hands}
    strengths_out = {h: HAND_STRENGTH.get(h, 50) for h in out_range_hands}

    # Trier les mains IN par force décroissante
    sorted_in = sorted(in_range_hands, key=lambda h: strengths_in[h], reverse=True)

    borderline_in = []

    # 🎯 Trouver les frontières de la range IN
    for i, hand in enumerate(sorted_in):
        current_strength = strengths_in[hand]
        is_border = False

        # Regarder en DESSOUS (main plus faible suivante)
        if i < len(sorted_in) - 1:
            next_hand = sorted_in[i + 1]
            next_strength = strengths_in[next_hand]
            gap_below = current_strength - next_strength

            if gap_below > 5:  # Gap significatif = frontière
                is_border = True
                print(
                    f"  [BORDER IN] {hand}({current_strength}) : gap de {gap_below} vers {next_hand}({next_strength})")
        else:
            # C'est la main la plus faible de la range → toujours borderline
            is_border = True
            print(f"  [BORDER IN] {hand}({current_strength}) : main la plus faible de la range")

        # Regarder si une main OUT est proche JUSTE EN DESSOUS
        if not is_border:
            closest_out_below = None
            min_distance = float('inf')

            for hand_out, strength_out in strengths_out.items():
                if strength_out < current_strength:  # Seulement en dessous
                    distance = current_strength - strength_out
                    if distance < min_distance:
                        min_distance = distance
                        closest_out_below = hand_out

            if closest_out_below and min_distance <= proximity_threshold:
                # Vérifier qu'il n'y a pas de main IN entre les deux
                has_in_between = any(
                    current_strength > s > strengths_out[closest_out_below]
                    for s in strengths_in.values()
                )

                if not has_in_between:
                    is_border = True
                    print(
                        f"  [BORDER IN] {hand}({current_strength}) : {closest_out_below}({strengths_out[closest_out_below]}) OUT proche en dessous (distance {min_distance})")

        if is_border:
            borderline_in.append(hand)

    # 🎯 Trouver les mains OUT proches d'une frontière IN
    borderline_out = []

    for hand_out, strength_out in strengths_out.items():
        # Trouver la main IN la plus proche
        closest_in = None
        min_distance = float('inf')

        for hand_in, strength_in in strengths_in.items():
            distance = abs(strength_out - strength_in)
            if distance < min_distance:
                min_distance = distance
                closest_in = hand_in

        if min_distance <= proximity_threshold:
            borderline_out.append(hand_out)
            print(
                f"  [BORDER OUT] {hand_out}({strength_out}) : proche de {closest_in}({strengths_in[closest_in]}) IN (distance {min_distance})")

    print(f"[BORDERLINE] IN : {len(borderline_in)} mains → {borderline_in}")
    print(f"[BORDERLINE] OUT : {len(borderline_out)} mains → {borderline_out[:10]}...")

    # Fallback si vides
    if not borderline_in:
        sorted_in_list = sorted(in_range_hands, key=lambda h: strengths_in[h])
        borderline_in = sorted_in_list[:max(1, len(sorted_in_list) // 5)]
        print(f"[BORDERLINE] Fallback IN : {borderline_in[:3]}")

    if not borderline_out:
        sorted_out = sorted(out_range_hands, key=lambda h: strengths_out[h], reverse=True)
        borderline_out = sorted_out[:max(1, len(sorted_out) // 5)]
        print(f"[BORDERLINE] Fallback OUT : {borderline_out[:3]}")

    return borderline_in, borderline_out

# Ajouter le chemin vers les modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

# Importer context_validator si disponible
try:
    from context_validator import ContextValidator

    # Chemin absolu vers la base de données
    db_path = Path(__file__).parent.parent / "data" / "poker_trainer.db"
    validator = ContextValidator(str(db_path))

    VALIDATOR_AVAILABLE = True
    print(f"✓ Context validator chargé - VALIDATOR_AVAILABLE = {VALIDATOR_AVAILABLE}")
    print(f"✓ Base de données: {db_path}")
    print(f"✓ Base existe: {db_path.exists()}")
except (ImportError, FileNotFoundError) as e:
    print(f"✗ ATTENTION: context_validator non disponible: {e}")
    VALIDATOR_AVAILABLE = False
except Exception as e:
    print(f"✗ ERREUR inattendue lors du chargement validator: {e}")
    import traceback

    traceback.print_exc()
    VALIDATOR_AVAILABLE = False

# Variable globale pour le nombre d'orphelins
ORPHAN_COUNT = 0


# ============================================
# CHECK ORPHELINS AU DÉMARRAGE
# ============================================

def check_orphans_on_startup():
    """Vérifie les orphelins au démarrage."""
    try:
        conn = get_db_connection()
        if not conn:
            return 0

        cursor = conn.cursor()
        project_root = Path(__file__).parent.parent

        cursor.execute("""
            SELECT COUNT(DISTINCT rc.id)
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
        """)

        total = cursor.fetchone()[0]
        if total == 0:
            conn.close()
            return 0

        cursor.execute("SELECT rf.file_path FROM range_files rf")

        orphan_count = 0
        for (file_path,) in cursor.fetchall():
            full_path = project_root / file_path
            if not full_path.exists():
                orphan_count += 1

        conn.close()

        if orphan_count > 0:
            print(f"⚠️  {orphan_count} fichier(s) JSON manquant(s) détecté(s)")
            print(f"   → Accédez à http://localhost:5000/orphans pour les gérer")

        return orphan_count

    except Exception as e:
        print(f"[ORPHANS] Erreur check: {e}")
        return 0


# ============================================
# UTILITAIRES
# ============================================

def get_db_connection():
    """Retourne une connexion à la base de données"""
    db_path = Path(__file__).parent.parent / "data" / "poker_trainer.db"
    if not db_path.exists():
        return None
    return sqlite3.connect(db_path)


def update_source_json(context_id: int, metadata: dict, range_labels: dict = None):
    """
    Met à jour le fichier JSON source avec les métadonnées validées et les labels de sous-ranges.
    """
    # Mapping label_canon → nom pour l'éditeur
    LABEL_TO_NAME = {
        "OPEN": "open",
        "CALL": "call",
        "R3_VALUE": "3bet_value",
        "R3_BLUFF": "3bet_bluff",
        "R4_VALUE": "4bet_value",
        "R4_BLUFF": "4bet_bluff",
        "R5_ALLIN": "5bet_allin",
        "ISO_VALUE": "iso_value",
        "ISO_BLUFF": "iso_bluff",
        "CHECK": "check",
        "FOLD": "fold",
        "RAISE": "raise",
        "UNKNOWN": "unknown"
    }

    try:
        print(f"[JSON] Début mise à jour JSON pour context_id={context_id}")

        conn = get_db_connection()
        if not conn:
            print("[JSON] ❌ Connexion DB impossible")
            return False, "Connexion DB impossible"

        cursor = conn.cursor()

        # Récupérer le chemin du fichier JSON
        cursor.execute("""
            SELECT rf.file_path
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
            WHERE rc.id = ?
        """, (context_id,))

        result = cursor.fetchone()
        print(f"[JSON] Résultat requête DB: {result}")

        if not result or not result[0]:
            conn.close()
            print("[JSON] ❌ Fichier source non trouvé en DB")
            return False, "Fichier source non trouvé"

        file_path_relative = result[0]
        project_root = Path(__file__).parent.parent
        file_path = project_root / file_path_relative

        print(f"[JSON] Chemin fichier: {file_path}")
        print(f"[JSON] Fichier existe: {file_path.exists()}")

        if not file_path.exists():
            conn.close()
            print(f"[JSON] ❌ Fichier introuvable: {file_path}")
            return False, f"Fichier non trouvé: {file_path}"

        # Charger le JSON
        print("[JSON] Chargement du fichier...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"[JSON] JSON chargé. Clés: {list(data.keys())}")

        # Mettre à jour les métadonnées dans le JSON
        if 'metadata' not in data:
            data['metadata'] = {}

        print("[JSON] Mise à jour des métadonnées...")
        data['metadata'].update({
            'table_format': metadata.get('table_format'),
            'hero_position': metadata.get('hero_position'),
            'vs_position': metadata.get('vs_position'),
            'primary_action': metadata.get('primary_action'),
            'game_type': metadata.get('game_type'),
            'variant': metadata.get('variant'),
            'stack_depth': metadata.get('stack_depth'),
            'stakes': metadata.get('stakes'),
            'sizing': metadata.get('sizing'),
            'validated': True,
            'validated_by_user': True
        })

        # Mettre à jour les labels des ranges si fournis
        if range_labels:
            print(f"[JSON] Mise à jour {len(range_labels)} labels de ranges...")

            if 'data' in data and 'ranges' in data['data']:
                ranges_dict = data['data']['ranges']
                print(f"[JSON] Structure détectée: data.data.ranges avec {len(ranges_dict)} ranges")

                # Créer une correspondance ID DB → range_key
                range_id_to_key = {}

                for range_id in range_labels.keys():
                    cursor.execute("SELECT range_key FROM ranges WHERE id = ?", (range_id,))
                    result = cursor.fetchone()
                    if result:
                        range_id_to_key[range_id] = result[0]

                print(f"[JSON] Correspondances ID→Key: {range_id_to_key}")

                # Mettre à jour les labels dans le JSON
                for range_id, label_canon in range_labels.items():
                    range_key = range_id_to_key.get(range_id)
                    if range_key and range_key in ranges_dict:
                        range_obj = ranges_dict[range_key]
                        old_label = range_obj.get('label_canon', 'N/A')
                        old_name = range_obj.get('name', 'N/A')

                        # Mettre à jour le label_canon
                        range_obj['label_canon'] = label_canon

                        # Mettre à jour aussi le nom pour l'éditeur
                        new_name = LABEL_TO_NAME.get(label_canon, label_canon.lower())
                        range_obj['name'] = new_name

                        print(
                            f"[JSON]   Range {range_key}: name={old_name}→{new_name}, label={old_label}→{label_canon}")
                    else:
                        print(f"[JSON]   ⚠️ Range ID {range_id} (key={range_key}) non trouvée dans JSON")

        conn.close()

        # Sauvegarder le JSON mis à jour
        print(f"[JSON] Sauvegarde dans {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("[JSON] ✅ JSON mis à jour avec succès")
        return True, "JSON mis à jour avec succès"

    except Exception as e:
        print(f"[JSON] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Erreur mise à jour JSON: {str(e)}"


# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def dashboard():
    """Page principale du dashboard"""
    return render_template('dashboard.html')


# ============================================
# ROUTES ORPHELINS
# ============================================

@app.route('/orphans')
def orphans_page():
    """Page de gestion des contextes dont le fichier JSON est manquant."""
    return render_template('orphans.html')


@app.route('/api/orphans/check', methods=['GET'])
def check_orphans():
    """Vérifie et retourne la liste des contextes orphelins."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'orphans': [], 'count': 0})

        cursor = conn.cursor()
        project_root = Path(__file__).parent.parent

        cursor.execute("""
            SELECT 
                rc.id,
                rc.original_name,
                rc.display_name,
                rf.filename,
                rf.file_path,
                rf.id as file_id,
                COUNT(DISTINCT r.id) as ranges_count,
                COUNT(DISTINCT rh.id) as hands_count
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
            LEFT JOIN ranges r ON rc.id = r.context_id
            LEFT JOIN range_hands rh ON r.id = rh.range_id
            GROUP BY rc.id
        """)

        orphans = []
        for row in cursor.fetchall():
            context_id, original_name, display_name, filename, file_path, file_id, ranges_count, hands_count = row

            full_path = project_root / file_path
            if not full_path.exists():
                orphans.append({
                    'context_id': context_id,
                    'file_id': file_id,
                    'name': display_name or original_name or filename,
                    'filename': filename,
                    'file_path': file_path,
                    'ranges_count': ranges_count,
                    'hands_count': hands_count
                })

        conn.close()

        return jsonify({
            'orphans': orphans,
            'count': len(orphans)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orphans/ignore/<int:context_id>', methods=['POST'])
def ignore_orphan(context_id):
    """Marque un orphelin comme ignoré (aucune action)."""
    return jsonify({
        'success': True,
        'message': 'Contexte ignoré - aucune modification effectuée'
    })


@app.route('/api/orphans/delete/<int:context_id>', methods=['POST'])
def delete_orphan(context_id):
    """Supprime un contexte orphelin de la base."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Connexion DB impossible'}), 500

        cursor = conn.cursor()

        # Les CASCADE suppriment automatiquement ranges, range_hands
        cursor.execute("""
            DELETE FROM range_files 
            WHERE id IN (
                SELECT file_id FROM range_contexts WHERE id = ?
            )
        """, (context_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Contexte supprimé de la base de données'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/orphans/rebuild/<int:context_id>', methods=['POST'])
def rebuild_orphan(context_id):
    """Reconstruit le JSON d'un contexte orphelin."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Connexion DB impossible'}), 500

        cursor = conn.cursor()

        # 1. Récupérer le contexte
        cursor.execute("""
            SELECT 
                rc.original_name, rc.table_format, rc.hero_position,
                rc.vs_position, rc.primary_action, rc.game_type,
                rc.variant, rc.stack_depth, rc.stakes, rc.sizing,
                rf.file_path
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
            WHERE rc.id = ?
        """, (context_id,))

        context_row = cursor.fetchone()
        if not context_row:
            conn.close()
            return jsonify({'success': False, 'message': 'Contexte non trouvé'}), 404

        # 2. Récupérer les ranges
        cursor.execute("""
            SELECT range_key, name, color, label_canon
            FROM ranges
            WHERE context_id = ?
            ORDER BY CAST(range_key AS INTEGER)
        """, (context_id,))

        ranges_data = {}
        max_index = 0
        for range_key, name, color, label_canon in cursor.fetchall():
            ranges_data[range_key] = {
                "name": name or f"range_{range_key}",
                "color": color or "#cccccc"
            }
            if label_canon:
                ranges_data[range_key]["label_canon"] = label_canon
            max_index = max(max_index, int(range_key))

        # 3. Récupérer les mains
        cursor.execute("""
            SELECT rh.hand, r.range_key
            FROM range_hands rh
            JOIN ranges r ON rh.range_id = r.id
            WHERE r.context_id = ?
            ORDER BY rh.hand
        """, (context_id,))

        values_data = {}
        for hand, range_key in cursor.fetchall():
            if hand not in values_data:
                values_data[hand] = []
            values_data[hand].append(int(range_key))

        conn.close()

        # 4. Construire le JSON
        json_data = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": {
                "url": "https://site2wouf.fr/poker-range-editor.php",
                "tool": "Poker Range Grid - Reconstructed from Database",
                "reconstructed": True
            },
            "data": {
                "ranges": ranges_data,
                "values": values_data,
                "maxIndex": max_index
            },
            "metadata": {
                "table_format": context_row[1],
                "hero_position": context_row[2],
                "vs_position": context_row[3] or "N/A",
                "primary_action": context_row[4],
                "game_type": context_row[5],
                "variant": context_row[6],
                "stack_depth": context_row[7],
                "stakes": context_row[8],
                "sizing": context_row[9],
                "validated": True,
                "validated_by_user": True,
                "reconstructed_from_db": True
            }
        }

        # 5. Écrire le fichier
        project_root = Path(__file__).parent.parent
        file_path = project_root / context_row[10]

        # Créer le répertoire si nécessaire
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            'success': True,
            'message': f'Fichier JSON reconstruit avec succès',
            'filename': file_path.name,
            'path': str(file_path)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500


# ============================================
# ROUTES DE VALIDATION
# ============================================

@app.route('/validate')
def validate_page():
    """Page de validation d'un contexte."""
    if not VALIDATOR_AVAILABLE:
        return "<h1>Erreur</h1><p>Module de validation non disponible</p>", 500
    return render_template('validate_context.html')


@app.route('/api/validation/context/<int:context_id>')
def get_context_for_validation(context_id):
    """Récupère les informations d'un contexte pour validation."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'error': 'Module de validation non disponible'}), 500

    try:
        context = validator.get_context_for_validation(context_id)

        if not context:
            return jsonify({'error': 'Contexte non trouvé'}), 404
        return jsonify(context)
    except Exception as e:
        print(f"Erreur get_context_for_validation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/validation/candidates')
def get_validation_candidates():
    """Récupère tous les contextes nécessitant une validation."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'error': 'Module de validation non disponible'}), 500

    try:
        candidates = validator.get_validation_candidates()
        return jsonify({
            'count': len(candidates),
            'contexts': candidates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/validation/validate/<int:context_id>', methods=['POST'])
def validate_context(context_id):
    """Valide et met à jour les métadonnées d'un contexte ET ses sous-ranges."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Extraire les paramètres spéciaux
        update_json = data.pop('update_json', False)
        range_labels_raw = data.pop('range_labels', None)

        # Convertir les clés des range_labels en entiers
        range_labels = None
        if range_labels_raw:
            try:
                range_labels = {int(k): v for k, v in range_labels_raw.items()}
            except (ValueError, AttributeError) as e:
                return jsonify({
                    'success': False,
                    'message': f'Format range_labels invalide: {str(e)}'
                }), 400

        # Valider et mettre à jour la base (contexte + sous-ranges)
        success, message = validator.validate_and_update(
            context_id=context_id,
            metadata=data,
            range_labels=range_labels
        )

        if not success:
            return jsonify({'success': False, 'message': message}), 400

        # Si demandé, mettre à jour le JSON source
        json_updated = False
        json_message = ""

        if update_json:
            json_success, json_message = update_source_json(
                context_id,
                data,
                range_labels
            )
            json_updated = json_success

        return jsonify({
            'success': True,
            'message': message,
            'json_updated': json_updated,
            'json_message': json_message if update_json else None
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500


@app.route('/api/validation/update-subranges', methods=['POST'])
def update_subranges():
    """Met à jour uniquement les labels des sous-ranges sans toucher au contexte."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        data = request.get_json()
        range_labels_raw = data.get('range_labels', {})

        if not range_labels_raw:
            return jsonify({
                'success': False,
                'message': 'Aucun label à mettre à jour'
            }), 400

        # Convertir les clés en entiers
        try:
            range_labels = {int(k): v for k, v in range_labels_raw.items()}
        except (ValueError, AttributeError) as e:
            return jsonify({
                'success': False,
                'message': f'Format range_labels invalide: {str(e)}'
            }), 400

        # Mettre à jour via le validator
        success, message = validator.update_subrange_labels(range_labels)

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500


@app.route('/api/validation/ignore/<int:context_id>', methods=['POST'])
def ignore_context(context_id):
    """Marque un contexte comme non exploitable."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Marqué manuellement comme non exploitable')

        success = validator.mark_as_non_exploitable(context_id, reason)

        return jsonify({
            'success': success,
            'message': 'Contexte marqué comme non exploitable' if success else 'Erreur'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/validation/rename-file/<int:context_id>', methods=['POST'])
def rename_context_file(context_id):
    """Renomme le fichier JSON selon le slug généré."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        data = request.get_json()
        slug = data.get('slug')

        if not slug:
            return jsonify({'success': False, 'message': 'Slug manquant'}), 400

        new_filename = f"{slug}.json"

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Connexion DB impossible'}), 500

        cursor = conn.cursor()

        cursor.execute("""
            SELECT rf.file_path, rf.filename, rf.id
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
            WHERE rc.id = ?
        """, (context_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'success': False, 'message': 'Contexte non trouvé'}), 404

        old_path_relative, old_filename, file_id = result

        project_root = Path(__file__).parent.parent
        old_path = project_root / old_path_relative

        if not old_path.exists():
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Fichier source non trouvé: {old_path}'
            }), 404

        new_path = old_path.parent / new_filename
        new_path_relative = str(new_path.relative_to(project_root))

        if new_path.exists() and new_path != old_path:
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Un fichier nommé "{new_filename}" existe déjà'
            }), 409

        if old_path == new_path:
            conn.close()
            return jsonify({
                'success': True,
                'message': 'Le fichier a déjà le bon nom',
                'filename': new_filename
            })

        import shutil
        shutil.move(str(old_path), str(new_path))

        cursor.execute("""
            UPDATE range_files
            SET filename = ?,
                file_path = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (new_filename, new_path_relative, file_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Fichier renommé avec succès',
            'old_name': old_filename,
            'new_name': new_filename
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500


@app.route('/api/validation/stats')
def get_validation_stats():
    """Récupère des statistiques sur les contextes à valider."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'total_pending': 0, 'by_confidence': {}})

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE needs_validation = 1")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                CASE 
                    WHEN confidence_score < 50 THEN 'low'
                    WHEN confidence_score < 80 THEN 'medium'
                    ELSE 'high'
                END as level,
                COUNT(*) as count
            FROM range_contexts 
            WHERE needs_validation = 1
            GROUP BY level
        """)
        by_conf = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            'total_pending': total,
            'by_confidence': by_conf
        })

    except Exception as e:
        print(f"Erreur get_validation_stats: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ROUTES PIPELINE
# ============================================

@app.route('/api/import_pipeline', methods=['POST'])
def api_import_pipeline():
    """Lance le pipeline intégré avec détection des contextes à valider"""
    try:
        os.environ['POKER_WEB_MODE'] = '1'
        project_root = Path(__file__).parent.parent

        print("Lancement du pipeline intégré...")

        result = subprocess.run([
            sys.executable, 'integrated_pipeline.py'
        ], cwd=project_root, capture_output=True, text=True)

        if result.returncode == 0:
            stats = get_pipeline_stats()
            contexts_to_validate = get_contexts_needing_validation()

            return jsonify({
                'success': True,
                'status': 'success',
                'message': 'Pipeline intégré terminé avec succès',
                'stats': stats,
                'contexts_to_validate': contexts_to_validate,
                'output': result.stdout,
                'error': result.stderr if result.stderr else None
            })
        else:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': 'Erreur lors du pipeline intégré',
                'output': result.stdout,
                'error': result.stderr
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'message': f'Erreur système: {str(e)}'
        }), 500


def get_pipeline_stats():
    """Récupère les statistiques du pipeline depuis la DB"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                'total_files': 0, 'total_contexts': 0, 'total_ranges': 0,
                'total_hands': 0, 'quiz_ready': 0, 'needs_validation': 0, 'errors': 0
            }

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM range_files")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts")
        total_contexts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ranges")
        total_ranges = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_hands")
        total_hands = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE quiz_ready = 1")
        quiz_ready = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE needs_validation = 1")
        needs_validation = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE error_message IS NOT NULL")
        errors = cursor.fetchone()[0]

        conn.close()

        return {
            'total_files': total_files,
            'total_contexts': total_contexts,
            'total_ranges': total_ranges,
            'total_hands': total_hands,
            'quiz_ready': quiz_ready,
            'needs_validation': needs_validation,
            'errors': errors
        }

    except Exception as e:
        print(f"Erreur get_pipeline_stats: {e}")
        return {
            'total_files': 0, 'total_contexts': 0, 'total_ranges': 0,
            'total_hands': 0, 'quiz_ready': 0, 'needs_validation': 0, 'errors': 0
        }


def get_contexts_needing_validation():
    """Récupère la liste des contextes nécessitant validation"""
    try:
        conn = get_db_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, display_name, original_name, confidence_score 
            FROM range_contexts 
            WHERE needs_validation = 1 
            LIMIT 5
        """)

        contexts = []
        for row in cursor.fetchall():
            contexts.append({
                'id': row[0],
                'name': row[1] or row[2] or 'Sans nom',
                'confidence': row[3] or 0
            })

        conn.close()
        return contexts

    except Exception as e:
        print(f"Erreur get_contexts_needing_validation: {e}")
        return []


# ============================================
# ROUTES DEBUG ET STATS
# ============================================

@app.route('/api/debug/db')
def api_debug_db():
    """API debug pour les statistiques de base"""
    try:
        conn = get_db_connection()

        if not conn:
            return jsonify({
                'status': 'no_database',
                'message': 'Base de données non créée - utilisez Import Pipeline',
                'data': {
                    'range_files': 0, 'range_contexts': 0,
                    'ranges': 0, 'range_hands': 0
                },
                'range_contexts_examples': []
            })

        cursor = conn.cursor()

        stats = {}
        for table in ['range_files', 'range_contexts', 'ranges', 'range_hands']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats[table] = 0

        try:
            cursor.execute("""
                SELECT id, display_name, original_name, confidence_score 
                FROM range_contexts 
                LIMIT 5
            """)
            examples = [
                {
                    'id': row[0],
                    'name': row[1] or row[2] or 'Sans nom',
                    'confidence': row[3] or 0
                }
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            examples = []

        conn.close()

        return jsonify({
            'status': 'success',
            'data': stats,
            'range_contexts_examples': examples
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """API pour les statistiques du dashboard"""
    return jsonify({'recent_imports': [], 'status': 'success'})


@app.route('/api/dashboard/contexts')
def api_dashboard_contexts():
    """API pour les contextes du dashboard avec statuts corrects"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([])

        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                rc.id,
                rc.display_name,
                rc.original_name,
                rc.confidence_score,
                rc.hero_position,
                rc.primary_action,
                rc.needs_validation,
                rc.quiz_ready,
                rc.error_message,
                rf.filename,
                (SELECT COUNT(*) FROM ranges WHERE context_id = rc.id) as ranges_count,
                (SELECT COUNT(*) FROM range_hands rh 
                 JOIN ranges r ON r.id = rh.range_id 
                 WHERE r.context_id = rc.id) as hands_count
            FROM range_contexts rc
            JOIN range_files rf ON rc.file_id = rf.id
            ORDER BY rc.needs_validation DESC, rc.quiz_ready DESC, rc.id DESC
            LIMIT 50
        """)

        contexts = []
        for row in cursor.fetchall():
            if row[6]:
                context_status = 'needs_validation'
            elif row[7]:
                context_status = 'quiz_ready'
            elif row[8]:
                context_status = 'error'
            else:
                context_status = 'unknown'

            contexts.append({
                'id': row[0],
                'name': row[1] or row[2] or 'Sans nom',
                'confidence': (row[3] or 0) / 100.0,
                'filename': row[9],
                'hero_position': row[4] or 'N/A',
                'primary_action': row[5] or 'N/A',
                'context_status': context_status,
                'ranges_count': row[10] or 0,
                'hands_count': row[11] or 0
            })

        conn.close()
        return jsonify(contexts)

    except Exception as e:
        print(f"Erreur dans api_dashboard_contexts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ROUTES QUIZ
# ============================================

@app.route('/api/quiz/check')
def api_quiz_check():
    """Vérifie si des contextes sont prêts pour le quiz"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'ready': False,
                'message': 'Base de données non initialisée',
                'ready_contexts': 0,
                'total_contexts': 0
            })

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE quiz_ready = 1")
        ready_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts")
        total_count = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'ready': ready_count > 0,
            'message': f'{ready_count} contexte(s) prêt(s) pour le quiz' if ready_count > 0 else 'Aucun contexte prêt',
            'ready_contexts': ready_count,
            'total_contexts': total_count
        })

    except Exception as e:
        return jsonify({
            'ready': False,
            'error': str(e)
        }), 500



# ============================================
# ROUTES DEBUG SUPPLÉMENTAIRES
# ============================================

@app.route('/debug_structure')
def debug_structure():
    """Affiche la structure de la base de données"""
    conn = get_db_connection()
    if not conn:
        return "<h1>Base de données non trouvée</h1>"

    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(ranges)")
    ranges_columns = cursor.fetchall()

    cursor.execute("PRAGMA table_info(range_contexts)")
    contexts_columns = cursor.fetchall()

    result = "<h1>Structure de la base de données</h1>"

    result += "<h2>Table: range_contexts</h2>"
    result += "<table border='1' cellpadding='10'>"
    result += "<tr><th>ID</th><th>Nom</th><th>Type</th><th>NOT NULL</th><th>Default</th></tr>"
    for col in contexts_columns:
        result += f"<tr><td>{col[0]}</td><td><strong>{col[1]}</strong></td><td>{col[2]}</td><td>{'Oui' if col[3] else 'Non'}</td><td>{col[4]}</td></tr>"
    result += "</table>"

    result += "<h2>Table: ranges</h2>"
    result += "<table border='1' cellpadding='10'>"
    result += "<tr><th>ID</th><th>Nom</th><th>Type</th><th>NOT NULL</th><th>Default</th></tr>"
    for col in ranges_columns:
        highlight = ' style="background-color: #ffff99;"' if col[1] == 'label_canon' else ''
        result += f"<tr{highlight}><td>{col[0]}</td><td><strong>{col[1]}</strong></td><td>{col[2]}</td><td>{'Oui' if col[3] else 'Non'}</td><td>{col[4]}</td></tr>"
    result += "</table>"

    has_label_canon = any(col[1] == 'label_canon' for col in ranges_columns)
    if has_label_canon:
        result += '<p style="color: green; font-weight: bold;">✓ Colonne label_canon présente</p>'

        cursor.execute("""
            SELECT label_canon, COUNT(*) as count
            FROM ranges
            WHERE label_canon IS NOT NULL
            GROUP BY label_canon
            ORDER BY count DESC
        """)
        label_stats = cursor.fetchall()

        if label_stats:
            result += "<h3>Distribution des labels canoniques</h3>"
            result += "<table border='1' cellpadding='10'>"
            result += "<tr><th>Label</th><th>Count</th></tr>"
            for label, count in label_stats:
                result += f"<tr><td><strong>{label}</strong></td><td>{count}</td></tr>"
            result += "</table>"
    else:
        result += '<p style="color: red; font-weight: bold;">✗ Colonne label_canon absente - Migration nécessaire!</p>'

    conn.close()
    return result


# ======================
# ROUTES QUIZ
# ======================

@app.route('/quiz-setup')
def quiz_setup():
    """Page de configuration du quiz"""
    return render_template('quiz_setup.html')


@app.route('/api/quiz/available-contexts')
def get_available_contexts():
    """Récupère tous les contextes validés prêts pour le quiz"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                rc.id,
                rc.display_name,
                rc.table_format,
                rc.hero_position,
                rc.primary_action,
                rc.vs_position,
                rc.stack_depth,
                rc.variant,
                COUNT(DISTINCT r.id) as range_count
            FROM range_contexts rc
            LEFT JOIN ranges r ON rc.id = r.context_id
            WHERE rc.quiz_ready = 1
            GROUP BY rc.id
            HAVING range_count > 0
            ORDER BY rc.display_name
        """)

        contexts = []
        for row in cursor.fetchall():
            contexts.append({
                'id': row[0],
                'display_name': row[1],
                'table_format': row[2],
                'hero_position': row[3],
                'primary_action': row[4],
                'vs_position': row[5],
                'stack_depth': row[6],
                'variant': row[7],
                'range_count': row[8]
            })

        conn.close()

        return jsonify({
            'success': True,
            'contexts': contexts,
            'total': len(contexts)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/quiz')
def quiz():
    """Page du quiz interactif"""
    # Récupère les paramètres
    context_ids = request.args.get('contexts', '')
    question_count = request.args.get('count', '10')

    if not context_ids:
        return "Erreur: Aucun contexte sélectionné", 400

    return render_template('quiz.html',
                           context_ids=context_ids,
                           question_count=question_count)


@app.route('/api/quiz/generate')
def generate_quiz_questions():
    """Génère les questions pour le quiz"""
    try:
        context_ids = request.args.get('contexts', '').split(',')
        question_count = int(request.args.get('count', 10))

        if not context_ids or not context_ids[0]:
            return jsonify({'error': 'Aucun contexte fourni'}), 400

        # Convertir les IDs en entiers
        context_ids = [int(id) for id in context_ids if id]

        print(f"[QUIZ] Génération de {question_count} questions pour contextes: {context_ids}")

        conn = get_db_connection()
        questions = []
        attempts = 0
        max_attempts = question_count * 3  # Essayer 3x plus pour compenser les skip

        while len(questions) < question_count and attempts < max_attempts:
            attempts += 1
            context_id = random.choice(context_ids)

            # Générer une question
            question = generate_single_question(conn, context_id)

            # ✅ Filtrer les None (questions skippées)
            if question:
                questions.append(question)

        conn.close()

        # Si aucune question générée, erreur explicite
        if len(questions) == 0:
            print(f"[QUIZ] ❌ ERREUR: Aucune question générée après {attempts} tentatives")
            print(f"[QUIZ] Les contextes {context_ids} ont probablement des label_canon manquants ou invalides")
            return jsonify({
                'error': 'Impossible de générer des questions. Les contextes sélectionnés ont des données incomplètes. Veuillez les valider via l\'interface de validation.'
            }), 400

        print(
            f"[QUIZ] ✅ {len(questions)} questions générées sur {question_count} demandées (après {attempts} tentatives)")

        return jsonify({
            'success': True,
            'questions': questions,
            'total': len(questions)
        })

    except Exception as e:
        print(f"[QUIZ] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/quiz/question', methods=['POST'])
def get_next_quiz_question():
    """Génère une seule question en évitant les doublons"""
    try:
        data = request.get_json()
        context_ids = data.get('context_ids', [])
        excluded = data.get('excluded', [])  # Format: [{hand: 'AA', context_id: 1}, ...]

        if not context_ids:
            return jsonify({'error': 'Aucun contexte fourni'}), 400

        # Convertir en set pour recherche O(1)
        excluded_set = {(q['hand'], q['context_id']) for q in excluded}

        print(f"[QUIZ] Génération question, {len(excluded)} déjà posées, contextes: {context_ids}")

        # Essayer de générer une question unique
        max_attempts = 100
        conn = get_db_connection()

        for attempt in range(max_attempts):
            context_id = random.choice(context_ids)
            question = generate_single_question(conn, context_id)

            if not question:
                continue

            # Vérifier si déjà posée
            key = (question['hand'], question['context_id'])
            if key not in excluded_set:
                conn.close()
                print(
                    f"[QUIZ] ✅ Question générée: {question['hand']} (context {context_id}) après {attempt + 1} tentatives")
                return jsonify({
                    'success': True,
                    'question': question
                })

        conn.close()

        # Aucune question unique trouvée
        print(f"[QUIZ] ⚠️ Plus de questions uniques disponibles après {max_attempts} tentatives")
        return jsonify({
            'error': 'no_more_questions',
            'message': 'Toutes les questions disponibles ont été utilisées'
        }), 404

    except Exception as e:
        print(f"[QUIZ] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_single_question(conn, context_id):
    """Génère une seule question pour un contexte donné"""
    cursor = conn.cursor()

    # Récupère le contexte
    cursor.execute("""
        SELECT 
            id, display_name, table_format, hero_position, 
            primary_action, vs_position, stack_depth
        FROM range_contexts 
        WHERE id = ?
    """, (context_id,))

    context_row = cursor.fetchone()
    if not context_row:
        return None

    context = {
        'id': context_row[0],
        'display_name': context_row[1],
        'table_format': context_row[2],
        'hero_position': context_row[3],
        'primary_action': context_row[4],
        'vs_position': context_row[5],
        'stack_depth': context_row[6]
    }

    # Récupère toutes les ranges du contexte
    cursor.execute("""
        SELECT 
            r.id, r.range_key, r.name, r.label_canon,
            GROUP_CONCAT(DISTINCT rh.hand) as hands
        FROM ranges r
        LEFT JOIN range_hands rh ON r.id = rh.range_id
        WHERE r.context_id = ?
        GROUP BY r.id
        ORDER BY r.range_key
    """, (context_id,))

    ranges = []
    for row in cursor.fetchall():
        hands_str = row[4]
        if hands_str:
            ranges.append({
                'id': row[0],
                'range_key': row[1],
                'name': row[2],
                'label_canon': row[3],
                'hands': hands_str.split(',')
            })

    if not ranges:
        return None

    # 🆕 UNIQUEMENT DES QUESTIONS SIMPLES POUR L'INSTANT
    # Les questions conditionnelles = amélioration #2 (questions à tiroirs)
    return generate_simple_question(context, ranges)


def generate_simple_action_options(correct_answer, main_range_action, context):
    """Génère des options SIMPLES adaptées au contexte"""

    options = []

    # 1. Toujours inclure la bonne réponse
    if correct_answer:
        options.append(correct_answer)

    # 2. FOLD ou CHECK selon le contexte
    primary = context.get('primary_action')
    if not primary:
        primary = ''
    primary_lower = primary.lower()

    hero_position = context.get('hero_position', '')

    # Si BB et action de check (pas de relance)
    if hero_position == 'BB' and 'check' in primary_lower:
        if 'CHECK' not in options:
            options.append('CHECK')
    else:
        # Sinon, toujours FOLD
        if 'FOLD' not in options:
            options.append('FOLD')

    # 3. 🆕 Pour DEFENSE, ne pas ajouter l'action principale (qui est 'DEFENSE')
    #    À la place, ajouter les actions des sous-ranges
    if main_range_action == 'DEFENSE':
        # Ne rien faire ici, on va ajouter des distracteurs pertinents plus bas
        pass
    elif main_range_action and main_range_action not in options:
        # Pour les autres contextes, ajouter l'action principale
        options.append(main_range_action)

    # 4. Ajouter des distracteurs si besoin
    if len(options) < 3:
        if 'defense' in primary_lower:
            # Context defense : distracteurs cohérents
            distractors = ['3BET', 'CALL', 'RAISE']
        elif 'open' in primary_lower:
            distractors = ['CALL', 'RAISE']
        elif 'check' in primary_lower:
            distractors = ['RAISE', 'CALL']
        elif '3bet' in primary_lower or 'squeeze' in primary_lower:
            distractors = ['CALL', 'RAISE']
        elif 'iso' in primary_lower:
            distractors = ['CALL', 'RAISE']
        else:
            distractors = ['CALL', 'RAISE']

        for distractor in distractors:
            if distractor not in options and len(options) < 3:
                options.append(distractor)

    # ✅ ORDRE FIXE
    return sort_actions(options)

def generate_simple_question(context, ranges):
    """Question simple sur l'action principale"""

    # Trouver la range principale
    main_range = None
    for r in ranges:
        if r['range_key'] == '1':
            main_range = r
            break

    if not main_range:
        print(f"[QUIZ] SKIP: Pas de range principale pour context_id={context['id']}")
        return None

    if not main_range['hands']:
        print(f"[QUIZ] SKIP: Range principale vide context_id={context['id']}")
        return None

    correct_action = main_range.get('label_canon')

    if not correct_action or correct_action == 'None' or correct_action == '':
        print(f"[QUIZ] SKIP: label_canon invalide pour range principale")
        return None

    normalized_action = normalize_action(correct_action)

    if not normalized_action:
        print(f"[QUIZ] SKIP: normalisation échouée pour '{correct_action}'")
        return None

    # 🆕 Préparer les mains IN et OUT
    in_range_hands = set(main_range['hands'])
    out_of_range_hands = set([h for h in ALL_POKER_HANDS if h not in in_range_hands])

    # 🆕 50% de chances in/out avec choix intelligent
    is_in_range = random.random() >= 0.5

    if is_in_range:
        # Main DANS la range
        hand = smart_hand_choice(in_range_hands, out_of_range_hands, is_in_range=True)

        # 🆕 Si c'est un contexte DEFENSE, trouver l'action dans les sous-ranges
        if normalized_action == 'DEFENSE':
            correct_answer = find_defense_action(hand, ranges)
            if not correct_answer:
                print(f"[QUIZ] SKIP: Main {hand} dans defense mais sans action dans sous-ranges")
                return None
        else:
            correct_answer = normalized_action

        print(f"[QUIZ] ✅ Question IN-RANGE: {hand} → {correct_answer} (context: {context['primary_action']})")
    else:
        # Main HORS de la range
        hand = smart_hand_choice(in_range_hands, out_of_range_hands, is_in_range=False)
        correct_answer = 'FOLD'
        print(f"[QUIZ] ✅ Question OUT-OF-RANGE: {hand} → FOLD (context: {context['primary_action']})")

    if not hand:
        print(f"[QUIZ] SKIP: Impossible de choisir une main")
        return None

    # Générer options en passant l'action principale
    options = generate_simple_action_options(correct_answer, normalized_action, context)
    options = [opt for opt in options if opt is not None]

    if len(options) < 2:
        print(f"[QUIZ] SKIP: Pas assez d'options valides ({len(options)})")
        return None

    question_text = format_simple_question(context, hand)

    print(f"[QUIZ] Options générées : {options}")

    return {
        'type': 'simple',
        'context_id': context['id'],
        'hand': hand,
        'question': question_text,
        'options': options,
        'correct_answer': correct_answer,
        'context_info': context
    }

def normalize_action(action):
    """Normalise les actions pour éviter les doublons (VALUE/BLUFF)"""
    # ⚠️ CRITIQUE : Gérer la string 'None' qui vient parfois de la DB
    if not action or action == 'None' or action == 'null' or action == '':
        print(f"[QUIZ] Warning: action invalide: {repr(action)}")
        return None

    action_map = {
        'R3_VALUE': '3BET',
        'R3_BLUFF': '3BET',
        'R4_VALUE': '4BET',
        'R4_BLUFF': '4BET',
        'R5_ALLIN': 'ALLIN',
        'ISO_VALUE': 'ISO',
        'ISO_BLUFF': 'ISO'
    }
    return action_map.get(action, action)


def find_defense_action(hand, ranges):
    """
    Trouve l'action correcte pour une main dans un contexte defense.
    Cherche dans les sous-ranges (range_key > 1).

    Args:
        hand: La main (ex: 'AA', 'KQs')
        ranges: Liste des ranges du contexte

    Returns:
        Action normalisée (CALL, 3BET, etc.) ou None
    """
    # Chercher dans les sous-ranges (range_key != '1')
    for r in ranges:
        if r['range_key'] != '1' and hand in r['hands']:
            label = r.get('label_canon')
            if label and label != 'None' and label != '':
                normalized = normalize_action(label)
                if normalized:
                    print(f"  [DEFENSE] {hand} trouvé dans '{r['name']}' → {normalized}")
                    return normalized

    # Main non trouvée dans les sous-ranges = incohérence !
    print(f"  [DEFENSE] ⚠️ {hand} dans range principale mais pas dans sous-ranges")
    return None

def generate_conditional_action_options(correct_answer, ranges, context):
    """
    Génère les options pour questions conditionnelles.
    Utilise les sous-ranges car elles sont pertinentes.

    Args:
        correct_answer: La bonne réponse
        ranges: Les ranges du contexte (pour récupérer les sous-ranges)
        context: Info du contexte

    Returns:
        Liste d'actions triées
    """
    options = [correct_answer] if correct_answer else []

    # Récupérer les actions des SOUS-RANGES uniquement
    sub_ranges = [r for r in ranges if int(r['range_key']) > 1]

    available_in_subranges = []
    for r in sub_ranges:
        label = r.get('label_canon')
        if label and label != 'None' and label != '':
            normalized = normalize_action(label)
            if normalized and normalized != correct_answer:
                available_in_subranges.append(normalized)

    # Dédupliquer
    available_in_subranges = list(set(available_in_subranges))

    # Toujours ajouter FOLD
    if 'FOLD' not in options:
        options.append('FOLD')

    # Ajouter les actions disponibles (max 4 options)
    for action in available_in_subranges:
        if action not in options and len(options) < 4:
            options.append(action)

    # ✅ ORDRE FIXE
    return sort_actions(options)

def generate_action_options(correct_answer, ranges, context):
    """
    Génère les options de réponse adaptées au contexte.

    Args:
        correct_answer: La bonne réponse
        ranges: Les ranges du contexte
        context: Info du contexte (pour adapter les options)

    Returns:
        Liste d'actions triées dans un ordre fixe
    """
    options = [correct_answer] if correct_answer else []

    # Récupérer toutes les actions disponibles dans ce contexte
    available_in_context = []
    for r in ranges:
        label = r.get('label_canon')
        if label and label != 'None' and label != '':
            normalized = normalize_action(label)
            if normalized and normalized != correct_answer:
                available_in_context.append(normalized)

    # Dédupliquer
    available_in_context = list(set(available_in_context))

    # Toujours ajouter FOLD
    if 'FOLD' not in options:
        options.append('FOLD')

    # Ajouter des distracteurs depuis le contexte (limité à 4 options max)
    for action in available_in_context:
        if action not in options and len(options) < 4:
            options.append(action)

    # Si vraiment pas assez d'options, ajouter des actions PERTINENTES selon le contexte
    if len(options) < 3:
        primary = context.get('primary_action', '').lower()

        # Choisir des fallbacks cohérents avec le contexte
        if 'open' in primary:
            # Contexte d'ouverture : pas de 3bet/4bet
            fallback = ['CALL', 'RAISE']
        elif 'defense' in primary:
            # Défense face à open : 3bet possible
            fallback = ['CALL', '3BET']
        elif '3bet' in primary or 'squeeze' in primary:
            # Face à 3bet : 4bet possible
            fallback = ['CALL', '4BET']
        elif '4bet' in primary:
            # Face à 4bet : all-in possible
            fallback = ['CALL', 'ALLIN']
        else:
            # Générique
            fallback = ['CALL', 'RAISE']

        for action in fallback:
            if action not in options and len(options) < 4:
                options.append(action)

    # ✅ ORDRE FIXE (pas de shuffle)
    return sort_actions(options)


def format_simple_question(context, hand):
    """Formate le texte d'une question simple en fonction du contexte"""
    table = context.get('table_format') or '?'
    position = context.get('hero_position') or '?'
    stack = context.get('stack_depth') or '100bb'
    primary_action = context.get('primary_action', '').lower()
    vs_position = context.get('vs_position') or 'UTG'

    # 🆕 Adapter la question selon le type de contexte
    if primary_action == 'defense' or 'defense' in primary_action:
        # Contexte de defense : mentionner qui a ouvert
        if vs_position and vs_position != 'N/A':
            return f"Table {table}, vous êtes {position} avec {stack}. {vs_position} ouvre. Vous avez {hand}. Que faites-vous ?"
        else:
            return f"Table {table}, vous êtes {position} avec {stack}. Un adversaire ouvre. Vous avez {hand}. Que faites-vous ?"

    elif primary_action == '3bet' or 'squeeze' in primary_action:
        # Contexte de 3bet/squeeze : mentionner l'open adverse
        if vs_position and vs_position != 'N/A':
            return f"Table {table}, vous êtes {position} avec {stack}. {vs_position} ouvre. Vous avez {hand}. Que faites-vous ?"
        else:
            return f"Table {table}, vous êtes {position} avec {stack}. Un adversaire ouvre. Vous avez {hand}. Que faites-vous ?"

    elif primary_action == '4bet':
        # Contexte de 4bet : mentionner le 3bet adverse
        if vs_position and vs_position != 'N/A':
            return f"Table {table}, vous êtes {position} avec {stack}. Vous ouvrez, {vs_position} 3bet. Vous avez {hand}. Que faites-vous ?"
        else:
            return f"Table {table}, vous êtes {position} avec {stack}. Vous ouvrez, un adversaire 3bet. Vous avez {hand}. Que faites-vous ?"

    elif primary_action == 'check':
        # BB option (personne n'a relancé)
        return f"Table {table}, vous êtes {position} avec {stack}. Personne n'a ouvert. Vous avez {hand}. Que faites-vous ?"

    else:
        # Open, iso, call, etc. → question neutre
        return f"Table {table}, vous êtes {position} avec {stack}. Vous avez {hand}. Que faites-vous ?"

def format_conditional_question(context, hand):
    """Formate le texte d'une question conditionnelle"""
    table = context.get('table_format') or '?'
    position = context.get('hero_position') or '?'
    action = translate_action(context.get('primary_action'))
    vs_pos = context.get('vs_position') or 'un adversaire'
    stack = context.get('stack_depth') or '100bb'

    if vs_pos == 'N/A' or not vs_pos:
        vs_pos = "un adversaire"

    return f"Table {table}, vous êtes {position} avec {stack}. Vous {action} {hand}, {vs_pos} relance."


def translate_action(action):
    """Traduit une action en français"""
    if not action:
        return 'jouez avec'

    translations = {
        'open': 'ouvrez avec',
        'defense': 'défendez avec',
        '3bet': '3-bet avec',
        'squeeze': 'squeezez avec',
        '4bet': '4-bet avec',
        'call': 'call avec',
        'raise': 'relancez avec'
    }
    return translations.get(action.lower(), action)

if __name__ == '__main__':
    ORPHAN_COUNT = check_orphans_on_startup()
    app.run(debug=True)