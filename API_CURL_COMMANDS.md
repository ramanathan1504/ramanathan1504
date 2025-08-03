# 📡 GitHub-JIRA Monitor API Curl Commands

This file contains all the curl commands for the APIs used in the GitHub-JIRA monitoring system.

## 🔧 Environment Variables Setup

First, set up your environment variables:

```bash
# GitHub Configuration
export GITHUB_TOKEN="your_github_personal_access_token"
export GITHUB_USER="ramanathan1504"

# JIRA Configuration  
export JIRA_AUTH="base64_encoded_email:api_token"
export JIRA_DOMAIN="osscontribution.atlassian.net"
export JIRA_PROJECT="OT"
```

### Creating JIRA Auth Token:
```bash
# Replace with your actual email and API token
echo -n "your-email@example.com:your_api_token" | base64
```

## 🐙 GitHub API Endpoints

### 1. Fetch GitHub User Events (Main Monitoring)
**Purpose**: Get all public events for a user (comments, issues, PRs, etc.)

```bash
curl -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events?per_page=100&page=1" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json"
```

**Pagination Example**:
```bash
# Get multiple pages
for page in {1..5}; do
  curl -X GET \
    "https://api.github.com/users/${GITHUB_USER}/events?per_page=100&page=${page}" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json"
done
```

### 2. Check Repository Fork Status
**Purpose**: Determine if a repository is a fork (for contribution vs discussion classification)

```bash
# Replace 'repository_name' with actual repo name
curl -X GET \
  "https://api.github.com/repos/${GITHUB_USER}/repository_name" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json"
```

**Example for specific repo**:
```bash
curl -X GET \
  "https://api.github.com/repos/ramanathan1504/jreleaser" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json"
```

### 3. Fetch Issue Details
**Purpose**: Get detailed information about a GitHub issue

```bash
# URL conversion: 
# From: https://github.com/owner/repo/issues/123
# To: https://api.github.com/repos/owner/repo/issues/123

curl -X GET \
  "https://api.github.com/repos/owner/repo/issues/123" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json"
```

**Real Example**:
```bash
curl -X GET \
  "https://api.github.com/repos/jreleaser/jreleaser/issues/1792" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json"
```

### 4. Get User Information
**Purpose**: Verify user details and permissions

```bash
curl -X GET \
  "https://api.github.com/user" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json"
```

## 🎯 JIRA API Endpoints

### 5. Search for Existing JIRA Tasks
**Purpose**: Check if a JIRA task already exists for a GitHub issue

```bash
# URL encode the JQL query
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/search?jql=project%20%3D%20${JIRA_PROJECT}%20AND%20summary%20~%20%22https://github.com/owner/repo/issues/123%22&maxResults=1" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json"
```

**More readable JQL version**:
```bash
# JQL: project = OT AND summary ~ "https://github.com/owner/repo/issues/123"
curl -X GET \
  'https://osscontribution.atlassian.net/rest/api/2/search' \
  -G \
  --data-urlencode 'jql=project = OT AND summary ~ "https://github.com/jreleaser/jreleaser/issues/1792"' \
  --data-urlencode 'maxResults=1' \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json"
```

### 6. Create New JIRA Task (Discussion)
**Purpose**: Create a new JIRA task for external repository discussions

```bash
curl -X POST \
  "https://${JIRA_DOMAIN}/rest/api/2/issue" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {
        "key": "OT"
      },
      "summary": "1792 - Sample Issue Title",
      "description": "GitHub Discussion\n\nRepository: jreleaser/jreleaser\nIssue: https://github.com/jreleaser/jreleaser/issues/1792\nTitle: Sample Issue Title\n\nComment:\nThis is the comment content that triggered the task creation.",
      "issuetype": {
        "name": "Task"
      },
      "labels": ["github-discussion", "external-repo"]
    }
  }'
```

### 7. Create New JIRA Task (Contribution)
**Purpose**: Create a new JIRA task for contributions to forked repositories

```bash
curl -X POST \
  "https://${JIRA_DOMAIN}/rest/api/2/issue" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {
        "key": "OT"
      },
      "summary": "1792 - Contribution to forked repository",
      "description": "GitHub Contribution\n\nRepository: ramanathan1504/jreleaser (fork)\nIssue: https://github.com/ramanathan1504/jreleaser/issues/1792\nTitle: Contribution issue title\n\nComment:\nContribution comment details here.",
      "issuetype": {
        "name": "Task"
      },
      "labels": ["github-contribution", "fork-repo"]
    }
  }'
```

