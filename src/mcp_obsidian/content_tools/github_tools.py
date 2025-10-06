"""
GitHub Tools - MCP tools for GitHub issue import and management
"""

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from ..clients import GitHubClient
from ..key_manager import KeyManager
from .. import obsidian


class GitHubToolHandler:
    """Handler for GitHub-related MCP tools"""

    def __init__(self):
        self.name = "obsidian_github_tools"
        self._key_manager = KeyManager()
        self.github_client = GitHubClient()

        # Get Obsidian API config
        self.obsidian_api_key = self._key_manager.get_obsidian_api_key()
        self.obsidian_host = self._key_manager.get_obsidian_host()
        self.obsidian_port = self._key_manager.get_obsidian_port()

        # Get LLM config for task extraction
        self.llm_api_base = self._key_manager.get_llm_api_base()
        self.llm_model = self._key_manager.get_llm_model()

    def get_tool_descriptions(self) -> List[Tool]:
        """Return all GitHub-related tool descriptions"""
        return [
            Tool(
                name="obsidian_import_github_issue",
                description="Import a GitHub issue as an Obsidian task. Uses AI to extract priority, tags, and action items from the issue content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "github_url": {
                            "type": "string",
                            "description": "GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)",
                            "format": "uri"
                        },
                        "project_folder": {
                            "type": "string",
                            "description": "Project folder path where the task should be created (e.g., 'Work/Turing/Projects/MyProject')"
                        },
                        "use_llm": {
                            "type": "boolean",
                            "description": "Use LLM to extract task metadata (default: true)",
                            "default": True
                        }
                    },
                    "required": ["github_url", "project_folder"]
                }
            )
        ]

    def run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a GitHub tool"""
        if tool_name == "obsidian_import_github_issue":
            return self._import_issue(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _import_issue(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Import a GitHub issue as an Obsidian task"""
        github_url = args["github_url"]
        project_folder = args["project_folder"]
        use_llm = args.get("use_llm", True)

        try:
            # Fetch issue data from GitHub
            issue_data = self.github_client.fetch_issue(github_url)

            # Extract task information
            if use_llm:
                task_info = self._extract_task_info_with_llm(issue_data, project_folder)
            else:
                task_info = self._extract_task_info_simple(issue_data, project_folder)

            # Create the task file
            filepath = self._create_task_file(task_info, project_folder)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Created task from GitHub issue: {filepath}\n\nTitle: {task_info['title']}\nPriority: {task_info['priority']}\nIssue: #{task_info['github_issue_number']}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error importing issue: {str(e)}"
                )
            ]

    def _extract_task_info_simple(self, issue_data: Dict[str, Any], project_folder: str) -> Dict[str, Any]:
        """Extract task info without LLM (simple extraction)"""
        # Determine priority from labels
        priority = "🟡 Medium"
        labels = [label['name'].lower() for label in issue_data.get('labels', [])]

        if any(l in labels for l in ['critical', 'urgent', 'high']):
            priority = "🔴 High"
        elif any(l in labels for l in ['low', 'minor']):
            priority = "🟢 Low"

        # Extract action items from issue body
        action_items = []
        body = issue_data.get('body', '') or ''

        # Look for task lists
        task_pattern = r'-\s*\[[ x]\]\s*(.+)'
        tasks = re.findall(task_pattern, body)
        action_items.extend(tasks[:5])  # Limit to 5 items

        if not action_items:
            action_items = [f"Review and implement issue #{issue_data['number']}"]

        # Generate tags from labels
        tags = [label['name'].lower().replace(' ', '-') for label in issue_data.get('labels', [])]

        return {
            'title': issue_data['title'],
            'priority': priority,
            'tags': tags,
            'summary': (issue_data.get('body', '') or '')[:500],  # First 500 chars
            'action_items': action_items,
            'github_url': issue_data['html_url'],
            'github_issue_number': issue_data['number'],
            'github_repo': f"{issue_data['html_url'].split('/')[3]}/{issue_data['html_url'].split('/')[4]}",
            'resources': []
        }

    def _extract_task_info_with_llm(self, issue_data: Dict[str, Any], project_folder: str) -> Dict[str, Any]:
        """Extract task info using LLM for intelligent parsing"""
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self.llm_api_base, api_key="sk-placeholder")

            system_prompt = """You are a task extraction assistant. Given a GitHub issue, extract relevant information to create an Obsidian task.

Return a JSON object with these fields:
- title: A concise task title (max 100 chars)
- priority: One of "🟢 Low", "🟡 Medium", "🔴 High", "🟣 Ultra-High" based on issue labels and content
- tags: Array of relevant tags (lowercase, hyphenated)
- summary: A brief summary of the issue (2-3 sentences)
- action_items: Array of specific action items extracted from the issue
- resources: Array of relevant URLs mentioned in the issue

Analyze the issue labels, title, and body to determine appropriate priority and tags."""

            issue_content = f"""
GitHub Issue #{issue_data['number']}: {issue_data['title']}
URL: {issue_data['html_url']}
State: {issue_data['state']}
Labels: {', '.join([label['name'] for label in issue_data.get('labels', [])])}
Created: {issue_data['created_at']}
Author: {issue_data['user']['login']}

Body:
{issue_data.get('body', 'No description provided')}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract task information from this GitHub issue:\n\n{issue_content}"}
            ]

            # Define the expected JSON structure
            tools = [{
                "type": "function",
                "function": {
                    "name": "create_task_info",
                    "description": "Create structured task information from GitHub issue",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["🟢 Low", "🟡 Medium", "🔴 High", "🟣 Ultra-High"]
                            },
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "summary": {"type": "string"},
                            "action_items": {"type": "array", "items": {"type": "string"}},
                            "resources": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["title", "priority", "tags", "summary", "action_items"]
                    }
                }
            }]

            response = client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=tools,
                tool_choice="required",
                temperature=0.3,
                max_tokens=1000
            )

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                task_info = json.loads(tool_call.function.arguments)

                # Add metadata
                task_info['github_url'] = issue_data['html_url']
                task_info['github_issue_number'] = issue_data['number']
                task_info['github_repo'] = f"{issue_data['html_url'].split('/')[3]}/{issue_data['html_url'].split('/')[4]}"

                return task_info

        except Exception as e:
            print(f"⚠️  LLM extraction failed, using simple extraction: {e}")

        # Fallback to simple extraction
        return self._extract_task_info_simple(issue_data, project_folder)

    def _create_task_file(self, task_info: Dict[str, Any], project_folder: str) -> str:
        """Create an Obsidian task file from extracted information"""
        # Extract project name from folder path
        project_name = project_folder.split('/')[-1]

        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', task_info['title']).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:80]
        filename = f"{safe_title}.md"
        filepath = f"{project_folder}/{filename}"

        # Format tags for YAML
        tags_list = [project_name.replace(' ', '-').lower(), 'github-issue']
        if task_info.get('tags'):
            tags_list.extend(task_info['tags'])

        tags_yaml = '\n'.join(f"  - {tag}" for tag in tags_list)

        # Build action items list
        action_items_md = '\n'.join(f"- [ ] {item}" for item in task_info['action_items'])
        if not action_items_md:
            action_items_md = f"- [ ] Review and implement GitHub issue requirements"

        # Build resources list
        resources_md = f"- [GitHub Issue #{task_info['github_issue_number']}]({task_info['github_url']})"
        if task_info.get('resources'):
            resources_md += '\n' + '\n'.join(f"- {url}" for url in task_info['resources'])

        # Create content
        content = f"""---
title: {task_info['title']}
project: {project_name}
status: 🔄 Not-Started
priority: {task_info['priority']}
tags:
{tags_yaml}
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
time-completed:
github_url: {task_info['github_url']}
github_issue: {task_info['github_issue_number']}
github_repo: {task_info['github_repo']}
---

## Meta Data Buttons

```meta-bind-embed
  [[Templates/Components/metabind-button-definitions]]
```

## 📝 Summary

{task_info['summary']}

## 🎯 Action Items

{action_items_md}

## 📎 Resources

{resources_md}

## 💡 Implementation Notes

_Add implementation details here as you work on this task._

## 🔗 Related

- [[{project_name} Dashboard]]
"""

        # Create the file using Obsidian API
        api = obsidian.Obsidian(
            api_key=self.obsidian_api_key,
            host=self.obsidian_host,
            port=self.obsidian_port
        )

        api.put_content(filepath, content)

        return filepath
