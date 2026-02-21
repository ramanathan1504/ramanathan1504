# Project Flow Documentation

## Overview
This project automates the processing of GitHub events and the creation/updating of JIRA tasks. It is structured as a CLI application, leveraging Picocli for command-line parsing and SLF4J for logging.

---

## Entry Point: `App.java`
- **Purpose:** CLI entry, parses arguments, starts workflow.
- **Main Steps:**
  - Parses three arguments: minutes to look back, results per page, max pages.
  - Initializes `GitHubJiraMonitor`.
  - Calls `runCoreWorkflow` with parsed arguments.

---

## Core Workflow: `GitHubJiraMonitor.java`
- **Initialization:**
  - Reads environment variables for GitHub and JIRA credentials, user, project, and organizations to skip.
  - Initializes API services: `GitHubApiService`, `JiraApiService`.
- **Main Method:** `runCoreWorkflow(sinceMinutes, perPage, maxPages)`
  - Calculates time window.
  - Gathers and groups GitHub data.
  - Creates JIRA objects from grouped data.
  - Updates pull request statuses and released tasks.

---

## Models
### `GitHubData.java`
- **Purpose:** DTOs for GitHub branches, forks, events, users, issues, comments.
- **Highlights:**
  - Nested classes for branch, fork, event, repo, payload, user, issue, comment.
  - Abstract base for comment-like items.

### `GitHubEventData.java`
- **Purpose:** Robust DTOs for GitHub webhook events.
- **Highlights:**
  - Classes for event, actor, repo, org, payload, issue, comment, pull request.
  - Handles various event types and payloads.

### `JiraData.java`
- **Purpose:** DTOs for JIRA search results, issues, fields, transitions, statuses.
- **Highlights:**
  - Classes for search result, issue, field, transition, status.

---

## Services
### `GitHubApiService.java`
- **Purpose:** Encapsulates GitHub API calls.
- **Main Methods:**
  - `hasReleases`, `listBranches`, `listCommits`, `listForks`.
  - Uses OkHttp and Jackson for HTTP and JSON.

### `JiraApiService.java`
- **Purpose:** Encapsulates JIRA API calls.
- **Main Methods:**
  - `searchIssues`, `createIssue`.
  - Uses OkHttp and Jackson for HTTP and JSON.

---

## Resources
- **JSON files:** Used for sample data and configuration.
- **Logging config:** `logback.xml`, `log4j2.xml` for logging setup.

---

## Full Flow Summary
1. **User runs CLI:** Arguments parsed in `App.java`.
2. **Monitor initialized:** `GitHubJiraMonitor` sets up environment and services.
3. **Workflow executed:**
   - GitHub events gathered and grouped.
   - JIRA issues created/updated based on grouped data.
   - Pull request statuses and released tasks updated.
4. **Models and services:** Handle data representation and API communication.

---

## Diagram (Textual)
```
App.java (CLI) --> GitHubJiraMonitor (workflow)
    |--> GitHubApiService (GitHub API)
    |--> JiraApiService (JIRA API)
    |--> Models (DTOs)
    |--> Resources (config, sample data)
```

---

## Extending/Modifying
- Add new event types: Extend models and update workflow logic.
- Change JIRA fields: Update `JiraData` and `JiraApiService`.
- Add logging or error handling: Modify workflow and services.

---

## Testing
- Test classes and resources are under `src/test`.
- Use sample JSON and logging configs for validation.

---

## Conclusion
This documentation provides a top-to-bottom summary of the project’s flow, main components, and their interactions. For detailed class/method logic, refer to the source files.

