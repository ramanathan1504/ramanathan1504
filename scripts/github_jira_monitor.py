#!/usr/bin/env python3
"""
GitHub to JIRA Comment Monitor
Processes GitHub comments and creates/updates JIRA tasks
"""

import os
import sys
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import base64

class GitHubJIRAMonitor:
    def __init__(self):
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.jira_auth = os.environ.get('JIRA_AUTH')
        self.github_user = 'ramanathan1504'
        self.skip_orgs = ['intemo_dev']
        self.jira_domain = 'osscontribution.atlassian.net'
        self.jira_project = 'OT'
        
        if not self.github_token or not self.jira_auth:
            print("❌ ERROR: Missing GITHUB_TOKEN or JIRA_AUTH environment variables")
            sys.exit(1)
    
    def fetch_github_events(self, since: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
        """Fetch GitHub events for the user"""
        print(f"🔍 Fetching GitHub events (max {max_pages} pages)...")
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        all_events = []
        
        for page in range(1, max_pages + 1):
            print(f"📄 Processing page {page}/{max_pages}")
            
            url = f"https://api.github.com/users/{self.github_user}/events"
            params = {'per_page': 100, 'page': page}
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 403:
                    print("⚠️  Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                elif response.status_code == 404:
                    print(f"✅ No more pages available. Processed {page-1} pages.")
                    break
                elif response.status_code != 200:
                    print(f"❌ GitHub API error: {response.status_code}")
                    continue
                
                events = response.json()
                if not events:
                    print(f"✅ No more events on page {page}")
                    break
                
                # Filter by time if since is provided
                if since:
                    filtered_events = [e for e in events if e.get('created_at', '') > since]
                    events = filtered_events
                
                all_events.extend(events)
                print(f"📊 Found {len(events)} events on page {page}")
                
                # Rate limiting
                if page < max_pages:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error fetching page {page}: {e}")
                continue
        
        print(f"✅ Total events fetched: {len(all_events)}")
        return all_events
    
    def filter_comment_events(self, events: List[Dict]) -> List[Dict]:
        """Filter for IssueCommentEvents"""
        comment_events = [e for e in events if e.get('type') == 'IssueCommentEvent']
        print(f"💬 Comment events found: {len(comment_events)}")
        return comment_events
    
    def should_skip_repo(self, repo_owner: str) -> bool:
        """Check if repo should be skipped"""
        if repo_owner == self.github_user:
            return True
        if repo_owner in self.skip_orgs:
            return True
        return False
    
    def check_fork_status(self, repo_name: str) -> bool:
        """Check if user has forked the repository"""
        try:
            # Extract repo name only (remove owner part)
            repo_name_only = repo_name.split('/')[-1]
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
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
    
    def get_issue_details(self, issue_url: str) -> Dict:
        """Fetch full issue details from GitHub"""
        try:
            # Convert HTML URL to API URL
            api_url = issue_url.replace('github.com', 'api.github.com/repos')
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Could not fetch issue details: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"⚠️  Error fetching issue details: {e}")
            return {}
    
    def search_existing_jira_task(self, issue_url: str) -> Optional[str]:
        """Search for existing JIRA task with this GitHub issue URL"""
        try:
            headers = {
                'Authorization': f'Basic {self.jira_auth}',
                'Content-Type': 'application/json'
            }
            
            # Search in summary for the issue URL
            jql = f'project = {self.jira_project} AND summary ~ "{issue_url}"'
            
            url = f"https://{self.jira_domain}/rest/api/2/search"
            params = {'jql': jql, 'maxResults': 1}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('total', 0) > 0:
                    issue_key = result['issues'][0]['key']
                    print(f"🔄 Found existing JIRA task: {issue_key}")
                    return issue_key
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error searching JIRA: {e}")
            return None
    
    def create_jira_task(self, event_data: Dict, is_fork: bool, dry_run: bool = False) -> bool:
        """Create or update JIRA task for the comment"""
        try:
            repo_name = event_data['repo_name']
            issue_url = event_data['issue_url']
            issue_number = event_data['issue_number']
            issue_title = event_data['issue_title']
            comment_body = event_data['comment_body']
            
            # Get full issue details
            issue_details = self.get_issue_details(issue_url)
            issue_body = issue_details.get('body', 'No description available')
            
            # Determine task type and labels
            if is_fork:
                task_type = "contribution"
                labels = ["github-forked", "contribution"]
                description_prefix = "Comment on Forked Repo (I have a fork):"
                print(f"🔄 Creating CONTRIBUTION task for {repo_name}")
            else:
                task_type = "discussion"
                labels = ["github-discussion", "external-repo"]
                description_prefix = "Discussion Comment on External Repo:"
                print(f"💬 Creating DISCUSSION task for {repo_name}")
            
            # Check for existing task
            existing_key = self.search_existing_jira_task(issue_url)
            
            if existing_key:
                return self.update_jira_task(existing_key, comment_body, dry_run)
            
            # Create new task
            task_summary = f"{issue_number} - {issue_title}"
            task_description = f"""{description_prefix}

Issue Description:
{issue_body}

My Comment:
{comment_body}

GitHub Issue: {issue_url}
Repo: {repo_name}
Original Date: {event_data.get('created_at', 'Unknown')}"""
            
            if dry_run:
                print(f"🧪 DRY RUN: Would create {task_type} task")
                print(f"   Summary: {task_summary}")
                print(f"   Labels: {labels}")
                return True
            
            # Create JIRA task
            headers = {
                'Authorization': f'Basic {self.jira_auth}',
                'Content-Type': 'application/json'
            }
            
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
                print(f"✅ Created JIRA task: {task_key}")
                return True
            else:
                print(f"❌ Failed to create JIRA task: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating JIRA task: {e}")
            return False
    
    def update_jira_task(self, task_key: str, new_comment: str, dry_run: bool = False) -> bool:
        """Update existing JIRA task with new comment"""
        try:
            if dry_run:
                print(f"🧪 DRY RUN: Would update task {task_key} with new comment")
                return True
            
            # Get current description
            headers = {
                'Authorization': f'Basic {self.jira_auth}',
                'Content-Type': 'application/json'
            }
            
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
            
            # Better repository name extraction
            repo_name = repo.get('name', 'unknown')
            repo_full_name = repo.get('full_name', 'unknown/unknown') 
            repo_owner = repo.get('owner', {}).get('login') or (repo_full_name.split('/')[0] if '/' in repo_full_name else 'unknown')
            
            # Use full name if available, otherwise construct it
            if repo_full_name and repo_full_name != 'unknown/unknown':
                repo_name = repo_full_name
            elif repo_name != 'unknown' and repo_owner != 'unknown':
                repo_name = f"{repo_owner}/{repo_name}"
            else:
                repo_name = repo_full_name
            
            comment = payload.get('comment', {})
            issue = payload.get('issue', {})
            
            comment_body = comment.get('body', 'No comment body')
            issue_url = issue.get('html_url', '')
            issue_title = issue.get('title', 'No title')
            issue_number = issue.get('number', 0)
            
            print(f"\n--- Processing Comment Event ---")
            print(f"Repository: {repo_name}")
            print(f"Owner: {repo_owner}")
            print(f"Issue: {issue_title}")
            print(f"URL: {issue_url}")
            print(f"Comment preview: {comment_body[:100]}...")
            
            # Check if should skip
            if self.should_skip_repo(repo_owner):
                print(f"✅ SKIPPED: Own/org repo - {repo_name}")
                return 'skipped', True
            
            # Check fork status
            is_fork = self.check_fork_status(repo_name)
            
            # Prepare event data
            event_data = {
                'repo_name': repo_name,
                'issue_url': issue_url,
                'issue_title': issue_title,
                'issue_number': issue_number,
                'comment_body': comment_body,
                'created_at': event.get('created_at', '')
            }
            
            # Create/update JIRA task
            success = self.create_jira_task(event_data, is_fork, dry_run)
            
            if success:
                return 'contribution' if is_fork else 'discussion', True
            else:
                return 'error', False
                
        except Exception as e:
            print(f"❌ Error processing event: {e}")
            return 'error', False
    
    def run_monitor(self, since_minutes: int = 15, dry_run: bool = False) -> Dict:
        """Run the monitoring workflow (recent comments only)"""
        print("=== Starting GitHub Comments Monitor ===")
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
        
        # Calculate since timestamp
        since = (datetime.now() - timedelta(minutes=since_minutes)).isoformat() + 'Z'
        print(f"Looking for comments since: {since}")
        
        # Fetch events
        events = self.fetch_github_events(since=since, max_pages=1)
        comment_events = self.filter_comment_events(events)
        
        if not comment_events:
            print("No recent comment events found in the specified time range")
            return {'total': 0, 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}
        
        # Process events
        stats = {'total': len(comment_events), 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}
        
        for event in comment_events:
            result, success = self.process_comment_event(event, dry_run)
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
    
    def run_migration(self, max_pages: int = 10, dry_run: bool = False) -> Dict:
        """Run the migration workflow (all historical comments)"""
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
        
        # Fetch all events
        events = self.fetch_github_events(max_pages=max_pages)
        comment_events = self.filter_comment_events(events)
        
        if not comment_events:
            print("No comment events found in the specified range")
            return {'total': 0, 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}
        
        # Process events
        stats = {'total': len(comment_events), 'processed': 0, 'created': 0, 'skipped': 0, 'errors': 0}
        
        for i, event in enumerate(comment_events, 1):
            print(f"\n📊 Processing comment {i}/{len(comment_events)}")
            result, success = self.process_comment_event(event, dry_run)
            stats['processed'] += 1
            
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

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python github_jira_monitor.py <monitor|migrate> [options]")
        print("  monitor [--since-minutes 15] [--dry-run]")
        print("  migrate [--max-pages 10] [--dry-run]")
        sys.exit(1)
    
    command = sys.argv[1]
    monitor = GitHubJIRAMonitor()
    
    if command == 'monitor':
        since_minutes = 15
        dry_run = False
        
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--since-minutes' and i + 3 < len(sys.argv):
                since_minutes = int(sys.argv[i + 3])
            elif arg == '--dry-run':
                dry_run = True
        
        stats = monitor.run_monitor(since_minutes=since_minutes, dry_run=dry_run)
        
    elif command == 'migrate':
        max_pages = 10
        dry_run = False
        
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--max-pages' and i + 3 < len(sys.argv):
                max_pages = int(sys.argv[i + 3])
            elif arg == '--dry-run':
                dry_run = True
        
        stats = monitor.run_migration(max_pages=max_pages, dry_run=dry_run)
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    # Exit with error code if there were errors
    if stats['errors'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
