#!/usr/bin/env python3
"""
Test script to analyze a single game in detail.
"""

import sys
import os
from fetch import ChessComAPI
from analyze import ChessAnalyzer
from utils import load_environment

def test_single_game_analysis():
    """Test analysis of a single game in detail."""
    print("🔍 Testing Single Game Analysis")
    print("=" * 50)
    
    # Load environment
    load_environment()
    
    # Initialize components
    api = ChessComAPI()
    analyzer = ChessAnalyzer()
    
    # Get username
    username = input("Enter Chess.com username: ").strip()
    if not username:
        print("Username required.")
        return
    
    print(f"\nFetching games for: {username}")
    
    # Fetch just one game
    games = api.get_user_games(username, count=1)
    
    if not games:
        print("No games found!")
        return
    
    game = games[0]
    pgn = game.get('pgn')
    
    if not pgn:
        print("No PGN data found!")
        return
    
    print(f"Analyzing game: {game.get('white', {}).get('username', 'Unknown')} vs {game.get('black', {}).get('username', 'Unknown')}")
    print(f"Result: {game.get('result', 'Unknown')}")
    
    # Initialize Stockfish
    if not analyzer.initialize_engine():
        print("Failed to initialize Stockfish!")
        return
    
    try:
        # Analyze the game
        errors = analyzer.analyze_game(pgn, username)
        
        print(f"\nAnalysis complete!")
        print(f"Total errors found: {len(errors)}")
        
        if errors:
            print("\nErrors found:")
            for i, error in enumerate(errors, 1):
                print(f"\nError {i} ({error['error_type']}):")
                print(f"  Move: {error['san_move']} (Move {error['move_number']})")
                print(f"  Evaluation before: {error['eval_before']:.2f}")
                print(f"  Evaluation after: {error['eval_after']:.2f}")
                print(f"  Evaluation change: {error['eval_change']:.2f}")
                print(f"  Position: {error['fen_before']}")
        else:
            print("\nNo errors detected (evaluation drops >= -0.3)")
            
            # Let's check a few moves to see what the evaluations look like
            print("\nChecking first 10 moves for evaluation patterns:")
            
            import chess.pgn
            from io import StringIO
            
            pgn_io = StringIO(pgn)
            game_obj = chess.pgn.read_game(pgn_io)
            board = game_obj.board()
            
            for i, move in enumerate(game_obj.mainline_moves()):
                if i >= 10:
                    break
                    
                # Get evaluation before move
                info = analyzer.engine.analyse(board, chess.engine.Limit(time=0.1))
                eval_score = info.get('score')
                if eval_score:
                    eval_centipawns = eval_score.white().score(mate_score=10000)
                    eval_pawns = eval_centipawns / 100.0
                    print(f"  Move {i+1}: {move.uci()} - Evaluation: {eval_pawns:.2f}")
                else:
                    print(f"  Move {i+1}: {move.uci()} - Evaluation: N/A")
                
                board.push(move)
    
    except Exception as e:
        print(f"Error during analysis: {e}")
    finally:
        analyzer.close_engine()

if __name__ == "__main__":
    test_single_game_analysis() 