#!/usr/bin/env python3
"""
Interface web pour le pipeline intégré v2.0
Architecture: poker-training/web/app_integrated.py
S'adapte aux modules existants et utilise le nouveau pipeline
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
from pathlib import Path
import sys
from datetime import datetime

# Ajout du répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

# Import du pipeline intégré
try:
    from integrated_import_v2 import IntegratedImportPipeline, ContextStatus, ValidationResult

    PIPELINE_AVAILABLE = True
except ImportError:
    print("⚠️  Pipeline intégré non trouvé, mode démo")
    PIPELINE_AVAILABLE = False


    # Mock classes pour la démo
    class MockValidationResult:
        def __init__(self, status, score, compatible, issues):
            self.status = type('obj', (object,), {'value': status})()
            self.compatibility_score = score
            self.is_compatible = compatible
            self.issues = issues


    class MockPipeline:
        def process_directory(self, path="data/ranges/"):
            return {
                'example_6max_BTN_vs_BB.json': MockValidationResult('compatible', 0.92, True, []),
                'example_CO_open.json': MockValidationResult('compatible', 0.85, True, []),
                'problematic_range.json': MockValidationResult('inconsistent', 0.45, False,
                                                               ['Overlaps détectés', 'Position manquante'])
            }

        def get_pipeline_summary(self):
            return {
                'pipeline_version': '2.0_demo',
                'modules_available': False,
                'total_imports': 3,
                'successful_imports': 3,
                'compatibility_stats': {'compatible': 2, 'inconsistent': 1},
                'avg_compatibility_score': 0.74,
                'ready_for_questions': 2,
                'database_path': 'data/poker_trainer.db'
            }


    IntegratedImportPipeline = MockPipeline

app = Flask(__name__)
app.secret_key = 'poker_training_integrated_2025'

# Instance globale du pipeline
pipeline = IntegratedImportPipeline()


@app.route('/')
def dashboard():
    """Dashboard principal avec vue d'ensemble du pipeline intégré"""
    try:
        # Récupération du résumé du pipeline
        summary = pipeline.get_pipeline_summary()

        # Statistiques pour l'affichage
        stats = {
            'pipeline_version': summary.get('pipeline_version', '2.0'),
            'modules_status': 'Existants' if summary.get('modules_available', False) else 'Fallback',
            'total_imports': summary.get('total_imports', 0),
            'successful_imports': summary.get('successful_imports', 0),
            'success_rate': (summary.get('successful_imports', 0) / max(summary.get('total_imports', 1), 1) * 100),
            'ready_for_questions': summary.get('ready_for_questions', 0),
            'avg_score': summary.get('avg_compatibility_score', 0),
            'compatibility_breakdown': summary.get('compatibility_stats', {})
        }

        # Messages d'état
        if stats['ready_for_questions'] > 0:
            flash(f"✅ {stats['ready_for_questions']} contextes prêts pour l'entraînement", 'success')
        else:
            flash("⚠️ Aucun contexte compatible trouvé. Importez des ranges d'abord.", 'warning')

        return render_template('dashboard_integrated.html', stats=stats)

    except Exception as e:
        app.logger.error(f"Erreur dashboard: {e}")
        flash(f"Erreur: {e}", 'error')
        return render_template('error.html', error=str(e))


@app.route('/import')
def import_page():
    """Page d'import avec pipeline intégré"""
    return render_template('import_integrated.html')


