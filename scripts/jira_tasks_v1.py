
"""
JIRA task and epic creation logic for GitHubJIRAMonitor.
"""

import requests
from datetime import datetime

def create_jira_objects_from_grouped_data(self, grouped_data, dry_run=False):
    print("\n🎯 === CREATING JIRA OBJECTS FROM GROUPED DATA ===")
    stats = {
        'epics_created': 0,
        'epics_found': 0,
        'tasks_created': 0,
        'tasks_updated': 0,
        'tasks_existing': 0,
        'errors': 0
    }
    supports_epics = self.project_supports_epic()
    epic_link_field = self.get_epic_link_field_id() if supports_epics else None
    print(f"📊 JIRA Project supports Epics: {supports_epics}")
    if supports_epics:
        print(f"📊 Epic Link field ID: {epic_link_field}")
    created_epics = {}
    for repo_key, issues in grouped_data.items():
        repo_owner, repo_name = repo_key.split('/', 1)
        if self.should_skip_repo(repo_owner):
            print(f"⏭️  Skipping {repo_key} (own repo or connected org)")
            continue
        print(f"\n📦 Processing repository: {repo_key} (external/forked repo)")
        epic_key = None
        if supports_epics:
            epic_key = self._get_or_create_epic_for_owner(repo_owner, created_epics, dry_run)
            if epic_key:
                if epic_key in created_epics:
                    stats['epics_found'] += 1
                else:
                    stats['epics_created'] += 1
                    created_epics[epic_key] = repo_owner
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

def _get_or_create_epic_for_owner(self, repo_owner, created_epics, dry_run=False):
    for epic_key, owner in created_epics.items():
        if owner == repo_owner:
            return epic_key
    try:
        headers = self.get_jira_headers()
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
        if dry_run:
            print(f"    🧪 DRY RUN: Would create Epic for {repo_owner}")
            epic_key = f"{repo_owner}-DRYRUN"
            created_epics[epic_key] = repo_owner
            return epic_key
        epic_summary = f"{repo_owner}"
        epic_description = f"""Epic for tracking GitHub contributions to repositories owned by {repo_owner}.
\nThis Epic automatically groups all GitHub issues, PRs, and contributions 
related to {repo_owner}'s repositories.
\nAuto-created by GitHub-JIRA Monitor
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
        print(f"    📝 Creating Epic with basic fields only (avoiding custom field errors)")
        url = f"https://{self.jira_domain}/rest/api/2/issue"
        response = requests.post(url, headers=headers, json=epic_payload, timeout=30)
        if response.status_code in [200, 201]:
            result = response.json()
            epic_key = result.get('key')
            print(f"    ✅ Created Epic: {epic_key} for {repo_owner}")
            created_epics[epic_key] = repo_owner
            self._verify_epic_creation(epic_key, repo_owner)
            return epic_key
        else:
            print(f"    ❌ Failed to create Epic for {repo_owner}: {response.status_code}")
            print(f"    📝 Response: {response.text[:300]}")
            return None
    except Exception as e:
        print(f"    ❌ Error creating Epic for {repo_owner}: {e}")
        return None

def _create_jira_task_from_grouped_data(self, repo_owner, repo_name, issue_num, issue_data, epic_key, dry_run=False):
    issue_details = issue_data.get('issue_details', {})
    pr_info = issue_data.get('pr_info', {})
    final_status = issue_data.get('final_status', 'DISCUSSION')
    status_reasons = issue_data.get('status_reasons', [])
    issue_title = issue_details.get('title', f'Issue #{issue_num}')
    issue_body = issue_details.get('body', 'No description available')
    issue_url = issue_details.get('html_url', f'https://github.com/{repo_owner}/{repo_name}/issues/{issue_num}')
    issue_author = issue_details.get('user', {}).get('login', 'unknown')
    created_at = issue_details.get('created_at', '')
    from .monitor_v1 import GitHubJIRAMonitor
    existing_key = GitHubJIRAMonitor.search_existing_jira_task(issue_url, issue_num, repo_name, repo_owner)
    if existing_key:
        print(f"    🔄 Task already exists: {existing_key}")
        status_mapping = {
            'DISCUSSION': 'Discussion',
            'DONE': 'Done',
            'BUILD BROKEN': 'Build BRoken'
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
    if pr_info.get('is_pr_itself'):
        if pr_info.get('pr_merged'):
            task_type = "✅ MERGED Pull Request"
        elif pr_info.get('pr_state') == 'open':
            task_type = "🔄 OPEN Pull Request"
        else:
            task_type = "💥 BUILD BROKEN Pull Request"
    else:
        task_type = f"📋 GitHub Issue - {final_status}"
    task_summary = f"#{issue_num} - {issue_title}"
    comments_data = self._get_issue_comments_for_task(repo_owner, repo_name, issue_num)
    first_comment = comments_data.get('first_comment', issue_body or 'No description available')
    subsequent_comments = comments_data.get('subsequent_comments', [])
    activity_log = self._create_activity_log_from_events(issue_data.get('events', []))
    task_description = f"""{task_type}
