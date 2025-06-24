#!/usr/bin/env python3
"""
Analyze last 50 games, find common mistakes, and get improvement suggestions from GPT-4.1.
"""

from fetch import ChessComAPI
from analyze import ChessAnalyzer
from explain import ChessExplainer
from utils import load_environment, load_username
from database import ChessDatabase
from collections import Counter
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import requests
import time


def analyze_game_worker(args):
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


def get_lost_games_from_year(api, username, year):
    """Fetch all lost games for the user from a specific year."""
    lost_games = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ChessAnalyzer/1.0)"}
    # Get list of archive URLs
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch archives for {username} (status {resp.status_code})")
        print(f"Response: {resp.text}")
        return []
    archive_urls = [url for url in resp.json().get('archives', [])[::-1] if f"/{year}/" in url]
    print(f"Found {len(archive_urls)} monthly archives for {year}.")
    
    for idx, archive_url in enumerate(archive_urls):
        month_resp = requests.get(archive_url, headers=headers)
        if month_resp.status_code != 200:
            print(f"Failed to fetch archive {archive_url} (status {month_resp.status_code})")
            print(f"Response: {month_resp.text}")
            continue
        month_games = month_resp.json().get('games', [])
        print(f"Archive {archive_url}: {len(month_games)} games found.")
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
    print(f"Collected {len(lost_games)} lost games in {year}.")
    return lost_games


