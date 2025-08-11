"""
Grouping and status analysis logic for GitHubJIRAMonitor.
"""

def gather_and_group_github_data(self, max_pages=10, since_minutes=None):
    """
    CORE FUNCTION: Gather all GitHub data and group by owner/repo/issue number
    This implements the flow from the STATUS_FLOW_PROPOSAL.md
    Returns structured data grouped by repo and issue with status analysis
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    print("🚀 === CORE DATA GATHERING & GROUPING ===")
    print(f"Fetching GitHub data (max {max_pages} pages)...")
    since = None
    if since_minutes:
        since = (datetime.now() - timedelta(minutes=since_minutes)).isoformat() + 'Z'
        print(f"Looking for events since: {since}")
    print("\n📊 Step 1: Gathering all GitHub events...")
    all_events = self.fetch_github_events(since=since, max_pages=max_pages)
    event_types_seen = set()
    for event in all_events:
        event_types_seen.add(event.get('type', 'UNKNOWN'))
    print(f"\n📝 All event types seen in fetched events: {sorted(event_types_seen)}")
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
    for event in all_events:
        repo_info = event.get('repo', {})
        repo_name = repo_info.get('name', '')
        if not repo_name or '/' not in repo_name:
            continue
        repo_owner, repo_name_only = repo_name.split('/', 1)
        should_skip = self.should_skip_repo(repo_owner)
        if should_skip:
            continue
        issue_numbers = extract_issue_numbers_from_event(self, event)
        for issue_num in issue_numbers:
            repo_key = f"{repo_owner}/{repo_name_only}"
            grouped_data[repo_key][issue_num]['events'].append(event)
            processed_repos.add(repo_key)
    print(f"\n📝 All forked/external repos processed: {sorted(processed_repos)}")
    print(f"\n🔗 List of all my forked/external repo names:")
    for repo in sorted(processed_repos):
        print(f"  - {repo}")
    commented_repos = set()
    for repo_key, issues in grouped_data.items():
        for issue_num, issue_data in issues.items():
            for event in issue_data['events']:
                if event.get('type') in ['IssueCommentEvent', 'PullRequestReviewCommentEvent']:
                    commented_repos.add(repo_key)
                    break
    print(f"\n💬 All forked/external repos with at least one comment event: {sorted(commented_repos)}")
    print(f"\n📈 Step 3: Analyzing status for each issue...")
    analyzed_data = {}
    for repo_key, issues in grouped_data.items():
        analyzed_data[repo_key] = {}
        repo_owner, repo_name_only = repo_key.split('/', 1)
        print(f"\n📦 Analyzing repository: {repo_key}")
        for issue_num, issue_data in issues.items():
            print(f"  🔍 Analyzing issue #{issue_num}...")
            for ev in issue_data['events']:
                ev_type = ev.get('type', 'UNKNOWN')
                ev_created = ev.get('created_at', 'N/A')
                print(f"    • Event: {ev_type} at {ev_created}")
            issue_details = get_issue_details_for_analysis(self, repo_owner, repo_name_only, issue_num)
            issue_data['issue_details'] = issue_details
            pr_info = analyze_pr_status_for_issue(self, repo_owner, repo_name_only, issue_num, issue_data['events'])
            issue_data['pr_info'] = pr_info
            final_status, status_reasons = determine_final_status(self, issue_data, pr_info)
            issue_data['final_status'] = final_status
            issue_data['status_reasons'] = status_reasons
            analyzed_data[repo_key][issue_num] = issue_data
            print(f"    📊 Final Status: {final_status}")
            print(f"    📝 Reasons: {', '.join(status_reasons)}")
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

def _extract_issue_numbers_from_event(self, event):
    """Extract all possible issue numbers from a GitHub event"""
    import re
    issue_numbers = []
    event_type = event.get('type', '')
    payload = event.get('payload', {})
    if event_type in ['IssuesEvent', 'PullRequestEvent', 'IssueCommentEvent', 'PullRequestReviewCommentEvent']:
        if 'issue' in payload:
            issue_numbers.append(payload['issue'].get('number'))
        if 'pull_request' in payload:
            issue_numbers.append(payload['pull_request'].get('number'))
    elif event_type == 'PushEvent':
        ref = payload.get('ref', '')
        branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
        branch_issue = self.parse_issue_from_branch(branch_name)
        if branch_issue:
            issue_numbers.append(branch_issue)
    if 'comment' in payload:
        comment_body = payload['comment'].get('body', '')
        referenced_issues = re.findall(r'#(\d+)', comment_body)
        issue_numbers.extend([int(num) for num in referenced_issues])
    return [num for num in issue_numbers if num]

def _get_issue_details_for_analysis(self, repo_owner, repo_name, issue_num):
    """Fetch detailed issue information for analysis"""
    import requests
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

def _analyze_pr_status_for_issue(self, repo_owner, repo_name, issue_num, events):
    """Analyze PR status for an issue using events and GitHub API"""
    import requests
    pr_info = {
        'has_pr': False,
        'pr_number': None,
        'pr_state': None,
        'pr_merged': False,
        'pr_branch': None,
        'is_pr_itself': False
    }
    try:
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
        for event in events:
            if event.get('type') == 'PushEvent':
                payload = event.get('payload', {})
                ref = payload.get('ref', '')
                branch_name = ref.replace('refs/heads/', '') if ref.startswith('refs/heads/') else ref
                pr_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
                pr_params = {'head': f"{repo_owner}:{branch_name}", 'state': 'all'}
                pr_response = requests.get(pr_url, headers=headers, params=pr_params, timeout=10)
                if pr_response.status_code == 200:
                    prs = pr_response.json()
                    if prs:
                        pr = prs[0]
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

def _determine_final_status(self, issue_data, pr_info):
    """
    Determine final status using STATUS_FLOW_PROPOSAL.md priority logic
    """
    reasons = []
    if pr_info.get('pr_merged'):
        reasons.append("PR merged")
        return 'DONE', reasons
    has_backward, backward_status, backward_reasons = detect_backward_flow_triggers(self, issue_data, pr_info)
    if has_backward:
        return backward_status, backward_reasons
    if pr_info.get('pr_state') == 'open' and len(issue_data['events']) > 1:
        recent_activity = any(
            event.get('type') in ['IssueCommentEvent', 'PullRequestReviewCommentEvent', 'PushEvent']
            for event in issue_data['events']
        )
        if recent_activity:
            reasons.append("Open PR with recent activity")
            return 'IN PROGRESS', reasons
    if pr_info.get('pr_state') == 'open':
        reasons.append("Open PR exists")
        return 'PULL REQUEST', reasons
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
    if pr_info.get('pr_state') == 'open':
        reasons.append("Open PR exists")
        return 'PULL REQUEST', reasons
    has_push_events = any(event.get('type') == 'PushEvent' for event in issue_data['events'])
    if has_push_events:
        reasons.append("Push events detected")
        return 'IN PROGRESS', reasons
    has_branch_creation = any(
        event.get('type') == 'CreateEvent' and event.get('payload', {}).get('ref_type') == 'branch'
        for event in issue_data['events']
    )
    if has_branch_creation:
        reasons.append("Branch created")
        return 'TODO', reasons
    reasons.append("Comment activity only")
    return 'DISCUSSION', reasons

def _detect_backward_flow_triggers(self, issue_data, pr_info):
    """
    Detect backward flow triggers from STATUS_FLOW_PROPOSAL.md
    """
    if not pr_info.get('pr_state') == 'open':
        return False, None, []
    backward_reasons = []
    events = issue_data.get('events', [])
    for event in events:
        event_type = event.get('type', '')
        payload = event.get('payload', {})
        if event_type == 'IssueCommentEvent':
            issue = payload.get('issue', {})
            if issue.get('pull_request'):
                backward_reasons.append("Comment on open PR")
                return True, 'IN PROGRESS', backward_reasons
        if event_type in ['IssueCommentEvent', 'PullRequestReviewCommentEvent']:
            comment_body = payload.get('comment', {}).get('body', '')
            if f'@{self.github_user}' in comment_body:
                if event_type == 'IssueCommentEvent':
                    issue = payload.get('issue', {})
                    if issue.get('pull_request'):
                        backward_reasons.append("@mention on open PR")
                        return True, 'IN PROGRESS', backward_reasons
                else:
                    backward_reasons.append("@mention in PR review")
                    return True, 'IN PROGRESS', backward_reasons
        if event_type == 'PullRequestReviewCommentEvent':
            backward_reasons.append("PR review comment received")
            return True, 'IN PROGRESS', backward_reasons
        if event_type == 'PushEvent':
            push_ref = payload.get('ref', '')
            pr_branch = pr_info.get('pr_branch', '')
            if pr_branch and push_ref.endswith(pr_branch):
                backward_reasons.append("Push to PR branch")
                return True, 'PULL REQUEST', backward_reasons
    return False, None, []

def _is_event_on_open_pr(self, event, pr_info):
    """
    Check if an event is happening on the open PR itself
    """
    event_type = event.get('type', '')
    payload = event.get('payload', {})
    if not pr_info.get('pr_state') == 'open':
        return False
    if event_type == 'IssueCommentEvent':
        issue = payload.get('issue', {})
        if issue.get('pull_request'):
            issue_number = issue.get('number')
            return issue_number == pr_info.get('pr_number')
    if event_type == 'PullRequestReviewCommentEvent':
        pr = payload.get('pull_request', {})
        pr_number = pr.get('number')
        return pr_number == pr_info.get('pr_number')
    if event_type == 'PushEvent':
        push_ref = payload.get('ref', '')
        pr_branch = pr_info.get('pr_branch', '')
        if pr_branch and push_ref.endswith(pr_branch):
            return True
    return False

# Aliases for monitor_v1.py delegation
extract_issue_numbers_from_event = _extract_issue_numbers_from_event
get_issue_details_for_analysis = _get_issue_details_for_analysis
analyze_pr_status_for_issue = _analyze_pr_status_for_issue
determine_final_status = _determine_final_status
detect_backward_flow_triggers = _detect_backward_flow_triggers
is_event_on_open_pr = _is_event_on_open_pr
