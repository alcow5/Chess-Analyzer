"""
Utility functions for the Chess Insight Analyzer.
"""

import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, Optional

CONFIG_FILE = "config.json"

def load_environment() -> None:
    """Load environment variables from .env file."""
    load_dotenv()

def get_openai_api_key() -> str:
    """Get OpenAI API key from environment variables."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    return api_key

def save_username(username: str) -> None:
    """Save username to config file."""
    config = load_config()
    config['username'] = username
    save_config(config)

def load_username() -> Optional[str]:
    """Load username from config file."""
    config = load_config()
    return config.get('username')

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save config file: {e}")

def format_evaluation(eval_score: float) -> str:
    """Format evaluation score for display."""
    if eval_score > 0:
        return f"+{eval_score:.2f}"
    return f"{eval_score:.2f}"

def format_move_number(move_number: int) -> str:
    """Format move number for display."""
    return f"{move_number}."

def get_player_color(game_data: Dict[str, Any], username: str) -> str:
    """Determine if the player was white or black in the game."""
    white_player = game_data.get('white', {}).get('username', '').lower()
    black_player = game_data.get('black', {}).get('username', '').lower()
    username_lower = username.lower()
    
    if username_lower == white_player:
        return 'white'
    elif username_lower == black_player:
        return 'black'
    else:
        raise ValueError(f"Player {username} not found in game data")

def get_opponent_rating(game_data: Dict[str, Any], username: str) -> Optional[int]:
    """Get the opponent's rating from game data."""
    white_player = game_data.get('white', {})
    black_player = game_data.get('black', {})
    username_lower = username.lower()
    
    if username_lower == white_player.get('username', '').lower():
        return black_player.get('rating')
    elif username_lower == black_player.get('username', '').lower():
        return white_player.get('rating')
    else:
        return None

def get_game_result(game_data: Dict[str, Any], username: str) -> str:
    """Get the game result from the player's perspective."""
    result = game_data.get('result', '')
    username_lower = username.lower()
    white_player = game_data.get('white', {}).get('username', '').lower()
    
    if username_lower == white_player:
        if result == '1-0':
            return 'Win'
        elif result == '0-1':
            return 'Loss'
        else:
            return 'Draw'
    else:
        if result == '0-1':
            return 'Win'
        elif result == '1-0':
            return 'Loss'
        else:
            return 'Draw' 