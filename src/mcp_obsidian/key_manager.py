"""
Centralized API Key Manager

Loads and provides access to all API keys and configuration from the Keys folder.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional


class KeyManager:
    """Centralized manager for API keys and configuration"""

    def __init__(self, vault_path: Optional[str] = None):
        """
        Initialize the KeyManager.

        Args:
            vault_path: Path to the Obsidian vault root.
                       If None, will attempt to auto-detect from file location.
        """
        if vault_path is None:
            # Auto-detect vault path
            # This file is in: AI Tools/mcp-obsidian/src/mcp_obsidian/key_manager.py
            # Vault root is 4 levels up
            vault_path = Path(__file__).parent.parent.parent.parent.parent

        self.vault_path = Path(vault_path)
        self.keys_path = self.vault_path / "Keys" / "api_keys.json"
        self._keys: Optional[Dict[str, Any]] = None
        self._initialization_error: Optional[str] = None

        # Don't fail immediately - allow lazy initialization
        # Check if file exists but don't raise until keys are actually needed
        if not self.keys_path.exists():
            self._initialization_error = (
                f"API keys file not found at {self.keys_path}. "
                f"Please create it with required API keys. "
                f"See the documentation for details on setting up Keys/api_keys.json"
            )

    def load_keys(self) -> Dict[str, Any]:
        """Load all keys from the JSON file (cached after first load)"""
        # Check if there was an initialization error
        if self._initialization_error:
            raise FileNotFoundError(self._initialization_error)

        if self._keys is None:
            try:
                with open(self.keys_path, 'r') as f:
                    self._keys = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in {self.keys_path}. "
                    f"Please check the file format. Error: {e}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load API keys from {self.keys_path}: {e}"
                )
        return self._keys

    def reload_keys(self) -> Dict[str, Any]:
        """Force reload keys from disk"""
        self._keys = None
        return self.load_keys()

    # IGDB API Keys
    def get_igdb_keys(self) -> Tuple[str, str]:
        """Get IGDB API credentials (Twitch Client ID and Secret)"""
        keys = self.load_keys()
        return (
            keys["igdb"]["client_id"],
            keys["igdb"]["client_secret"]
        )

    def get_igdb_client_id(self) -> str:
        """Get IGDB Twitch Client ID"""
        return self.get_igdb_keys()[0]

    def get_igdb_client_secret(self) -> str:
        """Get IGDB Twitch Client Secret"""
        return self.get_igdb_keys()[1]

    # GiantBomb API Keys
    def get_giantbomb_api_key(self) -> str:
        """Get GiantBomb API key"""
        keys = self.load_keys()
        return keys["giantbomb"]["api_key"]

    # Obsidian Local REST API
    def get_obsidian_config(self) -> Dict[str, Any]:
        """Get Obsidian Local REST API configuration"""
        keys = self.load_keys()
        return keys["obsidian"]

    def get_obsidian_api_key(self) -> str:
        """Get Obsidian Local REST API key"""
        return self.get_obsidian_config()["api_key"]

    def get_obsidian_host(self) -> str:
        """Get Obsidian API host"""
        return self.get_obsidian_config().get("host", "127.0.0.1")

    def get_obsidian_port(self) -> int:
        """Get Obsidian API port"""
        return self.get_obsidian_config().get("port", 27124)

    # Calibre Configuration
    def get_calibre_library_path(self) -> str:
        """Get Calibre library path"""
        keys = self.load_keys()
        return keys["calibre"]["library_path"]

    # LLM Configuration
    def get_llm_config(self) -> Dict[str, str]:
        """Get LLM API configuration"""
        keys = self.load_keys()
        return keys["llm"]

    def get_llm_api_base(self) -> str:
        """Get LLM API base URL"""
        return self.get_llm_config()["api_base"]

    def get_llm_model(self) -> str:
        """Get LLM model name"""
        return self.get_llm_config()["model"]

    # GitHub Configuration
    def get_github_token(self) -> str:
        """Get GitHub personal access token"""
        keys = self.load_keys()
        return keys["github"].get("token", "")

    # Generic getter for any key path
    def get(self, key_path: str) -> Any:
        """
        Get a value using dot notation path.

        Example:
            km.get("igdb.client_id")
            km.get("llm.api_base")

        Args:
            key_path: Dot-separated path to the key (e.g., "igdb.client_id")

        Returns:
            The value at that path

        Raises:
            KeyError: If the path doesn't exist
        """
        keys = self.load_keys()
        parts = key_path.split(".")

        current = keys
        for part in parts:
            if isinstance(current, dict):
                current = current[part]
            else:
                raise KeyError(f"Invalid key path: {key_path}")

        return current