\n*Repository:* {repo_owner}/{repo_name}
*Issue/PR:* #{issue_num} - {issue_title}
*Author:* @{issue_author}
*Created:* {created_at}
*URL:* {issue_url}
*Status:* {final_status}
\n----
\n*Original Issue Description:*
\n{first_comment}
\n----
\n*Status Analysis:*
• Final Status: {final_status}
• Reasons: {', '.join(status_reasons)}
• Has PR: {pr_info.get('has_pr', False)}
• PR Merged: {pr_info.get('pr_merged', False)}
\n{activity_log}
\n----
_Auto-synced from GitHub on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"""
    if dry_run:
        print(f"    🧪 DRY RUN: Would create task")
        print(f"      Summary: {task_summary}")
        print(f"      Status: {final_status}")
        print(f"      Epic: {epic_key or '[none]'}")
        print(f"      Comments to add: {len(subsequent_comments)}")
        return 'created'
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
        epic_to_attach = None
        if epic_key and self.project_supports_epic():
            print(f"    🔗 Will attach task to Epic: {epic_key} after creation")
            epic_to_attach = epic_key
        url = f"https://{self.jira_domain}/rest/api/2/issue"
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code in [200, 201]:
            result = response.json()
            task_key = result.get('key')
            if subsequent_comments:
                self._add_comments_to_jira_task(task_key, subsequent_comments)
            self._log_activity_transitions_to_jira(task_key, issue_data.get('events', []), final_status)
            if epic_to_attach and self.project_supports_epic():
                self._attach_epic_post_creation(task_key, epic_to_attach, repo_owner)
            status_mapping = {
                'DISCUSSION': 'Discussion',
                'DONE': 'Done',
                'BUILD BROKEN': 'Build BRoken'
            }
            jira_status = status_mapping.get(final_status, 'Discussion')
            print(f"    🔄 Transitioning task to status: {final_status} → {jira_status}")
            status_updated = self.update_jira_status(task_key, jira_status, dry_run=False)
            status_result = "✅ Status updated" if status_updated else "⚠️  Status transition failed"
            print(f"    ✅ Created task: {task_key} (Status: {final_status}, Epic: {epic_to_attach or '[none]'}, {status_result})")
            return 'created'
        else:
            print(f"    ❌ Failed to create task: {response.status_code} {response.text[:200]}")
            return 'error'
    except Exception as e:
        print(f"    ❌ Error creating task: {e}")
        return 'error'

def _verify_epic_creation(self, epic_key, repo_owner):
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

def _attach_epic_post_creation(self, task_key, epic_key, repo_owner):
    try:
        epic_link_field = self.get_epic_link_field_id()
        if not epic_link_field:
            print(f"    ❌ Could not find Epic Link field ID for project {self.jira_project}")
            return False
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

def _verify_epic_attachment(self, task_key, expected_epic_key):
    try:
        headers = self.get_jira_headers()
        url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(f"    ❌ Error verifying Epic attachment: {e}")
        return False

def _add_comments_to_jira_task(self, task_key, comments):
    for comment in comments:
        try:
            headers = self.get_jira_headers()
            url = f"https://{self.jira_domain}/rest/api/2/issue/{task_key}/comment"
            payload = {"body": comment}
            requests.post(url, headers=headers, json=payload, timeout=10)
        except Exception:
            pass

def _log_activity_transitions_to_jira(self, task_key, events, final_status):
    if not events:
        return
    # (No-op: placeholder for future status transition logging)
    pass
