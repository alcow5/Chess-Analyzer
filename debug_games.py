#!/usr/bin/env python3
"""
Debug script to examine Chess.com game data and PGN content.
"""

import sys
import os
from fetch import ChessComAPI
from utils import load_environment

def debug_games():
    """Debug the game fetching and PGN parsing."""
    print("🔍 Debugging Chess.com Game Data")
    print("=" * 50)
    
    # Load environment
    load_environment()
    
    # Initialize API
    api = ChessComAPI()
    
    # Get username
    username = input("Enter Chess.com username to debug: ").strip()
    if not username:
        print("Username required.")
        return
    
    print(f"\nFetching games for: {username}")
    
    # Fetch games
    games = api.get_user_games(username, count=3)  # Just get 3 for debugging
    
    if not games:
        print("No games found!")
        return
    
    print(f"Found {len(games)} games")
    
    for i, game in enumerate(games, 1):
        print(f"\n--- Game {i} ---")
        print(f"White: {game.get('white', {}).get('username', 'Unknown')}")
        print(f"Black: {game.get('black', {}).get('username', 'Unknown')}")
        print(f"Result: {game.get('result', 'Unknown')}")
        print(f"Time Control: {game.get('time_control', 'Unknown')}")
        print(f"End Time: {game.get('end_time', 'Unknown')}")
        
        # Check PGN
        pgn = game.get('pgn')
        if pgn:
            print(f"PGN Length: {len(pgn)} characters")
            print("PGN Preview (first 200 chars):")
            print(pgn[:200] + "..." if len(pgn) > 200 else pgn)
            
            # Try to parse with chess.pgn
            try:
                import chess.pgn
                from io import StringIO
                
                pgn_io = StringIO(pgn)
                parsed_game = chess.pgn.read_game(pgn_io)
                
                if parsed_game:
                    print("✅ PGN parsed successfully!")
                    print(f"Game headers: {dict(parsed_game.headers)}")
                    
                    # Count moves
                    move_count = 0
                    for move in parsed_game.mainline_moves():
                        move_count += 1
                    
                    print(f"Total moves: {move_count}")
                    
                    # Try to analyze first few moves
                    board = parsed_game.board()
                    print("\nFirst few moves:")
                    for j, move in enumerate(parsed_game.mainline_moves()):
                        if j >= 5:  # Only show first 5 moves
                            break
                        print(f"  Move {j+1}: {move.uci()} (FEN: {board.fen()})")
                        board.push(move)
                        
                else:
                    print("❌ PGN parsing returned None")
                    
            except Exception as e:
                print(f"❌ Error parsing PGN: {e}")
        else:
            print("❌ No PGN data found!")
        
        print("-" * 30)

if __name__ == "__main__":
    debug_games() 