# GitHub to JIRA Integration - Complete API Documentation

## 📋 Overview

This document explains the complete API flow for monitoring GitHub comments globally and automatically creating JIRA tasks. The system uses GitHub Events API to fetch user activities and JIRA REST API to create and manage tasks.

## 🏗️ Architecture Flow

```
GitHub Events API → Filter Comments → Fork Detection → JIRA Task Creation
       ↓                    ↓              ↓               ↓
   User Events    →  IssueCommentEvent → Check if Forked → Create/Update Task
```

## 🔧 API Endpoints & Usage

### 1. GitHub Events API

#### **Endpoint**: `GET /users/{username}/events`
```bash
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/users/ramanathan1504/events?per_page=100&page=1"
```

#### **Response Structure**:
```json
[
  {
    "type": "IssueCommentEvent",
    "created_at": "2025-08-03T10:30:00Z",
    "repo": {
      "full_name": "owner/repository",
      "owner": {
        "login": "owner"
      },
      "fork": false
    },
    "payload": {
      "comment": {
        "body": "My comment text"
      },
      "issue": {
        "html_url": "https://github.com/owner/repo/issues/123",
        "title": "Issue Title",
        "number": 123
      }
    }
  }
]
```

#### **Key Fields Extracted**:
- `type`: Filter for "IssueCommentEvent"
- `repo.owner.login`: Repository owner
- `repo.full_name`: Full repository name
- `payload.comment.body`: Comment content
- `payload.issue.html_url`: GitHub issue URL
- `payload.issue.title`: Issue title
- `payload.issue.number`: Issue number

### 2. GitHub Repository API (Fork Detection)

#### **Endpoint**: `GET /repos/{owner}/{repo}`
```bash
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/ramanathan1504/repository-name"
```

#### **Purpose**: Check if user has forked the external repository
#### **Key Field**: `fork: true/false`

### 3. GitHub Issues API (Detailed Issue Info)

#### **Endpoint**: `GET /repos/{owner}/{repo}/issues/{issue_number}`
```bash
curl -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/owner/repo/issues/123"
```

#### **Response Structure**:
```json
{
  "number": 123,
  "title": "Issue Title",
  "body": "Detailed issue description",
  "html_url": "https://github.com/owner/repo/issues/123"
}
```

### 4. JIRA REST API

#### **Search for Existing Tasks**
```bash
curl -X GET \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Content-Type: application/json" \
  "https://osscontribution.atlassian.net/rest/api/2/search?jql=project%20=%20OT%20AND%20summary%20~%20\"${ISSUE_URL}\""
```

#### **Create New Task**
```bash
curl -X POST \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Content-Type: application/json" \
  --data '{
    "fields": {
      "project": { "key": "OT" },
      "summary": "123 - Issue Title",
      "description": "Comment on Forked Repo...",
      "issuetype": { "name": "Task" },
      "labels": ["github-forked", "contribution"]
    }
  }' \
  "https://osscontribution.atlassian.net/rest/api/2/issue"
```

#### **Update Existing Task**
```bash
curl -X PUT \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Content-Type: application/json" \
  --data '{
    "fields": {
      "description": "Updated description with new comment"
    }
  }' \
  "https://osscontribution.atlassian.net/rest/api/2/issue/${TASK_KEY}"
```

## 🔄 Complete Data Flow

### Step 1: Fetch GitHub Events
```bash
# Get user's recent activities
EVENTS=$(curl -s -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/users/ramanathan1504/events?per_page=100")
```

### Step 2: Filter Comment Events
```bash
# Extract only IssueCommentEvents
COMMENT_EVENTS=$(echo "$EVENTS" | jq -c '.[] | select(.type == "IssueCommentEvent")')
```

### Step 3: Process Each Comment
```bash
# Extract event data
REPO_OWNER=$(echo "$event" | jq -r '.repo.owner.login')
REPO_NAME=$(echo "$event" | jq -r '.repo.full_name')
COMMENT_BODY=$(echo "$event" | jq -r '.payload.comment.body')
ISSUE_URL=$(echo "$event" | jq -r '.payload.issue.html_url')
ISSUE_TITLE=$(echo "$event" | jq -r '.payload.issue.title')
```

### Step 4: Filter External Repositories
```bash
# Skip own repositories and organization repos
if [ "$REPO_OWNER" = "ramanathan1504" ] || [ "$REPO_OWNER" = "intemo_dev" ]; then
  echo "SKIPPED: Own/org repo"
  continue
fi
```

### Step 5: Fork Detection Logic
```bash
# Check if user has forked the external repository
REPO_NAME_ONLY=$(echo "$REPO_NAME" | cut -d'/' -f2)
MY_FORK_CHECK=$(curl -s -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/ramanathan1504/$REPO_NAME_ONLY" | jq -r '.fork // false')

if [ "$MY_FORK_CHECK" = "true" ]; then
  TASK_TYPE="contribution"
  LABELS='["github-forked", "contribution"]'
else
  TASK_TYPE="discussion"
  LABELS='["github-discussion", "external-repo"]'
fi
```

