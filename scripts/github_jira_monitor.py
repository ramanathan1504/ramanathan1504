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
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class GitHubJIRAMonitor:
    def search_existing_jira_task(self, issue_url: str, issue_number: int, repo_name: str, repo_owner: str = None) -> Optional[str]:
        """Search for existing JIRA task with this GitHub issue URL in the description (deduplication by URL, repo, and issue number)"""
        try:
            headers = self.get_jira_headers()
            # Escape special characters in the issue URL for JQL search
            escaped_url = issue_url.replace('\\', '\\\\').replace('"', '\\"')
            # Use the escaped GitHub issue URL as a unique identifier in the description
            jql = f'project = "{self.jira_project}" AND description ~ "{escaped_url}" AND summary ~ "{issue_number}"'
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 10}
            print(f"🔍 [Deduplication] Searching for existing task with GitHub issue URL: {issue_url}")
            print(f"🔍 [Deduplication] JQL: {jql}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                print(f"📊 [Deduplication] Found {result.get('total', 0)} potential matches by URL/issue number")
                if result.get('total', 0) > 0:
                    for issue in result.get('issues', []):
                        desc = issue.get('fields', {}).get('description', '')
                        summary = issue.get('fields', {}).get('summary', '')
                        # Check both URL and issue number in summary for extra safety
                        if (issue_url.lower() in (desc or '').lower()):
                            # Check for summary pattern: '#issue_number' and repo_owner/repo_name
                            summary_lower = summary.lower()
                            repo_owner_match = repo_owner.lower() if repo_owner else ''
                            repo_name_match = repo_name.lower() if repo_name else ''
                            if (
                                f"#{issue_number}" in summary_lower and
                                (repo_owner_match in summary_lower or repo_owner_match in desc.lower()) and
                                (repo_name_match in summary_lower or repo_name_match in desc.lower())
                            ):
                                print(f"✅ [Deduplication] Exact match found: {issue['key']}")
                                return issue['key']
                    print(f"📝 [Deduplication] No exact URL+issue+repo match found in descriptions/summaries")
                else:
                    print(f"📝 [Deduplication] No tasks found with URL+issue in description/summary")
            else:
                print(f"⚠️  [Deduplication] JIRA search failed: {response.status_code} - {response.text[:200]}")
            return None
        except Exception as e:
            print(f"⚠️  [Deduplication] Error searching JIRA: {e}")
            return None

    def _create_activity_log_from_events(self, events):
        """Create a simple GitHub activity timeline from a list of events for JIRA description/logging."""
        if not events:
            return ""
        activity_lines = []
        # Sort events chronologically
        sorted_events = sorted(events, key=lambda x: x.get('created_at', ''))
        for event in sorted_events:
            event_type = event.get('type')
            created_at = event.get('created_at', '')
            if event_type == 'IssuesEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_lines.append(f"• Issue opened ({created_at})")
                elif action == 'closed':
                    activity_lines.append(f"• Issue closed ({created_at})")
                elif action == 'reopened':
                    activity_lines.append(f"• Issue reopened ({created_at})")
            elif event_type == 'PullRequestEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_lines.append(f"• Pull request opened ({created_at})")
                elif action == 'closed':
                    merged = event.get('payload', {}).get('pull_request', {}).get('merged', False)
                    if merged:
                        activity_lines.append(f"• Pull request merged ({created_at})")
                    else:
                        activity_lines.append(f"• Pull request closed without merge ({created_at})")
                elif action == 'reopened':
                    activity_lines.append(f"• Pull request reopened ({created_at})")
            elif event_type == 'PushEvent':
                ref = event.get('payload', {}).get('ref', '')
                commits = len(event.get('payload', {}).get('commits', []))
                if 'main' in ref or 'master' in ref:
                    activity_lines.append(f"• {commits} commits pushed to main branch ({created_at})")
            elif event_type == 'IssueCommentEvent':
                action = event.get('payload', {}).get('action')
                if action == 'created':
                    activity_lines.append(f"• Comment added ({created_at})")
        if activity_lines:
            return f"*GitHub Activity Timeline:*\n\n" + "\n".join(activity_lines[-10:])  # Last 10 activities
        return ""
    def _attach_epic_post_creation(self, task_key: str, epic_key: str, repo_owner: str) -> bool:
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
    def get_epic_link_field_id(self) -> str:
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

        self.github_user = os.environ.get('GH_USER')
        self.github_token = os.environ.get('GH_TOKEN')
        self.jira_domain = os.environ.get('JIRA_DOMAIN')
        self.jira_project = os.environ.get('JIRA_PROJECT')
        self.jira_auth = os.environ.get('JIRA_AUTH')
        # Comma-separated orgs to skip, or empty list
        skip_orgs = os.environ.get('SKIP_ORGS', '')
        self.skip_orgs = [org.strip() for org in skip_orgs.split(',') if org.strip()]
        
        # Always skip intemo-dev (your organization)
        if 'intemo-dev' not in self.skip_orgs:
            self.skip_orgs.append('intemo-dev')

        # Basic validation
        if not self.github_user or not self.github_token or not self.jira_domain or not self.jira_project or not self.jira_auth:
            print("❌ ERROR: Missing required environment variables. Please set GH_USER, GH_TOKEN, JIRA_DOMAIN, JIRA_PROJECT, JIRA_AUTH (and optionally SKIP_ORGS).")
            exit(1)

    def gather_and_group_github_data(self, max_pages: int = 10, since_minutes: int = None) -> Dict:
        """
        CORE FUNCTION: Gather all GitHub data and group by owner/repo/issue number
        This implements the flow from the STATUS_FLOW_PROPOSAL.md
        
        Returns structured data grouped by repo and issue with status analysis
        """
        print("🚀 === CORE DATA GATHERING & GROUPING ===")
        print(f"Fetching GitHub data (max {max_pages} pages)...")
        
        # Calculate since timestamp if provided
        since = None
        if since_minutes:
            since = (datetime.now() - timedelta(minutes=since_minutes)).isoformat() + 'Z'
            print(f"Looking for events since: {since}")
        
        # 1. GATHER ALL GITHUB EVENTS
        print("\n📊 Step 1: Gathering all GitHub events...")
        all_events = self.fetch_github_events(since=since, max_pages=max_pages)
        # Log all event types seen
        event_types_seen = set()
        for event in all_events:
            event_types_seen.add(event.get('type', 'UNKNOWN'))
        print(f"\n📝 All event types seen in fetched events: {sorted(event_types_seen)}")
        
        # 2. GROUP EVENTS BY REPO AND ISSUE
        print(f"\n🗂️  Step 2: Grouping {len(all_events)} events by owner/repo/issue...")
        grouped_data = defaultdict(lambda: defaultdict(lambda: {
            'issue_details': None,
            'events': [],
            'pr_info': None,
            'branch_info': {},
            'status_timeline': [],
            'final_status': 'DISCUSSION'
        }))
        processed_repos = set()
        
        # Group all events by repo and issue
        for event in all_events:
            repo_info = event.get('repo', {})
            repo_name = repo_info.get('name', '')
            # Log the repo name from event (removed for clean output)
            # if not repo_name or '/' not in repo_name:
            if not repo_name or '/' not in repo_name:
                # print(f"[DEBUG] Skipping event with invalid repo_name: {repo_name}")
                continue
            repo_owner, repo_name_only = repo_name.split('/', 1)
            # Log the repo_owner and repo_name_only (removed for clean output)
            # Check skip condition and log
            should_skip = self.should_skip_repo(repo_owner)
            # print(f"[DEBUG] should_skip_repo({repo_owner}) = {should_skip}")
            if should_skip:
                # print(f"[DEBUG] Skipping repo {repo_owner}/{repo_name_only} due to skip condition. (Own repo or org: {self.github_user}, {self.skip_orgs})")
                continue
            # else:
            #     print(f"[INFO] Including repo {repo_owner}/{repo_name_only} as external/forked (not in user/org skip list)")
            # Extract issue numbers from different event types
            issue_numbers = self._extract_issue_numbers_from_event(event)
            # print(f"[DEBUG] Extracted issue_numbers from event: {issue_numbers}")
            # Add event to all related issues
            for issue_num in issue_numbers:
                repo_key = f"{repo_owner}/{repo_name_only}"
                grouped_data[repo_key][issue_num]['events'].append(event)
                processed_repos.add(repo_key)
                # print(f"[DEBUG] Added event to grouped_data[{repo_key}][{issue_num}]")
        print(f"\n📝 All forked/external repos processed: {sorted(processed_repos)}")
        print(f"\n🔗 List of all my forked/external repo names:")
        for repo in sorted(processed_repos):
            print(f"  - {repo}")
        # Print all forked/external repos that had at least one comment event
        commented_repos = set()
        for repo_key, issues in grouped_data.items():
            for issue_num, issue_data in issues.items():
                for event in issue_data['events']:
                    if event.get('type') in ['IssueCommentEvent', 'PullRequestReviewCommentEvent']:
                        commented_repos.add(repo_key)
                        break
        print(f"\n💬 All forked/external repos with at least one comment event: {sorted(commented_repos)}")
        
        # 3. ANALYZE STATUS FOR EACH GROUPED ISSUE
        print(f"\n📈 Step 3: Analyzing status for each issue...")
        analyzed_data = {}
        
        for repo_key, issues in grouped_data.items():
            analyzed_data[repo_key] = {}
            repo_owner, repo_name_only = repo_key.split('/', 1)
            
            print(f"\n📦 Analyzing repository: {repo_key}")
            
            for issue_num, issue_data in issues.items():
                print(f"  🔍 Analyzing issue #{issue_num}...")
                # Log all events for this issue
                for ev in issue_data['events']:
                    ev_type = ev.get('type', 'UNKNOWN')
                    ev_created = ev.get('created_at', 'N/A')
                    print(f"    • Event: {ev_type} at {ev_created}")

                # Fetch full issue details
                issue_details = self._get_issue_details_for_analysis(repo_owner, repo_name_only, issue_num)
                issue_data['issue_details'] = issue_details

                # Analyze PR status
                pr_info = self._analyze_pr_status_for_issue(repo_owner, repo_name_only, issue_num, issue_data['events'])
                issue_data['pr_info'] = pr_info

                # Determine final status using STATUS_FLOW_PROPOSAL logic
                final_status, status_reasons = self._determine_final_status(issue_data, pr_info)
                issue_data['final_status'] = final_status
                issue_data['status_reasons'] = status_reasons

                # Store analyzed data
                analyzed_data[repo_key][issue_num] = issue_data

                print(f"    📊 Final Status: {final_status}")
                print(f"    📝 Reasons: {', '.join(status_reasons)}")
        
        # 4. SUMMARY STATISTICS
        total_repos = len(analyzed_data)
        total_issues = sum(len(issues) for issues in analyzed_data.values())
        status_counts = defaultdict(int)
        
        for repo_issues in analyzed_data.values():
            for issue_data in repo_issues.values():
                status_counts[issue_data['final_status']] += 1
        
        print(f"\n📊 === GROUPING SUMMARY ===")
        print(f"Total Repositories: {total_repos}")
        print(f"Total Issues: {total_issues}")
        print(f"Status Distribution:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        return {
            'grouped_data': analyzed_data,
            'summary': {
                'total_repos': total_repos,
                'total_issues': total_issues,
                'status_counts': dict(status_counts),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _extract_issue_numbers_from_event(self, event: Dict) -> List[int]:
        """Extract all possible issue numbers from a GitHub event"""
        issue_numbers = []
        event_type = event.get('type', '')
        payload = event.get('payload', {})
        
        # Direct issue/PR number from event
        if event_type in ['IssuesEvent', 'PullRequestEvent', 'IssueCommentEvent', 'PullRequestReviewCommentEvent']:
            if 'issue' in payload:
                issue_numbers.append(payload['issue'].get('number'))
            if 'pull_request' in payload:
                issue_numbers.append(payload['pull_request'].get('number'))
                
        # Extract from branch names in push events
        elif event_type == 'PushEvent':
            ref = payload.get('ref', '')
            branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
            branch_issue = self.parse_issue_from_branch(branch_name)
            if branch_issue:
                issue_numbers.append(branch_issue)
        
        # Extract from comments that reference issues
        if 'comment' in payload:
            comment_body = payload['comment'].get('body', '')
            referenced_issues = re.findall(r'#(\d+)', comment_body)
            issue_numbers.extend([int(num) for num in referenced_issues])
        
        return [num for num in issue_numbers if num]  # Remove None values
    
    def _get_issue_details_for_analysis(self, repo_owner: str, repo_name: str, issue_num: int) -> Dict:
        """Fetch detailed issue information for analysis"""
        try:
            headers = self.get_github_headers()
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_num}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"    ⚠️  Could not fetch issue #{issue_num}: {response.status_code}")
                return {}
        except Exception as e:
            print(f"    ❌ Error fetching issue #{issue_num}: {e}")
            return {}
    
    def _analyze_pr_status_for_issue(self, repo_owner: str, repo_name: str, issue_num: int, events: List[Dict]) -> Dict:
        """Analyze PR status for an issue using events and GitHub API"""
        pr_info = {
            'has_pr': False,
            'pr_number': None,
            'pr_state': None,
            'pr_merged': False,
            'pr_branch': None,
            'is_pr_itself': False
        }
        
        try:
            # Check if this issue number is actually a PR
            headers = self.get_github_headers()
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{issue_num}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                pr_data = response.json()
                pr_info.update({
                    'is_pr_itself': True,
                    'has_pr': True,
                    'pr_number': issue_num,
                    'pr_state': pr_data.get('state'),
                    'pr_merged': pr_data.get('merged', False),
                    'pr_branch': pr_data.get('head', {}).get('ref')
                })
                return pr_info
            
            # Look for linked PRs through branch names and events
            for event in events:
                if event.get('type') == 'PushEvent':
                    payload = event.get('payload', {})
                    ref = payload.get('ref', '')
                    branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
                    
                    # Check if there's a PR for this branch
                    pr_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
                    pr_params = {'head': f"{repo_owner}:{branch_name}", 'state': 'all'}
                    pr_response = requests.get(pr_url, headers=headers, params=pr_params, timeout=10)
                    
                    if pr_response.status_code == 200:
                        prs = pr_response.json()
                        if prs:
                            pr = prs[0]  # Get the first (most recent) PR for this branch
                            pr_info.update({
                                'has_pr': True,
                                'pr_number': pr.get('number'),
                                'pr_state': pr.get('state'),
                                'pr_merged': pr.get('merged', False),
                                'pr_branch': branch_name
                            })
                            break
            
            return pr_info
            
        except Exception as e:
            print(f"    ❌ Error analyzing PR status for issue #{issue_num}: {e}")
            return pr_info
    
    def _detect_backward_flow_triggers(self, issue_data: Dict, pr_info: Dict) -> Tuple[bool, str, List[str]]:
        """
        Detect backward flow triggers from STATUS_FLOW_PROPOSAL.md:
        1. Comment on open PR → IN PROGRESS
        2. @mention on open PR → IN PROGRESS  
        3. PR review comment → IN PROGRESS
        4. Push to PR branch → PULL REQUEST
        
        Returns: (has_backward_trigger, backward_status, reasons)
        """
        if not pr_info.get('pr_state') == 'open':
            return False, None, []
            
        backward_reasons = []
        events = issue_data.get('events', [])
        
        # Check for backward flow triggers on open PR
        for event in events:
            event_type = event.get('type', '')
            payload = event.get('payload', {})
            
            # 1. Comment on open PR → IN PROGRESS
            if event_type == 'IssueCommentEvent':
                issue = payload.get('issue', {})
                if issue.get('pull_request'):  # This is a PR comment
                    backward_reasons.append("Comment on open PR")
                    return True, 'IN PROGRESS', backward_reasons
            
            # 2. @mention on open PR → IN PROGRESS
            if event_type in ['IssueCommentEvent', 'PullRequestReviewCommentEvent']:
                comment_body = payload.get('comment', {}).get('body', '')
                if f'@{self.github_user}' in comment_body:
                    # Check if this comment is on the open PR
                    if event_type == 'IssueCommentEvent':
                        issue = payload.get('issue', {})
                        if issue.get('pull_request'):
                            backward_reasons.append("@mention on open PR")
                            return True, 'IN PROGRESS', backward_reasons
                    else:  # PullRequestReviewCommentEvent
                        backward_reasons.append("@mention in PR review")
                        return True, 'IN PROGRESS', backward_reasons
            
            # 3. PR review comment → IN PROGRESS
            if event_type == 'PullRequestReviewCommentEvent':
                backward_reasons.append("PR review comment received")
                return True, 'IN PROGRESS', backward_reasons
            
            # 4. Push to PR branch → PULL REQUEST (check if push is to PR branch)
            if event_type == 'PushEvent':
                push_ref = payload.get('ref', '')
                pr_branch = pr_info.get('pr_branch', '')
                if pr_branch and push_ref.endswith(pr_branch):
                    backward_reasons.append("Push to PR branch")
                    return True, 'PULL REQUEST', backward_reasons
        
        return False, None, []
    
    def _is_event_on_open_pr(self, event: Dict, pr_info: Dict) -> bool:
        """
        Check if an event is happening on the open PR itself
        This helps distinguish PR activity from general issue activity
        """
        if not pr_info.get('pr_state') == 'open':
            return False
            
        event_type = event.get('type', '')
        payload = event.get('payload', {})
        
        # For IssueCommentEvent, check if it's actually on a PR
        if event_type == 'IssueCommentEvent':
            issue = payload.get('issue', {})
            if issue.get('pull_request'):
                # Check if this is the same PR number
                issue_number = issue.get('number')
                return issue_number == pr_info.get('pr_number')
        
        # PullRequestReviewCommentEvent is always on a PR
        if event_type == 'PullRequestReviewCommentEvent':
            pr = payload.get('pull_request', {})
            pr_number = pr.get('number')
            return pr_number == pr_info.get('pr_number')
        
        # For PushEvent, check if it's to the PR branch
        if event_type == 'PushEvent':
            push_ref = payload.get('ref', '')
            pr_branch = pr_info.get('pr_branch', '')
            if pr_branch and push_ref.endswith(pr_branch):
                return True
        
        return False
    
    def _determine_final_status(self, issue_data: Dict, pr_info: Dict) -> Tuple[str, List[str]]:
        """
        Determine final status using STATUS_FLOW_PROPOSAL.md priority logic:
        BACKWARD FLOW (highest priority after MERGED):
        - Comment on open PR → IN PROGRESS
        - @mention on open PR → IN PROGRESS  
        - PR review comment → IN PROGRESS
        - Push to PR branch → PULL REQUEST
        
        FORWARD FLOW:
        1. MERGED (highest priority) → DONE
        2. RELEASED → RELEASED  
        3. OPEN PR + ACTIVITY → IN PROGRESS
        4. OPEN PR → PULL REQUEST
        5. CLOSED PR (not merged) → BUILD BROKEN
        6. COMMITS ON BRANCH → IN PROGRESS
        7. BRANCH CREATED → TODO
        8. COMMENT ONLY → DISCUSSION
        """
        reasons = []
        
        # 1. MERGED (highest priority) → DONE
        if pr_info.get('pr_merged'):
            reasons.append("PR merged")
            return 'DONE', reasons
        
        # 2. BACKWARD FLOW DETECTION (second highest priority)
        has_backward, backward_status, backward_reasons = self._detect_backward_flow_triggers(issue_data, pr_info)
        if has_backward:
            return backward_status, backward_reasons
        
        # 3. RELEASED → RELEASED (would need release detection - placeholder for now)
        # TODO: Implement release detection logic
        
        # 3. OPEN PR + ACTIVITY → IN PROGRESS
        if pr_info.get('pr_state') == 'open' and len(issue_data['events']) > 1:
            recent_activity = any(
                event.get('type') in ['IssueCommentEvent', 'PullRequestReviewCommentEvent', 'PushEvent']
                for event in issue_data['events']
            )
            if recent_activity:
                reasons.append("Open PR with recent activity")
                return 'IN PROGRESS', reasons
        
        # 4. OPEN PR → PULL REQUEST
        if pr_info.get('pr_state') == 'open':
            reasons.append("Open PR exists")
            return 'PULL REQUEST', reasons
        
        # 5. CLOSED PR (not merged) → BUILD BROKEN
        if pr_info.get('pr_state') == 'closed' and not pr_info.get('pr_merged'):
            reasons.append("PR closed without merge")
            return 'BUILD BROKEN', reasons
        if pr_info.get('pr_state') == 'open' and len(issue_data['events']) > 1:
            recent_activity = any(
                event.get('type') in ['IssueCommentEvent', 'PullRequestReviewCommentEvent', 'PushEvent']
                for event in issue_data['events']
            )
            if recent_activity:
                reasons.append("Open PR with recent activity")
                return 'IN PROGRESS', reasons
        
        # 5. OPEN PR → PULL REQUEST
        if pr_info.get('pr_state') == 'open':
            reasons.append("Open PR exists")
            return 'PULL REQUEST', reasons
        
        # 5. COMMITS ON BRANCH → IN PROGRESS
        has_push_events = any(event.get('type') == 'PushEvent' for event in issue_data['events'])
        if has_push_events:
            reasons.append("Push events detected")
            return 'IN PROGRESS', reasons
        
        # 6. BRANCH CREATED → TODO
        has_branch_creation = any(
            event.get('type') == 'CreateEvent' and event.get('payload', {}).get('ref_type') == 'branch'
            for event in issue_data['events']
        )
        if has_branch_creation:
            reasons.append("Branch created")
            return 'TODO', reasons
        
        # 7. COMMENT ONLY → DISCUSSION (default)
        reasons.append("Comment activity only")
        return 'DISCUSSION', reasons
    
    def create_jira_objects_from_grouped_data(self, grouped_data: Dict, dry_run: bool = False) -> Dict:
        """
        Create JIRA objects from the grouped and analyzed GitHub data
        This function creates Epics for repo owners and Tasks for issues
        """
        print("\n🎯 === CREATING JIRA OBJECTS FROM GROUPED DATA ===")
        
        stats = {
            'epics_created': 0,
            'epics_found': 0,
            'tasks_created': 0,
            'tasks_updated': 0,
            'tasks_existing': 0,
            'errors': 0
        }
        
        # Check if project supports Epics
        supports_epics = self.project_supports_epic()
        epic_link_field = self.get_epic_link_field_id() if supports_epics else None
        
        print(f"📊 JIRA Project supports Epics: {supports_epics}")
        if supports_epics:
            print(f"📊 Epic Link field ID: {epic_link_field}")
        
        created_epics = {}  # Cache for created/found epics
        
        for repo_key, issues in grouped_data.items():
            repo_owner, repo_name = repo_key.split('/', 1)
            
            # Filter: Only process forked and external repos (skip own repos and connected orgs)
            if self.should_skip_repo(repo_owner):
                print(f"⏭️  Skipping {repo_key} (own repo or connected org)")
                continue
                
            print(f"\n📦 Processing repository: {repo_key} (external/forked repo)")
            
            # 1. CREATE OR FIND EPIC FOR REPO OWNER (if supported)
            epic_key = None
            if supports_epics:
                epic_key = self._get_or_create_epic_for_owner(repo_owner, created_epics, dry_run)
                if epic_key:
                    if epic_key in created_epics:
                        stats['epics_found'] += 1
                    else:
                        stats['epics_created'] += 1
                        created_epics[epic_key] = repo_owner
            
            # 2. CREATE TASKS FOR EACH ISSUE
            for issue_num, issue_data in issues.items():
                print(f"  🎫 Processing issue #{issue_num}...")
                
                try:
                    result = self._create_jira_task_from_grouped_data(
                        repo_owner, repo_name, issue_num, issue_data, epic_key, dry_run
                    )
                    
                    if result == 'created':
                        stats['tasks_created'] += 1
                    elif result == 'updated':
                        stats['tasks_updated'] += 1
                    elif result == 'existing':
                        stats['tasks_existing'] += 1
                    
                except Exception as e:
                    print(f"    ❌ Error creating task for issue #{issue_num}: {e}")
                    stats['errors'] += 1
        
        print(f"\n📊 === JIRA OBJECT CREATION SUMMARY ===")
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        return stats
    
    def _get_or_create_epic_for_owner(self, repo_owner: str, created_epics: Dict, dry_run: bool = False) -> Optional[str]:
        """Get or create an Epic for the repository owner"""
        # Check if we already have this Epic
        for epic_key, owner in created_epics.items():
            if owner == repo_owner:
                return epic_key
        
        # Search for existing Epic
        try:
            headers = self.get_jira_headers()
            # Escape quotes in repo_owner for JQL search
            escaped_owner = repo_owner.replace('\\', '\\\\').replace('"', '\\"')
            jql = f'project = "{self.jira_project}" AND issuetype = Epic AND summary ~ "{escaped_owner}"'
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 1}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                issues = response.json().get('issues', [])
                if issues:
                    epic_key = issues[0]['key']
                    print(f"    📋 Found existing Epic: {epic_key} for {repo_owner}")
                    created_epics[epic_key] = repo_owner
                    return epic_key
            
            # Create new Epic
            if dry_run:
                print(f"    🧪 DRY RUN: Would create Epic for {repo_owner}")
                epic_key = f"{repo_owner}-DRYRUN"
                created_epics[epic_key] = repo_owner
                return epic_key
            
            epic_summary = f"{repo_owner}"
            epic_description = f"""Epic for tracking GitHub contributions to repositories owned by {repo_owner}.

This Epic automatically groups all GitHub issues, PRs, and contributions 
related to {repo_owner}'s repositories.

Auto-created by GitHub-JIRA Monitor
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            epic_payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": epic_summary,
                    "description": epic_description,
                    "issuetype": {"name": "Epic"},
                    "labels": [repo_owner, "github-contributions"]
                }
            }
            
            # Only add Epic fields if they are available on the create screen
            # Skip Epic Name and Epic Key fields for now to avoid 400 errors
            print(f"    📝 Creating Epic with basic fields only (avoiding custom field errors)")
            
            url = f"https://{self.jira_domain}/rest/api/2/issue"
            response = requests.post(url, headers=headers, json=epic_payload, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                epic_key = result.get('key')
                print(f"    ✅ Created Epic: {epic_key} for {repo_owner}")
                created_epics[epic_key] = repo_owner
                
                # Verify Epic was created properly
                self._verify_epic_creation(epic_key, repo_owner)
                
                return epic_key
            else:
                print(f"    ❌ Failed to create Epic for {repo_owner}: {response.status_code}")
                print(f"    📝 Response: {response.text[:300]}")
                return None
                
        except Exception as e:
            print(f"    ❌ Error creating Epic for {repo_owner}: {e}")
            return None
    
    def _verify_epic_creation(self, epic_key: str, repo_owner: str) -> bool:
        """Verify that an Epic was created successfully and has proper fields"""
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{epic_key}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                epic_data = response.json()
                fields = epic_data.get('fields', {})
                
                issue_type = fields.get('issuetype', {}).get('name', '')
                summary = fields.get('summary', '')
                
                if issue_type.lower() == 'epic':
                    print(f"    ✅ Epic {epic_key} verified as Epic type")
                    print(f"    📝 Epic Summary: {summary}")
                    
                    # Check Epic fields
                    epic_name = fields.get('customfield_10011')
                    epic_key_field = fields.get('customfield_10013')
                    
                    if epic_name:
                        print(f"    📝 Epic Name field: {epic_name}")
                    if epic_key_field:
                        print(f"    🔑 Epic Key field: {epic_key_field}")
                    
                    return True
                else:
                    print(f"    ⚠️  Created issue {epic_key} is not an Epic (type: {issue_type})")
                    return False
            else:
                print(f"    ❌ Could not verify Epic {epic_key}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error verifying Epic {epic_key}: {e}")
            return False
    
    def _create_jira_task_from_grouped_data(self, repo_owner: str, repo_name: str, issue_num: int, 
                                          issue_data: Dict, epic_key: Optional[str], dry_run: bool = False) -> str:
        """Create a JIRA task from grouped issue data"""
        issue_details = issue_data.get('issue_details', {})
        pr_info = issue_data.get('pr_info', {})
        final_status = issue_data.get('final_status', 'DISCUSSION')
        status_reasons = issue_data.get('status_reasons', [])
        
        # Extract issue information
        issue_title = issue_details.get('title', f'Issue #{issue_num}')
        issue_body = issue_details.get('body', 'No description available')
        issue_url = issue_details.get('html_url', f'https://github.com/{repo_owner}/{repo_name}/issues/{issue_num}')
        issue_author = issue_details.get('user', {}).get('login', 'unknown')
        created_at = issue_details.get('created_at', '')
        
        # Check for existing task
        existing_key = self.search_existing_jira_task(issue_url, issue_num, repo_name, repo_owner)
        if existing_key:
            print(f"    🔄 Task already exists: {existing_key}")
            
            # Update existing task status to ensure it's correct
            status_mapping = {
                'DISCUSSION': 'Discussion',   # Comment activity only = Discussion status
                'DONE': 'Done',              # Merged PRs = Done (completed work)
                'BUILD BROKEN': 'Build BRoken'      # Closed non-merged PRs = Build BRoken (failed builds)
            }
            jira_status = status_mapping.get(final_status, 'Discussion')
            
            print(f"    🔄 Updating existing task status: {final_status} → {jira_status}")
            status_updated = self.update_jira_status(existing_key, jira_status, dry_run=False)
            if status_updated:
                print(f"    ✅ Updated task status: {existing_key} → {jira_status}")
                return 'updated'
            else:
                print(f"    ⚠️  Failed to update task status: {existing_key}")
                return 'existing'
        
        # Determine task type and description prefix
        if pr_info.get('is_pr_itself'):
            if pr_info.get('pr_merged'):
                task_type = "✅ MERGED Pull Request"
            elif pr_info.get('pr_state') == 'open':
                task_type = "🔄 OPEN Pull Request"
            else:
                task_type = "💥 BUILD BROKEN Pull Request"
        else:
            task_type = f"📋 GitHub Issue - {final_status}"
        
        # Create task summary
        task_summary = f"#{issue_num} - {issue_title}"
        
        # Get the first comment (original description) and subsequent comments
        comments_data = self._get_issue_comments_for_task(repo_owner, repo_name, issue_num)
        first_comment = comments_data.get('first_comment', issue_body or 'No description available')
        subsequent_comments = comments_data.get('subsequent_comments', [])
        
        # Create activity log from events
        activity_log = self._create_activity_log_from_events(issue_data.get('events', []))
        
        # Create detailed description with first comment as main description
        task_description = f"""{task_type}