def main():
    print("♟️  Chess LLM Improvement Suggestions")
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
    print(f"\n📊 Database initialized: {db.db_path}")
    
    # Show database stats
    stats = db.get_stats(username)
    print(f"📈 Database stats for {username}:")
    print(f"  Total games: {stats['total_games']}")
    print(f"  Analyzed games: {stats['analyzed_games']}")
    print(f"  Total errors: {stats['total_errors']}")
    
    print(f"\n🔍 Fetching all lost games from 2025 for: {username}")
    api = ChessComAPI()
    lost_games = get_lost_games_from_year(api, username, 2025)
    print(f"✅ Found {len(lost_games)} lost games from 2025")
    
    if not lost_games:
        print("No lost games found!")
        return
    
    # Add games to database and check which need analysis
    games_to_analyze = []
    cached_games = []
    
    for game in lost_games:
        if game.get('pgn'):
            game_id = db.add_game(game, username)
            game['game_id'] = game_id
            
            if db.game_analyzed(game_id):
                # Get cached analysis
                cached_errors = db.get_analysis(game_id)
                cached_games.append(cached_errors)
                print(f"📋 Using cached analysis for game {game_id[:8]}... ({len(cached_errors)} errors)")
            else:
                games_to_analyze.append(game)
                print(f"🔄 Game {game_id[:8]}... needs analysis")
    
    # Combine cached and new analysis
    all_errors = []
    all_errors.extend([error for game_errors in cached_games for error in game_errors])
    
    # Analyze new games if any
    if games_to_analyze:
        print(f"\n🔄 Analyzing {len(games_to_analyze)} new games...")
        explainer = ChessExplainer()
        
        # Prepare arguments for parallel analysis
        game_args = [(game.get('pgn'), username, game.get('game_id'), db) for game in games_to_analyze]
        
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(analyze_game_worker, arg) for arg in game_args]
            for i, future in enumerate(as_completed(futures), 1):
                errors = future.result()
                all_errors.extend(errors)
                print(f"Analyzed game {i}/{len(game_args)}: {len(errors)} errors found")
    else:
        print(f"\n✅ All {len(lost_games)} games already analyzed! Using cached results.")
    
    if not all_errors:
        print("No errors found in lost games!")
        return
    
    # Enhanced analysis for better GPT prompts
    type_counts = Counter(e['error_type'] for e in all_errors)
    move_counts = Counter(e['san_move'] for e in all_errors)
    
    # Analyze color-specific patterns
    white_errors = [e for e in all_errors if e.get('player') == 'White']
    black_errors = [e for e in all_errors if e.get('player') == 'Black']
    
    white_type_counts = Counter(e['error_type'] for e in white_errors)
    black_type_counts = Counter(e['error_type'] for e in black_errors)
    white_move_counts = Counter(e['san_move'] for e in white_errors)
    black_move_counts = Counter(e['san_move'] for e in black_errors)
    
    # Analyze move context and patterns
    opening_moves = ['e4', 'd4', 'Nf3', 'Nc3', 'Bf4', 'Bc4', 'O-O', 'O-O-O']
    middle_game_moves = ['f4', 'e5', 'd5', 'c5', 'b3', 'g3', 'h3', 'a3']
    tactical_moves = ['Nxe4', 'Bxf7', 'Qxd4', 'Rxe8', 'Nxf6']
    
    opening_errors = [e for e in all_errors if e['san_move'] in opening_moves]
    middle_game_errors = [e for e in all_errors if e['san_move'] in middle_game_moves]
    tactical_errors = [e for e in all_errors if e['san_move'] in tactical_moves]
    
    # Analyze evaluation patterns
    blunders = [e for e in all_errors if e['error_type'] == 'Blunder']
    mistakes = [e for e in all_errors if e['error_type'] == 'Mistake']
    inaccuracies = [e for e in all_errors if e['error_type'] == 'Inaccuracy']
    
    # Calculate average evaluation drops
    def avg_eval_drop(errors):
        if not errors:
            return 0
        return sum(abs(e.get('eval_change', 0)) for e in errors) / len(errors)
    
    avg_blunder_drop = avg_eval_drop(blunders)
    avg_mistake_drop = avg_eval_drop(mistakes)
    avg_inaccuracy_drop = avg_eval_drop(inaccuracies)
    
    # Find most problematic move combinations
    move_combinations = []
    for i in range(len(all_errors) - 1):
        move_combinations.append((all_errors[i]['san_move'], all_errors[i+1]['san_move']))
    combo_counts = Counter(move_combinations)
    
    print("\n=== DETAILED ANALYSIS ===")
    print(f"Total errors analyzed: {len(all_errors)}")
    print(f"Games analyzed: {len(lost_games)}")
    print(f"Average errors per game: {len(all_errors)/len(lost_games):.1f}")
    
    print(f"\nColor Performance:")
    print(f"  White errors: {len(white_errors)} ({len(white_errors)/len(all_errors)*100:.1f}%)")
    print(f"  Black errors: {len(black_errors)} ({len(black_errors)/len(all_errors)*100:.1f}%)")
    
    # Debug: Show a few sample errors with their color
    if all_errors:
        print(f"\nSample errors with colors:")
        for i, error in enumerate(all_errors[:5]):
            print(f"  {i+1}. {error['san_move']} ({error.get('player', 'Unknown')}) - {error['error_type']}")
    
    print("\nError Types (Overall):")
    for t, count in type_counts.most_common():
        print(f"  {t}: {count} ({count/len(all_errors)*100:.1f}%)")
    
    print("\nError Types (White):")
    for t, count in white_type_counts.most_common():
        print(f"  {t}: {count} ({count/len(white_errors)*100:.1f}%)" if white_errors else "  No white errors")
    
    print("\nError Types (Black):")
    for t, count in black_type_counts.most_common():
        print(f"  {t}: {count} ({count/len(black_errors)*100:.1f}%)" if black_errors else "  No black errors")
    
    print("\nMost Common Error Moves (Overall):")
    for move, count in move_counts.most_common(10):
        print(f"  {move}: {count} times")
    
    print("\nMost Common Error Moves (White):")
    for move, count in white_move_counts.most_common(5):
        print(f"  {move}: {count} times")
    
    print("\nMost Common Error Moves (Black):")
    for move, count in black_move_counts.most_common(5):
        print(f"  {move}: {count} times")
    
    print(f"\nPhase Analysis:")
    print(f"  Opening errors: {len(opening_errors)} ({len(opening_errors)/len(all_errors)*100:.1f}%)")
    print(f"  Middle game errors: {len(middle_game_errors)} ({len(middle_game_errors)/len(all_errors)*100:.1f}%)")
    print(f"  Tactical errors: {len(tactical_errors)} ({len(tactical_errors)/len(all_errors)*100:.1f}%)")
    
    print(f"\nEvaluation Impact:")
    print(f"  Average blunder: -{avg_blunder_drop:.2f} pawns")
    print(f"  Average mistake: -{avg_mistake_drop:.2f} pawns")
    print(f"  Average inaccuracy: -{avg_inaccuracy_drop:.2f} pawns")
    
    if combo_counts:
        print(f"\nMost Common Error Combinations:")
        for (move1, move2), count in combo_counts.most_common(3):
            print(f"  {move1} → {move2}: {count} times")
    
    # Create enhanced prompt with color context
    enhanced_prompt = f"""
You are a chess improvement coach analyzing a player's performance. Here is a detailed analysis of their last {len(lost_games)} lost games:

**GAME STATISTICS:**
- Total games analyzed: {len(lost_games)}
- Total errors found: {len(all_errors)}
- Average errors per game: {len(all_errors)/len(lost_games):.1f}

**COLOR PERFORMANCE:**
- White errors: {len(white_errors)} ({len(white_errors)/len(all_errors)*100:.1f}%)
- Black errors: {len(black_errors)} ({len(black_errors)/len(all_errors)*100:.1f}%)

**ERROR BREAKDOWN (OVERALL):**
{chr(10).join(f"- {t}: {count} ({count/len(all_errors)*100:.1f}%)" for t, count in type_counts.most_common())}

**ERROR BREAKDOWN BY COLOR:**
**WHITE PLAY:**
{chr(10).join(f"- {t}: {count} ({count/len(white_errors)*100:.1f}%)" for t, count in white_type_counts.most_common()) if white_errors else "- No white errors"}

**BLACK PLAY:**
{chr(10).join(f"- {t}: {count} ({count/len(black_errors)*100:.1f}%)" for t, count in black_type_counts.most_common()) if black_errors else "- No black errors"}

**MOST PROBLEMATIC MOVES (OVERALL):**
{chr(10).join(f"- {move}: {count} times" for move, count in move_counts.most_common(8))}

**MOST PROBLEMATIC MOVES BY COLOR:**
**WHITE MOVES:**
{chr(10).join(f"- {move}: {count} times" for move, count in white_move_counts.most_common(5)) if white_errors else "- No white errors"}

**BLACK MOVES:**
{chr(10).join(f"- {move}: {count} times" for move, count in black_move_counts.most_common(5)) if black_errors else "- No black errors"}

**GAME PHASE ANALYSIS:**
- Opening errors: {len(opening_errors)} ({len(opening_errors)/len(all_errors)*100:.1f}%)
- Middle game errors: {len(middle_game_errors)} ({len(middle_game_errors)/len(all_errors)*100:.1f}%)
- Tactical errors: {len(tactical_errors)} ({len(tactical_errors)/len(all_errors)*100:.1f}%)

**EVALUATION IMPACT:**
- Average blunder: -{avg_blunder_drop:.2f} pawns
- Average mistake: -{avg_mistake_drop:.2f} pawns  
- Average inaccuracy: -{avg_inaccuracy_drop:.2f} pawns

**ERROR PATTERNS:**
{chr(10).join(f"- {move1} → {move2}: {count} times" for (move1, move2), count in combo_counts.most_common(3)) if combo_counts else "- No clear patterns detected"}

Based on this detailed analysis, provide:

1. **3 SPECIFIC OPENING IMPROVEMENTS** - What should they study/focus on in openings? (Specify if advice differs for White vs Black)
2. **3 MIDDLE GAME STRATEGIES** - How can they improve their middle game play? (Address any color-specific weaknesses)
3. **3 TACTICAL TRAINING FOCUSES** - What tactical patterns should they practice? (Mention specific moves they struggle with)
4. **2 TIME MANAGEMENT TIPS** - How can they avoid time pressure mistakes?
5. **1 CONCRETE STUDY PLAN** - What should they do for the next 2 weeks to improve?

**IMPORTANT:** When giving advice about specific moves, always clarify whether you're talking about playing as White or Black. For example, say "When playing as White, avoid premature f4 pushes" or "As Black, be careful with early ...e5 moves."

Be very specific, mention the exact moves they struggle with for each color, and provide actionable advice they can implement immediately.
"""
    
    print("\n🤖 Asking GPT-4.1 for detailed improvement suggestions...")
    print("Enhanced prompt length:", len(enhanced_prompt), "characters")
    explainer = ChessExplainer()
    suggestions = explainer.explain_error('N/A', 'N/A', 0, enhanced_prompt)
    print("\n=== DETAILED IMPROVEMENT SUGGESTIONS ===\n")
    print(suggestions)
    
    # Save enhanced report
    outdir = "reports"
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    with open(os.path.join(outdir, f"improvement_{username}.md"), "w", encoding="utf-8") as f:
        f.write("# Chess Improvement Analysis\n\n")
        f.write(f"## Player: {username}\n\n")
        f.write(f"## Analysis Summary\n\n")
        f.write(f"- **Games Analyzed**: {len(lost_games)}\n")
        f.write(f"- **Total Errors**: {len(all_errors)}\n")
        f.write(f"- **Average Errors per Game**: {len(all_errors)/len(lost_games):.1f}\n\n")
        
        f.write("### Color Performance\n")
        f.write(f"- White errors: {len(white_errors)} ({len(white_errors)/len(all_errors)*100:.1f}%)\n")
        f.write(f"- Black errors: {len(black_errors)} ({len(black_errors)/len(all_errors)*100:.1f}%)\n\n")
        
        f.write("### Error Types (Overall)\n")
        for t, count in type_counts.most_common():
            f.write(f"- {t}: {count} ({count/len(all_errors)*100:.1f}%)\n")
        f.write("\n")
        
        f.write("### Error Types (White)\n")
        for t, count in white_type_counts.most_common():
            f.write(f"- {t}: {count} ({count/len(white_errors)*100:.1f}%)" if white_errors else "- No white errors\n")
        f.write("\n")
        
        f.write("### Error Types (Black)\n")
        for t, count in black_type_counts.most_common():
            f.write(f"- {t}: {count} ({count/len(black_errors)*100:.1f}%)" if black_errors else "- No black errors\n")
        f.write("\n")
        
        f.write("### Most Common Error Moves (Overall)\n")
        for move, count in move_counts.most_common(10):
            f.write(f"- {move}: {count} times\n")
        f.write("\n")
        
        f.write("### Most Common Error Moves (White)\n")
        for move, count in white_move_counts.most_common(5):
            f.write(f"- {move}: {count} times\n")
        f.write("\n")
        
        f.write("### Most Common Error Moves (Black)\n")
        for move, count in black_move_counts.most_common(5):
            f.write(f"- {move}: {count} times\n")
        f.write("\n")
        
        f.write("### Game Phase Analysis\n")
        f.write(f"- Opening errors: {len(opening_errors)} ({len(opening_errors)/len(all_errors)*100:.1f}%)\n")
        f.write(f"- Middle game errors: {len(middle_game_errors)} ({len(middle_game_errors)/len(all_errors)*100:.1f}%)\n")
        f.write(f"- Tactical errors: {len(tactical_errors)} ({len(tactical_errors)/len(all_errors)*100:.1f}%)\n\n")
        
        f.write("### Evaluation Impact\n")
        f.write(f"- Average blunder: -{avg_blunder_drop:.2f} pawns\n")
        f.write(f"- Average mistake: -{avg_mistake_drop:.2f} pawns\n")
        f.write(f"- Average inaccuracy: -{avg_inaccuracy_drop:.2f} pawns\n\n")
        
        f.write("## Improvement Suggestions\n\n")
        f.write(suggestions)
        f.write("\n")
        
        f.write("---\n")
        f.write(f"*Analysis generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"\n✅ Detailed analysis saved to {os.path.join(outdir, f'improvement_{username}.md')}")
    
    # Ask about database cleanup
    try:
        cleanup = input("\n🗑️  Clean up old analysis data (older than 30 days)? (y/N): ").strip().lower()
        if cleanup in ['y', 'yes']:
            db.clear_old_data(30)
            print("✅ Old data cleaned up")
    except KeyboardInterrupt:
        print("\nSkipping cleanup")

if __name__ == "__main__":
    main() 