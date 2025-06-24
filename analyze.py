"""
Stockfish engine analysis and blunder detection.
"""

import chess
import chess.pgn
import chess.engine
from typing import List, Dict, Any, Tuple, Optional
import time
from io import StringIO

class ChessAnalyzer:
    """Handles chess analysis using Stockfish engine."""
    
    def __init__(self, engine_path: str = r"C:\Users\Alex\Downloads\stockfish-windows-x86-64-avx2.exe"):
        """
        Initialize the analyzer with Stockfish engine.
        
        Args:
            engine_path: Path to Stockfish executable (default: user's download path)
        """
        self.engine_path = engine_path
        self.engine = None
        self.blunder_threshold = -1.5  # Evaluation drop threshold for blunders
        self.mistake_threshold = -0.8  # Evaluation drop threshold for mistakes
        self.inaccuracy_threshold = -0.3  # Evaluation drop threshold for inaccuracies
        
    def initialize_engine(self) -> bool:
        """
        Initialize the Stockfish engine.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            return True
        except Exception as e:
            print(f"Error initializing Stockfish engine: {e}")
            print("Make sure Stockfish is installed and accessible via PATH")
            return False
    
    def close_engine(self):
        """Close the Stockfish engine."""
        if self.engine:
            self.engine.quit()
    
    def get_san_move(self, board: chess.Board, move: chess.Move) -> str:
        """
        Get SAN notation for a move, handling errors gracefully.
        
        Args:
            board: Chess board
            move: Move to convert
            
        Returns:
            SAN notation or UCI notation as fallback
        """
        try:
            return board.san(move)
        except (ValueError, AttributeError):
            # Fallback to UCI notation if SAN fails
            return move.uci()
    
    def get_error_type(self, eval_change: float) -> str:
        """
        Determine the type of error based on evaluation change.
        
        Args:
            eval_change: Evaluation change in pawns
            
        Returns:
            Error type string
        """
        if eval_change <= self.blunder_threshold:
            return "Blunder"
        elif eval_change <= self.mistake_threshold:
            return "Mistake"
        elif eval_change <= self.inaccuracy_threshold:
            return "Inaccuracy"
        else:
            return "Good"
    
    def analyze_game(self, pgn: str, username: str) -> List[Dict[str, Any]]:
        """
        Analyze a game and find errors for the specified player.
        
        Args:
            pgn: PGN string of the game
            username: Username of the player to analyze
            
        Returns:
            List of error dictionaries
        """
        if not self.engine:
            if not self.initialize_engine():
                return []
        
        try:
            # Parse the game using StringIO to convert string to file-like object
            pgn_io = StringIO(pgn)
            game = chess.pgn.read_game(pgn_io)
            if not game:
                print("Could not parse PGN")
                return []
            
            # Determine if the player is White or Black
            white_player = game.headers.get('White', '').lower()
            black_player = game.headers.get('Black', '').lower()
            username_lower = username.lower()
            
            if username_lower not in [white_player, black_player]:
                print(f"Player {username} not found in game")
                return []
            
            is_player_white = username_lower == white_player
            is_player_black = username_lower == black_player
            
            board = game.board()
            errors = []
            move_number = 1
            
            # Analyze each move
            for move in game.mainline_moves():
                try:
                    # Get position before the move
                    fen_before = board.fen()
                    is_white_turn = board.turn == chess.WHITE
                    
                    # Only analyze moves made by the specified player
                    should_analyze = (is_white_turn and is_player_white) or (not is_white_turn and is_player_black)
                    
                    if should_analyze:
                        # Get SAN notation for the move BEFORE making it
                        try:
                            san_move = board.san(move)
                        except (ValueError, AttributeError):
                            san_move = move.uci()
                        
                        # Get evaluation before the move
                        info_before = self.engine.analyse(board, chess.engine.Limit(time=0.1))
                        eval_before = info_before.get('score', None)
                        if eval_before is None:
                            eval_before_centipawns = 0
                        else:
                            eval_before_centipawns = eval_before.white().score(mate_score=10000)
                        
                        # Make the move
                        board.push(move)
                        
                        # Get evaluation after the move
                        info_after = self.engine.analyse(board, chess.engine.Limit(time=0.1))
                        eval_after = info_after.get('score', None)
                        if eval_after is None:
                            eval_after_centipawns = 0
                        else:
                            eval_after_centipawns = eval_after.white().score(mate_score=10000)
                        
                        # Calculate evaluation change from the perspective of the player who made the move
                        if is_white_turn:
                            # White's move: positive eval means White is winning
                            eval_change = eval_after_centipawns - eval_before_centipawns
                        else:
                            # Black's move: need to flip perspective since Stockfish evaluates from White's perspective
                            eval_change = -eval_after_centipawns - (-eval_before_centipawns)
                        
                        eval_change_pawns = eval_change / 100.0
                        
                        # Check if this is an error (evaluation drop)
                        if eval_change_pawns <= self.inaccuracy_threshold:
                            error_type = self.get_error_type(eval_change_pawns)
                            
                            error = {
                                'move_number': move_number,
                                'move': move.uci(),
                                'fen_before': fen_before,
                                'eval_before': eval_before_centipawns / 100.0,  # Convert to pawns
                                'eval_after': eval_after_centipawns / 100.0,
                                'eval_change': eval_change_pawns,
                                'san_move': san_move,
                                'error_type': error_type,
                                'player': 'White' if is_player_white else 'Black'  # Use the player's actual color, not whose turn it is
                            }
                            errors.append(error)
                    else:
                        # Just make the move without analyzing
                        board.push(move)
                    
                    move_number += 1
                    
                except Exception as e:
                    # Log the error but continue with analysis
                    print(f"  Error analyzing move {move_number}: {e}")
                    # Continue with next move
                    try:
                        board.push(move)
                        move_number += 1
                    except:
                        break
            
            return errors
            
        except Exception as e:
            print(f"Error analyzing game: {e}")
            return []
    
    def get_best_move(self, fen: str, time_limit: float = 0.5) -> Optional[str]:
        """
        Get the best move for a given position.
        
        Args:
            fen: FEN string of the position
            time_limit: Time limit for analysis in seconds
            
        Returns:
            Best move in UCI format or None if error
        """
        if not self.engine:
            if not self.initialize_engine():
                return None
        
        try:
            board = chess.Board(fen)
            result = self.engine.play(board, chess.engine.Limit(time=time_limit))
            return result.move.uci() if result.move else None
        except Exception as e:
            print(f"Error getting best move: {e}")
            return None
    
    def get_position_evaluation(self, fen: str, time_limit: float = 0.5) -> Optional[float]:
        """
        Get evaluation for a given position.
        
        Args:
            fen: FEN string of the position
            time_limit: Time limit for analysis in seconds
            
        Returns:
            Evaluation in pawns or None if error
        """
        if not self.engine:
            if not self.initialize_engine():
                return None
        
        try:
            board = chess.Board(fen)
            info = self.engine.analyse(board, chess.engine.Limit(time=time_limit))
            score = info.get('score', None)
            if score is None:
                return None
            return score.white().score(mate_score=10000) / 100.0
        except Exception as e:
            print(f"Error getting position evaluation: {e}")
            return None 