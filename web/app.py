from flask import Flask, render_template, jsonify, request
import subprocess
import os
import sys
import sqlite3
import json
from pathlib import Path
import re

app = Flask(__name__)

# Ajouter le chemin vers les modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'modules'))

# Importer context_validator si disponible

try:
    from context_validator import ContextValidator
    validator = ContextValidator("../data/poker_trainer.db")
    VALIDATOR_AVAILABLE = True
    print(f"✓ Context validator chargé - VALIDATOR_AVAILABLE = {VALIDATOR_AVAILABLE}")
except (ImportError, FileNotFoundError) as e:
    print(f"✗ ATTENTION: context_validator non disponible: {e}")
    VALIDATOR_AVAILABLE = False
except Exception as e:
    print(f"✗ ERREUR inattendue lors du chargement validator: {e}")
    import traceback
    traceback.print_exc()
    VALIDATOR_AVAILABLE = False


# ============================================
# UTILITAIRES
# ============================================

def get_db_connection():
    """Retourne une connexion à la base de données"""
    db_path = Path(__file__).parent.parent / "data" / "poker_trainer.db"
    if not db_path.exists():
        return None
    return sqlite3.connect(db_path)


# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def dashboard():
    """Page principale du dashboard"""
    return render_template('dashboard.html')


# ============================================
# ROUTES DE VALIDATION
# ============================================

@app.route('/validate')
def validate_page():
    """Page de validation d'un contexte."""
    print(f"=== Route /validate appelée - VALIDATOR_AVAILABLE = {VALIDATOR_AVAILABLE}")
    if not VALIDATOR_AVAILABLE:
        return "<h1>Erreur</h1><p>Module de validation non disponible</p>", 500
    return render_template('validate_context.html')


