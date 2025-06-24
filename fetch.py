"""
Chess.com API integration for fetching user games.
"""

import requests
from typing import List, Dict, Any, Optional
import time

class ChessComAPI:
    """Handles interactions with the Chess.com API."""
    
    BASE_URL = "https://api.chess.com/pub"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Chess-Insight-Analyzer/1.0'
        })
    
    def get_user_games(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch recent games for a user.
        
        Args:
            username: Chess.com username
            count: Number of games to fetch (default: 5)
            
        Returns:
            List of game data dictionaries
        """
        try:
            # Get user's game archives
            archives_url = f"{self.BASE_URL}/player/{username}/games/archives"
            response = self.session.get(archives_url)
            response.raise_for_status()
            
            archives_data = response.json()
            archives = archives_data.get('archives', [])
            
            if not archives:
                print(f"No games found for user {username}")
                return []
            
            # Get games from the most recent archives
            all_games = []
            for archive_url in archives[-3:]:  # Last 3 months
                try:
                    games_response = self.session.get(archive_url)
                    games_response.raise_for_status()
                    games_data = games_response.json()
                    games = games_data.get('games', [])
                    all_games.extend(games)
                    
                    # Rate limiting
                    time.sleep(0.1)
                    
                except requests.RequestException as e:
                    print(f"Error fetching games from {archive_url}: {e}")
                    continue
            
            # Sort by date and take the most recent
            all_games.sort(key=lambda x: x.get('end_time', 0), reverse=True)
            return all_games[:count]
            
        except requests.RequestException as e:
            print(f"Error fetching games for {username}: {e}")
            return []
    
    def get_game_pgn(self, game_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract PGN from game data.
        
        Args:
            game_data: Game data dictionary from Chess.com API
            
        Returns:
            PGN string or None if not available
        """
        return game_data.get('pgn')
    
    def validate_username(self, username: str) -> bool:
        """
        Validate if a username exists on Chess.com.
        
        Args:
            username: Chess.com username to validate
            
        Returns:
            True if username exists, False otherwise
        """
        try:
            profile_url = f"{self.BASE_URL}/player/{username}"
            response = self.session.get(profile_url)
            return response.status_code == 200
        except requests.RequestException:
            return False 