#!/usr/bin/env python3
"""
GitHub to JIRA Comment Monitor
Processes GitHub comments and creates/updates JIRA tasks
"""


import os
import sys
import json
import requests
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


class GitHubJIRAMonitor:
    def project_supports_epic(self) -> bool:
        """Check if the JIRA project supports the 'Epic' issue type."""
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/createmeta?projectKeys={self.jira_project}&expand=projects.issuetypes"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                projects = data.get('projects', [])
                if projects:
                    issue_types = projects[0].get('issuetypes', [])
                    for itype in issue_types:
                        if itype.get('name').lower() == 'epic':
                            return True
            print(f"[JIRA] Project {self.jira_project} does not support 'Epic' issue type.")
        except Exception as e:
            print(f"[JIRA] Error checking project issue types: {e}")
        return False
    def get_epic_link_field_id(self) -> str:
        """Dynamically find the custom field ID for 'Epic Link' in JIRA and cache it."""
        if hasattr(self, '_epic_link_field_id') and self._epic_link_field_id:
            return self._epic_link_field_id
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/field"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                for field in resp.json():
                    if field.get('name') == 'Epic Link':
                        self._epic_link_field_id = field['id']
                        print(f"[JIRA] Epic Link field id: {self._epic_link_field_id}")
                        return self._epic_link_field_id
            print("[JIRA] Could not find 'Epic Link' field, defaulting to 'customfield_10008'")
        except Exception as e:
            print(f"[JIRA] Error fetching Epic Link field id: {e}")
        self._epic_link_field_id = 'customfield_10008'
        return self._epic_link_field_id
    def post_action_log_to_jira(self, jira_key: str, action_type: str, action_detail: str, actor: str, timestamp: str, dry_run: bool = False) -> bool:
        """Post an action log comment to the JIRA issue using the provided template."""
        jira_comment = f"#### ⚙️ Action Log\n\n- **{action_type}**: {action_detail}\n- **Triggered By**: @{actor}\n- **Time**: {timestamp}\n\n---"
        if dry_run:
            print(f"🧪 DRY RUN: Would add action log to JIRA task {jira_key}:")
            print(jira_comment)
            return True
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{jira_key}/comment"
            payload = {"body": jira_comment}
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code in [200, 201]:
                print(f"✅ Added action log to JIRA task {jira_key}")
                return True
            else:
                print(f"❌ Failed to add action log to JIRA task {jira_key}: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Error adding action log to JIRA: {e}")
            return False
    def process_specific_issue(self, repo_owner: str, repo_name: str, issue_number: int, dry_run: bool = False) -> tuple:
        """Process a specific issue or PR for authorship events, ensuring correct repo pathing"""
        try:
            # Ensure correct repo path (owner/repo)
            if '/' in repo_name:
                repo_full = repo_name
            else:
                repo_full = f"{repo_owner}/{repo_name}"

            # Fetch issue details
            issue_url = f"https://github.com/{repo_full}/issues/{issue_number}"
            issue_details = self.get_issue_details(issue_url)
            if not issue_details:
                print(f"❌ Could not fetch issue #{issue_number}: 404")
                return 'error', False

            # Prepare event data for JIRA task creation
            event_data = {
                'repo_name': repo_full,
                'repo_owner': repo_owner,
                'issue_url': issue_url,
                'issue_title': issue_details.get('title', 'No title'),
                'issue_number': issue_number,
                'comment_body': issue_details.get('body', ''),
                'created_at': issue_details.get('created_at', '')
            }
            # Use fork status for label
            is_fork = self.check_fork_status(repo_full)
            # Use default kanban status and labels for authorship events
            kanban_status = None
            labels = None
            success = self.create_jira_task(event_data, is_fork, dry_run, kanban_status, labels)
            if success:
                return 'contribution', True
            else:
                return 'error', False
        except Exception as e:
            print(f"❌ Error processing specific issue: {e}")
            return 'error', False
    def get_jira_headers(self):
        """Return headers for JIRA API requests with correct Authorization"""
        return {
            'Authorization': f'Basic {self.jira_auth}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    def get_github_headers(self):
        """Return headers for GitHub API requests with correct Authorization format (no 'token ' prefix)"""
        return {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
        }

    def filter_comment_events(self, events: List[Dict]) -> List[Dict]:
        """Filter for IssueCommentEvents and PullRequestReviewCommentEvents"""
        comment_types = ['IssueCommentEvent', 'PullRequestReviewCommentEvent']
        comment_events = [e for e in events if e.get('type') in comment_types]
        print(f"💬 Comment events found: {len(comment_events)}")
        return comment_events

    def filter_authorship_events(self, events: List[Dict]) -> List[Dict]:
        """Filter for PR/Issue creation and Push events (authorship)"""
        authorship_types = ['PullRequestEvent', 'IssuesEvent', 'PushEvent']
        authorship_events = [e for e in events if e.get('type') in authorship_types]
        print(f"✍️  Authorship events found: {len(authorship_events)}")
        return authorship_events

    def fetch_github_events(self, since: str = None, max_pages: int = 10, repo: str = None) -> List[Dict]:
        """
        Fetch GitHub events for the authenticated user or for a specific repo.
        If repo is provided (format: owner/repo), fetch repo events. Otherwise, fetch user events (public events only).
        """
        headers = self.get_github_headers()
        # Debug: print the Authorization header and repr of token to verify token loading and invisible characters
        print(f"[DEBUG] Authorization header: {headers['Authorization']}")
        print(f"[DEBUG] Token repr: {repr(self.github_token)}")
        events = []
        page = 1
        while page <= max_pages:
            if repo:
                url = f"https://api.github.com/repos/{repo}/events"
            else:
                url = f"https://api.github.com/users/{self.github_user}/events"
            params = {'per_page': 100, 'page': page}
            if since:
                # The GitHub API does not support 'since' for events, but we can filter after fetching
                pass
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            if resp.status_code != 200:
                print(f"⚠️  GitHub API error fetching events: {resp.status_code} {resp.text[:200]}")
                break
            page_events = resp.json()
            if not page_events:
                break
            # If since is provided, filter events by created_at
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    filtered = [e for e in page_events if 'created_at' in e and datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')) >= since_dt]
                    events.extend(filtered)
                    # If all events are older than since, stop
                    if len(filtered) < len(page_events):
                        break
                except Exception as e:
                    events.extend(page_events)
            else:
                events.extend(page_events)
            if len(page_events) < 100:
                break
            page += 1
        print(f"✅ Total events fetched: {len(events)}")
        return events

    def __init__(self):
        # Load environment variables (optionally from .env)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # If dotenv is not installed, skip

        self.github_user = os.environ.get('GITHUB_USER')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.jira_domain = os.environ.get('JIRA_DOMAIN')
        self.jira_project = os.environ.get('JIRA_PROJECT')
        self.jira_auth = os.environ.get('JIRA_AUTH')
        # Comma-separated orgs to skip, or empty list
        skip_orgs = os.environ.get('SKIP_ORGS', '')
        self.skip_orgs = [org.strip() for org in skip_orgs.split(',') if org.strip()]

        # Basic validation
        if not self.github_user or not self.github_token or not self.jira_domain or not self.jira_project or not self.jira_auth:
            print("❌ ERROR: Missing required environment variables. Please set GITHUB_USER, GITHUB_TOKEN, JIRA_DOMAIN, JIRA_PROJECT, JIRA_AUTH (and optionally SKIP_ORGS).")
            exit(1)
    # All methods and their bodies below this line must be indented by 4 spaces (one level) under this class
    # ...existing code indented by 4 spaces...


    
    def should_skip_repo(self, repo_owner: str) -> bool:
        """Check if repo should be skipped"""
        if repo_owner == self.github_user:
            return True
        if repo_owner in self.skip_orgs:
            return True
        return False
    
    def parse_issue_from_branch(self, branch_name: str) -> Optional[int]:
        """Extract issue number from branch name patterns like 'fix-1650-*' or 'feature-2301-*'"""
        # Common patterns: fix-123-description, feature-456-name, issue-789, etc.
        patterns = [
            r'(?:fix|feature|bug|issue|pr)-(\d+)',  # fix-123, feature-456, etc.
            r'(\d+)-',  # Issue number at start
            r'#(\d+)',  # Hash prefix
            r'issue(\d+)',  # issue123
            r'(\d+)$',  # Just number at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, branch_name.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def check_fork_status(self, repo_name: str) -> bool:
        """Check if user has forked the repository"""
        try:
            # Extract repo name only (remove owner part)
            repo_name_only = repo_name.split('/')[-1]
            
            headers = self.get_github_headers()
            
            url = f"https://api.github.com/repos/{self.github_user}/{repo_name_only}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                is_fork = repo_data.get('fork', False)
                print(f"🔄 Fork check for {repo_name_only}: {'FOUND' if is_fork else 'NOT FOUND'}")
                return is_fork
            else:
                print(f"💬 No fork found for {repo_name_only}")
                return False
                
        except Exception as e:
            print(f"⚠️  Fork check failed for {repo_name}: {e}")
            return False
    
    def check_pr_branch_context(self, repo_owner: str, repo_name: str, branch_name: str = None, issue_number: int = None) -> Dict:
        """Check if current activity is related to an open PR"""
        try:
            headers = self.get_github_headers()
            
            # Get open PRs for this repo
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
            params = {'state': 'open', 'per_page': 50}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                open_prs = response.json()
                
                for pr in open_prs:
                    pr_branch = pr.get('head', {}).get('ref', '')
                    pr_number = pr.get('number')
                    
                    # Check if this branch matches a PR branch
                    if branch_name and pr_branch == branch_name:
                        return {
                            'is_pr_branch': True,
                            'pr_number': pr_number,
                            'pr_state': 'open',
                            'pr_branch': pr_branch
                        }
                    
                    # Check if issue number matches PR
                    if issue_number and pr_number == issue_number:
                        return {
                            'is_pr_related': True,
                            'pr_number': pr_number,
                            'pr_state': 'open',
                            'pr_branch': pr_branch
                        }
            
            return {'is_pr_branch': False, 'is_pr_related': False}
            
        except Exception as e:
            print(f"⚠️ Error checking PR context: {e}")
            return {'is_pr_branch': False, 'is_pr_related': False}
    
    def check_pr_status(self, repo_owner: str, repo_name: str, issue_number: int) -> Dict:
        """Check if there's a PR associated with this issue and its status"""
        try:
            headers = self.get_github_headers()
            
            # Check if this is already a PR (not an issue)
            pr_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{issue_number}"
            response = requests.get(pr_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                pr_data = response.json()
                state = pr_data.get('state', 'open')
                merged = pr_data.get('merged', False)
                
                return {
                    'is_pr': True,
                    'state': state,
                    'merged': merged,
                    'status': 'merged' if merged else state
                }
            
            # If not a PR, check for linked PRs that reference this issue
            # Search for PRs that mention this issue number
            search_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
            params = {'state': 'all', 'per_page': 10}
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                prs = response.json()
                for pr in prs:
                    # Check if PR body or title mentions this issue
                    pr_body = pr.get('body', '').lower()
                    pr_title = pr.get('title', '').lower()
                    issue_ref = f"#{issue_number}"
                    
                    if (issue_ref in pr_body or issue_ref in pr_title or 
                        f"fixes #{issue_number}" in pr_body or 
                        f"closes #{issue_number}" in pr_body):
                        
                        state = pr.get('state', 'open')
                        merged = pr.get('merged', False)
                        
                        return {
                            'is_pr': False,
                            'has_linked_pr': True,
                            'pr_number': pr.get('number'),
                            'state': state,
                            'merged': merged,
                            'status': 'merged' if merged else state
                        }
            
            # No PR found
            return {
                'is_pr': False,
                'has_linked_pr': False,
                'status': 'discussion'
            }
            
        except Exception as e:
            print(f"⚠️  Error checking PR status: {e}")
            return {
                'is_pr': False,
                'has_linked_pr': False,
                'status': 'discussion'
            }
    
    def determine_kanban_status(self, pr_status: Dict, is_fork: bool, repo_owner: str, repo_name: str, event_context: Dict = None) -> Tuple[str, List[str]]:
        """Enhanced status determination following the proposal's priority logic
        Status Priority Logic:
        1. MERGED (highest priority) → DONE
        2. RELEASED → RELEASED  
        3. OPEN PR + ACTIVITY → IN PROGRESS
        4. OPEN PR → PULL REQUEST
        5. COMMITS ON BRANCH → IN PROGRESS
        6. BRANCH CREATED → TODO
        7. COMMENT ONLY → DISCUSSION
        """
        # Create labels with owner and repo name (ensure repo_name is just the name, not owner/repo)
        repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
        
        # Avoid duplicate labels when owner and repo name are the same
        if repo_owner == repo_name_only:
            base_labels = [repo_owner]
        else:
            base_labels = [repo_owner, repo_name_only]
        
        # 1. Highest priority: MERGED → DONE
        if pr_status.get('merged', False) or pr_status.get('status') == 'merged':
            return "Done", base_labels + ["fork-repo", "merged"]
        
        # 2. RELEASED → RELEASED
        if pr_status.get('status') == 'released' or (pr_status.get('merged') and self.check_release_status(f"{repo_owner}/{repo_name}", pr_status.get('pr_number'))):
            return "Released", base_labels + ["fork-repo", "released"]
        
        # 3. OPEN PR + ACTIVITY → IN PROGRESS (Backward Flow)
        if event_context:
            is_push_event = event_context.get('is_push_event', False)
            is_comment_on_open_pr = event_context.get('is_comment_on_open_pr', False)
            is_mention_on_open_pr = event_context.get('is_mention_on_open_pr', False)
            if (is_push_event and pr_status.get('is_pr')) or is_comment_on_open_pr or is_mention_on_open_pr:
                return "In Progress", base_labels + ["fork-repo", "in-progress"]
        
        # 4. OPEN PR → PULL REQUEST
        if (pr_status.get('is_pr') or pr_status.get('has_linked_pr')):
            return "Pull Request", base_labels + ["fork-repo", "pull-request"]
        
        # 5. COMMITS ON BRANCH → IN PROGRESS (from PushEvent processing)
        if event_context:
            is_push_event = event_context.get('is_push_event', False)
            is_first_commit = event_context.get('is_first_commit', False)
            is_branch_work = event_context.get('is_branch_with_issue_number', False)
            if is_push_event and (is_first_commit or is_branch_work):
                return "In Progress", base_labels + ["fork-repo", "in-progress"]
        
        # 6. BRANCH CREATED → TODO
        if event_context and event_context.get('is_branch_created_with_issue', False):
            return "Todo", base_labels + ["fork-repo", "todo"]
        
        # 7. COMMENT ONLY → DISCUSSION (default case)
        return "Discussion", base_labels + ["fork-repo"]
    
    def check_release_status(self, repo_name: str, pr_number: int = None) -> bool:
        """Check if merged code has been released by looking for release tags"""
        try:
            headers = self.get_github_headers()
            
            # Get the latest releases for the repository
            url = f"https://api.github.com/repos/{repo_name}/releases"
            params = {'per_page': 10}  # Check last 10 releases
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                releases = response.json()
                
                if releases:
                    # Get the latest release
                    latest_release = releases[0]
                    release_date = latest_release.get('published_at', '')
                    release_tag = latest_release.get('tag_name', '')
                    
                    print(f"📦 Latest release: {release_tag} published at {release_date}")
                    
                    # If we have a specific PR number, we could check if it's included in the release
                    # For now, we'll consider any merged PR older than the latest release as potentially released
                    if release_date:
                        # Convert release date to datetime for comparison
                        from datetime import datetime
                        release_datetime = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                        
                        # For simplicity, if there's a release in the last 30 days, 
                        # we consider merged PRs as potentially released
                        now = datetime.now(release_datetime.tzinfo)
                        days_since_release = (now - release_datetime).days
                        
                        if days_since_release <= 30:
                            print(f"🚀 Recent release detected ({days_since_release} days ago)")
                            return True
                
            return False
            
        except Exception as e:
            print(f"⚠️  Error checking release status: {e}")
            return False
    
    def update_released_tasks(self, dry_run: bool = False) -> Dict:
        """Update merged tasks to Released status if they've been released"""
        print("🚀 Checking for released tasks...")
        
        try:
            # Search for tasks in "Done" status that might be released
            headers = self.get_jira_headers()
            
            # Find all "Done" tasks with "merged" label
            jql = f'project = "{self.jira_project}" AND status = "Done" AND labels = "merged"'
            
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 50}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            stats = {'checked': 0, 'updated': 0, 'errors': 0}
            
            if response.status_code == 200:
                result = response.json()
                done_tasks = result.get('issues', [])
                
                print(f"📊 Found {len(done_tasks)} tasks in Done status")
                
                for task in done_tasks:
                    stats['checked'] += 1
                    task_key = task['key']
                    summary = task.get('fields', {}).get('summary', '')
                    labels = task.get('fields', {}).get('labels', [])
                    
                    # Extract repo name from labels
                    repo_labels = [label for label in labels if label not in ['fork-repo', 'merged', 'pull-request']]
                    
                    if len(repo_labels) >= 2:
                        repo_name = f"{repo_labels[0]}/{repo_labels[1]}"
                    elif len(repo_labels) == 1:
                        # Single label might be owner/repo same name
                        repo_name = f"{repo_labels[0]}/{repo_labels[0]}"
                    else:
                        print(f"⚠️  Could not determine repo for task {task_key}")
                        continue
                    
                    print(f"🔍 Checking release status for {task_key}: {summary}")
                    
                    # Check if this repo has recent releases
                    if self.check_release_status(repo_name):
                        if dry_run:
                            print(f"🧪 DRY RUN: Would update {task_key} to Released status")
                            stats['updated'] += 1
                        else:
                            # Update to Released status
                            success = self.update_jira_status(task_key, "Released", dry_run=False)
                            if success:
                                print(f"🚀 Updated {task_key} to Released status")
                                stats['updated'] += 1
                            else:
                                print(f"❌ Failed to update {task_key}")
                                stats['errors'] += 1
                    else:
                        print(f"📝 No recent release found for {repo_name}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error updating released tasks: {e}")
            return {'checked': 0, 'updated': 0, 'errors': 1}
    
    def update_tasks_to_in_progress(self, repo_name: str, branch_name: str = None, dry_run: bool = False) -> Tuple[str, bool]:
        """Update related tasks to In Progress status when push events occur"""
        try:
            print(f"🔄 Checking for tasks to move to In Progress for {repo_name}")
            if branch_name:
                print(f"   Branch: {branch_name}")
            
            headers = self.get_jira_headers()
            
            # Extract repo parts for search
            repo_parts = repo_name.split('/')
            if len(repo_parts) >= 2:
                repo_owner = repo_parts[0]
                repo_name_only = repo_parts[1]
            else:
                print(f"⚠️  Invalid repo format: {repo_name}")
                return 'error', False
            
            # Search for tasks in Discussion or Pull Request status from this repo
            jql = f'project = "{self.jira_project}" AND (status = "Discussion" OR status = "Pull Request") AND (labels = "{repo_owner}" OR labels = "{repo_name_only}")'
            
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 20}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                tasks = result.get('issues', [])
                
                print(f"📊 Found {len(tasks)} potential tasks to update")
                
                if tasks:
                    # For push events, update the most recent task to In Progress
                    # In a real implementation, you might want to be more specific about which task
                    task = tasks[0]  # Take the first (most recent) task
                    task_key = task['key']
                    summary = task.get('fields', {}).get('summary', '')
                    
                    print(f"🔄 Moving {task_key} to In Progress: {summary}")
                    
                    if dry_run:
                        print(f"🧪 DRY RUN: Would update {task_key} to In Progress status")
                        return 'in_progress', True
                    else:
                        # Update to In Progress status
                        success = self.update_jira_status(task_key, "In Progress", dry_run=False)
                        if success:
                            print(f"✅ Updated {task_key} to In Progress status")
                            return 'in_progress', True
                        else:
                            print(f"❌ Failed to update {task_key}")
                            return 'error', False
                else:
                    print(f"📝 No tasks found to update for {repo_name}")
                    return 'no_tasks', True
            else:
                print(f"⚠️  JIRA search failed: {response.status_code}")
                return 'error', False
                
        except Exception as e:
            print(f"❌ Error updating tasks to In Progress: {e}")
            return 'error', False
    
    def process_push_event(self, event: Dict, dry_run: bool = False) -> Tuple[str, bool]:
        """Process PushEvent to detect branch work and move tasks to In Progress"""
        payload = event.get('payload', {})
        repo = event.get('repo', {})
        
        # Extract branch and repository info
        ref = payload.get('ref', '')
        branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
        repo_name = repo.get('name', '')
        repo_owner = repo_name.split('/')[0] if '/' in repo_name else ''
        repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
        
        print(f"🔄 Processing push to branch: {branch_name} in {repo_name}")
        
        # Check if this is a branch with issue number
        issue_number = self.parse_issue_from_branch(branch_name)
        
        if issue_number:
            print(f"📊 Detected issue #{issue_number} from branch {branch_name}")
            
            # Check if this push is to a PR branch
            pr_context = self.check_pr_branch_context(repo_owner, repo_name_only, branch_name, issue_number)
            is_pr_branch = pr_context.get('is_pr_branch', False)
            
            # Update related JIRA tasks
            result, success = self.update_tasks_to_in_progress(repo_name, branch_name, dry_run)
            
            if success:
                if is_pr_branch:
                    print(f"🔄 Push to PR branch detected - task moved to In Progress")
                else:
                    print(f"🚀 First commit on issue branch detected - task moved to In Progress")
                
                return result, True
            else:
                return result, False
        else:
            print(f"ℹ️  No issue number detected in branch name: {branch_name}")
            return 'no_issue_detected', True
    
    def get_issue_details(self, issue_url: str) -> Dict:
        """Fetch full issue details from GitHub"""
        try:
            api_url = None
            if 'github.com/' in issue_url:
                parts = issue_url.split('github.com/')[-1].split('/')
                if '/issues/' in issue_url and len(parts) >= 4:
                    owner, repo, _, number = parts[:4]
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
                elif '/pull/' in issue_url and len(parts) >= 4:
                    owner, repo, _, number = parts[:4]
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
                else:
                    print(f"⚠️  Could not parse issue or pull URL: {issue_url}")
                    return {}
            else:
                print(f"⚠️  Invalid issue URL: {issue_url}")
                return {}

            headers = self.get_github_headers()
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Could not fetch issue details: {response.status_code}")
                return {}
        except Exception as e:
            print(f"⚠️  Error fetching issue details: {e}")
            return {}
    
    def search_existing_jira_task(self, issue_url: str, issue_number: int, repo_name: str, repo_owner: str = None) -> Optional[str]:
        """Search for existing JIRA task with this GitHub issue (repo + issue number + owner)"""
        try:
            headers = self.get_jira_headers()
            repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
            # Use owner if provided, else try to extract from repo_name
            owner = repo_owner or (repo_name.split('/')[0] if '/' in repo_name else None)
            # Search by exact issue number, repo name, and owner in summary/labels
            jql = f'project = "{self.jira_project}" AND summary ~ "{issue_number}" AND labels = "{repo_name_only}"'
            if owner:
                jql += f' AND labels = "{owner}"'
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 20}
            print(f"🔍 Searching for existing task with issue #{issue_number} in {repo_name_only} (owner: {owner})")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                print(f"📊 Found {result.get('total', 0)} potential matches")
                if result.get('total', 0) > 0:
                    for issue in result.get('issues', []):
                        fields = issue.get('fields', {})
                        summary = fields.get('summary', '')
                        labels = fields.get('labels', [])
                        if str(issue_number) in summary and repo_name_only in labels and (not owner or owner in labels):
                            return issue.get('key')
                print(f"❌ No exact match found for issue #{issue_number} in {repo_name_only} (owner: {owner})")
            else:
                print(f"⚠️  JIRA search failed: {response.status_code}")
            return None
        except Exception as e:
            print(f"⚠️  Error searching JIRA: {e}")
            return None
    
    def create_jira_task(self, event_data: Dict, is_fork: bool, dry_run: bool = False, kanban_status: str = None, labels: List[str] = None) -> bool:
        """Create or update JIRA task for the comment, only if unique, and always log flow direction"""
        # Helper: Find or create Epic key for this repo owner
        def get_or_create_epic_key(repo_owner):
            try:
                # Check if project supports Epic
                if not self.project_supports_epic():
                    print(f"[JIRA] Skipping Epic creation/linking: project does not support 'Epic' issue type.")
                    return None
                headers = self.get_jira_headers()
                jql = f'project = "{self.jira_project}" AND issuetype = Epic AND summary ~ "{repo_owner}"'
                url = f"https://{self.jira_domain}/rest/api/2/search"
                params = {'jql': jql, 'maxResults': 1}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    issues = response.json().get('issues', [])
                    if issues:
                        return issues[0]['key']
                # If not found, create Epic (without customfield_10011)
                print(f"No Epic found for owner '{repo_owner}', creating new Epic...")
                payload = {
                    "fields": {
                        "project": {"key": self.jira_project},
                        "summary": repo_owner,
                        "issuetype": {"name": "Epic"}
                    }
                }
                create_url = f"https://{self.jira_domain}/rest/api/2/issue"
                create_resp = requests.post(create_url, headers=headers, json=payload, timeout=30)
                if create_resp.status_code in [200, 201]:
                    epic_key = create_resp.json().get('key')
                    print(f"Created Epic {epic_key} for owner '{repo_owner}'")
                    return epic_key
                else:
                    print(f"❌ Failed to create Epic for owner '{repo_owner}': {create_resp.status_code} {create_resp.text}")
            except Exception as e:
                print(f"⚠️  Error searching/creating Epic: {e}")
            return None

        """Create or update JIRA task for the comment, only if unique, and always log flow direction"""
        try:
            repo_name = event_data['repo_name']
            issue_url = event_data['issue_url']
            issue_number = event_data['issue_number']
            issue_title = event_data['issue_title']
            comment_body = event_data['comment_body']
            repo_owner = event_data.get('repo_owner', 'unknown')

            # Always define repo_name_only at the top
            repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name

            # Always use only the repo name as the label
            labels = [repo_name_only]

            # Find or create Epic for this repo owner
            epic_key = get_or_create_epic_key(repo_owner)


            # Get full issue details
            issue_details = self.get_issue_details(issue_url)
            issue_body = issue_details.get('body', 'No description available')
            issue_author = issue_details.get('user', {}).get('login', 'unknown')
            issue_created_at = issue_details.get('created_at', '')

            # Try to get the first comment (if any)
            first_comment = ''
            try:
                comments_url = issue_details.get('comments_url')
                if comments_url:
                    headers = self.get_github_headers()
                    resp = requests.get(comments_url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        comments = resp.json()
                        if comments:
                            first_comment = comments[0].get('body', '')
            except Exception as e:
                print(f"⚠️  Could not fetch first comment: {e}")

            # Format JIRA description with metadata and initial issue body
            description_lines = [
                '### 🔗 GitHub Issue Info',
                '',
                f'- **Repo:** `{repo_owner}/{repo_name_only}`',
                f'- **Issue Number:** `#{issue_number}`',
                f'- **Title:** {issue_title}',
                f'- **Author:** @{issue_author}',
                f'- **Created At:** {issue_created_at}',
                f'- **URL:** [View on GitHub]({issue_url})',
                '',
                '---',
                '',
                '### 📝 Initial Issue Description',
                '',
                issue_body or 'No description available',
            ]
            if first_comment:
                description_lines += [
                    '',
                    '---',
                    '',
                    '### 💬 First Comment',
                    '',
                    first_comment
                ]
            description_lines += [
                '',
                '---',
                '*This issue is auto-synced from GitHub.*'
            ]
            jira_description = '\n'.join(description_lines)

            # Use provided kanban_status and labels, or determine them
            if kanban_status is None or labels is None:
                pr_status = self.check_pr_status(repo_owner, repo_name_only, issue_number)
                kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name_only)
                # Always override labels to just repo name
                labels = [repo_name_only]

            # Enhanced status reporting
            print(f"📊 PR Status Analysis:")
            print(f"   Is Fork: {is_fork}")
            print(f"   Kanban Column: {kanban_status}")
            print(f"   Labels: {labels}")

            # Determine task type and description
            if kanban_status == "Done":
                task_type = "contribution-merged"
                description_prefix = "✅ MERGED Contribution"
                print(f"✅ Creating MERGED CONTRIBUTION task for {repo_name}")
            elif kanban_status == "In Progress":
                task_type = "contribution-active"
                description_prefix = "🔄 ACTIVE Work in Progress"
                print(f"🔄 Creating IN PROGRESS task for {repo_name}")
            elif kanban_status == "Pull Request":
                task_type = "contribution-pr"
                description_prefix = "🔄 Active Pull Request"
                print(f"🔄 Creating PULL REQUEST task for {repo_name}")
            elif is_fork:
                task_type = "contribution-discussion"
                description_prefix = "💭 Discussion on Forked Repo"
                print(f"💭 Creating FORK DISCUSSION task for {repo_name}")
            else:
                task_type = "external-discussion"
                description_prefix = "💬 Discussion on External Repo"
                print(f"💬 Creating EXTERNAL DISCUSSION task for {repo_name}")

            # Check for existing task (unique by issue_number, repo_name_only, repo_owner)
            existing_key = self.search_existing_jira_task(issue_url, issue_number, repo_name_only, repo_owner)
            if existing_key:
                print(f"🔄 Updating existing task {existing_key} instead of creating new one")
                # Always add a comment describing what happened and the flow direction
                flow_direction = f"[Status Flow] {kanban_status} (forward/backward as per doc)"
                comment_update = f"{comment_body}\n\n{flow_direction}"
                return self.update_jira_task_with_status(existing_key, comment_update, kanban_status, dry_run)
            else:
                # Create new JIRA task and link to Epic if found
                if dry_run:
                    print(f"🧪 DRY RUN: Would create JIRA task for {repo_name_only} with Epic {epic_key if epic_key else '[none]'}")
                    return True
                headers = self.get_jira_headers()
                # JIRA summary as issueNo-issueTitle
                summary = f"{issue_number}-{issue_title}"
                payload = {
                    "fields": {
                        "project": {"key": self.jira_project},
                        "summary": summary,
                        "description": jira_description,
                        "issuetype": {"name": "Task"},
                        "labels": labels
                    }
                }
                # Attach Epic link if found (dynamically determine field id)
                if epic_key:
                    epic_field_id = self.get_epic_link_field_id()
                    payload["fields"][epic_field_id] = epic_key
                url = f"https://{self.jira_domain}/rest/api/2/issue"
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code in [200, 201]:
                    result = response.json()
                    task_key = result.get('key', 'Unknown')
                    print(f"✅ Created JIRA task: {task_key} (Epic: {epic_key if epic_key else '[none]'})")
                    return True
                else:
                    print(f"❌ Failed to create JIRA task: {response.status_code} {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Error creating JIRA task: {e}")
            return False
    
    def update_jira_status(self, task_key: str, target_status: str, dry_run: bool = False) -> bool:
        """Update JIRA task status/workflow state"""
        try:
            if dry_run:
                print(f"🧪 DRY RUN: Would move task {task_key} to {target_status}")
                return True
            
            headers = self.get_jira_headers()
            
            # Get available transitions
            transitions_url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}/transitions"
            response = requests.get(transitions_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️  Could not get transitions for {task_key}")
                return False
            
            transitions = response.json().get('transitions', [])
            
            # Find transition that moves to target status
            target_transition = None
            for transition in transitions:
                to_status = transition.get('to', {}).get('name', '').lower()
                if target_status.lower() in to_status or to_status in target_status.lower():
                    target_transition = transition
                    break
            
            if not target_transition:
                print(f"⚠️  No transition found to move {task_key} to {target_status}")
                return False
            
            # Perform transition
            transition_payload = {
                "transition": {
                    "id": target_transition['id']
                }
            }
            
            response = requests.post(transitions_url, headers=headers, json=transition_payload, timeout=30)
            
            if response.status_code == 204:
                print(f"✅ Moved {task_key} to {target_status}")
                return True
            else:
                print(f"⚠️  Failed to move {task_key} to {target_status}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Error updating JIRA status: {e}")
            return False
    
    def update_jira_task_with_status(self, task_key: str, new_comment: str, target_status: str, dry_run: bool = False) -> bool:
        """Update existing JIRA task with new comment and potentially new status, always log flow direction"""
        try:
            if dry_run:
                print(f"🧪 DRY RUN: Would update task {task_key} with new comment and status {target_status}")
                return True
            # First update the comment
            success = self.update_jira_task(task_key, new_comment, dry_run=False)
            if success:
                # Then try to update status if needed
                self.update_jira_status(task_key, target_status, dry_run=False)
            return success
        except Exception as e:
            print(f"❌ Error updating JIRA task with status: {e}")
            return False
    
    def update_jira_task(self, task_key: str, new_comment: str, dry_run: bool = False) -> bool:
        """Update existing JIRA task with new comment"""
        try:
            if dry_run:
                print(f"🧪 DRY RUN: Would update task {task_key} with new comment")
                return True
            
            # Get current description
            headers = self.get_jira_headers()
            
            url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Could not fetch task {task_key}: {response.status_code}")
                return False
            
            current_data = response.json()
            current_desc = current_data.get('fields', {}).get('description', '')
            
            # Append new comment
            new_desc = f"{current_desc}\n\n--- New Comment ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ---\n{new_comment}"
            
            # Update task
            update_payload = {
                "fields": {
                    "description": new_desc
                }
            }
            
            response = requests.put(url, headers=headers, json=update_payload, timeout=30)
            
            if response.status_code == 204:
                print(f"✅ Updated JIRA task: {task_key}")
                return True
            else:
                print(f"❌ Failed to update task {task_key}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating JIRA task: {e}")
            return False
    
    def process_comment_event(self, event: Dict, dry_run: bool = False) -> Tuple[str, bool]:
        """Process a single comment event"""
        try:
            payload = event.get('payload', {})
            repo = event.get('repo', {})
            event_type = event.get('type', '')
            
            # Extract repository information from GitHub event
            repo_name_raw = repo.get('name', 'unknown')
            # Ensure we only get the repo name, not owner/repo format
            repo_name_only = repo_name_raw.split('/')[-1] if '/' in repo_name_raw else repo_name_raw
            repo_url = repo.get('url', '')
            
            # Extract owner from repository URL or issue URL
            repo_owner = 'unknown'
            repo_full_name = 'unknown/unknown'
            
            # Try to extract from repo URL: https://api.github.com/repos/owner/repo_name
            if repo_url and '/repos/' in repo_url:
                url_parts = repo_url.split('/repos/')[-1].split('/')
                if len(url_parts) >= 2:
                    repo_owner = url_parts[0]
                    repo_full_name = f"{repo_owner}/{repo_name_only}"
            
            # If that fails, try to extract from issue URL
            issue = payload.get('issue', {})
            issue_url = issue.get('html_url', '')
            if repo_owner == 'unknown' and issue_url:
                # Extract from: https://github.com/owner/repo/issues/123
                if 'github.com/' in issue_url:
                    url_parts = issue_url.split('github.com/')[-1].split('/')
                    if len(url_parts) >= 2:
                        repo_owner = url_parts[0]
                        repo_name_only = url_parts[1]
                        repo_full_name = f"{repo_owner}/{repo_name_only}"
            
            # Final repository name for processing
            repo_name = repo_full_name if repo_full_name != 'unknown/unknown' else repo_name_only
            
            comment = payload.get('comment', {})
            issue = payload.get('issue', {})
            
            comment_body = comment.get('body', 'No comment body')
            issue_url = issue.get('html_url', '')
            issue_title = issue.get('title', 'No title')
            issue_number = issue.get('number', 0)

            # Skip events with no issue URL
            if not issue_url:
                print("⚠️  SKIPPED: No issue URL found for this event")
                return 'skipped', False
            
            # Determine event context for "In Progress" detection
            is_review_comment = (event_type == 'PullRequestReviewCommentEvent')
            issue_author = issue.get('user', {}).get('login', '')
            is_own_issue_comment = (issue_author == self.github_user)
            
            print(f"\n--- Processing Comment Event ---")
            print(f"Repository: {repo_name}")
            print(f"Owner: {repo_owner}")
            print(f"Issue: {issue_title}")
            print(f"URL: {issue_url}")
            print(f"Event Type: {event_type}")
            print(f"Review Comment: {is_review_comment}")
            print(f"Own Issue Comment: {is_own_issue_comment}")
            print(f"Comment preview: {comment_body[:100]}...")
            
            # Check if should skip (skip own repos and specified orgs)
            if self.should_skip_repo(repo_owner):
                print(f"✅ SKIPPED: Own/org repo - {repo_name} (owner: {repo_owner})")
                return 'skipped', True
            
            # Only process if we have valid repository information
            if repo_owner == 'unknown' or repo_name == 'unknown/unknown':
                print(f"⚠️  SKIPPED: Could not determine repository owner/name")
                return 'skipped', False
            
            # Check fork status
            is_fork = self.check_fork_status(repo_name)
            
            # Check PR status to determine Kanban column
            repo_name_only = repo_name.split('/')[-1]
            pr_status = self.check_pr_status(repo_owner, repo_name_only, issue_number)
            
            # Enhanced context detection for bidirectional flow
            is_comment_on_open_pr = False
            is_mention_on_open_pr = False
            
            # Check if this comment is on an open PR
            if pr_status.get('is_pr') and pr_status.get('state') == 'open':
                is_comment_on_open_pr = True
                # Check if user is mentioned in the comment
                if f"@{self.github_user}" in comment_body:
                    is_mention_on_open_pr = True
            
            # Create event context for enhanced status determination
            event_context = {
                'event_type': event_type,
                'is_review_comment': is_review_comment,
                'is_push_event': False,
                'is_own_issue_comment': is_own_issue_comment,
                'is_comment_on_open_pr': is_comment_on_open_pr,
                'is_mention_on_open_pr': is_mention_on_open_pr
            }
            
            kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name_only, event_context)
            
            # Enhanced status reporting
            print(f"📊 PR Status Analysis:")
            print(f"   Is Fork: {is_fork}")
            print(f"   PR Status: {pr_status}")
            print(f"   Kanban Column: {kanban_status}")
            print(f"   Labels: {labels}")
            
            # Prepare event data
            event_data = {
                'repo_name': repo_name,
                'repo_owner': repo_owner,
                'issue_url': issue_url,
                'issue_title': issue_title,
                'issue_number': issue_number,
                'comment_body': comment_body,
                'created_at': event.get('created_at', '')
            }

            # Find the JIRA task for this issue
            jira_key = self.search_existing_jira_task(issue_url, issue_number, repo_name.split('/')[-1], repo_owner)
            if not jira_key:
                # If not found, create the task as usual
                success = self.create_jira_task(event_data, is_fork, dry_run, kanban_status, labels)
                if success:
                    return 'contribution' if is_fork else 'discussion', True
                else:
                    return 'error', False

            # If this is a PR review comment, just add the comment body and PR link
            if event_type == 'PullRequestReviewCommentEvent':
                pr_url = payload.get('pull_request', {}).get('html_url', '')
                comment_url = comment.get('html_url', '')
                comment_author = comment.get('user', {}).get('login', 'unknown')
                comment_created_at = comment.get('created_at', '')
                pr_link = pr_url or issue_url
                jira_comment = f"#### 💬 GitHub PR Review Comment by @{comment_author} on {comment_created_at}:\n{comment_body}\n\n[🔗 View PR]({pr_link})\n---"
            else:
                # Issue comment event
                comment_url = comment.get('html_url', '')
                comment_author = comment.get('user', {}).get('login', 'unknown')
                comment_created_at = comment.get('created_at', '')
                jira_comment = f"#### 💬 GitHub Comment by @{comment_author} on {comment_created_at}:\n{comment_body}\n\n[🔗 View comment]({comment_url})\n---"

            if dry_run:
                print(f"🧪 DRY RUN: Would add comment to JIRA task {jira_key}:")
                print(jira_comment)
                return 'commented', True

            # Add the comment to the JIRA task (as a comment, not description)
            try:
                headers = self.get_jira_headers()
                url = f"https://{self.jira_domain}/rest/api/2/issue/{jira_key}/comment"
                payload = {"body": jira_comment}
                resp = requests.post(url, headers=headers, json=payload, timeout=15)
                if resp.status_code in [200, 201]:
                    print(f"✅ Added comment to JIRA task {jira_key}")
                    return 'commented', True
                else:
                    print(f"❌ Failed to add comment to JIRA task {jira_key}: {resp.status_code} {resp.text}")
                    return 'error', False
            except Exception as e:
                print(f"❌ Error adding comment to JIRA: {e}")
                return 'error', False
                
        except Exception as e:
            print(f"❌ Error processing event: {e}")
            return 'error', False
    
    def process_authorship_event(self, event: Dict, dry_run: bool = False) -> Tuple[str, bool]:
        """Process a single authorship event (PR/Issue creation, Push events) using enhanced method"""
        try:
            event_type = event.get('type', '')
            payload = event.get('payload', {})
            repo = event.get('repo', {})
            
            # Extract repository information
            repo_name_raw = repo.get('name', 'unknown')
            repo_parts = repo_name_raw.split('/')
            
            if len(repo_parts) >= 2:
                repo_owner = repo_parts[0]
                repo_name = repo_name_raw
            else:
                print(f"⚠️  Invalid repository format: {repo_name_raw}")
                return 'error', False
            
            # Skip own repositories
            if self.should_skip_repo(repo_owner):
                print(f"⏭️  Skipping own/org repository: {repo_name}")
                return 'skipped', True
            
            # Handle different event types
            if event_type == 'PushEvent':
                # Use the new enhanced push event processing
                return self.process_push_event(event, dry_run)
                
            elif event_type == 'PullRequestEvent':
                item = payload.get('pull_request', {})
                item_type = 'pull_request'
            elif event_type == 'IssuesEvent':
                item = payload.get('issue', {})
                item_type = 'issue'
            else:
                print(f"⚠️  Unsupported authorship event type: {event_type}")
                return 'error', False
            
            issue_number = item.get('number', 0)
            issue_title = item.get('title', 'No title')
            
            print(f"\n--- Processing {item_type.title()} Authorship Event ---")
            print(f"Repository: {repo_name}")
            print(f"Number: #{issue_number}")
            print(f"Title: {issue_title}")
            
            # Use the enhanced process_specific_issue method (now ensures correct repo path)
            result, success = self.process_specific_issue(repo_owner, repo_name, issue_number, dry_run)
            print(f"✅ Authorship event processed: {result}")
            return result, success
            
        except Exception as e:
            print(f"❌ Error processing authorship event: {e}")
            return 'error', False
    
    def run_monitor(self, since_minutes: int = 15, dry_run: bool = False) -> Dict:
        """Run the enhanced monitoring workflow (comments + authorship detection) with detailed event type counts"""
        print("=== Starting Enhanced GitHub-JIRA Monitor ===")
        print(f"Timestamp: {datetime.now()}")
        print()

        print("=== Configuration Details ===")
        print(f"GitHub User: {self.github_user}")
        print(f"Organization to skip: {', '.join(self.skip_orgs)}")
        print(f"JIRA Domain: {self.jira_domain}")
        print(f"JIRA Project: {self.jira_project}")
        print(f"GitHub Token: {self.github_token[:10]}...")
        print(f"JIRA Auth: {self.jira_auth[:20]}...")
        print()

        print("=== Enhanced Detection Capabilities ===")
        print("✅ IssueCommentEvent - When you comment on issues/PRs")
        print("✅ PullRequestReviewCommentEvent - When you add code review comments → In Progress")
        print("✅ PullRequestEvent - When you create/open new PRs")
        print("✅ IssuesEvent - When you create/open new issues")
        print("✅ PushEvent - When you push commits → In Progress")
        print("✅ Author Detection - Processes PRs/issues you authored (even without comments)")
        print("✅ Smart Status Flow - Discussion → Todo → In Progress → Pull Request → Done → Released")
        print()
        print()

        # Calculate since timestamp
        since = (datetime.now() - timedelta(minutes=since_minutes)).isoformat() + 'Z'
        print(f"Looking for comments since: {since}")

        # Fetch events
        events = self.fetch_github_events(since=since, max_pages=1)

        # Detailed event type counts
        event_type_counts = {
            'IssueCommentEvent': 0,
            'PullRequestReviewCommentEvent': 0,
            'PullRequestEvent': 0,
            'IssuesEvent': 0,
            'PushEvent': 0
        }
        for e in events:
            t = e.get('type')
            if t in event_type_counts:
                event_type_counts[t] += 1

        print("\n--- Event Type Counts ---")
        for k, v in event_type_counts.items():
            print(f"{k}: {v}")
        print("-------------------------\n")

        comment_events = self.filter_comment_events(events)
        authorship_events = self.filter_authorship_events(events)

        total_events = len(comment_events) + len(authorship_events)

        if total_events == 0:
            print("No recent comment or authorship events found in the specified time range")
            return {'total': 0, 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}

        print(f"📊 Total events to process: {total_events}")

        # Process events
        stats = {'total': total_events, 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}

        # Process comment events (existing logic)
        for event in comment_events:
            result, success = self.process_comment_event(event, dry_run)
            stats['processed'] += 1

            if result == 'skipped':
                stats['skipped'] += 1
            elif result in ['contribution', 'discussion'] and success:
                stats['created'] += 1
            else:
                stats['errors'] += 1

        # Process authorship events (new logic using enhanced method)
        for event in authorship_events:
            result, success = self.process_authorship_event(event, dry_run)
            stats['processed'] += 1

            if result == 'skipped':
                stats['skipped'] += 1
            elif result in ['contribution', 'discussion'] and success:
                stats['created'] += 1
            else:
                stats['errors'] += 1

        print("\n=== Monitor Summary ===")
        print(f"Total Events: {stats['total']}")
        print(f"Processed: {stats['processed']}")
        print(f"JIRA Tasks Created/Updated: {stats['created']}")
        print(f"Skipped (own/org repos): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Timestamp: {datetime.now()}")

        return stats
    
    def fetch_user_pull_requests(self, repo_owner: str, repo_name: str, max_pages: int = 5) -> List[Dict]:
        """Fetch pull requests authored by the user in a specific repository"""
        print(f"🔍 Fetching your PRs from {repo_owner}/{repo_name}...")
        
        headers = self.get_github_headers()
        
        all_prs = []
        
        for page in range(1, max_pages + 1):
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
            params = {
                'state': 'all',
                'per_page': 100,
                'page': page,
                'sort': 'created',
                'direction': 'desc'
            }
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 403:
                    print("⚠️  Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                elif response.status_code != 200:
                    print(f"❌ GitHub API error: {response.status_code}")
                    break
                prs = response.json()
                if not prs:
                    print(f"✅ No more PRs on page {page}")
                    break
                # Filter PRs to only those authored by self.github_user
                user_prs = [pr for pr in prs if pr.get('user', {}).get('login') == self.github_user]
                all_prs.extend(user_prs)
                print(f"📊 Found {len(user_prs)} PRs by {self.github_user} on page {page}")
                # Rate limiting
                if page < max_pages:
                    time.sleep(2)
            except Exception as e:
                print(f"❌ Error fetching PRs page {page}: {e}")
                continue
        print(f"✅ Total PRs found: {len(all_prs)} (authored by {self.github_user})")
        return all_prs
    
    def process_pull_request(self, pr: Dict, repo_owner: str, repo_name: str, dry_run: bool = False) -> Tuple[str, bool]:
        """Process a single pull request and create JIRA task"""
        # No outer try block needed here; inner try/except is used for Epic search
        pr_number = pr.get('number', 0)
        pr_title = pr.get('title', 'No title')
        pr_body = pr.get('body', '')
        pr_url = pr.get('html_url', '')
        pr_state = pr.get('state', 'unknown')
        pr_merged = pr.get('merged', False)
        created_at = pr.get('created_at', '')

        print(f"\n--- Processing Pull Request #{pr_number} ---")
        print(f"Title: {pr_title}")
        print(f"State: {pr_state}")
        print(f"Merged: {pr_merged}")
        print(f"URL: {pr_url}")

        # Check if should skip (skip own repos)
        if self.should_skip_repo(repo_owner):
            print(f"✅ SKIPPED: Own/org repo - {repo_owner}/{repo_name}")
            return 'skipped', True

        # Check fork status
        is_fork = self.check_fork_status(f"{repo_owner}/{repo_name}")

        # For PR migration, always put PRs in Pull Request column (not Done)
        repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
        kanban_status = "Pull Request"
        task_type = "contribution-pr"
        if pr_merged:
            description_prefix = "✅ MERGED Pull Request"
        elif pr_state == 'closed':
            description_prefix = "📝 CLOSED Pull Request"
        elif pr_state == 'open':
            description_prefix = "🔄 OPEN Pull Request"
        else:
            description_prefix = "💭 Pull Request"
        # Only use the repo name as the label
        labels = [repo_name_only]

        # Try to find an Epic for this repo owner
        def find_epic_key(repo_owner):
            try:
                headers = self.get_jira_headers()
                jql = f'project = "{self.jira_project}" AND issuetype = Epic AND summary ~ "{repo_owner}"'
                url = f"https://{self.jira_domain}/rest/api/2/search"
                params = {'jql': jql, 'maxResults': 1}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 200:
                    issues = response.json().get('issues', [])
                    if issues:
                        return issues[0]['key']
            except Exception as e:
                print(f"⚠️  Error searching for Epic: {e}")
            return None
        epic_key = find_epic_key(repo_owner)

        print(f"📊 PR Analysis:")
        print(f"   Is Fork: {is_fork}")
        print(f"   Kanban Column: {kanban_status}")
        print(f"   Labels: {labels}")

        # Check for existing task
        existing_key = self.search_existing_jira_task(pr_url, pr_number, repo_name)

        if existing_key:
            print(f"🔄 JIRA task already exists: {existing_key}")
            return 'existing', True

        # Create new task
        task_summary = f"{pr_number} - {pr_title}"

        # Parse referenced issues from PR body
        referenced_issues = []
        if pr_body:
            import re
            # Look for "Fixes #123", "Closes #456", etc.
            issue_refs = re.findall(r'(?:fixes|closes|resolves)\s+#(\d+)', pr_body.lower())
            if issue_refs:
                referenced_issues = [f"#{issue}" for issue in issue_refs]

        ref_info = ""
        if referenced_issues:
            ref_info = f"\n🔗 References issues: {', '.join(referenced_issues)}"

        task_description = f"""{description_prefix}

Pull Request Description:
{pr_body}
{ref_info}

GitHub PR: {pr_url}
Repo: {repo_owner}/{repo_name}
Kanban Status: {kanban_status}
Created Date: {created_at}"""

        if dry_run:
            print(f"🧪 DRY RUN: Would create {task_type} task")
            print(f"   Summary: {task_summary}")
            print(f"   Labels: {labels}")
            print(f"   Kanban Status: {kanban_status}")
            return True, True

        # Create JIRA task
        headers = self.get_jira_headers()

        payload = {
            "fields": {
                "project": {"key": self.jira_project},
                "summary": task_summary,
                "description": task_description,
                "issuetype": {"name": "Task"},
                "labels": labels
        }
    }

        url = f"https://{self.jira_domain}/rest/api/2/issue"
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code in [200, 201]:
            result = response.json()
            task_key = result.get('key', 'Unknown')
            print(f"✅ Created JIRA task: {task_key} (Status: {kanban_status})")
            return 'created', True
        else:
            print(f"❌ Failed to create JIRA task: {response.status_code}")
            return 'error', False
            task_summary = f"{pr_number} - {pr_title}"
            task_description = f"{description_prefix}\n\nPull Request Description:\n{pr_body}\n\nGitHub PR: {pr_url}\nRepo: {repo_owner}/{repo_name}\nKanban Status: {kanban_status}\nCreated Date: {created_at}"
            if dry_run:
                print(f"🧪 DRY RUN: Would create PR JIRA task for {repo_name_only} with Epic {epic_key if epic_key else '[none]'}")
                return 'created', True
            headers = self.get_jira_headers()
            payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": task_summary,
                    "description": task_description,
                    "issuetype": {"name": "Task"},
                    "labels": labels
                }
            }
            if epic_key:
                payload["fields"]["customfield_10008"] = epic_key
            url = f"https://{self.jira_domain}/rest/api/2/issue"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code in [200, 201]:
                result = response.json()
                task_key = result.get('key', 'Unknown')
                print(f"✅ Created JIRA PR task: {task_key} (Epic: {epic_key if epic_key else '[none]'})")
                return 'created', True
            else:
                print(f"❌ Failed to create JIRA PR task: {response.status_code} {response.text}")
                return 'error', False
                if i < len(prs):
                    time.sleep(1)
        
        print("\\n=== PR Migration Summary ===")
        print(f"Total PRs Found: {stats['total']}")
        print(f"PRs Processed: {stats['processed']}")
        print(f"JIRA Tasks Created: {stats['created']}")
        print(f"Existing Tasks Found: {stats['existing']}")
        print(f"Skipped (own repos): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Timestamp: {datetime.now()}")
        
        return stats
    
    def run_migration(self, max_pages: int = 10, dry_run: bool = False, repos: str = None) -> Dict:
        """Run the migration workflow (all historical comments or for specific repos)"""
        print("=== Starting GitHub Comments Migration ===")
        print(f"Timestamp: {datetime.now()}")
        print(f"Max Pages: {max_pages}")
        print(f"Dry Run: {dry_run}")
        print()

        print("=== Configuration Details ===")
        print(f"GitHub User: {self.github_user}")
        print(f"Organization to skip: {', '.join(self.skip_orgs)}")
        print(f"JIRA Domain: {self.jira_domain}")
        print(f"JIRA Project: {self.jira_project}")
        print()

        stats = {'total': 0, 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}

        repo_list = []
        if repos:
            repo_list = [r.strip() for r in repos.split(',') if r.strip()]
        else:
            repo_list = [None]  # Default: all events

        for repo in repo_list:
            if repo:
                print(f"\n🔍 Fetching events for repository: {repo}")
            events = self.fetch_github_events(max_pages=max_pages, repo=repo)
            comment_events = self.filter_comment_events(events)

            if not comment_events:
                print(f"No comment events found in the specified range for {repo if repo else 'all repos'}")
                continue

            # Process events
            for i, event in enumerate(comment_events, 1):
                print(f"\n📊 Processing comment {i}/{len(comment_events)} for {repo if repo else 'all repos'}")
                result, success = self.process_comment_event(event, dry_run)
                stats['processed'] += 1
                stats['total'] += 1
                if result == 'skipped':
                    stats['skipped'] += 1
                elif result in ['contribution', 'discussion'] and success:
                    stats['created'] += 1
                else:
                    stats['errors'] += 1
                # Rate limiting between requests
                if i < len(comment_events):
                    time.sleep(1)

        print("\n=== Migration Summary ===")
        print(f"Total Comments Processed: {stats['total']}")
        print(f"JIRA Tasks Created/Updated: {stats['created']}")
        print(f"Skipped (own/org/existing): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Timestamp: {datetime.now()}")

        return stats
    
    def process_specific_issue(self, repo_owner: str, repo_name: str, issue_number: int, dry_run: bool = False) -> Tuple[str, bool]:
        """Process a specific GitHub issue by issue number"""
        try:
            print(f"\n--- Processing Specific Issue #{issue_number} ---")
            print(f"Repository: {repo_owner}/{repo_name}")
            
            # Check if should skip (skip own repos)
            if self.should_skip_repo(repo_owner):
                print(f"✅ SKIPPED: Own/org repo - {repo_owner}/{repo_name}")
                return 'skipped', True
            
            # Fetch issue details
            headers = self.get_github_headers()
            
            issue_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
            response = requests.get(issue_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Could not fetch issue #{issue_number}: {response.status_code}")
                return 'error', False
            
            issue_data = response.json()
            issue_title = issue_data.get('title', 'No title')
            issue_body = issue_data.get('body', 'No description available')
            issue_html_url = issue_data.get('html_url', '')
            issue_state = issue_data.get('state', 'unknown')
            created_at = issue_data.get('created_at', '')
            
            print(f"Title: {issue_title}")
            print(f"State: {issue_state}")
            print(f"URL: {issue_html_url}")
            
            # Check for existing JIRA task
            existing_key = self.search_existing_jira_task(issue_html_url, issue_number, repo_name)
            
            if existing_key:
                print(f"🔄 JIRA task already exists: {existing_key}")
                return 'existing', True
            
            # Check for user comments
            comments_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
            comments_response = requests.get(comments_url, headers=headers, timeout=10)
            
            user_comments = []
            if comments_response.status_code == 200:
                comments = comments_response.json()
                user_comments = [c for c in comments if c.get('user', {}).get('login') == self.github_user]
            
            print(f"Your comments found: {len(user_comments)}")
            
            # Check if user is the author of this issue/PR
            issue_author = issue_data.get('user', {}).get('login', '')
            is_author = (issue_author == self.github_user)
            
            print(f"Issue/PR author: {issue_author}")
            print(f"You are the author: {is_author}")
            
            if not user_comments and not is_author:
                print("❌ No comments found by you on this issue and you're not the author")
                return 'no_comments', False
            
            # Check fork status
            is_fork = self.check_fork_status(f"{repo_owner}/{repo_name}")
            
            # Determine content for JIRA task
            if user_comments:
                # Use the first comment for JIRA task creation
                first_comment = user_comments[0]
                comment_body = first_comment.get('body', 'No comment body')
                comment_date = first_comment.get('created_at', created_at)
                content_type = "comment"
            else:
                # User is author but no comments - use PR/issue description
                comment_body = f"Authored this {'PR' if issue_data.get('pull_request') else 'issue'}"
                comment_date = created_at
                content_type = "authorship"
            
            # Check PR status to determine Kanban column
            pr_status = self.check_pr_status(repo_owner, repo_name, issue_number)
            
            # For old issue migration, always use Pull Request for PRs (don't put in Done)
            if pr_status.get('is_pr') or pr_status.get('has_linked_pr'):
                # This is a PR or has linked PR - always go to Pull Request column
                kanban_status = "Pull Request"
                pr_state = pr_status.get('state', 'unknown')
                if pr_status.get('merged'):
                    labels = [repo_owner, repo_name, "fork-repo", "pull-request", "merged"]
                elif pr_state == 'closed':
                    labels = [repo_owner, repo_name, "fork-repo", "pull-request", "closed"]
                elif pr_state == 'open':
                    labels = [repo_owner, repo_name, "fork-repo", "pull-request", "open"]
                else:
                    labels = [repo_owner, repo_name, "fork-repo", "pull-request"]
            else:
                # Regular issue discussion
                kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name)
            
            # Avoid duplicate labels when owner and repo name are the same
            if repo_owner == repo_name:
                labels = [repo_owner] + [l for l in labels if l not in [repo_owner, repo_name]]
            
            print(f"📊 Issue Analysis:")
            print(f"   Is Fork: {is_fork}")
            print(f"   PR Status: {pr_status}")
            print(f"   Kanban Column: {kanban_status}")
            print(f"   Labels: {labels}")
            
            # Determine task type and description
            if kanban_status == "Done":
                task_type = "contribution-merged"
                description_prefix = "✅ MERGED Contribution"
            elif kanban_status == "Pull Request":
                task_type = "contribution-pr"
                description_prefix = "🔄 Active Pull Request"
            elif is_fork:
                task_type = "contribution-discussion"
                description_prefix = "💭 Discussion on Forked Repo"
            else:
                task_type = "external-discussion"
                description_prefix = "💬 Discussion on External Repo"
            
            # Create new task
            task_summary = f"{issue_number} - {issue_title}"
            
            # Enhanced description with PR status
            pr_info = ""
            if pr_status.get('is_pr'):
                pr_info = f"\n🔄 This is a Pull Request (#{issue_number}) - Status: {pr_status.get('state', 'unknown')}"
                if pr_status.get('merged'):
                    pr_info += " - ✅ MERGED"
            elif pr_status.get('has_linked_pr'):
                pr_info = f"\n🔗 Linked to PR #{pr_status.get('pr_number')} - Status: {pr_status.get('state', 'unknown')}"
                if pr_status.get('merged'):
                    pr_info += " - ✅ MERGED"
            
            # Add all comments if multiple, or authorship info
            if content_type == "authorship":
                comments_section = f"Authored this {'PR' if pr_status.get('is_pr') else 'issue'}:\n{issue_body}"
                if user_comments:
                    comments_section += f"\n\n--- My Comments ({len(user_comments)}) ---"
                    for i, comment in enumerate(user_comments, 1):
                        comment_date_extra = comment.get('created_at', 'Unknown')
                        comment_body_extra = comment.get('body', '')
                        comments_section += f"\n\nComment {i} ({comment_date_extra}):\n{comment_body_extra}"
            else:
                comments_section = f"My Comment:\n{comment_body}"
                if len(user_comments) > 1:
                    comments_section += f"\n\n--- Additional Comments ({len(user_comments)-1} more) ---"
                    for i, comment in enumerate(user_comments[1:], 2):
                        comment_date_extra = comment.get('created_at', 'Unknown')
                        comment_body_extra = comment.get('body', '')
                        comments_section += f"\n\nComment {i} ({comment_date_extra}):\n{comment_body_extra}"
            
            task_description = f"""{description_prefix}

Issue Description:
{issue_body}

{comments_section}
{pr_info}

GitHub Issue: {issue_html_url}
Repo: {repo_owner}/{repo_name}
Kanban Status: {kanban_status}
Original Date: {comment_date}"""
            
            if dry_run:
                print(f"🧪 DRY RUN: Would create {task_type} task")
                print(f"   Summary: {task_summary}")
                print(f"   Labels: {labels}")
                print(f"   Kanban Status: {kanban_status}")
                return 'dry_run', True
            
            # Create JIRA task
            headers = self.get_jira_headers()
            
            payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": task_summary,
                    "description": task_description,
                    "issuetype": {"name": "Task"},
                    "labels": labels
                }
            }
            
            url = f"https://{self.jira_domain}/rest/api/2/issue"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                task_key = result.get('key', 'Unknown')
                print(f"✅ Created JIRA task: {task_key} (Status: {kanban_status})")
                
                # Try to move to appropriate status if needed
                self.update_jira_status(task_key, kanban_status, dry_run=False)
                
                return 'created', True
            else:
                print(f"❌ Failed to create JIRA task: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return 'error', False
                
        except Exception as e:
            print(f"❌ Error processing issue: {e}")
            return 'error', False
    
    def run_old_issue_migration(self, issue_list: List[str], dry_run: bool = False) -> Dict:
        """Run migration for specific old issues that might not be in Events API"""
        print("=== Starting Old Issue Migration ===")
        print(f"Timestamp: {datetime.now()}")
        print(f"Dry Run: {dry_run}")
        print()
        
        print("=== Configuration Details ===")
        print(f"GitHub User: {self.github_user}")
        print(f"Issues to process: {', '.join(issue_list)}")
        print(f"JIRA Domain: {self.jira_domain}")
        print(f"JIRA Project: {self.jira_project}")
        print()
        
        stats = {'total': len(issue_list), 'processed': 0, 'created': 0, 'existing': 0, 'skipped': 0, 'no_comments': 0, 'errors': 0}
        
        for i, issue_spec in enumerate(issue_list, 1):
            try:
                # Parse issue specification: "owner/repo#123" or "owner/repo/123"
                if '#' in issue_spec:
                    repo_part, issue_num = issue_spec.split('#')
                elif '/' in issue_spec and issue_spec.count('/') >= 2:
                    parts = issue_spec.split('/')
                    repo_part = '/'.join(parts[:-1])
                    issue_num = parts[-1]
                else:
                    print(f"❌ Invalid issue format: {issue_spec}. Use 'owner/repo#123' or 'owner/repo/123'")
                    stats['errors'] += 1
                    continue
                
                repo_owner, repo_name = repo_part.split('/')
                issue_number = int(issue_num)
                
                print(f"\n📊 Processing issue {i}/{len(issue_list)}: {repo_owner}/{repo_name}#{issue_number}")
                result, success = self.process_specific_issue(repo_owner, repo_name, issue_number, dry_run)
                stats['processed'] += 1
                
                if result == 'skipped':
                    stats['skipped'] += 1
                elif result == 'existing':
                    stats['existing'] += 1
                elif result == 'no_comments':
                    stats['no_comments'] += 1
                elif result in ['created', 'dry_run'] and success:
                    stats['created'] += 1
                else:
                    stats['errors'] += 1
                
                # Rate limiting between requests
                if i < len(issue_list):
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error parsing issue spec '{issue_spec}': {e}")
                stats['errors'] += 1
                continue
        
        print("\n=== Old Issue Migration Summary ===")
        print(f"Total Issues: {stats['total']}")
        print(f"Issues Processed: {stats['processed']}")
        print(f"JIRA Tasks Created: {stats['created']}")
        print(f"Existing Tasks Found: {stats['existing']}")
        print(f"No Comments Found: {stats['no_comments']}")
        print(f"Skipped (own repos): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Timestamp: {datetime.now()}")
        
        return stats
    
    def process_create_event(self, event: Dict, dry_run: bool = False) -> Tuple[str, bool]:
        """Process a branch creation event to support TODO status in Kanban flow"""
        try:
            payload = event.get('payload', {})
            repo = event.get('repo', {})
            ref = payload.get('ref', '')
            branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
            repo_name = repo.get('name', '')
            repo_owner = repo_name.split('/')[0] if '/' in repo_name else ''
            repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
            
            print(f"\n--- Processing Branch Creation Event ---")
            print(f"Repository: {repo_name}")
            print(f"Branch: {branch_name}")
            
            # Detect issue number in branch name
            issue_number = self.parse_issue_from_branch(branch_name)
            if not issue_number:
                print(f"No issue number detected in branch name: {branch_name}")
                return 'no_issue_detected', True
            
            # Check fork status
            is_fork = self.check_fork_status(repo_name)
            
            # Event context for TODO
            event_context = {'is_branch_created_with_issue': True}
            pr_status = {}  # No PR yet
            kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name_only, event_context)
            
            # Prepare event data
            event_data = {
                'repo_name': repo_name,
                'repo_owner': repo_owner,
                'issue_url': f"https://github.com/{repo_name}/issues/{issue_number}",
                'issue_title': f"Branch created for issue #{issue_number}",
                'issue_number': issue_number,
                'comment_body': f"Branch {branch_name} created for issue #{issue_number}",
                'created_at': event.get('created_at', '')
            }
            success = self.create_jira_task(event_data, is_fork, dry_run, kanban_status, labels)
            if success:
                return 'todo', True
            else:
                return 'error', False
        except Exception as e:
            print(f"❌ Error processing branch creation event: {e}")
            return 'error', False

    def run_full_migration(self, target_repos: list = None, max_pages: int = 5, limit_per_repo: int = 0, dry_run: bool = False) -> dict:
        """Run migration for all event types (PRs, issues, comments, pushes) for specified repos."""
        print("=== Starting Full Migration (All Event Types) ===")
        print(f"Timestamp: {datetime.now()}")
        print(f"Max Pages per repo: {max_pages}")
        print(f"Limit per repo: {limit_per_repo if limit_per_repo > 0 else 'No limit'}")
        print(f"Dry Run: {dry_run}")
        print()

        if target_repos is None:
            print("❌ No target repositories specified. Use --repos to specify repos.")
            return {'total': 0, 'processed': 0, 'created': 0, 'existing': 0, 'skipped': 0, 'errors': 0}

        print("=== Configuration Details ===")
        print(f"GitHub User: {self.github_user}")
        print(f"Target Repositories: {', '.join(target_repos)}")
        print(f"JIRA Domain: {self.jira_domain}")
        print(f"JIRA Project: {self.jira_project}")
        print()

        stats = {'total': 0, 'processed': 0, 'created': 0, 'existing': 0, 'skipped': 0, 'errors': 0}

        for repo_full_name in target_repos:
            if '/' not in repo_full_name:
                print(f"⚠️  Invalid repo format: {repo_full_name}")
                stats['skipped'] += 1
                continue
            repo_owner, repo_name = repo_full_name.split('/', 1)

            # Fetch all events for this repo
            print(f"\n🔍 Fetching events for repository: {repo_full_name}")
            events = self.fetch_github_events(repo=repo_full_name, max_pages=max_pages)
            comment_events = self.filter_comment_events(events)
            authorship_events = self.filter_authorship_events(events)
            total_events = len(comment_events) + len(authorship_events)
            stats['total'] += total_events

            print(f"📊 Total events to process for {repo_full_name}: {total_events}")

            # Process comment events
            for event in comment_events:
                try:
                    result, success = self.process_comment_event(event, dry_run)
                    stats['processed'] += 1
                    if result == 'skipped':
                        stats['skipped'] += 1
                    elif result in ['contribution', 'discussion'] and success:
                        stats['created'] += 1
                    else:
                        stats['errors'] += 1
                except Exception as e:
                    print(f"❌ Error processing comment event: {e}")
                    stats['errors'] += 1

            # Process authorship events
            for event in authorship_events:
                try:
                    result, success = self.process_authorship_event(event, dry_run)
                    stats['processed'] += 1
                    if result == 'skipped':
                        stats['skipped'] += 1
                    elif result in ['contribution', 'discussion'] and success:
                        stats['created'] += 1
                    else:
                        stats['errors'] += 1
                except Exception as e:
                    print(f"❌ Error processing authorship event: {e}")
                    stats['errors'] += 1

        print("\n=== Migration Summary ===")
        for k, v in stats.items():
            print(f"{k.title()}: {v}")
        return stats

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GitHub-JIRA Monitor/Migration Tool")
    parser.add_argument('mode', choices=['monitor', 'migrate'], help='Run in monitor or migrate mode')
    parser.add_argument('--since', type=int, default=15, help='Minutes to look back for monitor mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no JIRA changes)')
    parser.add_argument('--max-pages', type=int, default=10, help='Max pages to fetch per repo for migration')
    parser.add_argument('--limit-per-repo', type=int, default=0, help='Limit PRs per repo (0 = no limit)')
    parser.add_argument('--repos', nargs='*', help='Target repositories for migration (owner/repo format)')
    args = parser.parse_args()

    monitor = GitHubJIRAMonitor()

if args.mode == 'monitor':
    monitor.run_monitor(since_minutes=args.since, dry_run=args.dry_run)
elif args.mode == 'migrate':
    target_repos = args.repos if args.repos else None
    stats = monitor.run_full_migration(
        target_repos=target_repos,
        max_pages=args.max_pages,
        limit_per_repo=args.limit_per_repo,
        dry_run=args.dry_run
    )
    print("\n=== Migration Summary ===")
    for k, v in stats.items():
        print(f"{k.title()}: {v}")