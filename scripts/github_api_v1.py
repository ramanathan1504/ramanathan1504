# Required imports for moved functions
import requests
import time
# --- Moved from github_api.py ---
def fetch_user_pull_requests(self, repo_owner, repo_name, max_pages=5):
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
            user_prs = [pr for pr in prs if pr.get('user', {}).get('login') == self.github_user]
            all_prs.extend(user_prs)
            print(f"📊 Found {len(user_prs)} PRs by {self.github_user} on page {page}")
            if page < max_pages:
                time.sleep(2)
        except Exception as e:
            print(f"❌ Error fetching PRs page {page}: {e}")
            continue
    print(f"✅ Total PRs found: {len(all_prs)} (authored by {self.github_user})")
    return all_prs

def process_pull_request(self, pr, repo_owner, repo_name, dry_run=False):
    """Process a single pull request and create JIRA task"""
    pr_number = pr.get('number', 0)
    pr_title = pr.get('title', 'No title')
    pr_body = pr.get('body', '')
    pr_url = pr.get('html_url', '')
    pr_state = pr.get('state', 'unknown')
    pr_merged = pr.get('merged', False)
    created_at = pr.get('created_at', '')
    print(f"[GITHUB] Processing PR #{pr_number}: {pr_title}")
    print(f"  State: {pr_state}, Merged: {pr_merged}, Created: {created_at}")
    print(f"  URL: {pr_url}")
    if dry_run:
        print(f"[DRY RUN] Would process PR #{pr_number} in {repo_owner}/{repo_name}")
        return True
    # Example: fetch PR details, comments, reviews, etc.
    # (Add your real logic here as needed for your workflow)
    return True

def process_specific_issue(self, repo_owner, repo_name, issue_number, dry_run=False):
    """Process a specific GitHub issue by issue number"""
    print(f"[GITHUB] Processing issue #{issue_number} in {repo_owner}/{repo_name}")
    if dry_run:
        print(f"[DRY RUN] Would process issue #{issue_number}")
        return True
    headers = self.get_github_headers()
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            issue = resp.json()
            print(f"[GITHUB] Issue title: {issue.get('title')}")
            print(f"[GITHUB] Issue state: {issue.get('state')}")
            return issue
        else:
            print(f"[GITHUB] Failed to fetch issue: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[GITHUB] Exception fetching issue: {e}")
        return None
# --- Copied from v1.py ---
def get_github_headers(github_token):
    """Return headers for GitHub API requests with correct Authorization format (no 'token ' prefix)"""
    return {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
    }

def fetch_github_events(github_user, github_token, since=None, max_pages=10, repo=None):
    """
    Fetch GitHub events for the authenticated user or for a specific repo.
    If repo is provided (format: owner/repo), fetch repo events. Otherwise, fetch user events (public events only).
    """
    headers = get_github_headers(github_token)
    print(f"[DEBUG] Authorization header: {headers['Authorization']}")
    print(f"[DEBUG] Token repr: {repr(github_token)}")
    from datetime import datetime
    events = []
    page = 1
    while page <= max_pages:
        if repo:
            url = f"https://api.github.com/repos/{repo}/events"
        else:
            url = f"https://api.github.com/users/{github_user}/events"
        params = {'per_page': 100, 'page': page}
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"⚠️  GitHub API error fetching events: {resp.status_code} {resp.text[:200]}")
            break
        page_events = resp.json()
        if not page_events:
            break
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                filtered = [e for e in page_events if 'created_at' in e and datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')) >= since_dt]
                events.extend(filtered)
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

def parse_issue_from_branch(branch_name):
    """Extract issue number from branch name patterns like 'fix-1650-*' or 'feature-2301-*'"""
    import re
    patterns = [
        r'(?:fix|feature|bug|issue|pr)-(\d+)',
        r'(\d+)-',
        r'#(\d+)',
        r'issue(\d+)',
        r'(\d+)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, branch_name.lower())
        if match:
            return int(match.group(1))
    return None
# GitHub API related functions from v1.py
# (Function bodies copied exactly from v1.py)
