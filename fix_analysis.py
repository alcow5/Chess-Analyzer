#!/usr/bin/env python3
"""
Fix the analysis by clearing the database and re-analyzing with proper color detection.
"""

from database import ChessDatabase
from analyze import ChessAnalyzer
from fetch import ChessComAPI
from utils import load_environment, load_username
from concurrent.futures import ProcessPoolExecutor, as_completed
import requests
import time

def analyze_game_worker_fixed(args):
    """Fixed version that properly tracks player color."""
    pgn, username, game_id, db = args
    analyzer = ChessAnalyzer()
    analyzer.initialize_engine()
    try:
        errors = analyzer.analyze_game(pgn, username)
        # Save analysis to database
        if db:
            db.save_analysis(game_id, errors)
        return errors
    finally:
        analyzer.close_engine()

def get_last_n_lost_games(api, username, n=100):
    """Fetch the last n games the user lost, working backwards through monthly archives."""
    lost_games = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ChessAnalyzer/1.0)"}
    # Get list of archive URLs
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch archives for {username} (status {resp.status_code})")
        print(f"Response: {resp.text}")
        return []
    archive_urls = resp.json().get('archives', [])[::-1]  # Most recent first
    print(f"Found {len(archive_urls)} monthly archives.")
    
    for idx, archive_url in enumerate(archive_urls):
        month_resp = requests.get(archive_url, headers=headers)
        if month_resp.status_code != 200:
            print(f"Failed to fetch archive {archive_url} (status {month_resp.status_code})")
            print(f"Response: {month_resp.text}")
            continue
        month_games = month_resp.json().get('games', [])
        print(f"Archive {archive_url}: {len(month_games)} games found.")
        
        # Process games in chronological order (oldest first) to get the most recent losses
        for game in month_games:
            white = game.get('white', {}).get('username', '').lower()
            black = game.get('black', {}).get('username', '').lower()
            white_result = game.get('white', {}).get('result', '').lower()
            black_result = game.get('black', {}).get('result', '').lower()
            user_is_white = username.lower() == white
            user_is_black = username.lower() == black
            
            if user_is_white and white_result in ['checkmated', 'timeout', 'resigned', 'lose', 'abandoned', 'timeout vs computer']:
                lost_games.append(game)
                print(f"Found lost game as White: {white_result}")
            elif user_is_black and black_result in ['checkmated', 'timeout', 'resigned', 'lose', 'abandoned', 'timeout vs computer']:
                lost_games.append(game)
                print(f"Found lost game as Black: {black_result}")
            
            if len(lost_games) >= n:
                print(f"✅ Collected {len(lost_games)} lost games. Stopping search.")
                return lost_games[:n]
    
    print(f"Collected {len(lost_games)} lost games in total.")
    return lost_games

def main():
    print("🔧 Fixing Chess Analysis Database")
    print("=" * 50)
    
    load_environment()
    username = load_username()
    if not username:
        username = input("Enter Chess.com username: ").strip()
        if not username:
            print("Username required.")
            return
    
    # Initialize database
    db = ChessDatabase()
    print(f"\n📊 Database: {db.db_path}")
    
    # Clear all existing analysis data
    print("\n🗑️  Clearing existing analysis data...")
    with db.conn() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM analysis')
        cursor.execute('UPDATE games SET analyzed = FALSE')
        conn.commit()
    print("✅ Database cleared")
    
    # Fetch games again
    print(f"\n🔍 Fetching last 100 lost games for: {username}")
    api = ChessComAPI()
    lost_games = get_last_n_lost_games(api, username, n=100)
    print(f"✅ Found {len(lost_games)} lost games")
    
    if not lost_games:
        print("No lost games found!")
        return
    
    # Add games to database
    games_to_analyze = []
    for game in lost_games:
        if game.get('pgn'):
            game_id = db.add_game(game, username)
            game['game_id'] = game_id
            games_to_analyze.append(game)
            print(f"🔄 Game {game_id[:8]}... queued for analysis")
    
    # Analyze all games with fixed logic
    print(f"\n🔄 Re-analyzing {len(games_to_analyze)} games with fixed color detection...")
    
    # Prepare arguments for parallel analysis
    game_args = [(game.get('pgn'), username, game.get('game_id'), db) for game in games_to_analyze]
    
    all_errors = []
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(analyze_game_worker_fixed, arg) for arg in game_args]
        for i, future in enumerate(as_completed(futures), 1):
            errors = future.result()
            all_errors.extend(errors)
            print(f"Analyzed game {i}/{len(game_args)}: {len(errors)} errors found")
    
    # Show summary
    print(f"\n📊 Analysis Complete!")
    print(f"Total errors found: {len(all_errors)}")
    
    if all_errors:
        from collections import Counter
        white_errors = [e for e in all_errors if e.get('player') == 'White']
        black_errors = [e for e in all_errors if e.get('player') == 'Black']
        
        print(f"White errors: {len(white_errors)} ({len(white_errors)/len(all_errors)*100:.1f}%)")
        print(f"Black errors: {len(black_errors)} ({len(black_errors)/len(all_errors)*100:.1f}%)")
        
        print(f"\nSample errors with colors:")
        for i, error in enumerate(all_errors[:10]):
            print(f"  {i+1}. {error['san_move']} ({error.get('player', 'Unknown')}) - {error['error_type']}")
    
    print(f"\n✅ Database fixed and re-analyzed!")

if __name__ == "__main__":
    main() 