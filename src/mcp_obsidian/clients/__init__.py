"""
API Clients for external services
"""

from .igdb_client import IGDBClient
from .giantbomb_client import GiantBombClient
from .calibre_client import CalibreClient
from .github_client import GitHubClient

__all__ = [
    'IGDBClient',
    'GiantBombClient',
    'CalibreClient',
    'GitHubClient',
]
