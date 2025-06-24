"""
Report generation for chess analysis results.
"""

from typing import List, Dict, Any
from utils import format_evaluation, format_move_number
import os
from datetime import datetime

class ReportGenerator:
    """Generates formatted reports from chess analysis."""
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_game_report(self, username: str, game_data: Dict[str, Any], 
                           blunders: List[Dict[str, Any]], 
                           explanations: List[Dict[str, Any]]) -> str:
        """
        Generate a detailed report for a single game.
        
        Args:
            username: Chess.com username
            game_data: Game data from Chess.com API
            blunders: List of blunder data
            explanations: List of GPT-4 explanations
            
        Returns:
            Formatted report string
        """
        from utils import get_player_color, get_opponent_rating, get_game_result
        
        player_color = get_player_color(game_data, username)
        opponent_rating = get_opponent_rating(game_data, username)
        result = get_game_result(game_data, username)
        
        # Game header
        report = f"""# Chess Game Analysis Report

**Player**: {username} ({player_color})
**Opponent**: {game_data.get('black' if player_color == 'white' else 'white', {}).get('username', 'Unknown')}
**Opponent Rating**: {opponent_rating or 'Unknown'}
**Result**: {result}
**Date**: {datetime.fromtimestamp(game_data.get('end_time', 0)).strftime('%Y-%m-%d %H:%M')}

## Game Summary

- **Total Moves**: {len(blunders) + 1 if blunders else 'Unknown'}
- **Blunders Found**: {len(blunders)}
- **Performance**: {'Good' if len(blunders) <= 1 else 'Needs Improvement' if len(blunders) <= 3 else 'Poor'}

"""
        
        if not blunders:
            report += "## Analysis\n\n🎉 **No blunders detected!** This was a well-played game.\n\n"
        else:
            report += "## Blunder Analysis\n\n"
            
            for i, (blunder, explanation) in enumerate(zip(blunders, explanations), 1):
                report += self._format_blunder_section(i, blunder, explanation, player_color)
        
        return report
    
    def _format_blunder_section(self, blunder_num: int, blunder: Dict[str, Any], 
                               explanation: Dict[str, Any], player_color: str) -> str:
        """
        Format a single blunder section.
        
        Args:
            blunder_num: Blunder number
            blunder: Blunder data
            explanation: GPT-4 explanation
            
        Returns:
            Formatted blunder section
        """
        move_num = blunder['move_number']
        move = blunder['san_move']
        eval_before = blunder['eval_before']
        eval_after = blunder['eval_after']
        eval_change = blunder['eval_change']
        
        section = f"""### Blunder #{blunder_num}: Move {format_move_number(move_num)}{move}

**Position**: `{blunder['fen_before']}`
**Evaluation Before**: {format_evaluation(eval_before)}
**Evaluation After**: {format_evaluation(eval_after)}
**Evaluation Change**: {format_evaluation(eval_change)}

#### Analysis

**Why this was a blunder:**
{explanation.get('why_blunder', 'No explanation available.')}

**What should have been played:**
{explanation.get('correct_plan', 'No suggestion available.')}

**Lesson learned:**
{explanation.get('lesson_learned', 'No lesson provided.')}

---
"""
        return section
    
    def generate_summary_report(self, username: str, games_analysis: List[Dict[str, Any]]) -> str:
        """
        Generate a summary report for all analyzed games.
        
        Args:
            username: Chess.com username
            games_analysis: List of game analysis results
            
        Returns:
            Formatted summary report
        """
        total_games = len(games_analysis)
        total_blunders = sum(len(game.get('blunders', [])) for game in games_analysis)
        wins = sum(1 for game in games_analysis if game.get('result') == 'Win')
        losses = sum(1 for game in games_analysis if game.get('result') == 'Loss')
        draws = total_games - wins - losses
        
        report = f"""# Chess Analysis Summary Report

**Player**: {username}
**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Games Analyzed**: {total_games}

## Overall Statistics

- **Games Won**: {wins}
- **Games Lost**: {losses}
- **Games Drawn**: {draws}
- **Win Rate**: {(wins/total_games*100):.1f}%
- **Total Blunders**: {total_blunders}
- **Average Blunders per Game**: {(total_blunders/total_games):.1f}

## Performance Assessment

"""
        
        if total_blunders == 0:
            report += "🎉 **Excellent performance!** No blunders detected across all games.\n\n"
        elif total_blunders <= total_games:
            report += "✅ **Good performance!** Low blunder rate indicates solid play.\n\n"
        elif total_blunders <= total_games * 2:
            report += "⚠️ **Moderate performance.** Some improvement needed in tactical awareness.\n\n"
        else:
            report += "❌ **Needs improvement.** High blunder rate suggests tactical training is needed.\n\n"
        
        # Game-by-game summary
        report += "## Game-by-Game Summary\n\n"
        for i, game in enumerate(games_analysis, 1):
            result = game.get('result', 'Unknown')
            opponent = game.get('opponent', 'Unknown')
            blunders = len(game.get('blunders', []))
            
            report += f"{i}. **{result}** vs {opponent} - {blunders} blunder{'s' if blunders != 1 else ''}\n"
        
        return report
    
    def generate_report(self, username: str, games: List[Dict[str, Any]], 
                       explained_errors: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive report for all games and errors.
        
        Args:
            username: Chess.com username
            games: List of game data
            explained_errors: List of errors with explanations
            
        Returns:
            Formatted report string
        """
        total_games = len(games)
        total_errors = len(explained_errors)
        
        # Count error types
        blunders = [e for e in explained_errors if e['error_type'] == 'Blunder']
        mistakes = [e for e in explained_errors if e['error_type'] == 'Mistake']
        inaccuracies = [e for e in explained_errors if e['error_type'] == 'Inaccuracy']
        
        report = f"""# Chess LLM Analysis Report

**Player**: {username}
**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Games Analyzed**: {total_games}

## Overall Statistics

- **Total Errors Found**: {total_errors}
- **Blunders**: {len(blunders)}
- **Mistakes**: {len(mistakes)}
- **Inaccuracies**: {len(inaccuracies)}
- **Average Errors per Game**: {(total_errors/total_games):.1f}

## Performance Assessment

"""
        
        if total_errors == 0:
            report += "🎉 **Excellent performance!** No errors detected across all games.\n\n"
        elif len(blunders) == 0:
            report += "✅ **Good performance!** No blunders detected, only minor mistakes.\n\n"
        elif len(blunders) <= total_games:
            report += "⚠️ **Moderate performance.** Some blunders detected, tactical training recommended.\n\n"
        else:
            report += "❌ **Needs improvement.** High blunder rate suggests tactical training is needed.\n\n"
        
        # Game-by-game summary
        report += "## Game-by-Game Summary\n\n"
        for i, game in enumerate(games, 1):
            white = game.get('white', {}).get('username', 'Unknown')
            black = game.get('black', {}).get('username', 'Unknown')
            result = game.get('result', 'Unknown')
            
            # Count errors for this game
            game_errors = [e for e in explained_errors if e.get('game_info', {}).get('game_number') == i]
            game_blunders = [e for e in game_errors if e['error_type'] == 'Blunder']
            game_mistakes = [e for e in game_errors if e['error_type'] == 'Mistake']
            game_inaccuracies = [e for e in game_errors if e['error_type'] == 'Inaccuracy']
            
            report += f"{i}. **{white} vs {black}** - {result}\n"
            report += f"   - Errors: {len(game_errors)} (Blunders: {len(game_blunders)}, Mistakes: {len(game_mistakes)}, Inaccuracies: {len(game_inaccuracies)})\n\n"
        
        # Detailed error analysis
        if explained_errors:
            report += "## Detailed Error Analysis\n\n"
            
            for i, error in enumerate(explained_errors, 1):
                game_info = error.get('game_info', {})
                game_num = game_info.get('game_number', 'Unknown')
                white = game_info.get('white', 'Unknown')
                black = game_info.get('black', 'Unknown')
                
                report += f"### Error #{i}: {error['error_type']} in Game {game_num}\n\n"
                report += f"**Game**: {white} vs {black}\n"
                report += f"**Move**: {error['move_number']}. {error['san_move']} ({error['player']})\n"
                report += f"**Evaluation Change**: {error['eval_change']:.2f} pawns\n"
                report += f"**Position**: `{error['fen_before']}`\n\n"
                report += f"**Analysis**:\n{error.get('explanation', 'No explanation available.')}\n\n"
                report += "---\n\n"
        
        return report
    
    def save_report(self, report_content: str, username: str) -> str:
        """
        Save a report to file.
        
        Args:
            report_content: Report content
            username: Username for filename generation
            
        Returns:
            Full path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"chess_analysis_{username}_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return filepath
    
    def print_report(self, report_content: str):
        """
        Print a report to console with basic formatting.
        
        Args:
            report_content: Report content to print
        """
        # Simple console formatting
        lines = report_content.split('\n')
        for line in lines:
            if line.startswith('# '):
                print(f"\n{'='*50}")
                print(line[2:].upper())
                print('='*50)
            elif line.startswith('## '):
                print(f"\n{'-'*30}")
                print(line[3:])
                print('-'*30)
            elif line.startswith('### '):
                print(f"\n{line[4:]}")
                print('-'*20)
            elif line.startswith('**') and line.endswith('**'):
                print(f"\n{line}")
            else:
                print(line) 