@app.route('/api/run_import', methods=['POST'])
def api_run_import():
    """API: Exécuter l'import intégré"""
    try:
        # Paramètres optionnels
        data = request.get_json() or {}
        directory_path = data.get('directory', 'data/ranges/')

        # Exécution du pipeline
        results = pipeline.process_directory(directory_path)

        # Formatage des résultats pour l'API
        formatted_results = []
        for filename, result in results.items():
            formatted_results.append({
                'filename': filename,
                'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                'compatibility_score': result.compatibility_score,
                'is_compatible': result.is_compatible,
                'issues': result.issues,
                'status_class': 'success' if result.is_compatible else 'danger',
                'status_icon': '✅' if result.is_compatible else '❌'
            })

        # Statistiques globales
        total_files = len(formatted_results)
        compatible_files = sum(1 for r in formatted_results if r['is_compatible'])

        return jsonify({
            'success': True,
            'results': formatted_results,
            'summary': {
                'total_files': total_files,
                'compatible_files': compatible_files,
                'success_rate': (compatible_files / total_files * 100) if total_files > 0 else 0,
                'pipeline_version': '2.0_integrated'
            }
        })

    except Exception as e:
        app.logger.error(f"Erreur API import: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/contexts')
def contexts_page():
    """Page d'overview des contextes avec leurs statuts"""
    try:
        # Import récent pour avoir les dernières données
        results = pipeline.process_directory()

        # Regroupement par statut
        contexts_by_status = {
            'compatible': [],
            'incomplete': [],
            'inconsistent': [],
            'invalid': []
        }

        for filename, result in results.items():
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            contexts_by_status.setdefault(status, []).append({
                'filename': filename,
                'score': result.compatibility_score,
                'issues': result.issues
            })

        return render_template('contexts.html', contexts=contexts_by_status)

    except Exception as e:
        app.logger.error(f"Erreur page contextes: {e}")
        flash(f"Erreur: {e}", 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/context_details/<filename>')
def api_context_details(filename):
    """API: Détails d'un contexte spécifique"""
    try:
        # Pour l'instant, simulation des détails
        # Dans la vraie implémentation, récupérer depuis la base de données

        mock_details = {
            'filename': filename,
            'context': {
                'hero_position': 'BTN',
                'villain_position': 'BB',
                'action': 'defense',
                'table_size': 6
            },
            'ranges': {
                'call': {'color': '#4CAF50', 'hands_count': 45},
                'fold': {'color': '#F44336', 'hands_count': 89},
                '3bet_value': {'color': '#FF9800', 'hands_count': 12},
                '3bet_bluff': {'color': '#E91E63', 'hands_count': 8}
            },
            'metadata': {
                'total_hands': 154,
                'complexity_score': 0.75,
                'standardization_applied': True,
                'enrichment_version': '4.0'
            }
        }

        return jsonify(mock_details)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/prepare_questions')
def prepare_questions_page():
    """Page de préparation pour le futur module Questions"""
    try:
        # Récupération des contextes compatibles
        results = pipeline.process_directory()
        compatible_contexts = [
            filename for filename, result in results.items()
            if result.is_compatible
        ]

        return render_template('prepare_questions.html',
                               compatible_contexts=compatible_contexts,
                               total_compatible=len(compatible_contexts))

    except Exception as e:
        app.logger.error(f"Erreur page préparation: {e}")
        flash(f"Erreur: {e}", 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/validate_for_questions', methods=['POST'])
def api_validate_for_questions():
    """API: Validation spécifique pour le module Questions (à venir)"""
    try:
        data = request.get_json() or {}
        selected_contexts = data.get('contexts', [])

        # Simulation de validation pour Questions
        validation_results = []
        for context in selected_contexts:
            # Dans la vraie implémentation, validation approfondie
            validation_results.append({
                'context': context,
                'valid_for_questions': True,
                'question_types_supported': ['hand_action', 'frequency', 'range_comparison'],
                'estimated_questions': 25,
                'difficulty_levels': [1, 2, 3]
            })

        return jsonify({
            'success': True,
            'validated_contexts': validation_results,
            'total_questions_estimated': sum(r['estimated_questions'] for r in validation_results),
            'ready_for_questions_module': len(validation_results) > 0
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Templates HTML intégrés (simulation - dans la vraie implémentation, fichiers séparés)
@app.route('/demo_templates')
def demo_templates():
    """Page de démonstration des templates (développement)"""
    return """
    <h2>Templates à créer:</h2>
    <ul>
        <li>dashboard_integrated.html - Dashboard principal</li>
        <li>import_integrated.html - Interface d'import</li>
        <li>contexts.html - Overview des contextes</li>
        <li>prepare_questions.html - Préparation module Questions</li>
    </ul>

    <p>Structure suggérée avec Bootstrap pour un design moderne:</p>
    <pre>
    templates/
    ├── base.html (layout principal)
    ├── dashboard_integrated.html
    ├── import_integrated.html  
    ├── contexts.html
    ├── prepare_questions.html
    └── components/
        ├── status_badge.html
        ├── progress_bar.html
        └── compatibility_meter.html
    </pre>
    """


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html',
                           error="Page non trouvée",
                           suggestion="Retourner au dashboard"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html',
                           error="Erreur interne du serveur",
                           suggestion="Vérifier les logs et la configuration"), 500


if __name__ == '__main__':
    print("🚀 Interface Web Pipeline Intégré v2.0")
    print("=" * 40)
    print(f"Pipeline disponible: {'✅' if PIPELINE_AVAILABLE else '❌ (mode démo)'}")
    print("Routes disponibles:")
    print("  / - Dashboard principal")
    print("  /import - Interface d'import")
    print("  /contexts - Overview des contextes")
    print("  /prepare_questions - Préparation Questions")
    print("  /api/* - API REST")
    print()
    print("🌐 Serveur démarré sur http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)  # !/usr/bin/env python3
"""
Interface web intégrée pour le poker training
Architecture: poker-training/web/app.py v2.0
Intègre le pipeline JSON → Import → Questions
"""

from flask import Flask, render_template, request, jsonify, session
import json
import os
from pathlib import Path
import sys

# Ajout du répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from integrated_import import IntegratedImportPipeline, ContextStatus
    from questions import TrainingManager, QuestionType, QuestionDifficulty
except ImportError:
    # Fallback si modules pas encore créés
    print("⚠️  Modules intégrés non trouvés, utilisation de mocks")


    class MockIntegratedImportPipeline:
        def process_directory(self):
            return {
                'example_range.json': type('obj', (object,), {
                    'status': ContextStatus.COMPATIBLE,
                    'compatibility_score': 0.85,
                    'is_compatible': True,
                    'issues': []
                })()
            }

        def get_compatible_contexts(self):
            return [(123456, 0.85), (789012, 0.92)]


    class MockTrainingManager:
        def start_session(self, **kwargs):
            return type('obj', (object,), {'session_id': 'mock_session'})()

        def get_current_question(self):
            return type('obj', (object,), {
                'question_text': 'Avec AKo en BTN face à BB, que faites-vous ?',
                'correct_answer': 'Raise',
                'wrong_answers': ['Call', 'Fold'],
                'type': type('obj', (object,), {'value': 'hand_action'})(),
                'difficulty': type('obj', (object,), {'value': 2})(),
                'explanation': 'AKo est premium et bénéficie d\'un raise.'
            })()

        def answer_question(self, answer):
            return {
                'correct': True,
                'correct_answer': 'Raise',
                'explanation': 'Bonne réponse !',
                'score': 1,
                'progress': '1/10'
            }

        def get_session_stats(self):
            return {
                'session_id': 'mock',
                'score': 8,
                'total_questions': 10,
                'accuracy': 80.0,
                'completed': False
            }


    IntegratedImportPipeline = MockIntegratedImportPipeline
    TrainingManager = MockTrainingManager
    ContextStatus = type('ContextStatus', (), {
        'COMPATIBLE': 'compatible',
        'INCOMPLETE': 'incomplete',
        'INCONSISTENT': 'inconsistent',
        'INVALID': 'invalid'
    })()
    QuestionType = type('QuestionType', (), {
        'HAND_ACTION': 'hand_action',
        'FREQUENCY': 'frequency',
        'RANGE_COMPARISON': 'range_comparison'
    })()
    QuestionDifficulty = type('QuestionDifficulty', (), {
        'BEGINNER': 1,
        'INTERMEDIATE': 2,
        'ADVANCED': 3
    })()

app = Flask(__name__)
app.secret_key = 'poker_training_secret_key_2025'

# Instances globales
pipeline = IntegratedImportPipeline()
training_manager = TrainingManager()


@app.route('/')
def dashboard():
    """Dashboard principal avec vue d'ensemble"""
    try:
        # Statistiques d'import
        import_results = pipeline.process_directory()

        total_files = len(import_results)
        compatible_files = sum(1 for r in import_results.values() if r.is_compatible)

        # Contextes disponibles pour questions
        compatible_contexts = pipeline.get_compatible_contexts()

        stats = {
            'total_files': total_files,
            'compatible_files': compatible_files,
            'compatibility_rate': (compatible_files / total_files * 100) if total_files > 0 else 0,
            'available_contexts': len(compatible_contexts),
            'ready_for_training': compatible_files > 0
        }

        return render_template('dashboard.html',
                               stats=stats,
                               import_results=import_results)

    except Exception as e:
        app.logger.error(f"Erreur dashboard: {e}")
        return render_template('error.html', error=str(e))


@app.route('/import')
def import_page():
    """Page d'import avec résultats détaillés"""
    try:
        # Exécution de l'import intégré
        import_results = pipeline.process_directory()

        # Préparation des données pour l'affichage
        results_data = []
        for filename, result in import_results.items():
            results_data.append({
                'filename': filename,
                'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                'score': result.compatibility_score,
                'is_compatible': result.is_compatible,
                'issues': result.issues,
                'status_color': 'success' if result.is_compatible else 'danger',
                'status_icon': '🟢' if result.is_compatible else '🔴'
            })

        return render_template('import.html', results=results_data)

    except Exception as e:
        app.logger.error(f"Erreur import: {e}")
        return render_template('error.html', error=str(e))


@app.route('/training')
def training_page():
    """Page d'entraînement interactive"""
    return render_template('training.html')


@app.route('/api/start_session', methods=['POST'])
def api_start_session():
    """API: Démarrer une session d'entraînement"""
    try:
        data = request.get_json() or {}

        difficulty_map = {
            '1': QuestionDifficulty.BEGINNER,
            '2': QuestionDifficulty.INTERMEDIATE,
            '3': QuestionDifficulty.ADVANCED
        }

        difficulty = difficulty_map.get(data.get('difficulty', '2'), QuestionDifficulty.INTERMEDIATE)
        question_count = int(data.get('question_count', 10))

        # Types de questions sélectionnés
        selected_types = data.get('question_types', [])
        question_