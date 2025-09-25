#!/usr/bin/env python3
"""
Interface Web pour Poker Training - Version fonctionnelle
"""

import os
import json
import sqlite3
import subprocess
import threading
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# Configuration des chemins
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'poker-training-secret'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Chemins
PROJECT_ROOT = parent_dir
DB_PATH = PROJECT_ROOT / "data" / "poker_trainer.db"
RANGES_DIR = PROJECT_ROOT / "data" / "ranges"
UPLOAD_FOLDER = RANGES_DIR

# Créer dossiers
RANGES_DIR.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

print(f"📂 Projet: {PROJECT_ROOT}")
print(f"📊 Base: {DB_PATH} (existe: {DB_PATH.exists()})")
print(f"📁 Ranges: {RANGES_DIR}")

# Stockage des résultats d'import
import_results = {}


# ============================================================================
# ROUTES PRINCIPALES
# ============================================================================

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/import')
def import_page():
    return render_template('import.html')


@app.route('/enrich')
def enrich_page():
    return render_template('enrich.html')


@app.route('/quiz')
def quiz_page():
    return render_template('quiz.html')


# ============================================================================
# API DASHBOARD
# ============================================================================

@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    """Stats dashboard - Version testée et fonctionnelle"""
    try:
        stats = {
            'total_files': 0,
            'total_contexts': 0,
            'total_ranges': 0,
            'total_hands': 0,
            'recent_imports': [],
            'contexts_by_confidence': {'high': 0, 'medium': 0, 'low': 0},
        }

        if not DB_PATH.exists():
            return jsonify(stats)

        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Stats simples
            cursor.execute("SELECT COUNT(*) FROM range_files WHERE status = 'imported'")
            stats['total_files'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM range_contexts")
            stats['total_contexts'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ranges")
            stats['total_ranges'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM range_hands")
            stats['total_hands'] = cursor.fetchone()[0]

            # Imports récents
            cursor.execute("""
                SELECT rf.filename, rf.imported_at, rc.name, rc.confidence
                FROM range_files rf
                LEFT JOIN range_contexts rc ON rf.id = rc.file_id
                WHERE rf.status = 'imported'
                ORDER BY rf.imported_at DESC
                LIMIT 5
            """)

            recent_imports = []
            for row in cursor.fetchall():
                recent_imports.append({
                    'filename': row[0],
                    'imported_at': row[1],
                    'context_name': row[2] or 'N/A',
                    'confidence': float(row[3]) if row[3] else 0.0
                })

            stats['recent_imports'] = recent_imports

            # Distribution confiance
            cursor.execute("SELECT confidence FROM range_contexts WHERE confidence IS NOT NULL")
            confidences = cursor.fetchall()

            high = medium = low = 0
            for (conf,) in confidences:
                if conf >= 0.8:
                    high += 1
                elif conf >= 0.5:
                    medium += 1
                else:
                    low += 1

            stats['contexts_by_confidence'] = {'high': high, 'medium': medium, 'low': low}

        return jsonify(stats)

    except Exception as e:
        app.logger.error(f"Erreur stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/contexts')
def get_contexts_list():
    """Contexts dashboard - Version avec comptage optimisé"""
    try:
        if not DB_PATH.exists():
            return jsonify([])

        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()

            # Requête optimisée avec comptage en une fois
            cursor.execute("""
                SELECT 
                    rc.id, rc.name, rc.confidence, rc.parsed_metadata,
                    rf.filename, rf.imported_at,
                    COUNT(DISTINCT r.id) as ranges_count,
                    COUNT(rh.id) as hands_count
                FROM range_contexts rc
                LEFT JOIN range_files rf ON rc.file_id = rf.id
                LEFT JOIN ranges r ON rc.id = r.context_id
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                GROUP BY rc.id, rc.name, rc.confidence, rc.parsed_metadata, rf.filename, rf.imported_at
                ORDER BY rf.imported_at DESC
                LIMIT 15
            """)

            contexts = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[3]) if row[3] else {}
                except:
                    metadata = {}

                contexts.append({
                    'id': row[0],
                    'name': row[1],
                    'confidence': float(row[2]) if row[2] else 0.0,
                    'filename': row[4],
                    'imported_at': row[5],
                    'ranges_count': row[6] or 0,
                    'hands_count': row[7] or 0,
                    'hero_position': metadata.get('hero_position'),
                    'primary_action': metadata.get('primary_action'),
                    'vs_position': metadata.get('vs_position')
                })

            app.logger.info(f"📋 Loaded {len(contexts)} contexts avec comptages")
            return jsonify(contexts)

    except Exception as e:
        app.logger.error(f"Erreur contexts optimisé: {e}")

        # Fallback : version simple sans comptage si la requête complexe échoue
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        rc.id, rc.name, rc.confidence, rc.parsed_metadata,
                        rf.filename, rf.imported_at
                    FROM range_contexts rc
                    LEFT JOIN range_files rf ON rc.file_id = rf.id
                    ORDER BY rf.imported_at DESC
                    LIMIT 10
                """)

                contexts = []
                for row in cursor.fetchall():
                    try:
                        metadata = json.loads(row[3]) if row[3] else {}
                    except:
                        metadata = {}

                    contexts.append({
                        'id': row[0],
                        'name': row[1],
                        'confidence': float(row[2]) if row[2] else 0.0,
                        'filename': row[4],
                        'imported_at': row[5],
                        'ranges_count': '?',
                        'hands_count': '?',
                        'hero_position': metadata.get('hero_position'),
                        'primary_action': metadata.get('primary_action'),
                        'vs_position': metadata.get('vs_position')
                    })

                app.logger.info(f"📋 Fallback: loaded {len(contexts)} contexts sans comptages")
                return jsonify(contexts)

        except Exception as fallback_error:
            app.logger.error(f"Erreur fallback contexts: {fallback_error}")
            return jsonify({'error': str(fallback_error)}), 500


# ============================================================================
# API IMPORT
# ============================================================================

@app.route('/api/import/files')
def get_import_files():
    """Liste les fichiers pour import"""
    try:
        files_info = []

        for file_path in RANGES_DIR.glob("*.json"):
            file_info = {
                'name': file_path.name,
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'status': 'pending'
            }

            # Vérifier si déjà importé
            if DB_PATH.exists():
                with sqlite3.connect(str(DB_PATH)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT status, imported_at FROM range_files WHERE filename = ?",
                        (file_path.name,)
                    )
                    result = cursor.fetchone()
                    if result:
                        file_info['status'] = result[0]
                        file_info['imported_at'] = result[1]

            files_info.append(file_info)

        return jsonify(files_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/upload', methods=['POST'])
def upload_file():
    """Upload d'un fichier"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400

        if file and file.filename.endswith('.json'):
            filename = secure_filename(file.filename)
            filepath = RANGES_DIR / filename
            file.save(str(filepath))

            return jsonify({
                'success': True,
                'filename': filename,
                'message': f'Fichier {filename} uploadé avec succès'
            })
        else:
            return jsonify({'error': 'Seuls les fichiers JSON sont acceptés'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/run', methods=['POST'])
def run_import():
    """Lance l'import"""
    try:
        data = request.get_json() or {}
        filename = data.get('filename')

        # Trouver le script
        script_path = PROJECT_ROOT / "poker-training.py"
        if not script_path.exists():
            script_path = PROJECT_ROOT / "poker_training.py"

        if not script_path.exists():
            return jsonify({'error': 'Script poker-training.py non trouvé'}), 404

        cmd = ['python3', script_path.name]
        job_id = filename or 'all'

        app.logger.info(f"🚀 Commande import: {cmd}")
        app.logger.info(f"📂 Working directory: {PROJECT_ROOT}")
        app.logger.info(f"📄 Script existe: {script_path.exists()}")

        def run_import_process():
            try:
                app.logger.info(f"📥 Début subprocess import")
                result = subprocess.run(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                app.logger.info(f"✅ Import terminé - Code: {result.returncode}")
                app.logger.info(f"📝 Stdout: {result.stdout[:500]}...")
                if result.stderr:
                    app.logger.warning(f"⚠️ Stderr: {result.stderr[:500]}...")

                import_results[job_id] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'completed_at': datetime.now().isoformat()
                }

            except subprocess.TimeoutExpired:
                app.logger.error("⏰ Import timeout")
                import_results[job_id] = {
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Import timeout (> 5 minutes)',
                    'completed_at': datetime.now().isoformat()
                }
            except Exception as e:
                app.logger.error(f"❌ Erreur subprocess: {e}")
                import_results[job_id] = {
                    'returncode': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'completed_at': datetime.now().isoformat()
                }

        # Marquer comme en cours
        import_results[job_id] = {
            'returncode': None,
            'stdout': '',
            'stderr': '',
            'started_at': datetime.now().isoformat()
        }

        # Lancer en arrière-plan
        thread = threading.Thread(target=run_import_process)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Import lancé - script simple sans confirmations',
            'job_id': job_id
        })

    except Exception as e:
        app.logger.error(f"❌ Erreur lancement import: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/status/<job_id>')
def get_import_status(job_id):
    """Statut d'un import"""
    try:
        if job_id not in import_results:
            return jsonify({'error': 'Job non trouvé'}), 404

        result = import_results[job_id]

        if result['returncode'] is None:
            return jsonify({
                'status': 'running',
                'started_at': result['started_at']
            })
        else:
            return jsonify({
                'status': 'completed',
                'success': result['returncode'] == 0,
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'completed_at': result['completed_at']
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ENRICHISSEMENT
# ============================================================================

@app.route('/api/enrich/contexts')
def get_enrich_contexts():
    """Liste les contextes pour l'enrichissement"""
    try:
        if not DB_PATH.exists():
            return jsonify([])

        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    rc.id, rc.name, rc.confidence, rc.parsed_metadata,
                    rf.filename, rf.imported_at,
                    COUNT(DISTINCT r.id) as ranges_count,
                    COUNT(rh.id) as hands_count
                FROM range_contexts rc
                LEFT JOIN range_files rf ON rc.file_id = rf.id
                LEFT JOIN ranges r ON rc.id = r.context_id
                LEFT JOIN range_hands rh ON r.id = rh.range_id
                GROUP BY rc.id, rc.name, rc.confidence, rc.parsed_metadata, rf.filename, rf.imported_at
                ORDER BY rc.confidence ASC, rf.imported_at DESC
            """)

            contexts = []
            for row in cursor.fetchall():
                try:
                    parsed_metadata = json.loads(row['parsed_metadata']) if row['parsed_metadata'] else {}
                except:
                    parsed_metadata = {}

                contexts.append({
                    'id': row['id'],
                    'name': row['name'],
                    'confidence': float(row['confidence']) if row['confidence'] else 0.0,
                    'filename': row['filename'],
                    'imported_at': row['imported_at'],
                    'ranges_count': row['ranges_count'] or 0,
                    'hands_count': row['hands_count'] or 0,
                    'parsed_metadata': parsed_metadata
                })

            return jsonify(contexts)

    except Exception as e:
        app.logger.error(f"Erreur enrich contexts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/enrich/run', methods=['POST'])
def run_enrichment():
    """Lance l'enrichissement - Version simple"""
    try:
        data = request.get_json() or {}
        context_ids = data.get('context_ids', [])

        # Trouver le script d'enrichissement
        script_path = PROJECT_ROOT / "enrich_ranges.py"
        if not script_path.exists():
            return jsonify({'error': 'Script enrich_ranges.py non trouvé'}), 404

        # Pour l'instant, lancer le script tel quel sans paramètres
        cmd = ['python3', script_path.name]
        job_id = f"enrich_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Environnement avec mode web
        env = os.environ.copy()
        env['POKER_WEB_MODE'] = '1'

        def run_enrichment_process():
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minutes timeout
                    env=env
                )

                import_results[job_id] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'completed_at': datetime.now().isoformat()
                }

            except subprocess.TimeoutExpired:
                import_results[job_id] = {
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Enrichissement timeout (> 10 minutes)',
                    'completed_at': datetime.now().isoformat()
                }
            except Exception as e:
                import_results[job_id] = {
                    'returncode': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'completed_at': datetime.now().isoformat()
                }

        # Marquer comme en cours
        import_results[job_id] = {
            'returncode': None,
            'stdout': '',
            'stderr': '',
            'started_at': datetime.now().isoformat(),
            'context_ids': context_ids,
            'total_contexts': len(context_ids) if context_ids else 0
        }

        # Lancer en arrière-plan
        thread = threading.Thread(target=run_enrichment_process)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'Enrichissement lancé (script standard)',
            'job_id': job_id,
            'note': 'Le script enrich_ranges.py sera exécuté normalement'
        })

    except Exception as e:
        app.logger.error(f"Erreur lancement enrichissement: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/enrich/status/<job_id>')
def get_enrichment_status(job_id):
    """Récupère le statut d'un enrichissement en cours"""
    try:
        if job_id not in import_results:
            return jsonify({'error': 'Job non trouvé'}), 404

        result = import_results[job_id]

        if result['returncode'] is None:
            # En cours - calculer un progrès approximatif
            started_at = datetime.fromisoformat(result['started_at'])
            elapsed = (datetime.now() - started_at).total_seconds()
            total_contexts = result.get('total_contexts', 1)

            # Estimation : 30 secondes par contexte en moyenne
            estimated_duration = total_contexts * 30
            progress = min(95, (elapsed / estimated_duration) * 100) if estimated_duration > 0 else 0

            return jsonify({
                'status': 'running',
                'progress': progress,
                'message': f'Enrichissement en cours...',
                'started_at': result['started_at'],
                'elapsed_seconds': int(elapsed)
            })
        else:
            # Terminé
            return jsonify({
                'status': 'completed',
                'success': result['returncode'] == 0,
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'completed_at': result['completed_at'],
                'progress': 100
            })

    except Exception as e:
        app.logger.error(f"Erreur status enrichissement: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ROUTES DE DEBUG
# ============================================================================

@app.route('/api/debug/db')
def debug_db():
    """Debug base de données"""
    try:
        result = {
            'db_path': str(DB_PATH),
            'db_exists': DB_PATH.exists(),
            'tables': [],
            'data': {}
        }

        if not DB_PATH.exists():
            return jsonify(result)

        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            result['tables'] = tables

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result['data'][table] = cursor.fetchone()['count']

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/test/scripts')
def test_scripts():
    """Test des scripts"""
    results = {}

    try:
        import poker_training
        results['poker_training'] = {'status': 'success', 'message': 'Import réussi'}
    except ImportError as e:
        results['poker_training'] = {'status': 'error', 'message': f'Erreur: {e}'}

    for script_name in ['enrich_ranges', 'questions']:
        try:
            __import__(script_name)
            results[script_name] = {'status': 'success', 'message': 'Import réussi'}
        except ImportError as e:
            results[script_name] = {'status': 'error', 'message': f'Erreur: {e}'}

    try:
        if DB_PATH.exists():
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                results['database'] = {
                    'status': 'success',
                    'message': f'Base trouvée, {len(tables)} tables',
                    'tables': [t[0] for t in tables]
                }
        else:
            results['database'] = {'status': 'warning', 'message': 'Base non trouvée'}
    except Exception as e:
        results['database'] = {'status': 'error', 'message': f'Erreur: {e}'}

    return jsonify(results)


# ============================================================================
# FICHIERS STATIQUES
# ============================================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import logging

    logging.basicConfig(level=logging.INFO)

    print("🃏 POKER TRAINING WEB - Version Fonctionnelle")
    print("=" * 60)
    print(f"🌐 Dashboard: http://localhost:5000")
    print(f"📥 Import: http://localhost:5000/import")
    print(f"✨ Enrichir: http://localhost:5000/enrich")
    print(f"🧪 Test: http://localhost:5000/api/test/scripts")
    print("=" * 60)

    app.run(debug=True, host='127.0.0.1', port=5000)