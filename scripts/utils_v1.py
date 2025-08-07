"""
Utility/helper functions for GitHubJIRAMonitor.
"""

def should_skip_repo(self, repo_owner):
    """Return True if the repo_owner is the user or in the skip_orgs list"""
    if not repo_owner:
        return True
    if repo_owner.lower() == self.github_user.lower():
        return True
    if repo_owner.lower() in [org.lower() for org in self.skip_orgs]:
        return True
    return False

def parse_issue_from_branch(self, branch_name):
    """Parse issue number from branch name (e.g., issue-123, fix/456, etc.)"""
    import re
    match = re.search(r'(?:issue|fix|bug|feature)[-/](\d+)', branch_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
