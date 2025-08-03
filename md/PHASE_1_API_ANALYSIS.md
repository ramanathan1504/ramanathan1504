# Phase 1: API Analysis & Integration

## 🎯 **Phase 1 Scope**
**Objective**: Document and analyze all GitHub/JIRA APIs used in the system with input/output specifications

## 📊 **GitHub API Endpoints Used**

### **1. User Events API**
```
Endpoint: GET /users/{username}/events
Purpose: Fetch user's recent GitHub activity
Rate Limit: 5000 requests/hour (authenticated)
```

#### **Input Parameters:**
```json
{
  "username": "ramanathan1504",
  "per_page": 100,
  "page": 1
}
```

#### **Output Response:**
```json
[
  {
    "id": "12345678901",
    "type": "IssueCommentEvent",
    "created_at": "2025-08-03T10:30:00Z",
    "repo": {
      "name": "kubernetes/kubernetes",
      "url": "https://api.github.com/repos/kubernetes/kubernetes"
    },
    "payload": {
      "action": "created",
      "issue": {
        "number": 1650,
        "title": "Add support for container runtime",
        "html_url": "https://github.com/kubernetes/kubernetes/issues/1650",
        "user": {
          "login": "maintainer123"
        }
      },
      "comment": {
        "body": "I can work on this feature",
        "user": {
          "login": "ramanathan1504"
        }
      }
    }
  }
]
```

### **2. Repository Information API**
```
Endpoint: GET /repos/{owner}/{repo}
Purpose: Get repository details and fork status
Rate Limit: 5000 requests/hour
```

#### **Input Parameters:**
```json
{
  "owner": "ramanathan1504",
  "repo": "kubernetes"
}
```

#### **Output Response:**
```json
{
  "name": "kubernetes",
  "full_name": "ramanathan1504/kubernetes",
  "fork": true,
  "parent": {
    "full_name": "kubernetes/kubernetes"
  },
  "created_at": "2025-01-15T08:20:00Z"
}
```

### **3. Pull Request API**
```
Endpoint: GET /repos/{owner}/{repo}/pulls/{pull_number}
Purpose: Get PR details and status
Rate Limit: 5000 requests/hour
```

#### **Input Parameters:**
```json
{
  "owner": "kubernetes",
  "repo": "kubernetes", 
  "pull_number": 1933
}
```

#### **Output Response:**
```json
{
  "number": 1933,
  "title": "Fix memory leak in parser",
  "state": "closed",
  "merged": true,
  "merged_at": "2025-07-30T14:25:00Z",
  "head": {
    "ref": "fix-1650-memory-leak",
    "sha": "abc123def456"
  },
  "base": {
    "ref": "main"
  },
  "body": "Fixes #1650\n\nThis PR addresses the memory leak issue..."
}
```

### **4. Issue Details API**
```
Endpoint: GET /repos/{owner}/{repo}/issues/{issue_number}
Purpose: Get issue/PR details
Rate Limit: 5000 requests/hour
```

#### **Input Parameters:**
```json
{
  "owner": "kubernetes",
  "repo": "kubernetes",
  "issue_number": 1650
}
```

#### **Output Response:**
```json
{
  "number": 1650,
  "title": "Add support for container runtime",
  "body": "Currently the system doesn't support custom container runtimes...",
  "state": "open",
  "html_url": "https://github.com/kubernetes/kubernetes/issues/1650",
  "user": {
    "login": "issue_author"
  },
  "created_at": "2025-07-01T09:15:00Z"
}
```

### **5. Repository Releases API**
```
Endpoint: GET /repos/{owner}/{repo}/releases
Purpose: Check for recent releases
Rate Limit: 5000 requests/hour
```

#### **Input Parameters:**
```json
{
  "owner": "kubernetes",
  "repo": "kubernetes",
  "per_page": 10
}
```

#### **Output Response:**
```json
[
  {
    "tag_name": "v1.28.0",
    "name": "Release v1.28.0",
    "published_at": "2025-07-25T16:00:00Z",
    "body": "This release includes:\n- Fix for memory leak (#1933)\n- Performance improvements"
  }
]
```

## 🔧 **JIRA API Endpoints Used**

### **1. Issue Search API**
```
Endpoint: GET /rest/api/2/search
Purpose: Search for existing JIRA tasks
Rate Limit: 300 requests/minute
```

#### **Input Parameters:**
```json
{
  "jql": "project = \"OT\" AND summary ~ \"1650\" AND labels = \"kubernetes\"",
  "maxResults": 20,
  "fields": ["summary", "labels", "status"]
}
```

#### **Output Response:**
```json
{
  "total": 1,
  "issues": [
    {
      "key": "OT-36",
      "fields": {
        "summary": "1650 - Add support for container runtime",
        "labels": ["kubernetes", "kubernetes"],
        "status": {
          "name": "Discussion"
        }
      }
    }
  ]
}
```

