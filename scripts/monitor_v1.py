# Main workflow and class for v1, using the split-out modules

import os
import requests
from . import github_api_v1
from . import jira_api_v1
from . import comments_v1
from datetime import datetime, timedelta
from collections import defaultdict
import re
from .utils_v1 import should_skip_repo, parse_issue_from_branch
from . import analysis_v1
from . import jira_tasks_v1

from .placeholders_v1 import MonitorPlaceholders

# --- Centralized config validation ---
def validate_config():
    required_env = [
        'GH_USER', 'GH_TOKEN', 'JIRA_DOMAIN', 'JIRA_PROJECT', 'JIRA_AUTH'
    ]
    missing = [k for k in required_env if not os.environ.get(k)]
    if missing:
        print(f"\n❌ ERROR: Missing required config: {', '.join(missing)}. Please check your .env, secrets, or workflow configuration.")
        exit(1)

class GitHubJIRAMonitor(MonitorPlaceholders):
    def update_jira_status(self, task_key, status, dry_run=False):
        """Delegate to jira_api_v1.update_jira_status for modular access."""
        return jira_api_v1.update_jira_status(self.jira_domain, self.jira_auth, task_key, status, dry_run=dry_run)
    def should_skip_repo(self, repo_owner):
        """Delegate to utils_v1.should_skip_repo for modular access."""
        return should_skip_repo(self, repo_owner)

    def parse_issue_from_branch(self, branch_name):
        """Delegate to utils_v1.parse_issue_from_branch for modular access."""
        return parse_issue_from_branch(branch_name)
    def __init__(self):
        self.github_user = os.environ.get('GH_USER', 'octocat')
        self.github_token = os.environ.get('GH_TOKEN', '')
        self.jira_domain = os.environ.get('JIRA_DOMAIN', '')
        self.jira_project = os.environ.get('JIRA_PROJECT', '')
        self.jira_auth = os.environ.get('JIRA_AUTH', '')
        skip_orgs = os.environ.get('SKIP_ORGS', '')
        self.skip_orgs = [org.strip() for org in skip_orgs.split(',') if org.strip()]
        if 'intemo-dev' not in self.skip_orgs:
            self.skip_orgs.append('intemo-dev')
        if not self.github_user or not self.github_token or not self.jira_domain or not self.jira_project or not self.jira_auth:
            print("❌ ERROR: Missing required environment variables. Please set GH_USER, GH_TOKEN, JIRA_DOMAIN, JIRA_PROJECT, JIRA_AUTH (and optionally SKIP_ORGS).")
            exit(1)

    # --- Modular API methods ---
    fetch_user_pull_requests = staticmethod(github_api_v1.fetch_user_pull_requests)
    process_pull_request = staticmethod(github_api_v1.process_pull_request)
    process_specific_issue = staticmethod(github_api_v1.process_specific_issue)
    def get_github_headers(self):
        return github_api_v1.get_github_headers(self.github_token)

    def get_jira_headers(self):
        return jira_api_v1.get_jira_headers(self.jira_auth)
    @staticmethod
    def search_existing_jira_task(issue_url, issue_number, repo_name, repo_owner):
        # Import config from environment for static context
        import os
        jira_domain = os.environ.get('JIRA_DOMAIN', '')
        jira_project = os.environ.get('JIRA_PROJECT', '')
        jira_auth = os.environ.get('JIRA_AUTH', '')
        print(f"[DEBUG] search_existing_jira_task called with: issue_url={issue_url}, issue_number={issue_number}, repo_name={repo_name}, repo_owner={repo_owner}")
        return jira_api_v1.search_existing_jira_task(jira_domain, jira_project, jira_auth, issue_url, issue_number, repo_name, repo_owner)
    project_supports_epic = staticmethod(jira_api_v1.project_supports_epic) if hasattr(jira_api_v1, 'project_supports_epic') else staticmethod(lambda *a, **kw: False)
    filter_comment_events = staticmethod(comments_v1.filter_comment_events)
    filter_authorship_events = staticmethod(comments_v1.filter_authorship_events)

    # --- All workflow, grouping, and logging methods from v1.py ---
    # Use comments_v1.create_activity_log_from_events instead of local method
    def _attach_epic_post_creation(self, task_key: str, epic_key: str, repo_owner: str):
        """Attach a JIRA task to an Epic after creation using the Epic Link field."""
        try:
            epic_link_field = self.get_epic_link_field_id()
            if not epic_link_field:
                print(f"    ❌ Could not find Epic Link field ID for project {self.jira_project}")
                return False
            # Extra debug: print which field is being used
            print(f"    [DEBUG] Using Epic Link field: {epic_link_field}")
            if epic_link_field == 'customfield_10011':
                print(f"    [WARNING] Attempting to use 'Epic Name' field (customfield_10011) for Task. This is incorrect. You must use the 'Epic Link' field (usually customfield_10014 or similar) for Task-to-Epic relationships.")
            url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}"
            headers = self.get_jira_headers()
            payload = {"fields": {epic_link_field: epic_key}}
            response = requests.put(url, headers=headers, json=payload, timeout=15)
            if response.status_code in [200, 204]:
                print(f"    ✅ Successfully attached {task_key} to Epic {epic_key}")
                return True
            else:
                print(f"    ❌ Failed to attach Epic: {response.status_code} {response.text}")
                return False
        except Exception as e:
            print(f"    ❌ Exception attaching Epic: {e}")
            return False
    def add_jira_comment_for_pr_review(self, repo_owner, repo_name, issue_number, body, author, created, resolved, dry_run=False):
        """
        Add a PR review comment to the corresponding JIRA task, including resolved/unresolved status.
        """
        # Find the JIRA task for this issue/PR
        issue_url = f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}"
        jira_key = self.search_existing_jira_task(issue_url, issue_number, repo_name, repo_owner)
        if not jira_key:
            print(f"      ⚠️  No JIRA task found for PR #{issue_number} in {repo_owner}/{repo_name}")
            return False
        status_str = 'RESOLVED' if resolved else 'UNRESOLVED'
        jira_comment = (
            f"GITHUB PR REVIEW COMMENT\n"
            f"------------------------\n"
            f"Author: @{author}\n"
            f"Date: {created}\n"
            f"Status: {status_str}\n"
            f"Comment: {body}\n"
            f"------------------------"
        )
        if dry_run:
            print(f"      🧪 DRY RUN: Would add PR review comment to JIRA {jira_key}:")
            print(jira_comment)
            return True
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{jira_key}/comment"
            payload = {"body": jira_comment}
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code in [200, 201]:
                print(f"      ✅ Added PR review comment to JIRA {jira_key}")
                return True
            else:
                print(f"      ❌ Failed to add PR review comment to JIRA {jira_key}: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"      ❌ Error adding PR review comment to JIRA: {e}")
            return False
    def process_all_forked_repos(self, max_issues_per_repo=20, dry_run=False):
        """
        Fetch all forked repos for the user and process their issues/PRs directly.
        This covers all forks, not just those with recent activity.
        """
        print("\n🚀 === PROCESSING ALL FORKED REPOS ===")
        headers = self.get_github_headers()
        url = f"https://api.github.com/users/{self.github_user}/repos?type=forks&per_page=100"
        page = 1
        forked_repos = []
        while True:
            paged_url = url + f"&page={page}"
            resp = requests.get(paged_url, headers=headers, timeout=20)
            if resp.status_code != 200:
                print(f"❌ Error fetching forked repos: {resp.status_code} {resp.text[:200]}")
                break
            repos = resp.json()
            if not repos:
                break
            forked_repos.extend(repos)
            if len(repos) < 100:
                break
            page += 1
        print(f"✅ Total forked repos found: {len(forked_repos)}")
        # Optionally process issues/PRs for each forked repo here
    def project_supports_epic(self):
        try:
            url = f"https://{self.jira_domain}/rest/api/2/issue/createmeta?projectKeys={self.jira_project}&expand=projects.issuetypes"
            headers = self.get_jira_headers()
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
    def get_epic_link_field_id(self):
        """Dynamically find the custom field ID for 'Epic Link' in JIRA and cache it. Only returns true Epic Link fields, never Epic Name."""
        if hasattr(self, '_epic_link_field_id') and self._epic_link_field_id:
            return self._epic_link_field_id
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/field"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                fields = resp.json()
                # Only consider fields with 'Epic Link' in the name or id, never 'Epic Name'
                for field in fields:
                    field_name = field.get('name', '').strip()
                    field_id = field.get('id', '')
                    # Only match 'Epic Link' (not 'Epic Name')
                    if field_name.lower() == 'epic link' or ('epic' in field_name.lower() and 'link' in field_name.lower()):
                        if 'name' in field and field['name'].lower() == 'epic name':
                            continue
                        self._epic_link_field_id = field_id
                        print(f"[JIRA] Found Epic Link field: '{field_name}' -> {field_id}")
                        return self._epic_link_field_id
                    # Also allow id-based match for legacy JIRA (e.g. customfield_10014)
                    if 'epic' in field_id.lower() and 'link' in field_id.lower():
                        self._epic_link_field_id = field_id
                        print(f"[JIRA] Found Epic Link field by id: '{field_name}' -> {field_id}")
                        return self._epic_link_field_id
                print("[JIRA] No valid Epic Link field found (only 'Epic Name' or none present). Please check your JIRA configuration.")
                return None
        except Exception as e:
            print(f"❌ Error processing specific issue: {e}")
            return None
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
    def filter_comment_events(self, events):
        """Filter for IssueCommentEvents and PullRequestReviewCommentEvents"""
        comment_types = ['IssueCommentEvent', 'PullRequestReviewCommentEvent']
        comment_events = [e for e in events if e.get('type') in comment_types]
        print(f"💬 Comment events found: {len(comment_events)}")
        return comment_events
    def filter_authorship_events(self, events):
        """Filter for PR/Issue creation and Push events (authorship)"""
        authorship_types = ['PullRequestEvent', 'IssuesEvent', 'PushEvent']
        authorship_events = [e for e in events if e.get('type') in authorship_types]
        print(f"✍️  Authorship events found: {len(authorship_events)}")
        return authorship_events
    def fetch_github_events(self, since=None, max_pages=10, repo=None):
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
    def gather_and_group_github_data(self, max_pages=10, since_minutes=None):
        """
        CORE FUNCTION: Gather all GitHub data and group by owner/repo/issue number
        This implements the flow from the STATUS_FLOW_PROPOSAL.md
        Returns structured data grouped by repo and issue with status analysis
        """
        return analysis_v1.gather_and_group_github_data(self, max_pages=max_pages, since_minutes=since_minutes)
    def _extract_issue_numbers_from_event(self, event):
        """Extract all possible issue numbers from a GitHub event"""
        return analysis_v1.extract_issue_numbers_from_event(self, event)
    def _get_issue_details_for_analysis(self, repo_owner, repo_name, issue_num):
        """Fetch detailed issue information for analysis"""
        return analysis_v1.get_issue_details_for_analysis(self, repo_owner, repo_name, issue_num)
    def _analyze_pr_status_for_issue(self, repo_owner, repo_name, issue_num, events):
        """Analyze PR status for an issue using events and GitHub API"""
        return analysis_v1.analyze_pr_status_for_issue(self, repo_owner, repo_name, issue_num, events)
    def _detect_backward_flow_triggers(self, issue_data, pr_info):
        """
        Detect backward flow triggers from STATUS_FLOW_PROPOSAL.md
        """
        return analysis_v1.detect_backward_flow_triggers(self, issue_data, pr_info)
    def _is_event_on_open_pr(self, event, pr_info):
        """
        Check if an event is happening on the open PR itself
        """
        return analysis_v1.is_event_on_open_pr(self, event, pr_info)
    def _determine_final_status(self, issue_data, pr_info):
        """
        Determine final status using STATUS_FLOW_PROPOSAL.md priority logic
        """
        return analysis_v1.determine_final_status(self, issue_data, pr_info)
    def create_jira_objects_from_grouped_data(self, grouped_data, dry_run=False):
        """
        Create JIRA objects from the grouped and analyzed GitHub data
        Delegates to jira_tasks_v1 for all JIRA epic/task creation logic.
        """
        return jira_tasks_v1.create_jira_objects_from_grouped_data(self, grouped_data, dry_run=dry_run)
    def _get_or_create_epic_for_owner(self, repo_owner, created_epics, dry_run=False):
        """Get or create an Epic for the repository owner (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._get_or_create_epic_for_owner(self, repo_owner, created_epics, dry_run=dry_run)
    def _verify_epic_creation(self, epic_key, repo_owner):
        """Verify that an Epic was created successfully and has proper fields (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._verify_epic_creation(self, epic_key, repo_owner)
    def _create_jira_task_from_grouped_data(self, repo_owner, repo_name, issue_num, issue_data, epic_key, dry_run=False):
        """Create a JIRA task from grouped issue data (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._create_jira_task_from_grouped_data(self, repo_owner, repo_name, issue_num, issue_data, epic_key, dry_run=dry_run)
    def _verify_epic_attachment(self, task_key, expected_epic_key):
        """Verify that a task is properly attached to an Epic (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._verify_epic_attachment(self, task_key, expected_epic_key)
    def _get_issue_comments_for_task(self, repo_owner, repo_name, issue_num):
        """Extract comments from GitHub issue/PR data for JIRA task creation"""
        first_comment = None
        subsequent_comments = []
        try:
            # Build GitHub API URLs
            issue_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_num}"
            comments_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_num}/comments"
            pr_review_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{issue_num}/comments"
            headers = self.get_github_headers()
            # Fetch issue details (for the original body)
            issue_response = requests.get(issue_url, headers=headers)
            if issue_response.status_code == 200:
                issue_data = issue_response.json()
                first_comment = issue_data
            # Fetch issue comments
            comments = []
            comments_response = requests.get(comments_url, headers=headers)
            if comments_response.status_code == 200:
                comments = comments_response.json()
            # Fetch PR review comments (if PR)
            pr_review_comments = []
            pr_review_response = requests.get(pr_review_url, headers=headers)
            if pr_review_response.status_code == 200:
                pr_review_comments = pr_review_response.json()
            # Combine all comments (issue comments + PR review comments)
            all_comments = []
            # Add issue comments (skip if body is same as first_comment to avoid duplication)
            for c in comments:
                if first_comment and c.get('body', '') == first_comment.get('body', ''):
                    continue
                all_comments.append(c.get('body', ''))
            for c in pr_review_comments:
                all_comments.append(c.get('body', ''))
            subsequent_comments = all_comments
        except Exception as e:
            pass
        return {
            'first_comment': first_comment.get('body', '') if first_comment else None,
            'subsequent_comments': subsequent_comments
        }
    def _add_comments_to_jira_task(self, task_key, comments):
        """Add GitHub comments to JIRA task as comments (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._add_comments_to_jira_task(self, task_key, comments)
    def _log_activity_transitions_to_jira(self, task_key, events, final_status):
        """Log status transitions as JIRA comments based on GitHub events (delegated to jira_tasks_v1)"""
        return jira_tasks_v1._log_activity_transitions_to_jira(self, task_key, events, final_status)
    def run_core_workflow(self, max_pages=10, since_minutes=None, dry_run=True):
        """Main entry point for running the core workflow"""
        grouped = self.gather_and_group_github_data(max_pages=max_pages, since_minutes=since_minutes)
        stats = self.create_jira_objects_from_grouped_data(grouped['grouped_data'], dry_run=dry_run)
        print("\n=== WORKFLOW COMPLETE ===")
        print(stats)
        return stats

# v1.py style main guard and usage example
if __name__ == "__main__":
    validate_config()
    monitor = GitHubJIRAMonitor()
    monitor.run_core_workflow(max_pages=10, since_minutes=None, dry_run=True)
