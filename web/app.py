from flask import Flask, render_template, jsonify, request, send_from_directory
import subprocess
import os
import sys
import sqlite3
import json
from pathlib import Path
import re
from datetime import datetime
import random

CARDS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'cartes')

# Ajouter le chemin vers les modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

# Imports des modules refactorisés
from quiz_generator import QuizGenerator
from poker_constants import ALL_POKER_HANDS
from conflict_detector import detect_context_conflicts

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

app = Flask(__name__)

# Variable globale pour le nombre d'orphelins
ORPHAN_COUNT = 0


# ============================================
# UTILITAIRES
# ============================================

def generate_human_title_and_slug(table_format, hero_position, primary_action, action_sequence, stack_depth):
    """
    Génère le titre humain et le slug pour un contexte

    Args:
        table_format: Format de table (6max, 9max, etc.)
        hero_position: Position du héros (BTN, CO, etc.)
        primary_action: Action principale (open, defense, squeeze, vs_limpers)
        action_sequence: Dict contenant opener, callers, limpers, etc.
        stack_depth: Profondeur de stack (100bb, etc.)

    Returns:
        tuple: (human_title, slug)
    """
    # HUMAN TITLE
    if primary_action == 'open':
        action_text = 'Open'
    elif primary_action == 'defense':
        if action_sequence and action_sequence.get('opener'):
            opener = action_sequence['opener']
            action_text = f'Défense vs {opener} open'
        else:
            action_text = 'Défense'
    elif primary_action == 'squeeze':
        opener = action_sequence.get('opener') if action_sequence else None
        callers = action_sequence.get('callers', []) if action_sequence else []

        if opener and callers:
            callers_text = ' + '.join(callers)
            action_text = f'Squeeze vs {opener} open + {callers_text} call'
        elif opener:
            action_text = f'Squeeze vs {opener} open'
        else:
            action_text = 'Squeeze'
    elif primary_action == 'vs_limpers':
        limpers_count = action_sequence.get('limpers_count') if action_sequence else None
        limpers = action_sequence.get('limpers', []) if action_sequence else []

        if limpers_count:
            action_text = f'Vs {limpers_count} limper(s)'
        elif limpers:
            limpers_text = ' + '.join(limpers)
            action_text = f'Vs {limpers_text} limp'
        else:
            action_text = 'Vs limpers'
    else:
        action_text = primary_action.capitalize()

    human_title = f"{table_format} · {hero_position} · {action_text} · {stack_depth}"

    # SLUG
    if primary_action == 'open':
        ctx_key = 'open'
    elif primary_action == 'defense':
        opener = action_sequence.get('opener') if action_sequence else None
        if opener:
            ctx_key = f'defense-vs-{opener.lower()}'
        else:
            ctx_key = 'defense'
    elif primary_action == 'squeeze':
        opener = action_sequence.get('opener') if action_sequence else None
        callers = action_sequence.get('callers', []) if action_sequence else []

        positions = [opener] + callers if opener else callers
        positions = [p for p in positions if p]

        if positions:
            ctx_key = f'squeeze-{"-".join([p.lower() for p in positions])}'
        else:
            ctx_key = 'squeeze'
    elif primary_action == 'vs_limpers':
        limpers_count = action_sequence.get('limpers_count') if action_sequence else None
        limpers = action_sequence.get('limpers', []) if action_sequence else []

        if limpers_count:
            ctx_key = f'vs-{limpers_count}limpers'
        elif limpers:
            ctx_key = f'vs-limpers-{"-".join([l.lower() for l in limpers])}'
        else:
            ctx_key = 'vs-limpers'
    else:
        ctx_key = primary_action.replace(' ', '-').lower()

    slug = f"nlhe-{table_format.lower()}-{hero_position.lower()}-{ctx_key}-{stack_depth.lower()}"
    slug = slug.replace(' ', '').replace('+', '')  # Nettoyer

    return human_title, slug


