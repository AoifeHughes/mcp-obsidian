"""
IGDB API Client
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..key_manager import KeyManager


class IGDBClient:
    """Client for interacting with IGDB API"""

    # API Configuration - Load from centralized keys
    IGDB_BASE_URL = "https://api.igdb.com/v4"

    def __init__(self):
        try:
            self._key_manager = KeyManager()
            self.TWITCH_CLIENT_ID, self.TWITCH_CLIENT_SECRET = self._key_manager.get_igdb_keys()
        except Exception as e:
            raise RuntimeError(
                f"Failed to load IGDB API keys. "
                f"Please set up Keys/api_keys.json with valid IGDB credentials. "
                f"Error: {e}"
            )

        # Store token cache in Keys directory alongside api_keys.json
        keys_dir = self._key_manager.keys_dir
        self.TOKEN_CACHE_FILE = keys_dir / "igdb_token_cache.json"

        self.token = None
        self.token_expires_at = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'ObsidianGameDB/1.0'})
        self.last_api_call = 0
        
    def search_games(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for games by title"""
        self._ensure_token()
        self._rate_limit()
        
        headers = {
            'Client-ID': self.TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {self.token}'
        }
        
        # Build query
        fields = [
            'name', 'summary', 'first_release_date', 'platforms.name',
            'genres.name', 'themes.name', 'cover.image_id', 'involved_companies.company.name'
        ]
        
        query_str = f'''
        search "{query}";
        fields {','.join(fields)};
        limit {limit};
        '''
        
        response = self.session.post(
            f"{self.IGDB_BASE_URL}/games",
            headers=headers,
            data=query_str
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"IGDB API error: {response.status_code} {response.text}")
            
    def get_game_by_id(self, game_id: int) -> Dict[str, Any]:
        """Get detailed game information by ID"""
        self._ensure_token()
        self._rate_limit()
        
        headers = {
            'Client-ID': self.TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {self.token}'
        }
        
        fields = [
            'name', 'summary', 'storyline', 'first_release_date',
            'platforms.name', 'genres.name', 'themes.name', 
            'keywords.name', 'game_modes.name', 'player_perspectives.name',
            'cover.image_id', 'screenshots.image_id',
            'involved_companies.company.name', 'involved_companies.developer',
            'involved_companies.publisher', 'websites.url'
        ]
        
        query_str = f'''
        where id = {game_id};
        fields {','.join(fields)};
        '''
        
        response = self.session.post(
            f"{self.IGDB_BASE_URL}/games",
            headers=headers,
            data=query_str
        )
        
        if response.status_code == 200:
            games = response.json()
            return games[0] if games else None
        else:
            raise Exception(f"IGDB API error: {response.status_code} {response.text}")
            
    def _ensure_token(self):
        """Ensure we have a valid access token"""
        if self.token and self.token_expires_at and time.time() < self.token_expires_at:
            return
            
        # Try to load cached token
        if self._load_cached_token():
            return
            
        # Get new token
        self._get_new_token()
        
    def _get_new_token(self):
        """Get a new access token from Twitch"""
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.TWITCH_CLIENT_ID,
            "client_secret": self.TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            self.token_expires_at = time.time() + token_data["expires_in"] - 60
            self._save_token_cache()
        else:
            raise Exception(f"Failed to get access token: {response.status_code} {response.text}")
            
    def _load_cached_token(self) -> bool:
        """Load token from cache if valid"""
        cache_path = Path(self.TOKEN_CACHE_FILE)
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)

            if cache.get('expires_at', 0) > time.time():
                self.token = cache['token']
                self.token_expires_at = cache['expires_at']
                return True
        except:
            pass

        return False

    def _save_token_cache(self):
        """Save token to cache"""
        cache = {
            'token': self.token,
            'expires_at': self.token_expires_at
        }

        # Ensure Keys directory exists
        cache_path = Path(self.TOKEN_CACHE_FILE)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_path, 'w') as f:
            json.dump(cache, f)
            
    def _rate_limit(self):
        """Ensure proper spacing between API requests"""
        elapsed = time.time() - self.last_api_call
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
        self.last_api_call = time.time()