*Repository:* {repo_owner}/{repo_name}
*Issue/PR:* #{issue_num} - {issue_title}
*Author:* @{issue_author}
*Created:* {created_at}
*URL:* {issue_url}
*Status:* {final_status}

----

*Original Issue Description:*

{first_comment}

----

*Status Analysis:*
• Final Status: {final_status}
• Reasons: {', '.join(status_reasons)}
• Has PR: {pr_info.get('has_pr', False)}
• PR Merged: {pr_info.get('pr_merged', False)}

{activity_log}

----
_Auto-synced from GitHub on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"""

        if dry_run:
            print(f"    🧪 DRY RUN: Would create task")
            print(f"      Summary: {task_summary}")
            print(f"      Status: {final_status}")
            print(f"      Epic: {epic_key or '[none]'}")
            print(f"      Comments to add: {len(subsequent_comments)}")
            return 'created'
        
        # Create JIRA task
        try:
            headers = self.get_jira_headers()
            
            payload = {
                "fields": {
                    "project": {"key": self.jira_project},
                    "summary": task_summary,
                    "description": task_description,
                    "issuetype": {"name": "Task"},
                    "labels": [repo_name, repo_owner, final_status.lower().replace(' ', '-')]
                }
            }
            
            # Add Epic link if available - Enhanced Epic attachment
            epic_to_attach = None
            if epic_key and self.project_supports_epic():
                print(f"    🔗 Will attach task to Epic: {epic_key} after creation")
                epic_to_attach = epic_key
                # Don't add Epic field during creation as it's not on the create screen
            else:
                if not epic_key:
                    print(f"    ℹ️  No Epic key available for linking")
                if not self.project_supports_epic():
                    print(f"    ℹ️  Project does not support Epics")
            
            url = f"https://{self.jira_domain}/rest/api/2/issue"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                task_key = result.get('key')
                
                # Add subsequent comments to JIRA task
                if subsequent_comments:
                    self._add_comments_to_jira_task(task_key, subsequent_comments)
                
                # Log activity transitions in JIRA comments
                self._log_activity_transitions_to_jira(task_key, issue_data.get('events', []), final_status)
                
                # Attach Epic after task creation if needed
                if epic_to_attach and self.project_supports_epic():
                    print(f"    🔗 Attaching task to Epic: {epic_to_attach}")
                    epic_attached = self._attach_epic_post_creation(task_key, epic_to_attach, repo_owner)
                    epic_status = "✅ Epic attached" if epic_attached else "⚠️  Epic attachment failed"
                else:
                    epic_status = "No Epic"
                
                # Map internal status to JIRA status names
                status_mapping = {
                    'DISCUSSION': 'Discussion',   # Comment activity only = Discussion status
                    'DONE': 'Done',              # Merged PRs = Done (completed work)
                    'BUILD BROKEN': 'Build BRoken'      # Closed non-merged PRs = Build BRoken (failed builds)
                }
                jira_status = status_mapping.get(final_status, 'Discussion')
                
                # Transition task to correct status
                print(f"    🔄 Transitioning task to status: {final_status} → {jira_status}")
                status_updated = self.update_jira_status(task_key, jira_status, dry_run=False)
                status_result = "✅ Status updated" if status_updated else "⚠️  Status transition failed"
                
                print(f"    ✅ Created task: {task_key} (Status: {final_status}, Epic: {epic_to_attach or '[none]'}, {epic_status}, {status_result})")
                
                return 'created'
            else:
                print(f"    ❌ Failed to create task: {response.status_code} {response.text[:200]}")
                return 'error'
                
        except Exception as e:
            print(f"    ❌ Error creating task: {e}")
            return 'error'
    
    def _verify_epic_attachment(self, task_key: str, expected_epic_key: str) -> bool:
        """Verify that a task is properly attached to an Epic"""
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                task_data = response.json()
                fields = task_data.get('fields', {})
                
                # Check different Epic link field possibilities
                epic_link_field = self.get_epic_link_field_id()
                
                # Method 1: Check standard Epic Link field
                epic_link = fields.get(epic_link_field)
                if epic_link == expected_epic_key:
                    print(f"    ✅ Epic attachment verified via {epic_link_field}")
                    return True
                
                # Method 2: Check alternative Epic fields
                for alt_field in ['customfield_10014', 'customfield_10011', 'customfield_10010']:
                    alt_epic = fields.get(alt_field)
                    if alt_epic == expected_epic_key:
                        print(f"    ✅ Epic attachment verified via {alt_field}")
                        return True
                
                # Method 3: Check Epic Name field
                epic_name_field = fields.get('customfield_10011')
                expected_epic_name = f"GitHub Contributions - {expected_epic_key.split('-')[0] if '-' in expected_epic_key else 'unknown'}"
                if epic_name_field == expected_epic_name:
                    print(f"    ✅ Epic attachment verified via Epic Name field")
                    return True
                
                print(f"    ⚠️  Epic attachment not found in any field")
                return False
            else:
                print(f"    ❌ Could not verify Epic attachment: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error verifying Epic attachment: {e}")
            return False
    
    def _get_issue_comments_for_task(self, repo_owner, repo_name, issue_num):
        """Extract comments from GitHub issue/PR data for JIRA task creation"""
        # (Removed duplicate/unfinished try block that caused SyntaxError)
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
                # The first comment is the issue body
                first_comment = {
                    'body': issue_data.get('body', ''),
                    'user': issue_data.get('user', {}),
                    'created_at': issue_data.get('created_at', ''),
                    'id': 0,
                    '__type': 'issue_body'
                }
            else:
                first_comment = {'body': '', 'user': {}, 'created_at': '', 'id': 0, '__type': 'issue_body'}

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
                c_body = c.get('body', '') or ''
                c_user = c.get('user', {}) or {}
                c_login = c_user.get('login', '') or ''
                fc_body = first_comment.get('body', '') or ''
                fc_user = first_comment.get('user', {}) or {}
                fc_login = fc_user.get('login', '') or ''
                # Avoid duplicating the issue body as a comment
                if (c_body.strip() == fc_body.strip()) and (c_login == fc_login):
                    continue
                all_comments.append({
                    'body': c_body,
                    'user': c_user,
                    'created_at': c.get('created_at', '') or '',
                    'id': c.get('id', 0),
                    '__type': 'issue_comment'
                })
            # Add PR review comments
            for c in pr_review_comments:
                c_body = c.get('body', '') or ''
                c_user = c.get('user', {}) or {}
                all_comments.append({
                    'body': c_body,
                    'user': c_user,
                    'created_at': c.get('created_at', '') or '',
                    'id': c.get('id', 0),
                    '__type': 'pr_review_comment'
                })

            # Sort all comments by created_at (chronological order)
            all_comments_sorted = sorted(all_comments, key=lambda x: x.get('created_at', ''))

            # All comments (issue/PR review) go to subsequent_comments
            subsequent_comments = all_comments_sorted

        except Exception as e:
            print(f"      ⚠️  Could not fetch comments from GitHub API: {e}")
            first_comment = {'body': '', 'user': {}, 'created_at': '', 'id': 0, '__type': 'issue_body'}
            subsequent_comments = []

        return {
            'first_comment': first_comment.get('body', '') if first_comment else None,
            'subsequent_comments': subsequent_comments
        }
        activity_lines = []
        
        # Process events chronologically
        sorted_events = sorted(events, key=lambda x: x.get('created_at', ''))
        
        for event in sorted_events:
            event_type = event.get('type')
            created_at = event.get('created_at', '')
            
            if event_type == 'IssuesEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_lines.append(f"• Issue opened ({created_at})")
                elif action == 'closed':
                    activity_lines.append(f"• Issue closed ({created_at})")
                elif action == 'reopened':
                    activity_lines.append(f"• Issue reopened ({created_at})")
                    
            elif event_type == 'PullRequestEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_lines.append(f"• Pull request opened ({created_at})")
                elif action == 'closed':
                    merged = event.get('payload', {}).get('pull_request', {}).get('merged', False)
                    if merged:
                        activity_lines.append(f"• Pull request merged ({created_at})")
                    else:
                        activity_lines.append(f"• Pull request closed without merge ({created_at})")
                elif action == 'reopened':
                    activity_lines.append(f"• Pull request reopened ({created_at})")
                    
            elif event_type == 'PushEvent':
                ref = event.get('payload', {}).get('ref', '')
                commits = len(event.get('payload', {}).get('commits', []))
                if 'main' in ref or 'master' in ref:
                    activity_lines.append(f"• {commits} commits pushed to main branch ({created_at})")
                    
            elif event_type == 'IssueCommentEvent':
                action = event.get('payload', {}).get('action')
                if action == 'created':
                    activity_lines.append(f"• Comment added ({created_at})")
        
        if activity_lines:
            return f"*GitHub Activity Timeline:*\n\n" + "\n".join(activity_lines[-10:])  # Last 10 activities
        
        return ""

    def _add_comments_to_jira_task(self, task_key, comments):
        """Add GitHub comments to JIRA task as comments"""
        for comment in comments:
            # Support both old and new comment dicts
            author = comment.get('author')
            if not author:
                # Try GitHub API v3/4 style
                user = comment.get('user', {})
                author = user.get('login', 'Unknown')
            created_at = comment.get('created_at', '')
            body = comment.get('body', '')
            comment_body = f"*GitHub Comment by {author} at {created_at}:*\n\n{body}"
            jira_comment_data = {"body": comment_body}
            comment_url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}/comment"
            headers = self.get_jira_headers()
            response = requests.post(
                comment_url,
                headers=headers,
                json=jira_comment_data
            )
            if response.status_code in [200, 201]:
                print(f"      ✅ Added comment from {author} ({created_at})")
            else:
                print(f"      ❌ Failed to add comment: {response.status_code} - {response.text}")

    def _log_activity_transitions_to_jira(self, task_key, events, final_status):
        """Log status transitions as JIRA comments based on GitHub events"""
        if not events:
            return
            
        activity_log = []
        
        # Track important events that indicate status changes
        for event in events:
            event_type = event.get('type')
            created_at = event.get('created_at', '')
            
            if event_type == 'IssuesEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_log.append(f"• Issue opened → Status: TO DO ({created_at})")
                elif action == 'closed':
                    activity_log.append(f"• Issue closed → Status: DONE ({created_at})")
                elif action == 'reopened':
                    activity_log.append(f"• Issue reopened → Status: TO DO ({created_at})")
                    
            elif event_type == 'PullRequestEvent':
                action = event.get('payload', {}).get('action')
                if action == 'opened':
                    activity_log.append(f"• Pull request opened → Status: IN PROGRESS ({created_at})")
                elif action == 'closed':
                    merged = event.get('payload', {}).get('pull_request', {}).get('merged', False)
                    if merged:
                        activity_log.append(f"• Pull request merged → Status: DONE ({created_at})")
                    else:
                        activity_log.append(f"• Pull request closed (not merged) → Status: PULL REQUEST ({created_at})")
                elif action == 'reopened':
                    activity_log.append(f"• Pull request reopened → Status: IN PROGRESS ({created_at})")
                    
            elif event_type == 'PushEvent':
                ref = event.get('payload', {}).get('ref', '')
                if 'main' in ref or 'master' in ref:
                    activity_log.append(f"• Code pushed to main branch → Status: IN PROGRESS ({created_at})")
        
        if activity_log:
            activity_body = f"*Activity Log - Status Transitions:*\n\n" + "\n".join(activity_log) + f"\n\n*Final Status: {final_status}*"
            jira_comment_data = {"body": activity_body}
            comment_url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}/comment"
            headers = self.get_jira_headers()
            response = requests.post(
                comment_url,
                headers=headers,
                json=jira_comment_data
            )
            if response.status_code in [200, 201]:
                print(f"      ✅ Added activity log with {len(activity_log)} transitions")
            else:
                print(f"      ❌ Failed to add activity log: {response.status_code} - {response.text}")
    
    def run_core_workflow(self, max_pages: int = 10, since_minutes: int = None, dry_run: bool = False) -> Dict:
        """
        CORE WORKFLOW: Implements your requested process:
        1. Get all data from GitHub and group by owner/repo/issue
        2. Analyze status for each grouped item
        3. Create JIRA objects (Epics + Tasks) 
        4. Then handle comments (separate step)
        """
        print("🚀 === STARTING CORE WORKFLOW ===")
        print(f"Max Pages: {max_pages}")
        print(f"Since Minutes: {since_minutes or 'All time'}")
        print(f"Dry Run: {dry_run}")
        print(f"Timestamp: {datetime.now()}")
        
        workflow_stats = {
            'start_time': datetime.now(),
            'data_gathering': {},
            'jira_creation': {},
            'total_time': None
        }
        
        try:
            # STEP 1: GATHER AND GROUP ALL GITHUB DATA
            print("\n" + "="*60)
            print("STEP 1: GATHER AND GROUP GITHUB DATA")
            print("="*60)
            
            data_result = self.gather_and_group_github_data(max_pages=max_pages, since_minutes=since_minutes)
            grouped_data = data_result['grouped_data']
            workflow_stats['data_gathering'] = data_result['summary']
            
            if not grouped_data:
                print("⚠️  No data found to process")
                return workflow_stats
            
            # STEP 2: CREATE JIRA OBJECTS FROM GROUPED DATA
            print("\n" + "="*60)
            print("STEP 2: CREATE JIRA OBJECTS")
            print("="*60)
            
            jira_stats = self.create_jira_objects_from_grouped_data(grouped_data, dry_run=dry_run)
            workflow_stats['jira_creation'] = jira_stats
            
            # STEP 3: SUMMARY
            workflow_stats['end_time'] = datetime.now()
            workflow_stats['total_time'] = (workflow_stats['end_time'] - workflow_stats['start_time']).total_seconds()
            
            print("\n" + "="*60)
            print("CORE WORKFLOW COMPLETED")
            print("="*60)
            print(f"⏱️  Total Time: {workflow_stats['total_time']:.2f} seconds")
            print(f"📊 Repositories Processed: {workflow_stats['data_gathering']['total_repos']}")
            print(f"🎫 Issues Analyzed: {workflow_stats['data_gathering']['total_issues']}")
            print(f"📋 Epics Created: {workflow_stats['jira_creation']['epics_created']}")
            print(f"🎯 Tasks Created: {workflow_stats['jira_creation']['tasks_created']}")
            print(f"🔄 Tasks Updated: {workflow_stats['jira_creation']['tasks_updated']}")
            print(f"❌ Errors: {workflow_stats['jira_creation']['errors']}")
            
            print(f"\n📈 Status Distribution:")
            for status, count in workflow_stats['data_gathering']['status_counts'].items():
                print(f"  {status}: {count}")
            
            return workflow_stats
            
        except Exception as e:
            print(f"❌ CORE WORKFLOW ERROR: {e}")
            workflow_stats['error'] = str(e)
            return workflow_stats
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
        # Always use only the repo name as the label
        repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
        base_labels = [repo_name_only]

        # 1. Highest priority: MERGED → DONE
        if pr_status.get('merged', False) or pr_status.get('status') == 'merged':
            return "Done", base_labels

        # 2. RELEASED → RELEASED
        if pr_status.get('status') == 'released' or (pr_status.get('merged') and self.check_release_status(f"{repo_owner}/{repo_name}", pr_status.get('pr_number'))):
            return "Released", base_labels

        # 3. OPEN PR + ACTIVITY → IN PROGRESS (Backward Flow)
        if event_context:
            is_push_event = event_context.get('is_push_event', False)
            is_comment_on_open_pr = event_context.get('is_comment_on_open_pr', False)
            is_mention_on_open_pr = event_context.get('is_mention_on_open_pr', False)
            if (is_push_event and pr_status.get('is_pr')) or is_comment_on_open_pr or is_mention_on_open_pr:
                return "In Progress", base_labels

        # 4. OPEN PR → PULL REQUEST
        if (pr_status.get('is_pr') or pr_status.get('has_linked_pr')):
            return "Pull Request", base_labels

        # 5. COMMITS ON BRANCH → IN PROGRESS (from PushEvent processing)
        if event_context:
            is_push_event = event_context.get('is_push_event', False)
            is_first_commit = event_context.get('is_first_commit', False)
            is_branch_work = event_context.get('is_branch_with_issue_number', False)
            if is_push_event and (is_first_commit or is_branch_work):
                return "In Progress", base_labels

        # 6. BRANCH CREATED → TODO
        if event_context and event_context.get('is_branch_created_with_issue', False):
            return "Todo", base_labels

        # 7. COMMENT ONLY → DISCUSSION (default case)
        return "Discussion", base_labels
    
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
                    
                    # Only use the first label as the repo name
                    if labels:
                        repo_name = labels[0]
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
        """
        Search for existing JIRA task with this GitHub issue URL in the description or summary (deduplication by URL or summary pattern).
        Returns the JIRA key if found, else None.
        """
        try:
            headers = self.get_jira_headers()
            # Escape special characters in the issue URL for JQL search
            escaped_url = issue_url.replace('\\', '\\\\').replace('"', '\\"')
            summary_pattern = f"#{issue_number}"
            repo_name_pattern = repo_name or ''
            repo_owner_pattern = repo_owner or ''
            # JQL: match URL in description or issue number/repo/owner in summary, but only for Tasks (not Epics)
            jql = (
                f'project = "{self.jira_project}" AND issuetype = "Task" AND '
                f'(description ~ "{escaped_url}" OR summary ~ "{summary_pattern}" OR summary ~ "{repo_name_pattern}" OR summary ~ "{repo_owner_pattern}")'
            )
            print(f"🔍 Searching for existing task with GitHub issue URL, summary, repo, or owner: {issue_url}, {summary_pattern}, {repo_name_pattern}, {repo_owner_pattern}")
            print(f"🔍 Escaped JQL query: {jql}")
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 5}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                print(f"📊 Found {result.get('total', 0)} potential matches by URL, summary, repo, or owner")
                if result.get('total', 0) > 0:
                    for issue in result.get('issues', []):
                        desc = issue.get('fields', {}).get('description', '') or ''
                        summ = issue.get('fields', {}).get('summary', '') or ''
                        if (
                            (issue_url.lower() in desc.lower()) or
                            (summary_pattern in summ) or
                            (repo_name_pattern and repo_name_pattern.lower() in summ.lower()) or
                            (repo_owner_pattern and repo_owner_pattern.lower() in summ.lower())
                        ):
                            print(f"✅ Found existing JIRA task: {issue['key']} for URL, summary, repo, or owner pattern")
                            return issue['key']
                    print(f"📝 No exact URL, summary, repo, or owner match found")
                else:
                    print(f"📝 No tasks found with URL, summary, repo, or owner pattern")
            else:
                print(f"⚠️  JIRA search failed: {response.status_code} - {response.text[:200]}")
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
                # (Epic creation logic would go here if needed)
                return None
            except Exception as e:
                print(f"[JIRA] Error in get_or_create_epic_key: {e}")
                return None

        epic_key = get_or_create_epic_key(event_data.get('repo_owner', 'unknown'))

        # Get full issue details
        issue_url = event_data.get('issue_url')
        issue_number = event_data.get('issue_number')
        issue_title = event_data.get('issue_title')
        repo_owner = event_data.get('repo_owner', 'unknown')
        repo_name = event_data.get('repo_name', '')
        repo_name_only = repo_name.split('/')[-1] if '/' in repo_name else repo_name
        comment_body = event_data.get('comment_body', '')

        issue_details = self.get_issue_details(issue_url)
        issue_body = issue_details.get('body', 'No description available')
        issue_author = issue_details.get('user', {}).get('login', 'unknown')
        issue_created_at = issue_details.get('created_at', '')

        # Format JIRA description with plain text and simple lists for better JIRA rendering
        description_lines = [
            'GITHUB ISSUE INFO',
            '-----------------',
            f"- Repo: {repo_owner}/{repo_name_only}",
            f"- Issue Number: #{issue_number}",
            f"- Title: {issue_title}",
            f"- Author: @{issue_author}",
            f"- Created At: {issue_created_at}",
            f"- URL: {issue_url}",
            '',
            'INITIAL ISSUE DESCRIPTION',
            '-------------------------',
            (issue_body or 'No description available'),
            '',
            '-------------------------',
            'This issue is auto-synced from GitHub.'
        ]
        jira_description = '\n'.join(description_lines)

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
            # Attach Epic link if found and project supports Epics
            epic_field_id = getattr(self, 'epic_link_field_id', None)
            if epic_key and epic_field_id:
                payload["fields"][epic_field_id] = epic_key
            url = f"https://{self.jira_domain}/rest/api/2/issue"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code in [200, 201]:
                print(f"✅ Created JIRA task: {response.json().get('key', 'Unknown')} (Status: {kanban_status})")
                return True
            else:
                print(f"❌ Failed to create JIRA task: {response.status_code} {response.text}")
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
        """
        Update existing JIRA task with a new comment, ensuring uniqueness and highlighting commenter info.
        Only add the comment if it is not already present in the description.
        """
        try:
            if dry_run:
                print(f"🧪 DRY RUN: Would update JIRA task {task_key} with comment:")
                print(new_comment)
                return True

            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ Could not fetch task {task_key}: {response.status_code}")
                return False

            current_data = response.json()
            current_desc = current_data.get('fields', {}).get('description', '')

            # Only add the comment if it is not already present (unique by content)
            if new_comment.strip() in current_desc:
                print(f"⚠️  Comment already exists in JIRA task {task_key}, skipping duplicate.")
                return True

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            new_desc = f"{current_desc}\n\n--- New Comment ({now_str}) ---\n{new_comment}"

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
        """
        Process a single comment event, ensuring unique comment addition and highlighting commenter info.
        """
        try:
            payload = event.get('payload', {})
            repo = event.get('repo', {})
            event_type = event.get('type', '')

            repo_name_raw = repo.get('name', 'unknown')
            repo_name_only = repo_name_raw.split('/')[-1] if '/' in repo_name_raw else repo_name_raw
            repo_url = repo.get('url', '')
            repo_owner = 'unknown'
            repo_full_name = 'unknown/unknown'

            # Try to extract owner from repo URL
            if repo_url and '/repos/' in repo_url:
                try:
                    repo_owner = repo_url.split('/repos/')[1].split('/')[0]
                    repo_full_name = '/'.join(repo_url.split('/repos/')[1].split('/')[:2])
                except Exception:
                    pass

            # Fallback: extract from issue URL
            issue = payload.get('issue', {})
            issue_url = issue.get('html_url', '')
            if repo_owner == 'unknown' and issue_url and 'github.com/' in issue_url:
                try:
                    repo_owner = issue_url.split('github.com/')[1].split('/')[0]
                    repo_full_name = '/'.join(issue_url.split('github.com/')[1].split('/')[:2])
                except Exception:
                    pass

            repo_name = repo_full_name if repo_full_name != 'unknown/unknown' else repo_name_only
            comment = payload.get('comment', {})
            issue = payload.get('issue', {})
            comment_body = comment.get('body', 'No comment body')
            issue_url = issue.get('html_url', '')
            issue_title = issue.get('title', 'No title')
            issue_number = issue.get('number', 0)

            if not issue_url:
                print("⚠️  SKIPPED: No issue URL found for this event")
                return 'skipped', False

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

            if self.should_skip_repo(repo_owner):
                print(f"✅ SKIPPED: Own/org repo - {repo_name} (owner: {repo_owner})")
                return 'skipped', False

            if repo_owner == 'unknown' or repo_name == 'unknown/unknown':
                print(f"⚠️  SKIPPED: Could not determine repository owner/name")
                return 'skipped', False

            is_fork = self.check_fork_status(repo_name)
            repo_name_only = repo_name.split('/')[-1]
            pr_status = self.check_pr_status(repo_owner, repo_name_only, issue_number)

            is_comment_on_open_pr = False
            is_mention_on_open_pr = False
            if pr_status.get('is_pr') and pr_status.get('state') == 'open':
                is_comment_on_open_pr = True
                if f"@{self.github_user}" in comment_body:
                    is_mention_on_open_pr = True

            event_context = {
                'event_type': event_type,
                'is_review_comment': is_review_comment,
                'is_push_event': False,
                'is_own_issue_comment': is_own_issue_comment,
                'is_comment_on_open_pr': is_comment_on_open_pr,
                'is_mention_on_open_pr': is_mention_on_open_pr
            }

            kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name_only, event_context)

            print(f"📊 PR Status Analysis:")
            print(f"   Is Fork: {is_fork}")
            print(f"   PR Status: {pr_status}")
            print(f"   Kanban Column: {kanban_status}")
            print(f"   Labels: {labels}")

            event_data = {
                'repo_name': repo_name,
                'repo_owner': repo_owner,
                'issue_url': issue_url,
                'issue_title': issue_title,
                'issue_number': issue_number,
                'comment_body': comment_body,
                'created_at': event.get('created_at', '')
            }

            jira_key = self.search_existing_jira_task(issue_url, issue_number, repo_name.split('/')[-1], repo_owner)
            if not jira_key:
                success = self.create_jira_task(event_data, is_fork, dry_run, kanban_status, labels)
                if not success:
                    return 'error', False
                jira_key = self.search_existing_jira_task(issue_url, issue_number, repo_name.split('/')[-1], repo_owner)
                if not jira_key:
                    print(f"❌ Could not find or create JIRA task for comment event.")
                    return 'error', False

            # Format comment for JIRA, highlight commenter and time
            comment_author = comment.get('user', {}).get('login', 'unknown')
            comment_created_at = comment.get('created_at', '')
            if is_review_comment:
                pr_url = payload.get('pull_request', {}).get('html_url', '')
                comment_url = comment.get('html_url', '')
                pr_link = pr_url or issue_url
                jira_comment = (
                    f"**GitHub PR Review by @{comment_author} at {comment_created_at}**\n"
                    f"PR: {pr_link}\n"
                    f"Comment: {comment_body}\n"
                    f"[View on GitHub|{comment_url}]"
                )
            else:
                comment_url = comment.get('html_url', '')
                jira_comment = (
                    f"**GitHub Comment by @{comment_author} at {comment_created_at}**\n\n{comment_body}\n\n[View on GitHub|{comment_url}]"
                )

            if dry_run:
                print(f"🧪 DRY RUN: Would add comment to JIRA task {jira_key}:")
                print(jira_comment)
                return 'dry_run', True

            # Add the comment to the JIRA task description (unique, highlighted)
            success = self.update_jira_task(jira_key, jira_comment, dry_run=False)
            return ('contribution', True) if success else ('error', False)
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
            # Ensure repo_owner and repo_name are not duplicated (never owner/repo as repo_name)
            if '/' in repo_name:
                parts = repo_name.split('/')
                repo_owner = parts[0]
                repo_name = parts[1]
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
            description_prefix = "💥 BUILD BROKEN Pull Request"
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
                print(f"No comment events found in the specified range for {repo if repo else 'all repos'}")
                continue

            # Fetch comment events for migration (should be defined or fetched here)
            comment_events = self.filter_comment_events(self.fetch_github_events(max_pages=max_pages))
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

            # Ensure repo_name is just the repo name, not owner/repo
            if '/' in repo_name:
                repo_name = repo_name.split('/')[-1]

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
                repo_label = repo_name
                labels = [repo_label]
            else:
                # Regular issue discussion
                kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name)
                labels = [repo_name]

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
    parser.add_argument('mode', choices=['monitor', 'migrate', 'core'], 
                       help='Run mode: monitor (real-time), migrate (historical), core (new workflow)')
    parser.add_argument('--since', type=int, default=15, help='Minutes to look back for monitor/core mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no JIRA changes)')
    parser.add_argument('--max-pages', type=int, default=10, help='Max pages to fetch per repo')
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
    elif args.mode == 'core':
        # NEW CORE WORKFLOW MODE
        print("🚀 Running CORE WORKFLOW as requested")
        print("This implements: gather all GitHub data → group by owner/repo/issue → analyze status → create JIRA objects")
        
        stats = monitor.run_core_workflow(
            max_pages=args.max_pages,
            since_minutes=args.since if args.since != 15 else None,  # None = all time if default
            dry_run=args.dry_run
        )
        
        if 'error' in stats:
            print(f"\n❌ Workflow failed: {stats['error']}")
            sys.exit(1)
        else:
            print(f"\n✅ Core workflow completed successfully!")
            sys.exit(0)