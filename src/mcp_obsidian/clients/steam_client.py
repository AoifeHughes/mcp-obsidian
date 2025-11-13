"""
Steam API Client
"""

import json
import time
import requests
from typing import Dict, Any, List, Optional

from ..key_manager import KeyManager


class SteamClient:
    """Client for interacting with Steam API"""

    STEAM_API_BASE_URL = "http://api.steampowered.com"
    STEAM_STORE_API_URL = "https://store.steampowered.com/api"

    def __init__(self):
        try:
            self._key_manager = KeyManager()
            self.api_key, self.steamid64 = self._key_manager.get_steam_keys()
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Steam API keys. "
                f"Please set up Keys/api_keys.json with valid Steam credentials. "
                f"Error: {e}"
            )

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'ObsidianGameDB/1.0'})
        self.last_api_call = 0

    def get_owned_games(self, include_free_games: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of games owned by the Steam user.

        Args:
            include_free_games: Include free games in the results

        Returns:
            List of game dictionaries with appid, name, playtime, etc.
        """
        self._rate_limit()

        url = f"{self.STEAM_API_BASE_URL}/IPlayerService/GetOwnedGames/v0001/"
        params = {
            'key': self.api_key,
            'steamid': self.steamid64,
            'format': 'json',
            'include_appinfo': 1,
            'include_played_free_games': 1 if include_free_games else 0
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get('response', {}).get('games', [])
        else:
            raise Exception(f"Steam API error: {response.status_code} {response.text}")

    def get_game_details(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific game from Steam Store API.

        Args:
            appid: Steam application ID

        Returns:
            Dictionary with detailed game information, or None if not found
        """
        self._rate_limit()

        url = f"{self.STEAM_STORE_API_URL}/appdetails"
        params = {
            'appids': appid,
            'l': 'english'  # Language
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            app_data = data.get(str(appid), {})

            if app_data.get('success'):
                return app_data.get('data')

        return None

    def get_recently_played_games(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recently played games.

        Args:
            count: Number of games to return (max 100)

        Returns:
            List of recently played games with playtime data
        """
        self._rate_limit()

        url = f"{self.STEAM_API_BASE_URL}/IPlayerService/GetRecentlyPlayedGames/v0001/"
        params = {
            'key': self.api_key,
            'steamid': self.steamid64,
            'format': 'json',
            'count': min(count, 100)
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get('response', {}).get('games', [])
        else:
            raise Exception(f"Steam API error: {response.status_code} {response.text}")

    def get_player_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get player profile information.

        Returns:
            Dictionary with player profile data
        """
        self._rate_limit()

        url = f"{self.STEAM_API_BASE_URL}/ISteamUser/GetPlayerSummaries/v0002/"
        params = {
            'key': self.api_key,
            'steamids': self.steamid64,
            'format': 'json'
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            players = data.get('response', {}).get('players', [])
            return players[0] if players else None
        else:
            raise Exception(f"Steam API error: {response.status_code} {response.text}")

    def get_game_achievements(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Get achievement data for a specific game.

        Args:
            appid: Steam application ID

        Returns:
            Dictionary with achievement data, or None if not available
        """
        self._rate_limit()

        url = f"{self.STEAM_API_BASE_URL}/ISteamUserStats/GetPlayerAchievements/v0001/"
        params = {
            'key': self.api_key,
            'steamid': self.steamid64,
            'appid': appid,
            'format': 'json',
            'l': 'english'
        }

        response = self.session.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get('playerstats', {}).get('success'):
                return data.get('playerstats', {})

        return None

    def get_header_image_url(self, appid: int) -> str:
        """
        Get the header image URL for a game.

        Args:
            appid: Steam application ID

        Returns:
            URL string for the game's header image
        """
        return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"

    def get_library_image_url(self, appid: int) -> str:
        """
        Get the library capsule image URL for a game (better quality).

        Args:
            appid: Steam application ID

        Returns:
            URL string for the game's library image
        """
        return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg"

    def _rate_limit(self):
        """Ensure proper spacing between API requests"""
        # Steam API has rate limits, be conservative
        elapsed = time.time() - self.last_api_call
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
        self.last_api_call = time.time()
