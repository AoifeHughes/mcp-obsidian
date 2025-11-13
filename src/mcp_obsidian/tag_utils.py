"""
Tag utilities for ensuring Obsidian-compliant tags.

Valid tag characters: a-z, A-Z, 0-9, hyphen (-), underscore (_)
"""

import re
from typing import List


def sanitize_tag(tag: str) -> str:
    """
    Clean a tag to be Obsidian-compliant.

    Rules:
    1. Remove prefixes with slashes (genre/, platform/, etc.)
    2. Remove parentheses and their content: role-playing-(rpg) -> role-playing-rpg
    3. Replace spaces with hyphens
    4. Remove or replace special characters
    5. Convert to lowercase
    6. Remove multiple consecutive hyphens
    7. Strip leading/trailing hyphens

    Args:
        tag: Raw tag string

    Returns:
        Cleaned tag string safe for Obsidian

    Examples:
        >>> sanitize_tag("genre/action")
        'action'
        >>> sanitize_tag("Role-Playing (RPG)")
        'role-playing-rpg'
        >>> sanitize_tag("Hack & Slash")
        'hack-and-slash'
    """
    if not isinstance(tag, str):
        return str(tag)

    # Remove any prefix with slash (genre/, platform/, etc.)
    if '/' in tag:
        tag = tag.split('/')[-1]

    # Replace (content) with -content
    # turn-based-strategy-(tbs) -> turn-based-strategy-tbs
    tag = re.sub(r'\(([^)]+)\)', r'-\1', tag)

    # Replace apostrophes and quotes
    tag = tag.replace("'", "").replace('"', '')

    # Replace & with -and-
    tag = tag.replace('&', '-and-')

    # Replace spaces with hyphens
    tag = tag.replace(' ', '-')

    # Remove any character that's not alphanumeric, hyphen, or underscore
    tag = re.sub(r'[^a-zA-Z0-9\-_]', '', tag)

    # Convert to lowercase
    tag = tag.lower()

    # Replace multiple hyphens with single hyphen
    tag = re.sub(r'-+', '-', tag)

    # Remove leading/trailing hyphens
    tag = tag.strip('-')

    return tag


def sanitize_tags(tags: List[str]) -> List[str]:
    """
    Clean a list of tags, removing duplicates.

    Args:
        tags: List of raw tag strings

    Returns:
        List of cleaned, unique tags
    """
    cleaned = []
    seen = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue

        clean_tag = sanitize_tag(tag)

        if clean_tag and clean_tag not in seen:
            cleaned.append(clean_tag)
            seen.add(clean_tag)

    return cleaned


def make_genre_tags(genres: List[str]) -> List[str]:
    """
    Convert genre names to valid tags.

    Args:
        genres: List of genre names (e.g., ["Role-playing (RPG)", "Strategy"])

    Returns:
        List of cleaned genre tags (e.g., ["role-playing-rpg", "strategy"])
    """
    return sanitize_tags(genres)
