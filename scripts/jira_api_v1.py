# --- Additional JIRA helpers from v1.py ---
def update_jira_status(jira_domain, jira_auth, task_key, status, dry_run=False):
    """Update the status of a JIRA task"""
    import requests
    if dry_run:
        print(f"[DRY RUN] Would update JIRA task {task_key} to status '{status}'")
        return True
    try:
        headers = get_jira_headers(jira_auth)
        # Get all transitions for the issue
        url = f"https://{jira_domain}/rest/api/2/issue/{task_key}/transitions"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"[JIRA] Failed to get transitions: {resp.status_code} {resp.text[:200]}")
            return False
        transitions = resp.json().get('transitions', [])
        # Find the transition id for the desired status
        transition_id = None
        for t in transitions:
            if t.get('name', '').lower() == status.lower():
                transition_id = t.get('id')
                break
        if not transition_id:
            print(f"[JIRA] No transition found for status '{status}' on {task_key}")
            return False
        # Perform the transition
        payload = {"transition": {"id": transition_id}}
        resp2 = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp2.status_code in [200, 204]:
            print(f"[JIRA] Updated {task_key} to status '{status}'")
            return True
        else:
            print(f"[JIRA] Failed to update status: {resp2.status_code} {resp2.text[:200]}")
            return False
    except Exception as e:
        print(f"[JIRA] Exception updating status: {e}")
        return False

def create_jira_task(jira_domain, jira_project, jira_auth, summary, description, labels=None):
    """Create a new JIRA task"""
    import requests
    try:
        headers = get_jira_headers(jira_auth)
        payload = {
            "fields": {
                "project": {"key": jira_project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
                "labels": labels or []
            }
        }
        url = f"https://{jira_domain}/rest/api/2/issue"
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in [200, 201]:
            print(f"[JIRA] Created task: {resp.json().get('key')}")
            return resp.json().get('key')
        else:
            print(f"[JIRA] Failed to create task: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[JIRA] Exception creating task: {e}")
        return None

def update_jira_task_with_status(jira_domain, jira_auth, task_key, fields, status):
    """Update a JIRA task with new fields and status"""
    import requests
    try:
        headers = get_jira_headers(jira_auth)
        url = f"https://{jira_domain}/rest/api/2/issue/{task_key}"
        resp = requests.put(url, headers=headers, json={"fields": fields}, timeout=10)
        if resp.status_code not in [200, 204]:
            print(f"[JIRA] Failed to update fields: {resp.status_code} {resp.text[:200]}")
            return False
        # Now update status
        return update_jira_status(jira_domain, jira_auth, task_key, status)
    except Exception as e:
        print(f"[JIRA] Exception updating task with status: {e}")
        return False

def update_jira_task(jira_domain, jira_auth, task_key, fields):
    """Update a JIRA task with new fields only"""
    import requests
    try:
        headers = get_jira_headers(jira_auth)
        url = f"https://{jira_domain}/rest/api/2/issue/{task_key}"
        resp = requests.put(url, headers=headers, json={"fields": fields}, timeout=10)
        if resp.status_code in [200, 204]:
            print(f"[JIRA] Updated task {task_key} fields.")
            return True
        else:
            print(f"[JIRA] Failed to update task fields: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[JIRA] Exception updating task: {e}")
        return False
# --- Copied from v1.py ---
def get_jira_headers(jira_auth):
    """Return headers for JIRA API requests with correct Authorization"""
    return {
        'Authorization': f'Basic {jira_auth}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

def search_existing_jira_task(jira_domain, jira_project, jira_auth, issue_url, issue_number, repo_name, repo_owner=None):
    """Search for existing JIRA task with this GitHub issue URL in the description (deduplication by URL, repo, and issue number)"""
    import requests
    try:
        headers = get_jira_headers(jira_auth)
        escaped_url = issue_url.replace('\\', '\\\\').replace('"', '\\"')
        jql = f'project = "{jira_project}" AND description ~ "{escaped_url}" AND summary ~ "{issue_number}"'
        url = f"https://{jira_domain}/rest/api/2/search"
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
                    if (issue_url.lower() in (desc or '').lower()):
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

def project_supports_epic(jira_domain, jira_project, jira_auth):
    import requests
    try:
        url = f"https://{jira_domain}/rest/api/2/issue/createmeta?projectKeys={jira_project}&expand=projects.issuetypes"
        headers = get_jira_headers(jira_auth)
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get('projects', [])
            if projects:
                issue_types = projects[0].get('issuetypes', [])
                for itype in issue_types:
                    if itype.get('name').lower() == 'epic':
                        return True
        print(f"[JIRA] Project {jira_project} does not support 'Epic' issue type.")
    except Exception as e:
        print(f"[JIRA] Error checking project issue types: {e}")
    return False
# JIRA API related functions from v1.py
# (Function bodies copied exactly from v1.py)
