"""
Quiz History Manager - Gestion de l'historique des quiz utilisateur

Base de données séparée pour l'historique :
- quiz_sessions : Métadonnées de chaque session de quiz
- quiz_answers : Réponses individuelles avec détails drill-down
- user_stats : Statistiques pré-calculées pour performances

Séparé de poker_trainer.db pour permettre :
- Suppression/réimport des ranges sans perdre l'historique
- Backup séparé de l'historique utilisateur
- Analyses avancées de progression
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class QuizHistoryManager:
    """Gestionnaire de l'historique des sessions de quiz"""
    
    def __init__(self, db_path: str = 'data/quiz_history.db'):
        """
        Initialise le gestionnaire d'historique
        
        Args:
            db_path: Chemin vers la base de données d'historique
        """
        self.db_path = db_path
        self._init_db()
        print(f"[HISTORY] QuizHistoryManager initialisé : {db_path}")
    
    def _init_db(self):
        """Crée les tables si elles n'existent pas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des sessions de quiz
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_start DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_end DATETIME,
                aggression_level TEXT,
                total_questions INTEGER,
                correct_answers INTEGER DEFAULT 0,
                score_percentage REAL,
                contexts_used TEXT,
                completed BOOLEAN DEFAULT 0
            )
        """)
        
        # Table des réponses individuelles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_number INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                hand TEXT NOT NULL,
                context_id INTEGER NOT NULL,
                context_name TEXT,
                context_action TEXT,
                
                question_type TEXT NOT NULL,
                drill_level INTEGER,
                drill_total_steps INTEGER,
                
                user_answer TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                
                villain_position TEXT,
                sequence_history TEXT,
                
                FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Table des statistiques utilisateur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_sessions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                average_score REAL DEFAULT 0,
                best_score REAL DEFAULT 0,
                best_session_id INTEGER,
                last_session_date DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialiser user_stats si vide
        cursor.execute("SELECT COUNT(*) FROM user_stats")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO user_stats (id) VALUES (1)")
        
        # Index pour performances
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_date 
            ON quiz_sessions(date_start)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_answers_session 
            ON quiz_answers(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_answers_context 
            ON quiz_answers(context_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_answers_correct 
            ON quiz_answers(is_correct)
        """)
        
        conn.commit()
        conn.close()
        print("[HISTORY] Base de données initialisée")
    
    # ============================================
    # GESTION DES SESSIONS
    # ============================================
    
    def start_session(self, aggression_level: str, contexts_used: List[int], total_questions: int) -> int:
        """
        Démarre une nouvelle session de quiz
        
        Args:
            aggression_level: Niveau d'agressivité (low/medium/high)
            contexts_used: Liste des IDs de contextes utilisés
            total_questions: Nombre total de questions prévues
            
        Returns:
            session_id: ID de la session créée
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quiz_sessions (aggression_level, contexts_used, total_questions)
            VALUES (?, ?, ?)
        """, (
            aggression_level,
            json.dumps(contexts_used),
            total_questions
        ))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[HISTORY] Session démarrée : ID={session_id}, aggression={aggression_level}, questions={total_questions}")
        return session_id
    
    def end_session(self, session_id: int) -> Dict[str, Any]:
        """
        Termine une session et calcule les statistiques
        
        Args:
            session_id: ID de la session à terminer
            
        Returns:
            Dict avec les stats de la session
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculer les stats de la session
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM quiz_answers
            WHERE session_id = ?
        """, (session_id,))
        
        total, correct = cursor.fetchone()
        correct = correct or 0
        score_percentage = round((correct / total * 100) if total > 0 else 0, 2)
        
        # Mettre à jour la session
        cursor.execute("""
            UPDATE quiz_sessions
            SET date_end = CURRENT_TIMESTAMP,
                correct_answers = ?,
                score_percentage = ?,
                completed = 1
            WHERE id = ?
        """, (correct, score_percentage, session_id))
        
        # Mettre à jour les stats utilisateur
        self._update_user_stats(cursor, session_id, total, correct, score_percentage)
        
        conn.commit()
        conn.close()
        
        stats = {
            'session_id': session_id,
            'total_questions': total,
            'correct_answers': correct,
            'score_percentage': score_percentage
        }
        
        print(f"[HISTORY] Session terminée : ID={session_id}, score={score_percentage}%")
        return stats
    
    def _update_user_stats(self, cursor, session_id: int, total: int, correct: int, score: float):
        """Met à jour les statistiques utilisateur"""
        cursor.execute("""
            UPDATE user_stats
            SET total_sessions = total_sessions + 1,
                total_questions = total_questions + ?,
                total_correct = total_correct + ?,
                average_score = (
                    SELECT AVG(score_percentage) 
                    FROM quiz_sessions 
                    WHERE completed = 1
                ),
                best_score = MAX(best_score, ?),
                best_session_id = CASE 
                    WHEN ? > best_score THEN ? 
                    ELSE best_session_id 
                END,
                last_session_date = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (total, correct, score, score, session_id))
    
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            Dict avec les infos de la session ou None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM quiz_sessions WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            session = dict(row)
            session['contexts_used'] = json.loads(session['contexts_used'])
            return session
        return None
    
    # ============================================
    # GESTION DES RÉPONSES
    # ============================================
    
    def save_answer(self, session_id: int, answer_data: Dict[str, Any]):
        """
        Sauvegarde une réponse
        
        Args:
            session_id: ID de la session
            answer_data: Dict contenant les données de la réponse
                - hand: Main jouée (ex: "KK")
                - context_id: ID du contexte
                - context_name: Nom du contexte
                - context_action: Action primaire du contexte
                - question_type: 'simple' ou 'drill_down'
                - user_answer: Réponse de l'utilisateur
                - correct_answer: Bonne réponse
                - is_correct: Boolean
                - question_number: Numéro de la question (optionnel)
                - drill_level: Niveau drill-down (optionnel)
                - drill_total_steps: Nombre total d'étapes (optionnel)
                - villain_position: Position du vilain (optionnel)
                - sequence_history: Historique de la séquence (optionnel)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convertir sequence_history en JSON si présent
        sequence_json = None
        if answer_data.get('sequence_history'):
            sequence_json = json.dumps(answer_data['sequence_history'])
        
        cursor.execute("""
            INSERT INTO quiz_answers (
                session_id, question_number, hand, context_id, context_name, context_action,
                question_type, drill_level, drill_total_steps,
                user_answer, correct_answer, is_correct,
                villain_position, sequence_history
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            answer_data.get('question_number'),
            answer_data['hand'],
            answer_data['context_id'],
            answer_data['context_name'],
            answer_data['context_action'],
            answer_data['question_type'],
            answer_data.get('drill_level'),
            answer_data.get('drill_total_steps'),
            answer_data['user_answer'],
            answer_data['correct_answer'],
            answer_data['is_correct'],
            answer_data.get('villain_position'),
            sequence_json
        ))
        
        conn.commit()
        conn.close()
        
        status = "✅" if answer_data['is_correct'] else "❌"
        print(f"[HISTORY] Réponse sauvegardée : {status} {answer_data['hand']} - {answer_data['question_type']}")
    
    def get_session_answers(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Récupère toutes les réponses d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            Liste des réponses
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM quiz_answers
            WHERE session_id = ?
            ORDER BY question_number, timestamp
        """, (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        answers = []
        for row in rows:
            answer = dict(row)
            # Parser le JSON de sequence_history si présent
            if answer['sequence_history']:
                answer['sequence_history'] = json.loads(answer['sequence_history'])
            answers.append(answer)
        
        return answers
    
    def get_session_results(self, session_id: int) -> Dict[str, Any]:
        """
        Récupère les résultats complets d'une session
        
        Args:
            session_id: ID de la session
            
        Returns:
            Dict avec session info + answers
        """
        session = self.get_session(session_id)
        answers = self.get_session_answers(session_id)
        
        return {
            'session': session,
            'answers': answers
        }
    
    # ============================================
    # STATISTIQUES
    # ============================================
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques globales de l'utilisateur
        
        Returns:
            Dict avec toutes les stats
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_stats WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else {}
    
    def get_context_stats(self, context_id: int, limit_days: int = 30) -> Dict[str, Any]:
        """
        Statistiques pour un contexte spécifique
        
        Args:
            context_id: ID du contexte
            limit_days: Nombre de jours à analyser
            
        Returns:
            Dict avec stats du contexte
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=limit_days)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                ROUND(AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END), 2) as success_rate,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM quiz_answers
            WHERE context_id = ? AND timestamp > ?
        """, (context_id, date_limit))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'context_id': context_id,
            'total_questions': row[0] or 0,
            'correct_answers': row[1] or 0,
            'success_rate': row[2] or 0,
            'first_seen': row[3],
            'last_seen': row[4]
        }
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère les sessions récentes
        
        Args:
            limit: Nombre de sessions à récupérer
            
        Returns:
            Liste des sessions
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM quiz_sessions
            WHERE completed = 1
            ORDER BY date_start DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            session = dict(row)
            session['contexts_used'] = json.loads(session['contexts_used'])
            sessions.append(session)
        
        return sessions
    
    def get_progression_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Données de progression sur les N derniers jours
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            Liste avec date + score moyen par jour
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                DATE(date_start) as date,
                COUNT(*) as sessions_count,
                ROUND(AVG(score_percentage), 2) as avg_score
            FROM quiz_sessions
            WHERE completed = 1 AND date_start > ?
            GROUP BY DATE(date_start)
            ORDER BY date
        """, (date_limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'date': row[0],
                'sessions_count': row[1],
                'avg_score': row[2]
            }
            for row in rows
        ]
    
    def get_error_patterns(self, limit_days: int = 30) -> Dict[str, Any]:
        """
        Analyse des patterns d'erreurs
        
        Args:
            limit_days: Nombre de jours à analyser
            
        Returns:
            Dict avec différents patterns détectés
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=limit_days)).isoformat()
        
        # Erreurs par contexte
        cursor.execute("""
            SELECT 
                context_name,
                COUNT(*) as error_count
            FROM quiz_answers
            WHERE is_correct = 0 AND timestamp > ?
            GROUP BY context_name
            ORDER BY error_count DESC
            LIMIT 5
        """, (date_limit,))
        
        errors_by_context = [
            {'context': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Tendance tight/loose
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN user_answer = 'FOLD' AND is_correct = 0 THEN 1 ELSE 0 END) as fold_errors,
                SUM(CASE WHEN user_answer IN ('RAISE', 'OPEN', '3BET') AND is_correct = 0 THEN 1 ELSE 0 END) as raise_errors,
                COUNT(*) as total_errors
            FROM quiz_answers
            WHERE is_correct = 0 AND timestamp > ?
        """, (date_limit,))
        
        fold_err, raise_err, total_err = cursor.fetchone()
        
        tendency = None
        if total_err > 0:
            if fold_err > total_err * 0.6:
                tendency = 'too_tight'
            elif raise_err > total_err * 0.6:
                tendency = 'too_loose'
        
        conn.close()
        
        return {
            'errors_by_context': errors_by_context,
            'tendency': tendency,
            'fold_errors': fold_err or 0,
            'raise_errors': raise_err or 0,
            'total_errors': total_err or 0
        }
    
    # ============================================
    # UTILITAIRES
    # ============================================
    
    def export_to_csv(self, session_id: int, output_path: str):
        """
        Exporte une session en CSV
        
        Args:
            session_id: ID de la session
            output_path: Chemin du fichier de sortie
        """
        import csv
        
        answers = self.get_session_answers(session_id)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'question_number', 'hand', 'context_name', 'context_action',
                'question_type', 'drill_level', 'user_answer', 'correct_answer',
                'is_correct', 'villain_position'
            ])
            writer.writeheader()
            
            for answer in answers:
                writer.writerow({
                    'question_number': answer['question_number'],
                    'hand': answer['hand'],
                    'context_name': answer['context_name'],
                    'context_action': answer['context_action'],
                    'question_type': answer['question_type'],
                    'drill_level': answer['drill_level'],
                    'user_answer': answer['user_answer'],
                    'correct_answer': answer['correct_answer'],
                    'is_correct': answer['is_correct'],
                    'villain_position': answer['villain_position']
                })
        
        print(f"[HISTORY] Session {session_id} exportée vers {output_path}")
    
    def delete_old_sessions(self, days: int = 90):
        """
        Supprime les sessions de plus de X jours
        
        Args:
            days: Nombre de jours à conserver
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            DELETE FROM quiz_sessions
            WHERE date_start < ? AND completed = 1
        """, (date_limit,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[HISTORY] {deleted} sessions supprimées (> {days} jours)")
        return deleted


# ============================================
# EXEMPLE D'UTILISATION
# ============================================
if __name__ == '__main__':
    # Test du module
    manager = QuizHistoryManager('data/quiz_history.db')
    
    # Démarrer une session
    session_id = manager.start_session(
        aggression_level='medium',
        contexts_used=[1, 2, 3],
        total_questions=10
    )
    
    # Simuler quelques réponses
    for i in range(5):
        manager.save_answer(session_id, {
            'question_number': i + 1,
            'hand': 'AKs',
            'context_id': 1,
            'context_name': 'UTG Open',
            'context_action': 'open',
            'question_type': 'simple',
            'user_answer': 'RAISE',
            'correct_answer': 'RAISE',
            'is_correct': True
        })
    
    # Terminer la session
    stats = manager.end_session(session_id)
    print(f"Session stats: {stats}")
    
    # Récupérer stats utilisateur
    user_stats = manager.get_user_stats()
    print(f"User stats: {user_stats}")