### **2. Issue Creation API**
```
Endpoint: POST /rest/api/2/issue
Purpose: Create new JIRA task
Rate Limit: 300 requests/minute
```

#### **Input Parameters:**
```json
{
  "fields": {
    "project": {
      "key": "OT"
    },
    "summary": "1650 - Add support for container runtime",
    "description": "💭 Discussion on Forked Repo\n\nIssue Description:\nCurrently the system doesn't support...\n\nMy Comment:\nI can work on this feature\n\nGitHub Issue: https://github.com/kubernetes/kubernetes/issues/1650",
    "issuetype": {
      "name": "Task"
    },
    "labels": ["kubernetes", "kubernetes"]
  }
}
```

#### **Output Response:**
```json
{
  "key": "OT-41",
  "self": "https://osscontribution.atlassian.net/rest/api/2/issue/OT-41"
}
```

### **3. Issue Transitions API**
```
Endpoint: GET /rest/api/2/issue/{issueKey}/transitions
Purpose: Get available status transitions
Rate Limit: 300 requests/minute
```

#### **Input Parameters:**
```json
{
  "issueKey": "OT-41"
}
```

#### **Output Response:**
```json
{
  "transitions": [
    {
      "id": "11",
      "name": "To Do",
      "to": {
        "name": "Todo"
      }
    },
    {
      "id": "21", 
      "name": "In Progress",
      "to": {
        "name": "In Progress"
      }
    }
  ]
}
```

### **4. Issue Transition Execution API**
```
Endpoint: POST /rest/api/2/issue/{issueKey}/transitions
Purpose: Execute status transition
Rate Limit: 300 requests/minute
```

#### **Input Parameters:**
```json
{
  "issueKey": "OT-41",
  "transition": {
    "id": "21"
  }
}
```

#### **Output Response:**
```
HTTP 204 No Content (success)
```

## 🔄 **API Usage Flow**

### **1. Monitor Workflow:**
```
1. GET /users/ramanathan1504/events → Fetch recent events
2. For each repo: GET /repos/ramanathan1504/{repo} → Check fork status  
3. For each issue: GET /repos/{owner}/{repo}/issues/{number} → Get details
4. For PRs: GET /repos/{owner}/{repo}/pulls/{number} → Get PR status
5. Search JIRA: GET /rest/api/2/search → Check existing tasks
6. Create/Update JIRA: POST /rest/api/2/issue → Create new task
7. Update Status: POST /rest/api/2/issue/{key}/transitions → Set status
```

### **2. Migration Workflow:**
```
1. GET /users/ramanathan1504/events?page=1,2,3... → Bulk fetch events
2. Same processing flow as monitor
3. GET /repos/{owner}/{repo}/releases → Check release status
4. Batch process all found issues/PRs
```

## 📊 **API Response Processing**

### **Event Type Detection:**
```python
event_types = [
    "IssueCommentEvent",           # User comments on issues/PRs
    "PullRequestReviewCommentEvent", # Code review comments  
    "PullRequestEvent",            # PR opened/closed/merged
    "IssuesEvent",                 # Issue opened/closed
    "PushEvent"                    # Commits pushed
]
```

### **Repository Classification:**
```python
def classify_repo(repo_data):
    if repo_data.get('fork') == True:
        return "Type-1-Fork"      # User has fork
    else:
        return "Type-2-External"  # External repo
```

### **Status Determination:**
```python
def determine_status(pr_data, repo_type):
    if repo_type == "Type-2-External":
        return "DISCUSSION"
    
    if pr_data.get('merged') == True:
        return "DONE"
    elif pr_data.get('state') == 'open':
        return "PULL REQUEST"
    else:
        return "DISCUSSION"
```

## 🛡️ **Error Handling & Rate Limits**

### **GitHub Rate Limit Handling:**
```python
if response.status_code == 403:
    # Rate limited - wait 60 seconds
    time.sleep(60)
    retry_request()
```

### **JIRA Rate Limit Handling:**
```python
if response.status_code == 429:
    # Too many requests - exponential backoff
    wait_time = 2 ** retry_count
    time.sleep(wait_time)
```

### **API Authentication:**
```python
# GitHub
headers = {
    'Authorization': f'token {github_token}',
    'Accept': 'application/vnd.github.v3+json'
}

# JIRA  
headers = {
    'Authorization': f'Basic {base64_encoded_credentials}',
    'Content-Type': 'application/json'
}
```

## ✅ **Phase 1 Deliverables**

1. **Complete API Documentation** ✅
2. **Input/Output Specifications** ✅
3. **Error Handling Patterns** ✅
4. **Rate Limit Management** ✅
5. **Authentication Methods** ✅
6. **API Usage Flows** ✅

**Phase 1 Complete - Ready for Phase 2!**
