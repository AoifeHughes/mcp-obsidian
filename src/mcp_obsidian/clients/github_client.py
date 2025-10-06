"""
GitHub API Client
"""

import os
import re
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from ..key_manager import KeyManager


class GitHubClient:
    """Client for interacting with GitHub API"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'ObsidianGitHubIntegration/1.0'
        })

        # Load GitHub token from centralized keys (if available)
        try:
            self._key_manager = KeyManager()
            github_token = self._key_manager.get_github_token()
            if github_token:
                self.session.headers['Authorization'] = f'token {github_token}'
        except:
            # Fallback to environment variable
            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token:
                self.session.headers['Authorization'] = f'token {github_token}'
            
    def fetch_issue(self, github_url: str) -> Dict[str, Any]:
        """Fetch issue data from GitHub API"""
        # Parse the URL
        parts = self.parse_github_url(github_url)
        
        # GitHub API endpoint
        api_url = f"https://api.github.com/repos/{parts['owner']}/{parts['repo']}/issues/{parts['issue_number']}"
        
        response = self.session.get(api_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue: {response.status_code} {response.text}")
            
        return response.json()
        
    def parse_github_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub issue URL to extract owner, repo, and issue number"""
        # Pattern: https://github.com/owner/repo/issues/number
        pattern = r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)'
        match = re.match(pattern, url)
        
        if not match:
            raise ValueError(f"Invalid GitHub issue URL: {url}")
            
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'issue_number': match.group(3)
        }