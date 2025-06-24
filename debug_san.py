#!/usr/bin/env python3
"""
Debug script to examine SAN parsing errors.
"""

import chess
import chess.pgn
from io import StringIO
from fetch import ChessComAPI
from utils import load_environment

def debug_san_parsing():
    """Debug SAN parsing errors."""
    print("🔍 Debugging SAN Parsing Errors")
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
    
    try:
        # Parse the game
        pgn_io = StringIO(pgn)
        game_obj = chess.pgn.read_game(pgn_io)
        board = game_obj.board()
        
        print("\nAnalyzing moves for SAN parsing issues:")
        print("-" * 80)
        
        for i, move in enumerate(game_obj.mainline_moves()):
            if i >= 20:  # Check first 20 moves
                break
                
            # Get position before the move
            fen_before = board.fen()
            is_white_turn = board.turn == chess.WHITE
            
            print(f"Move {i+1:2d} ({'White' if is_white_turn else 'Black'}): {move.uci()}")
            print(f"  Position: {fen_before}")
            
            # Try to get SAN notation
            try:
                san_move = board.san(move)
                print(f"  SAN: {san_move} ✅")
            except Exception as e:
                print(f"  SAN: ERROR - {e}")
                print(f"  Move UCI: {move.uci()}")
                print(f"  From square: {chess.square_name(move.from_square)}")
                print(f"  To square: {chess.square_name(move.to_square)}")
                if move.promotion:
                    print(f"  Promotion: {move.promotion}")
            
            # Make the move
            board.push(move)
            print()
    
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    debug_san_parsing() 