#!/usr/bin/env python3
"""
Debug script to examine evaluation calculations in detail.
"""

import chess
import chess.pgn
import chess.engine
from io import StringIO
from fetch import ChessComAPI
from utils import load_environment

def debug_evaluation():
    """Debug evaluation calculations step by step."""
    print("🔍 Debugging Evaluation Calculations")
    print("=" * 50)
    
    # Load environment
    load_environment()
    
    # Initialize components
    api = ChessComAPI()
    
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
    
    # Initialize Stockfish
    engine_path = r"C:\Users\Alex\Downloads\stockfish-windows-x86-64-avx2.exe"
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    
    try:
        # Parse the game
        pgn_io = StringIO(pgn)
        game_obj = chess.pgn.read_game(pgn_io)
        board = game_obj.board()
        
        print("\nAnalyzing first 15 moves in detail:")
        print("-" * 80)
        
        for i, move in enumerate(game_obj.mainline_moves()):
            if i >= 15:
                break
                
            # Get position before the move
            fen_before = board.fen()
            is_white_turn = board.turn == chess.WHITE
            
            # Get evaluation before the move
            info_before = engine.analyse(board, chess.engine.Limit(time=0.1))
            eval_before = info_before.get('score', None)
            if eval_before is None:
                eval_before_centipawns = 0
            else:
                eval_before_centipawns = eval_before.white().score(mate_score=10000)
            
            # Make the move
            board.push(move)
            
            # Get evaluation after the move
            info_after = engine.analyse(board, chess.engine.Limit(time=0.1))
            eval_after = info_after.get('score', None)
            if eval_after is None:
                eval_after_centipawns = 0
            else:
                eval_after_centipawns = eval_after.white().score(mate_score=10000)
            
            # Calculate evaluation change
            if is_white_turn:
                eval_change = eval_after_centipawns - eval_before_centipawns
            else:
                eval_change = -eval_after_centipawns - (-eval_before_centipawns)
                eval_change = -eval_change
            
            eval_change_pawns = eval_change / 100.0
            
            # Get SAN notation
            try:
                san_move = board.san(move)
            except:
                san_move = move.uci()
            
            print(f"Move {i+1:2d} ({'White' if is_white_turn else 'Black'}): {san_move}")
            print(f"  Eval before: {eval_before_centipawns/100.0:6.2f}  Eval after: {eval_after_centipawns/100.0:6.2f}")
            print(f"  Change: {eval_change_pawns:6.2f} pawns")
            
            # Check if this is an error
            if eval_change_pawns <= -0.3:
                print(f"  ⚠️  ERROR DETECTED!")
            elif eval_change_pawns <= -0.8:
                print(f"  ❌ MISTAKE DETECTED!")
            elif eval_change_pawns <= -1.5:
                print(f"  💥 BLUNDER DETECTED!")
            else:
                print(f"  ✅ Good move")
            
            print()
    
    except Exception as e:
        print(f"Error during analysis: {e}")
    finally:
        engine.quit()

if __name__ == "__main__":
    debug_evaluation() 