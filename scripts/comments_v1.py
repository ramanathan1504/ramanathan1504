"""
comments_v1.py: Event/comment logic for GitHubJIRAMonitor.
Contains helpers for event filtering and activity log creation.
"""
# Additional event formatting helper moved from monitor_v1.py
def create_activity_log_from_events(events):
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
# --- Copied from v1.py ---
def filter_comment_events(events):
    """Filter for IssueCommentEvents and PullRequestReviewCommentEvents"""
    comment_types = ['IssueCommentEvent', 'PullRequestReviewCommentEvent']
    comment_events = [e for e in events if e.get('type') in comment_types]
    print(f"💬 Comment events found: {len(comment_events)}")
    return comment_events

def filter_authorship_events(events):
    """Filter for PR/Issue creation and Push events (authorship)"""
    authorship_types = ['PullRequestEvent', 'IssuesEvent', 'PushEvent']
    authorship_events = [e for e in events if e.get('type') in authorship_types]
    print(f"✍️  Authorship events found: {len(authorship_events)}")
    return authorship_events
# Comment/event filter functions from v1.py
# (Function bodies copied exactly from v1.py)