### 8. Get JIRA Task Details
**Purpose**: Retrieve details of an existing JIRA task

```bash
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/issue/OT-123" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json"
```

### 9. Update Existing JIRA Task
**Purpose**: Update the description of an existing JIRA task with new comments

```bash
curl -X PUT \
  "https://${JIRA_DOMAIN}/rest/api/2/issue/OT-123" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "description": "Updated GitHub Discussion\n\nRepository: jreleaser/jreleaser\nIssue: https://github.com/jreleaser/jreleaser/issues/1792\nTitle: Updated issue title\n\nLatest Comment:\nThis is the new comment that triggered the update.\n\nPrevious comments and discussions continue below..."
    }
  }'
```

### 10. Get JIRA Project Information
**Purpose**: Verify JIRA project details and permissions

```bash
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/project/${JIRA_PROJECT}" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json"
```

## 🧪 Testing Commands

### Test GitHub Authentication
```bash
curl -X GET \
  "https://api.github.com/user" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json"
```

### Test JIRA Authentication
```bash
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/myself" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json"
```

### Test GitHub Events (Limited)
```bash
curl -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events?per_page=5&page=1" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json"
```

### Test JIRA Search
```bash
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/search?jql=project%20%3D%20${JIRA_PROJECT}&maxResults=1" \
  -H "Authorization: Basic ${JIRA_AUTH}" \
  -H "Accept: application/json"
```

## 📊 Rate Limiting Information

### GitHub API Limits:
- **Authenticated**: 5,000 requests per hour
- **Search API**: 30 requests per minute
- **Headers to check**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### JIRA API Limits:
- **Standard**: 10 requests per second per IP
- **Bulk operations**: Lower limits apply
- **Headers to check**: `X-RateLimit-*` headers

## 🚨 Error Handling Examples

### Handle GitHub Rate Limiting:
```bash
response=$(curl -s -w "\n%{http_code}" -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events" \
  -H "Authorization: token ${GITHUB_TOKEN}")

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "403" ]; then
  echo "Rate limited. Wait and retry."
fi
```

### Handle JIRA Authentication Errors:
```bash
response=$(curl -s -w "\n%{http_code}" -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/myself" \
  -H "Authorization: Basic ${JIRA_AUTH}")

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "401" ]; then
  echo "JIRA authentication failed. Check credentials."
fi
```

## 🔗 Useful JQ Filters

### Extract GitHub Event Types:
```bash
curl -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events?per_page=10" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" | \
  jq -r '.[].type' | sort | uniq -c
```

### Extract JIRA Task Keys:
```bash
curl -X GET \
  "https://${JIRA_DOMAIN}/rest/api/2/search?jql=project%20%3D%20${JIRA_PROJECT}&maxResults=10" \
  -H "Authorization: Basic ${JIRA_AUTH}" | \
  jq -r '.issues[].key'
```

### Filter Comment Events:
```bash
curl -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events?per_page=50" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" | \
  jq '.[] | select(.type == "IssueCommentEvent") | {repo: .repo.name, issue: .payload.issue.number, comment: .payload.comment.body}'
```

## 📝 Notes

1. **Authentication**: Always keep your tokens secure and never commit them to version control
2. **Rate Limiting**: Implement proper delays between requests in production
3. **Error Handling**: Always check HTTP status codes and handle errors gracefully
4. **Pagination**: GitHub events are paginated; adjust `page` parameter as needed
5. **URL Encoding**: JQL queries need proper URL encoding for special characters
6. **Timeouts**: Add appropriate timeout values for production use

## 🔄 Complete Workflow Example

```bash
#!/bin/bash

# 1. Get recent GitHub events
events=$(curl -s -X GET \
  "https://api.github.com/users/${GITHUB_USER}/events?per_page=10" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json")

# 2. Filter comment events
comment_events=$(echo "$events" | jq '.[] | select(.type == "IssueCommentEvent")')

# 3. For each comment event, check if JIRA task exists
# 4. Create or update JIRA task as needed

echo "Workflow complete!"
```

This file provides all the curl commands needed to interact with the GitHub and JIRA APIs used in the monitoring system.
