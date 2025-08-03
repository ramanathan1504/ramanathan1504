# Data Handling & Processing Flow

## 🎯 Quick Reference: GitHub to JIRA Data Flow

### 1. GitHub Events Fetching
```bash
# Fetch user events with pagination
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/users/ramanathan1504/events?per_page=100&page=${page}"
```

**Data Extracted:**
```json
{
  "type": "IssueCommentEvent",
  "repo": {
    "full_name": "owner/repo",
    "owner": {"login": "owner"}
  },
  "payload": {
    "comment": {"body": "comment text"},
    "issue": {
      "html_url": "github.com/owner/repo/issues/123",
      "title": "Issue Title",
      "number": 123
    }
  }
}
```

### 2. Fork Detection Process
```bash
# Step 1: Extract repo name
REPO_NAME_ONLY=$(echo "owner/repo-name" | cut -d'/' -f2)

# Step 2: Check if I have a fork
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/ramanathan1504/${REPO_NAME_ONLY}"

# Step 3: Determine task type
if fork exists → CONTRIBUTION task
if no fork → DISCUSSION task
```

### 3. Issue Details Enhancement
```bash
# Convert issue URL to API endpoint
ISSUE_API_URL=$(echo "${ISSUE_URL}" | sed 's|github.com|api.github.com/repos|')

# Fetch full issue details
curl -H "Authorization: token ${GH_TOKEN}" "${ISSUE_API_URL}"
```

**Enhanced Data:**
```json
{
  "number": 123,
  "title": "Issue Title",
  "body": "Full issue description...",
  "html_url": "github.com/owner/repo/issues/123"
}
```

### 4. JIRA Task Creation Logic
```bash
# Task Summary Format
TASK_SUMMARY="${ISSUE_NUMBER} - ${ISSUE_TITLE}"

# Task Description Format
TASK_DESCRIPTION="
${DESCRIPTION_PREFIX}

Issue Description:
${ISSUE_BODY}

My Comment:
${COMMENT_BODY}

GitHub Issue: ${ISSUE_URL}
Repo: ${REPO_NAME}
"

# Task Labels by Type
CONTRIBUTION: ["github-forked", "contribution"]
DISCUSSION:   ["github-discussion", "external-repo"]
```

## 🔄 Processing States

### Repository Filtering
```
Own Repo (ramanathan1504/*) → SKIP
Org Repo (intemo_dev/*)    → SKIP  
External Repo              → PROCESS
```

### Fork Classification
```
Has Fork   → Contribution Task → Labels: github-forked, contribution
No Fork    → Discussion Task   → Labels: github-discussion, external-repo
```

### JIRA Task Handling
```
Existing Task → UPDATE with new comment
No Task       → CREATE new task
```

## 📊 Data Transformation Examples

### Input: GitHub Comment Event
```json
{
  "type": "IssueCommentEvent",
  "repo": {"full_name": "facebook/react", "owner": {"login": "facebook"}},
  "payload": {
    "comment": {"body": "Great feature! Thanks for implementing this."},
    "issue": {
      "html_url": "https://github.com/facebook/react/issues/12345",
      "title": "Add new React hook for state management",
      "number": 12345
    }
  }
}
```

### Output: JIRA Task (No Fork - Discussion)
```json
{
  "summary": "12345 - Add new React hook for state management",
  "description": "Discussion Comment on External Repo:\n\nIssue Description:\nThis PR adds a new React hook...\n\nMy Comment:\nGreat feature! Thanks for implementing this.",
  "labels": ["github-discussion", "external-repo"],
  "project": {"key": "OT"},
  "issuetype": {"name": "Task"}
}
```

### Output: JIRA Task (Has Fork - Contribution)
```json
{
  "summary": "12345 - Add new React hook for state management", 
  "description": "Comment on Forked Repo (I have a fork):\n\nIssue Description:\nThis PR adds a new React hook...\n\nMy Comment:\nGreat feature! Thanks for implementing this.",
  "labels": ["github-forked", "contribution"],
  "project": {"key": "OT"},
  "issuetype": {"name": "Task"}
}
```

## 🛠️ Error Handling & Recovery

### GitHub API Responses
```bash
HTTP 200 → Process normally
HTTP 403 → Rate limited, wait 60s and retry
HTTP 404 → No more pages, stop pagination
Invalid JSON → Log error, skip event
```

### JIRA API Responses
```bash
Success → Extract task key, log success
Failed → Log error response, increment error counter
Duplicate → Update existing task with new comment
```

## 📈 Counter Management (Subshell Fix)
```bash
# Problem: Counters lost in while loop subshell
# Solution: Use temporary files

# Before processing
echo "$TOTAL_PROCESSED" > /tmp/total_processed

# During processing
TOTAL_PROCESSED=$(cat /tmp/total_processed)
TOTAL_PROCESSED=$((TOTAL_PROCESSED + 1))
echo "$TOTAL_PROCESSED" > /tmp/total_processed

# After processing
TOTAL_PROCESSED=$(cat /tmp/total_processed)
```

## 🎮 Manual Testing Commands

### Test GitHub API
```bash
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/users/ramanathan1504/events?per_page=5" | jq '.[0]'
```

### Test Fork Detection
```bash
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/ramanathan1504/react" | jq '.fork'
```

### Test JIRA Search
```bash
curl -X GET \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  "https://osscontribution.atlassian.net/rest/api/2/search?jql=project=OT" | jq '.total'
```

This covers the complete data handling process from GitHub API to JIRA task creation!
