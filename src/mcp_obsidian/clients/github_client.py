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
        api_url = f"https://api.github.com/repos/{parts['owner']}/{parts['repo']}/issues/{parts['number']}"

        response = self.session.get(api_url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue: {response.status_code} {response.text}")

        return response.json()

    def fetch_pull_request(self, github_url: str) -> Dict[str, Any]:
        """Fetch pull request data from GitHub API"""
        # Parse the URL
        parts = self.parse_github_url(github_url)

        # GitHub API endpoint for PRs
        api_url = f"https://api.github.com/repos/{parts['owner']}/{parts['repo']}/pulls/{parts['number']}"

        response = self.session.get(api_url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch pull request: {response.status_code} {response.text}")

        return response.json()

    def parse_github_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub issue or PR URL to extract owner, repo, number, and type"""
        # Pattern for issues: https://github.com/owner/repo/issues/number
        issue_pattern = r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)'
        issue_match = re.match(issue_pattern, url)

        if issue_match:
            return {
                'owner': issue_match.group(1),
                'repo': issue_match.group(2),
                'number': issue_match.group(3),
                'type': 'issue'
            }

        # Pattern for PRs: https://github.com/owner/repo/pull/number
        pr_pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        pr_match = re.match(pr_pattern, url)

        if pr_match:
            return {
                'owner': pr_match.group(1),
                'repo': pr_match.group(2),
                'number': pr_match.group(3),
                'type': 'pull_request'
            }

        raise ValueError(f"Invalid GitHub issue or PR URL: {url}. Expected format: https://github.com/owner/repo/issues/number or https://github.com/owner/repo/pull/number")