### Step 6: Get Detailed Issue Information
```bash
# Convert GitHub issue URL to API URL
ISSUE_API_URL=$(echo "$ISSUE_URL" | sed 's|github.com|api.github.com/repos|' | sed 's|/issues/|/issues/|')
ISSUE_DETAILS=$(curl -s -H "Authorization: token ${GH_TOKEN}" "$ISSUE_API_URL")

ISSUE_NUMBER=$(echo "$ISSUE_DETAILS" | jq -r '.number')
ISSUE_BODY=$(echo "$ISSUE_DETAILS" | jq -r '.body')
```

### Step 7: Check for Existing JIRA Task
```bash
# Search JIRA for existing task
SEARCH_JQL="project = OT AND summary ~ \"$ISSUE_URL\""
EXISTING_ISSUE=$(curl -s -X GET \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  "https://osscontribution.atlassian.net/rest/api/2/search?jql=$(echo "$SEARCH_JQL" | sed 's/ /%20/g')")

EXISTING_KEY=$(echo "$EXISTING_ISSUE" | jq -r '.issues[0].key // empty')
```

### Step 8: Create or Update JIRA Task
```bash
if [ -n "$EXISTING_KEY" ]; then
  # Update existing task
  echo "Updating existing task: $EXISTING_KEY"
else
  # Create new task
  TASK_SUMMARY="$ISSUE_NUMBER - $ISSUE_TITLE"
  TASK_DESCRIPTION="$DESCRIPTION_PREFIX\n\nIssue Description:\n$ISSUE_BODY\n\nMy Comment:\n$COMMENT_BODY"
fi
```

## 🎯 Task Classification Logic

### Contribution Tasks
- **Condition**: User has forked the external repository
- **Labels**: `["github-forked", "contribution"]`
- **Purpose**: Track actual code contributions

### Discussion Tasks
- **Condition**: User has NOT forked the external repository
- **Labels**: `["github-discussion", "external-repo"]`
- **Purpose**: Track community engagement and discussions

## 📊 JIRA Task Structure

### Task Summary Format
```
{issue_number} - {issue_title}
Example: "123 - Fix authentication bug in login module"
```

### Task Description Format
```
Comment on Forked Repo (I have a fork):

Issue Description:
{original_issue_description}

My Comment:
{user_comment_content}

GitHub Issue: {github_issue_url}
Repo: {repository_full_name}
Original Date: {comment_date}
```

## 🔐 Authentication Setup

### GitHub Token (GH_TOKEN)
```bash
# Personal Access Token with permissions:
# - public_repo (for public repositories)
# - read:user (for user events)
```

### JIRA Authentication (JIRA_AUTH)
```bash
# Base64 encoded: email:api_token
echo -n "your-email@domain.com:your-jira-api-token" | base64
```

## ⚠️ Error Handling

### GitHub API Errors
- **HTTP 403**: Rate limiting - wait 60 seconds and retry
- **HTTP 404**: No more pages - stop pagination
- **Invalid JSON**: Log response and skip

### JIRA API Errors
- **Failed searches**: Log error and continue
- **Failed creation**: Log response and increment error counter

## 🚀 Workflow Triggers

### Real-time Monitoring
- **Schedule**: Every 10 minutes via cron
- **Scope**: Last 15 minutes of activity
- **Purpose**: Immediate JIRA task creation

### Historical Migration
- **Trigger**: Manual workflow dispatch
- **Scope**: All historical events (paginated)
- **Purpose**: Migrate existing comments to JIRA

## 📈 Performance Considerations

### Rate Limiting
- **GitHub**: 5000 requests/hour for authenticated users
- **JIRA**: Varies by plan (typically 10-20 requests/second)
- **Delays**: 1-2 seconds between requests

### Pagination
- **GitHub Events**: 100 events per page
- **Processing**: One page at a time with progress tracking
- **Stopping**: When no more events or errors occur

## 🔍 Debugging & Monitoring

### Log Output Format
```
=== Processing Comment Event ===
Repository: owner/repo-name
Owner: owner
Issue: Issue Title
URL: https://github.com/owner/repo/issues/123
🔄 FORK DETECTED: treating as CONTRIBUTION
📝 CREATE: Creating new contribution task
✅ SUCCESS: Created JIRA task: OT-456
```

### Success Indicators
- ✅ SKIPPED: Own/org repositories
- 🔄 FORK DETECTED: Contribution task
- 💬 NO FORK: Discussion task  
- 📝 CREATE: New JIRA task created
- ⚠️ ALREADY EXISTS: Task already exists
- ❌ ERROR: API failures

This documentation provides the complete technical overview of how GitHub comments are fetched, processed, and converted into JIRA tasks with proper classification and error handling.
