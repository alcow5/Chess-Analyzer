#!/usr/bin/env python3
"""
Database module for caching chess game analysis results.
"""

import sqlite3
import json
import hashlib
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

class ChessDatabase:
    """SQLite database for storing chess game analysis results."""
    
    def __init__(self, db_path: str = "chess_analysis.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Games table - stores game metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    pgn TEXT NOT NULL,
                    white_player TEXT NOT NULL,
                    black_player TEXT NOT NULL,
                    result TEXT NOT NULL,
                    date_played TEXT,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analyzed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Analysis table - stores analysis results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    move_number INTEGER NOT NULL,
                    move TEXT NOT NULL,
                    san_move TEXT NOT NULL,
                    fen_before TEXT NOT NULL,
                    eval_before REAL NOT NULL,
                    eval_after REAL NOT NULL,
                    eval_change REAL NOT NULL,
                    error_type TEXT NOT NULL,
                    player TEXT NOT NULL,
                    date_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_username ON games (username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_analyzed ON games (analyzed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_game_id ON analysis (game_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_player ON analysis (player)')
            
            conn.commit()
    
    def generate_game_id(self, pgn: str, username: str) -> str:
        """Generate a unique game ID based on PGN and username."""
        content = f"{pgn[:100]}{username}"  # Use first 100 chars of PGN + username
        return hashlib.md5(content.encode()).hexdigest()
    
    def game_exists(self, game_id: str) -> bool:
        """Check if a game already exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM games WHERE game_id = ?', (game_id,))
            return cursor.fetchone() is not None
    
    def game_analyzed(self, game_id: str) -> bool:
        """Check if a game has been analyzed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT analyzed FROM games WHERE game_id = ?', (game_id,))
            result = cursor.fetchone()
            return result[0] if result else False
    
    def add_game(self, game_data: Dict[str, Any], username: str) -> str:
        """
        Add a new game to the database.
        
        Args:
            game_data: Game data from Chess.com API
            username: Username of the player
            
        Returns:
            Game ID
        """
        pgn = game_data.get('pgn', '')
        game_id = self.generate_game_id(pgn, username)
        
        if self.game_exists(game_id):
            return game_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO games (game_id, username, pgn, white_player, black_player, result, date_played)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_id,
                username,
                pgn,
                game_data.get('white', {}).get('username', ''),
                game_data.get('black', {}).get('username', ''),
                game_data.get('white', {}).get('result', ''),
                game_data.get('end_time', '')
            ))
            conn.commit()
        
        return game_id
    
    def save_analysis(self, game_id: str, errors: List[Dict[str, Any]]):
        """
        Save analysis results for a game.
        
        Args:
            game_id: Game ID
            errors: List of error dictionaries from analysis
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear any existing analysis for this game
            cursor.execute('DELETE FROM analysis WHERE game_id = ?', (game_id,))
            
            # Insert new analysis results
            for error in errors:
                cursor.execute('''
                    INSERT INTO analysis (game_id, move_number, move, san_move, fen_before, 
                                        eval_before, eval_after, eval_change, error_type, player)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    error.get('move_number', 0),
                    error.get('move', ''),
                    error.get('san_move', ''),
                    error.get('fen_before', ''),
                    error.get('eval_before', 0.0),
                    error.get('eval_after', 0.0),
                    error.get('eval_change', 0.0),
                    error.get('error_type', ''),
                    error.get('player', '')
                ))
            
            # Mark game as analyzed
            cursor.execute('UPDATE games SET analyzed = TRUE WHERE game_id = ?', (game_id,))
            conn.commit()
    
    def get_analysis(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve analysis results for a game.
        
        Args:
            game_id: Game ID
            
        Returns:
            List of error dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT move_number, move, san_move, fen_before, eval_before, eval_after, 
                       eval_change, error_type, player
                FROM analysis 
                WHERE game_id = ?
                ORDER BY move_number
            ''', (game_id,))
            
            results = cursor.fetchall()
            errors = []
            for row in results:
                errors.append({
                    'move_number': row[0],
                    'move': row[1],
                    'san_move': row[2],
                    'fen_before': row[3],
                    'eval_before': row[4],
                    'eval_after': row[5],
                    'eval_change': row[6],
                    'error_type': row[7],
                    'player': row[8]
                })
            
            return errors
    
    def get_unanalyzed_games(self, username: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get unanalyzed games for a user.
        
        Args:
            username: Username
            limit: Maximum number of games to return
            
        Returns:
            List of game dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = '''
                SELECT game_id, pgn, white_player, black_player, result, date_played
                FROM games 
                WHERE username = ? AND analyzed = FALSE
                ORDER BY date_added DESC
            '''
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (username,))
            results = cursor.fetchall()
            
            games = []
            for row in results:
                games.append({
                    'game_id': row[0],
                    'pgn': row[1],
                    'white_player': row[2],
                    'black_player': row[3],
                    'result': row[4],
                    'date_played': row[5]
                })
            
            return games
    
    def get_stats(self, username: str) -> Dict[str, Any]:
        """
        Get analysis statistics for a user.
        
        Args:
            username: Username
            
        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total games
            cursor.execute('SELECT COUNT(*) FROM games WHERE username = ?', (username,))
            total_games = cursor.fetchone()[0]
            
            # Analyzed games
            cursor.execute('SELECT COUNT(*) FROM games WHERE username = ? AND analyzed = TRUE', (username,))
            analyzed_games = cursor.fetchone()[0]
            
            # Total errors
            cursor.execute('''
                SELECT COUNT(*) FROM analysis a
                JOIN games g ON a.game_id = g.game_id
                WHERE g.username = ?
            ''', (username,))
            total_errors = cursor.fetchone()[0]
            
            # Error types
            cursor.execute('''
                SELECT error_type, COUNT(*) FROM analysis a
                JOIN games g ON a.game_id = g.game_id
                WHERE g.username = ?
                GROUP BY error_type
            ''', (username,))
            error_types = dict(cursor.fetchall())
            
            return {
                'total_games': total_games,
                'analyzed_games': analyzed_games,
                'total_errors': total_errors,
                'error_types': error_types
            }
    
    def clear_old_data(self, days: int = 30):
        """
        Clear old analysis data to save space.
        
        Args:
            days: Number of days to keep
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM analysis 
                WHERE date_analyzed < datetime('now', '-{} days')
            '''.format(days))
            conn.commit()
    
    def conn(self):
        """Get a database connection context manager."""
        return sqlite3.connect(self.db_path) 