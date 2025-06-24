#!/usr/bin/env python3
"""
Main application for Chess LLM Analyzer.
"""

import os
import sys
from fetch import ChessComAPI
from analyze import ChessAnalyzer
from explain import ChessExplainer
from report import ReportGenerator
from utils import load_environment, save_username, load_username

def main():
    """Main application entry point."""
    print("♟️  Chess LLM Analyzer")
    print("=" * 50)
    
    # Load environment variables
    load_environment()
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        print("Please set your OpenAI API key in the .env file.")
        return
    
    # Initialize components
    api = ChessComAPI()
    analyzer = ChessAnalyzer()
    explainer = ChessExplainer()
    report_gen = ReportGenerator()
    
    # Get or load username
    username = load_username()
    if not username:
        username = input("Enter Chess.com username: ").strip()
        if not username:
            print("Username required.")
            return
        save_username(username)
    else:
        print(f"Using saved username: {username}")
        change_username = input("Change username? (y/N): ").strip().lower()
        if change_username == 'y':
            username = input("Enter new Chess.com username: ").strip()
            if username:
                save_username(username)
            else:
                print("Username required.")
                return
    
    print(f"\n🔍 Fetching recent games for: {username}")
    
    # Fetch recent games
    games = api.get_user_games(username, count=5)
    
    if not games:
        print("❌ No games found for this username.")
        return
    
    print(f"✅ Found {len(games)} recent games")
    
    # Initialize Stockfish engine
    if not analyzer.initialize_engine():
        print("❌ Failed to initialize Stockfish engine.")
        print("Make sure Stockfish is installed and accessible.")
        return
    
    try:
        all_errors = []
        
        # Analyze each game
        for i, game in enumerate(games, 1):
            print(f"\n📊 Analyzing game {i}/{len(games)}...")
            
            pgn = game.get('pgn')
            if not pgn:
                print(f"  ⚠️  No PGN data for game {i}")
                continue
            
            # Get game info
            white = game.get('white', {}).get('username', 'Unknown')
            black = game.get('black', {}).get('username', 'Unknown')
            result = game.get('result', 'Unknown')
            
            print(f"  {white} vs {black} - {result}")
            
            # Analyze the game
            errors = analyzer.analyze_game(pgn, username)
            
            if errors:
                print(f"  ⚠️  Found {len(errors)} errors")
                # Add game context to errors
                for error in errors:
                    error['game_info'] = {
                        'game_number': i,
                        'white': white,
                        'black': black,
                        'result': result
                    }
                all_errors.extend(errors)
            else:
                print(f"  ✅ No errors detected")
        
        print(f"\n📈 Analysis Summary:")
        print(f"  Total games analyzed: {len(games)}")
        print(f"  Total errors found: {len(all_errors)}")
        
        if all_errors:
            # Count error types
            blunders = [e for e in all_errors if e['error_type'] == 'Blunder']
            mistakes = [e for e in all_errors if e['error_type'] == 'Mistake']
            inaccuracies = [e for e in all_errors if e['error_type'] == 'Inaccuracy']
            
            print(f"  Blunders: {len(blunders)}")
            print(f"  Mistakes: {len(mistakes)}")
            print(f"  Inaccuracies: {len(inaccuracies)}")
            
            # Sort errors by severity (blunders first, then by evaluation change)
            all_errors.sort(key=lambda x: (
                {'Blunder': 0, 'Mistake': 1, 'Inaccuracy': 2}[x['error_type']],
                x['eval_change']
            ))
            
            # Limit the number of errors to explain (most critical ones)
            max_errors_to_explain = min(15, len(all_errors))
            
            # Ask user for confirmation and allow them to adjust the number
            estimated_cost = explainer.estimate_cost(max_errors_to_explain)
            print(f"\n💰 Estimated cost for {max_errors_to_explain} explanations: ${estimated_cost:.3f}")
            
            adjust_errors = input(f"Explain top {max_errors_to_explain} errors? (y/N/a=adjust): ").strip().lower()
            
            if adjust_errors == 'a':
                try:
                    max_errors_to_explain = int(input(f"Enter number of errors to explain (1-{len(all_errors)}): "))
                    max_errors_to_explain = max(1, min(max_errors_to_explain, len(all_errors)))
                    estimated_cost = explainer.estimate_cost(max_errors_to_explain)
                    print(f"💰 New estimated cost: ${estimated_cost:.3f}")
                    errors_to_explain = all_errors[:max_errors_to_explain]
                    print(f"\n🤖 Getting AI explanations for top {max_errors_to_explain} errors...")
                    explained_errors = explainer.explain_errors_batch(errors_to_explain, max_errors_to_explain)
                except ValueError:
                    print("Invalid input, using default.")
                    errors_to_explain = all_errors[:max_errors_to_explain]
                    explained_errors = explainer.explain_errors_batch(errors_to_explain, max_errors_to_explain)
            elif adjust_errors != 'y':
                print("Skipping explanations to save costs.")
                explained_errors = []
            else:
                errors_to_explain = all_errors[:max_errors_to_explain]
                print(f"\n🤖 Getting AI explanations for top {max_errors_to_explain} errors...")
                explained_errors = explainer.explain_errors_batch(errors_to_explain, max_errors_to_explain)
            
            # Generate report
            print(f"\n📝 Generating report...")
            report_content = report_gen.generate_report(username, games, explained_errors)
            
            # Save report
            filename = report_gen.save_report(report_content, username)
            print(f"✅ Report saved to: {filename}")
            
            # Display summary in terminal
            print(f"\n📋 Error Summary (Top {len(explained_errors)}):")
            for error in explained_errors:
                game_info = error['game_info']
                print(f"\n{error['error_type']} in Game {game_info['game_number']} (Move {error['move_number']}):")
                print(f"  {error['san_move']} - Evaluation change: {error['eval_change']:.2f}")
                print(f"  {error.get('explanation', 'No explanation available.')[:100]}...")
            
            # Show cost summary
            if hasattr(explainer, 'total_cost'):
                print(f"\n💰 Total API cost: ${explainer.total_cost:.3f}")
        else:
            print("🎉 No errors found! Great playing!")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
    finally:
        analyzer.close_engine()

if __name__ == "__main__":
    main() 