def get_db_connection():
    """Retourne une connexion à la base de données"""
    db_path = Path(__file__).parent.parent / "data" / "poker_trainer.db"
    if not db_path.exists():
        return None
    return sqlite3.connect(db_path)


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
            print(f"⚠️  {orphan_count} fichier(s) JSON manquant(s) détectés")
            print(f"   → Accédez à http://localhost:5000/orphans pour les gérer")

        return orphan_count

    except Exception as e:
        print(f"[ORPHANS] Erreur check: {e}")
        return 0


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
            print("[JSON] ✗ Connexion DB impossible")
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
            print("[JSON] ✗ Fichier source non trouvé en DB")
            return False, "Fichier source non trouvé"

        file_path_relative = result[0]
        project_root = Path(__file__).parent.parent
        file_path = project_root / file_path_relative

        print(f"[JSON] Chemin fichier: {file_path}")
        print(f"[JSON] Fichier existe: {file_path.exists()}")

        if not file_path.exists():
            conn.close()
            print(f"[JSON] ✗ Fichier introuvable: {file_path}")
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
        print(f"[JSON] ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Erreur mise à jour JSON: {str(e)}"


# ============================================
# ROUTES PRINCIPALES
# ============================================
@app.route('/cards/<path:filename>')
def cards_static(filename):
    return send_from_directory(CARDS_DIR, filename)


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
def get_validation_context(context_id):
    """Retourne les données d'un contexte pour validation"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Récupérer TOUTES les métadonnées
    cursor.execute("""
        SELECT 
            rc.id, rc.original_name, rc.display_name, rc.cleaned_name,
            rc.table_format, rc.hero_position, rc.vs_position, rc.primary_action,
            rc.action_sequence,
            rc.stack_depth, rc.game_type, rc.variant, rc.sizing, rc.stakes,
            rc.confidence_score, rc.needs_validation,
            rf.filename, rf.file_path
        FROM range_contexts rc
        LEFT JOIN range_files rf ON rc.file_id = rf.id
        WHERE rc.id = ?
    """, (context_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Contexte non trouvé'}), 404

    # Construire le contexte
    context = {
        'id': row[0],
        'original_name': row[1],
        'display_name': row[2],
        'cleaned_name': row[3],
        'table_format': row[4],
        'hero_position': row[5],
        'vs_position': row[6],
        'primary_action': row[7],
        'action_sequence': json.loads(row[8]) if row[8] else None,
        'stack_depth': row[9],
        'game_type': row[10],
        'variant': row[11],
        'sizing': row[12],
        'stakes': row[13],
        'confidence_score': row[14],
        'needs_validation': row[15],
        'filename': row[16],
        'file_path': row[17]
    }

    # 🆕 Générer human_title et slug avec la fonction helper
    if context['table_format'] and context['hero_position'] and context['primary_action']:
        context['human_title'], context['slug'] = generate_human_title_and_slug(
            context['table_format'],
            context['hero_position'],
            context['primary_action'],
            context['action_sequence'],
            context['stack_depth']
        )
    else:
        context['human_title'] = context['display_name'] or context['original_name']
        context['slug'] = context['cleaned_name'] or context['original_name']

    # Récupérer les ranges et leurs mains
    cursor.execute("""
        SELECT 
            r.id, r.range_key, r.name, r.color, r.label_canon,
            COUNT(DISTINCT rh.hand) as hand_count
        FROM ranges r
        LEFT JOIN range_hands rh ON r.id = rh.range_id
        WHERE r.context_id = ?
        GROUP BY r.id
        ORDER BY r.range_key
    """, (context_id,))

    ranges = []
    for r in cursor.fetchall():
        ranges.append({
            'id': r[0],
            'range_key': r[1],
            'name': r[2],
            'color': r[3],
            'label_canon': r[4],
            'hand_count': r[5]
        })

    context['ranges'] = ranges

    # Résumé des sous-ranges
    subranges_summary = {}
    for r in ranges:
        if r['range_key'] != '1' and r['label_canon']:
            label = r['label_canon']
            subranges_summary[label] = subranges_summary.get(label, 0) + 1

    context['subranges_summary'] = subranges_summary

    # Labels disponibles
    from poker_constants import AVAILABLE_LABELS
    context['available_labels'] = AVAILABLE_LABELS

    # Générer des warnings si nécessaire
    warnings = []

    if context['primary_action'] == 'defense' and len(ranges) == 1:
        warnings.append("Contexte DEFENSE sans sous-ranges détectés")

    if context['confidence_score'] < 60:
        warnings.append(f"Confiance de détection faible : {context['confidence_score']}%")

    context['warnings'] = warnings

    conn.close()
    return jsonify(context)


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
    try:
        stats = get_pipeline_stats()

        # Ajouter les stats d'import récents si nécessaire
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT filename, created_at 
                FROM range_files 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_imports = [
                {'filename': row[0], 'date': row[1]}
                for row in cursor.fetchall()
            ]
            conn.close()
        else:
            recent_imports = []

        return jsonify({
            'status': 'success',
            'stats': stats,
            'recent_imports': recent_imports
        })

    except Exception as e:
        print(f"Erreur api_dashboard_stats: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'stats': {
                'total_files': 0,
                'total_contexts': 0,
                'total_ranges': 0,
                'total_hands': 0
            }
        }), 500


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


# ============================================
# ROUTES QUIZ - CONFIGURATION ET GENERATION
# ============================================

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
    return render_template('quiz.html')


@app.route('/api/quiz/question', methods=['POST'])
def get_next_quiz_question():
    """Génère une seule question en évitant les doublons"""
    try:
        data = request.get_json()
        context_ids = data.get('context_ids', [])
        excluded = data.get('excluded', [])
        aggression = data.get('aggression', 'medium')  # 🎚️ Paramètre d'agressivité

        if not context_ids:
            return jsonify({'error': 'Aucun contexte fourni'}), 400

        # Convertir en set pour recherche O(1)
        excluded_set = {(q['hand'], q['context_id']) for q in excluded}

        print(f"[QUIZ] Génération question, {len(excluded)} déjà posées, contextes: {context_ids}")

        # Essayer de générer une question unique
        max_attempts = 100
        generator = QuizGenerator(aggression_level=aggression)  # 🎚️ Passer l'agressivité

        for attempt in range(max_attempts):
            context_id = random.choice(context_ids)
            print(f"[QUIZ] 🎲 Tentative {attempt + 1}: Contexte sélectionné = {context_id}")
            question = generator.generate_question(context_id)

            if not question:
                print(f"[QUIZ] ✗ Contexte {context_id} a échoué (question = None)")
                continue

            # Vérifier si déjà posée
            key = (question['hand'], question['context_id'])
            if key not in excluded_set:
                print(
                    f"[QUIZ] ✅ Question générée: {question['hand']} (context {context_id}) après {attempt + 1} tentatives")
                return jsonify({
                    'success': True,
                    'question': question
                })

        # Aucune question unique trouvée
        print(f"[QUIZ] ⚠️ Plus de questions uniques disponibles après {max_attempts} tentatives")
        return jsonify({
            'error': 'no_more_questions',
            'message': 'Toutes les questions disponibles ont été utilisées'
        }), 404

    except Exception as e:
        print(f"[QUIZ] ✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# 🆕 ROUTES GESTION DES CONFLITS ET VARIANTES
# ============================================

@app.route('/api/quiz/detect-conflicts', methods=['POST'])
def detect_conflicts():
    """
    Détecte les conflits entre contextes sélectionnés.

    Body JSON:
        {
            "context_ids": [1, 2, 3]
        }

    Returns JSON:
        {
            "has_conflicts": true,
            "conflicts": {
                "6max|UTG|100bb|open|GENERIC": {
                    "contexts": [
                        {"id": 1, "name": "UTG 100bb open range agressive"},
                        {"id": 2, "name": "UTG 100bb open range tight"}
                    ],
                    "conflicts_by_level": {
                        "0": {"AKo": {"1": "RAISE", "2": "CALL"}},
                        "1": {"AKs": {"1": "RAISE", "2": "CALL"}}
                    },
                    "total_conflicts": 2
                }
            }
        }
    """
    try:
        data = request.get_json()
        context_ids = data.get('context_ids', [])

        if not context_ids or len(context_ids) < 2:
            return jsonify({
                'has_conflicts': False,
                'conflicts': {}
            })

        # Détecter les conflits
        conflicts = detect_context_conflicts(context_ids)

        return jsonify({
            'has_conflicts': bool(conflicts),
            'conflicts': conflicts
        })

    except Exception as e:
        print(f"[API] Erreur détection conflits: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz_with_variants():
    """
    Génère un quiz avec support des variantes.
    🆕 Respecte le nombre de SOUS-QUESTIONS demandé (drill-down = N sous-questions)

    Body JSON:
        {
            "context_ids": [1, 2],
            "question_count": 10,
            "variants": {
                "1": "Fin de soirée",
                "2": "Début de session"
            }
        }

    Returns JSON:
        {
            "questions": [
                {
                    "type": "simple",
                    "context_id": 1,
                    "variant": "Fin de soirée",
                    "hand": "AKs",
                    "question": "...",
                    "options": [...],
                    "correct_answer": "RAISE"
                }
            ]
        }
    """
    try:
        data = request.get_json()
        context_ids = data.get('context_ids', [])
        question_count = data.get('question_count', 10)
        variants = data.get('variants', {})  # Dict {context_id: variant_text}
        aggression = data.get('aggression', 'medium')  # 🎚️ Paramètre d'agressivité

        if not context_ids:
            return jsonify({'error': 'Aucun contexte sélectionné'}), 400
        
        # 🎚️ Log du niveau d'agressivité
        print(f"[QUIZ GEN] 🎚️ Agressivité de la table: {aggression.upper()}")

        generator = QuizGenerator(aggression_level=aggression)  # 🎚️ Passer l'agressivité
        questions = []
        total_subquestions = 0  # 🆕 Compteur de sous-questions
        used_hands_by_context = {}  # 🔧 v4.3.7 : Tracker les mains PAR CONTEXTE
        max_attempts = question_count * 10  # Éviter boucle infinie
        attempts = 0

        # 🆕 Générer jusqu'à atteindre le nombre de sous-questions demandé
        while total_subquestions < question_count and attempts < max_attempts:
            attempts += 1

            # Choisir un contexte aléatoire
            context_id = random.choice(context_ids)
            
            # 🔧 v4.3.7 : Initialiser le set pour ce contexte si nécessaire
            if context_id not in used_hands_by_context:
                used_hands_by_context[context_id] = set()

            # 🔧 BUGFIX v4.3.5 : Forcer les questions simples quand il reste peu de place
            # Si on est proche de la limite, temporairement désactiver le drill_down
            # Les questions drill-down font généralement 2-3 étapes minimum
            remaining_slots = question_count - total_subquestions
            force_simple = False
            
            if remaining_slots <= 2:
                # Moins de 3 places : forcer question simple pour être sûr de remplir exactement
                force_simple = True
                original_can_drill = generator.drill_down_gen.can_generate_drill_down
                generator.drill_down_gen.can_generate_drill_down = lambda ranges: False
                print(f"[QUIZ GEN] 🎯 Reste {remaining_slots} place(s) → force question SIMPLE")
            
            # 🆕 v4.3.7 : Passer les mains déjà utilisées POUR CE CONTEXTE
            question = generator.generate_question(context_id, used_hands=used_hands_by_context[context_id])
            
            # Restaurer la fonction d'origine si modifiée
            if force_simple:
                generator.drill_down_gen.can_generate_drill_down = original_can_drill

            if question:
                # 🆕 v4.3.7 : Ajouter la main au tracker DU CONTEXTE
                if 'hand' in question:
                    used_hands_by_context[context_id].add(question['hand'])
                    total_used = sum(len(hands) for hands in used_hands_by_context.values())
                    print(f"[QUIZ GEN] 🎲 Main utilisée: {question['hand']} dans contexte {context_id} (total global: {total_used} mains)")
                
                # 🆕 Calculer combien de sous-questions cette question ajoute
                if question['type'] == 'drill_down':
                    subq_count = len(question['levels'])
                else:
                    subq_count = 1

                # 🆕 Vérifier si on peut ajouter cette question sans dépasser
                if total_subquestions + subq_count <= question_count:
                    # Ajouter la variante si elle existe
                    variant = variants.get(str(context_id))
                    if variant:
                        question['variant'] = variant

                    questions.append(question)
                    total_subquestions += subq_count
                    print(
                        f"[QUIZ GEN] Question ajoutée ({question['type']}), sous-questions: {total_subquestions}/{question_count}")
                else:
                    # Pas assez de place pour cette question drill-down
                    # Réessayer (normalement ne devrait plus arriver avec le fix)
                    print(
                        f"[QUIZ GEN] Question ignorée (trop longue), sous-questions actuelles: {total_subquestions}/{question_count}")
                    continue

        print(f"[QUIZ GEN] ✅ Quiz généré: {len(questions)} questions, {total_subquestions} sous-questions")

        return jsonify({
            'questions': questions
        })

    except Exception as e:
        print(f"[API] Erreur génération quiz: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/test-quiz')
def test_quiz():
    return render_template('test-quiz.html')

@app.route('/quiz-result')
def quiz_result():
    return render_template('quiz-result.html')
if __name__ == '__main__':
    ORPHAN_COUNT = check_orphans_on_startup()
    app.run(debug=True)