@app.route('/api/validation/context/<int:context_id>')
def get_context_for_validation(context_id):
    """Récupère les informations d'un contexte pour validation."""
    print(f"=== DEBUG: VALIDATOR_AVAILABLE = {VALIDATOR_AVAILABLE}")

    if not VALIDATOR_AVAILABLE:
        print("=== DEBUG: Validator non disponible")
        return jsonify({'error': 'Module de validation non disponible'}), 500

    try:
        print(f"=== DEBUG: Appel validator.get_context_for_validation({context_id})")
        context = validator.get_context_for_validation(context_id)
        print(f"=== DEBUG: Contexte récupéré: {context is not None}")

        if not context:
            return jsonify({'error': 'Contexte non trouvé'}), 404
        return jsonify(context)
    except Exception as e:
        print(f"=== DEBUG: Exception levée: {e}")
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
    """Valide et met à jour les métadonnées d'un contexte."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        metadata = request.get_json()
        if not metadata:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Extraire le flag update_json
        update_json = metadata.pop('update_json', False)

        # Valider et mettre à jour la base
        success, message = validator.validate_and_update(context_id, metadata)

        if not success:
            return jsonify({'success': False, 'message': message})

        # Si demandé, mettre à jour le JSON
        json_updated = False
        json_message = ""
        if update_json:
            json_success, json_message = validator.update_json_file(context_id, metadata)
            json_updated = json_success

            if not json_success and "CONFLICT" in json_message:
                # Retourner un conflit pour demander confirmation
                return jsonify({
                    'success': True,
                    'message': message,
                    'json_conflict': True,
                    'json_message': json_message
                })

        return jsonify({
            'success': True,
            'message': message,
            'json_updated': json_updated,
            'json_message': json_message if update_json else None
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur : {str(e)}'}), 500


@app.route('/api/validation/ignore/<int:context_id>', methods=['POST'])
def ignore_context(context_id):
    """Marque un contexte comme non exploitable."""
    if not VALIDATOR_AVAILABLE:
        return jsonify({'success': False, 'message': 'Module non disponible'}), 500

    try:
        success = validator.mark_as_non_exploitable(
            context_id,
            reason="Marqué manuellement comme non exploitable"
        )
        return jsonify({
            'success': success,
            'message': 'Contexte marqué comme non exploitable' if success else 'Erreur'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/validation/stats')
def get_validation_stats():
    """Récupère des statistiques sur les contextes à valider."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'total_pending': 0, 'by_confidence': {}})

        cursor = conn.cursor()

        # Compter les contextes nécessitant validation
        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE needs_validation = 1")
        total = cursor.fetchone()[0]

        # Grouper par niveau de confiance
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

        # Stats de base
        cursor.execute("SELECT COUNT(*) FROM range_files")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_contexts")
        total_contexts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ranges")
        total_ranges = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM range_hands")
        total_hands = cursor.fetchone()[0]

        # Compter par statut
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

        # Compter les enregistrements
        stats = {}
        for table in ['range_files', 'range_contexts', 'ranges', 'range_hands']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats[table] = 0

        # Exemples
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
            # Déterminer le statut
            if row[6]:  # needs_validation
                context_status = 'needs_validation'
            elif row[7]:  # quiz_ready
                context_status = 'quiz_ready'
            elif row[8]:  # error_message
                context_status = 'error'
            else:
                context_status = 'unknown'

            contexts.append({
                'id': row[0],
                'name': row[1] or row[2] or 'Sans nom',  # display_name ou original_name
                'confidence': (row[3] or 0) / 100.0,  # confidence_score en 0-1
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

        # Compter les contextes prêts pour quiz
        cursor.execute("SELECT COUNT(*) FROM range_contexts WHERE quiz_ready = 1")
        ready_count = cursor.fetchone()[0]

        # Compter le total
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


@app.route('/quiz')
def quiz_page():
    """Page d'interface quiz (à implémenter)"""
    return "<h1>Interface Quiz</h1><p>En développement...</p>"


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
    cursor.execute("PRAGMA table_info(range_contexts)")
    columns = cursor.fetchall()

    result = "<h1>Structure de range_contexts</h1><table border='1' cellpadding='10'>"
    result += "<tr><th>ID</th><th>Nom</th><th>Type</th><th>NOT NULL</th><th>Default</th></tr>"

    for col in columns:
        result += f"<tr><td>{col[0]}</td><td><strong>{col[1]}</strong></td><td>{col[2]}</td><td>{'Oui' if col[3] else 'Non'}</td><td>{col[4]}</td></tr>"

    result += "</table>"
    conn.close()
    return result


@app.route('/debug_all_contexts')
def debug_all_contexts():
    """Debug : affiche tous les contextes"""
    conn = get_db_connection()
    if not conn:
        return "<h1>Base de données non trouvée</h1>"

    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, display_name, original_name, confidence_score,
            hero_position, primary_action, table_format,
            needs_validation, quiz_ready, error_message
        FROM range_contexts
    """)
    rows = cursor.fetchall()

    result = "<h1>Tous les contextes</h1>"
    for row in rows:
        status_icon = '🟢' if row[8] else ('🟡' if row[7] else '⚪')

        result += f"""
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
            <h3>{status_icon} #{row[0]} - {row[1] or row[2]}</h3>
            <p><strong>Confidence:</strong> {row[3] or 0}%</p>
            <p><strong>Position:</strong> {row[4] or 'N/A'}</p>
            <p><strong>Action:</strong> {row[5] or 'N/A'}</p>
            <p><strong>Format:</strong> {row[6] or 'N/A'}</p>
            <p><strong>Needs validation:</strong> {row[7]}</p>
            <p><strong>Quiz ready:</strong> {row[8]}</p>
            {f'<p style="color: red;"><strong>Error:</strong> {row[9]}</p>' if row[9] else ''}
        </div>
        """

    conn.close()
    return result


@app.route('/debug_metadata')
def debug_metadata():
    """Debug : métadonnées détaillées"""
    conn = get_db_connection()
    if not conn:
        return "<h1>Base de données non trouvée</h1>"

    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, display_name, original_name,
            table_format, hero_position, vs_position, primary_action,
            game_type, variant, stack_depth, stakes, sizing,
            confidence_score, needs_validation, quiz_ready, error_message
        FROM range_contexts 
        LIMIT 5
    """)
    rows = cursor.fetchall()

    result = "<h1>Métadonnées détaillées (5 premiers)</h1>"
    for row in rows:
        result += f"""
        <div style="border: 2px solid #667eea; padding: 15px; margin: 15px 0; border-radius: 10px;">
            <h2>#{row[0]} - {row[1] or row[2]}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 5px;"><strong>Format table:</strong></td><td>{row[3] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Position héros:</strong></td><td>{row[4] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Position vs:</strong></td><td>{row[5] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Action:</strong></td><td>{row[6] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Game type:</strong></td><td>{row[7] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Variant:</strong></td><td>{row[8] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Stack depth:</strong></td><td>{row[9] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Stakes:</strong></td><td>{row[10] or 'N/A'}</td></tr>
                <tr><td style="padding: 5px;"><strong>Sizing:</strong></td><td>{row[11] or 'N/A'}</td></tr>
                <tr style="background: #f0f0f0;"><td style="padding: 5px;"><strong>Confidence:</strong></td><td>{row[12] or 0}%</td></tr>
                <tr style="background: #f0f0f0;"><td style="padding: 5px;"><strong>Needs validation:</strong></td><td>{row[13]}</td></tr>
                <tr style="background: #f0f0f0;"><td style="padding: 5px;"><strong>Quiz ready:</strong></td><td>{row[14]}</td></tr>
                {f'<tr style="background: #ffe0e0;"><td style="padding: 5px;"><strong>Error:</strong></td><td>{row[15]}</td></tr>' if row[15] else ''}
            </table>
        </div>
        """

    conn.close()
    return result


if __name__ == '__main__':
    app.run(debug=True)