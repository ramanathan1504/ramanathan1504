# GitHub JIRA Integration System Documentation

## Overview
A comprehensive system for tracking GitHub contributions in JIRA with complete lifecycle management from discussion to release.

## System Architecture

### Components
1. **Ongoing Monitor Workflow** (`github-jira-monitor.yml`) - Continuous monitoring
2. **One-Time Migration Workflow** (`github-jira-one-time-migration.yml`) - Historical data migration  
3. **Python Monitor Script** (`scripts/github_jira_monitor.py`) - Core logic engine

## Workflow Documentation

### 1. Ongoing GitHub JIRA Monitor (`github-jira-monitor.yml`)

#### Purpose
Continuous monitoring of GitHub activity with automatic JIRA task creation and lifecycle management.

#### Triggers
- **Automatic Schedule**:
  - Every 10 minutes: Monitor GitHub events
  - Every hour (minute 0): Check for releases
- **Manual Execution**: Trigger with custom parameters

#### Operations
- `monitor` - Real-time GitHub activity monitoring
- `release-check` - Update Done → Released status
- `both` - Combined monitoring and release checking

#### Configuration
```yaml
inputs:
  operation: monitor|release-check|both
  since_minutes: "15"  # Time range for monitoring
  dry_run: "false"     # Test mode without creating tasks
```

#### Environment Variables
- `GITHUB_TOKEN` - GitHub API access token
- `JIRA_AUTH` - Base64 encoded JIRA credentials

### 2. One-Time Migration Workflow (`github-jira-one-time-migration.yml`)

#### Purpose
Initial setup and historical data migration. **Use once then archive.**

#### Operations
- `migrate` - Historical comment migration
- `pr-migrate` - Specific repository PR migration
- `old-issue` - Specific issue migration

#### Configuration
```yaml
inputs:
  operation: migrate|pr-migrate|old-issue
  max_pages: "10"                           # Pagination limit
  target_repos: "owner/repo1,owner/repo2"   # PR migration targets
  limit_per_repo: "0"                       # PR limit per repo
  issue_list: "owner/repo#123,owner/repo#456" # Specific issues
  dry_run: "true"                           # Test mode
```

## Python Script Documentation (`github_jira_monitor.py`)

### Class: GitHubJIRAMonitor

#### Initialization
```python
monitor = GitHubJIRAMonitor()
```

#### Core Methods

##### Event Detection
- `fetch_github_events()` - Retrieve GitHub events
- `filter_comment_events()` - Filter comment-related events
- `filter_authorship_events()` - Filter authored content events

##### Event Processing
- `process_comment_event()` - Handle comments with mention detection
- `process_authorship_event()` - Handle authored PRs/issues
- `determine_kanban_status()` - Smart status assignment logic

##### JIRA Integration
- `create_jira_task()` - Create new JIRA tasks
- `update_jira_status()` - Update task status
- `search_existing_jira_task()` - Find existing tasks

##### Status Management
- `check_release_status()` - Detect if code is released
- `update_released_tasks()` - Batch update to Released status
- `update_tasks_to_in_progress()` - Update to In Progress status

##### Main Workflows
- `run_monitor()` - Main monitoring workflow
- `run_migration()` - Historical migration
- `run_pr_migration()` - Repository-specific PR migration
- `run_old_issue_migration()` - Specific issue migration

### Command Line Interface

#### Available Commands
```bash
# Ongoing monitoring
python github_jira_monitor.py monitor [--since-minutes 15] [--dry-run]

# Release checking
python github_jira_monitor.py release-check [--dry-run]

# One-time migrations (use migration workflow instead)
python github_jira_monitor.py migrate [--max-pages 10] [--dry-run]
python github_jira_monitor.py pr-migrate [--max-pages 5] [--repos repo1,repo2] [--limit 50] [--dry-run]
python github_jira_monitor.py old-issue [--issues owner/repo#123,owner/repo#456] [--dry-run]
```

## Status Flow Logic

### 6-Stage Kanban Flow
```
Discussion → Todo → In Progress → Pull Request → Done → Released
```

### Status Assignment Rules

#### Discussion
- Mentions (@ramanathan1504) in external repositories
- General discussions about potential contributions

#### Todo  
- Mentions (@ramanathan1504) in forked repositories
- Issues assigned to you
- Feature requests you're interested in

#### In Progress
- Push events to branches you're working on
- Review comments on your PRs (feedback received)
- Active development indicators

#### Pull Request
- PRs you create (PullRequestEvent - opened)
- Active pull requests under review

#### Done
- Merged pull requests
- Completed issues
- Resolved tasks

#### Released
- Code that has been deployed/released
- Based on release tags and version detection

## Event Detection Logic

### GitHub Events Monitored

#### IssueCommentEvent
- Comments on issues
- Comments on pull requests
- Mention detection within comments

#### PullRequestReviewCommentEvent  
- Code review comments
- Review feedback detection
- Context-aware In Progress updates

#### PullRequestEvent
- PR creation (opened)
- PR status changes
- Authorship detection

#### IssuesEvent
- Issue creation (opened)
- Issue assignments
- Authorship tracking

#### PushEvent
- Code pushes to branches
- In Progress status triggers
- Development activity tracking

### Smart Logic Features

#### Mention Detection
```python
# Detects @ramanathan1504 mentions
if '@ramanathan1504' in comment_body:
    # Check if repository is forked
    if is_forked_repo:
        status = "Todo"
    else:
        status = "Discussion"
```

#### Fork Detection
```python
# Determines repository relationship
def is_forked_repository(repo_name):
    # Check if repo is fork of another repo
    # Used for smart status assignment
```

#### Duplicate Prevention
```python
# Repository-specific task matching
def search_existing_jira_task(repo_name, issue_number):
    # Prevents duplicate tasks for same GitHub item
    # Enables task updates vs new creation
```

## Configuration and Setup

### GitHub Secrets Required
```yaml
secrets:
  GH_TOKEN: "ghp_xxxxxxxxxxxxxxxxxxxx"  # GitHub Personal Access Token
  JIRA_AUTH: "base64(username:password)" # JIRA Authentication
```

### GitHub Token Permissions
- `repo` - Repository access
- `user` - User information
- `notifications` - Event access

### JIRA Configuration
- Domain: `osscontribution.atlassian.net`
- Project: `OT`
- Required custom fields for status transitions

## Usage Patterns

### Initial Setup
1. Run one-time migration workflow to backfill historical data
2. Enable ongoing monitoring workflow
3. Archive migration workflow after completion

### Ongoing Operations
- Monitoring runs automatically every 10 minutes
- Release checking runs automatically every hour
- Manual triggers available for immediate updates

### Troubleshooting
- Use `dry_run: true` for testing
- Check GitHub API rate limits
- Verify JIRA authentication and permissions
- Monitor workflow logs for error messages

## Integration Points

### GitHub Integration
- Uses GitHub REST API v3
- Respects rate limiting (5000 requests/hour)
- Handles pagination for large datasets
- Processes webhooks via scheduled polling

### JIRA Integration  
- Uses JIRA REST API v2
- Creates tasks in specified project
- Updates task status via transitions
- Maintains task metadata and links

### Error Handling
- Graceful API failure handling
- Retry logic for transient errors
- Comprehensive logging and error reporting
- Rollback capabilities for failed operations

## Performance Considerations

### API Efficiency
- Batched API requests where possible
- Intelligent pagination management
- Duplicate detection prevents unnecessary API calls
- Time-based filtering reduces processing overhead

### Rate Limiting
- Built-in GitHub API rate limit handling
- Exponential backoff for API errors
- Distributed processing across time windows
- Manual trigger rate limiting

### Scalability
- Configurable page limits for large datasets
- Repository-specific processing options
- Granular time range controls
- Background processing capabilities

## Security Considerations

### Token Management
- Secrets stored in GitHub repository settings
- No hardcoded credentials in code
- Secure API authentication methods
- Token rotation support

### Access Control
- Principle of least privilege for API tokens
- Repository-specific access controls
- User-specific event filtering
- Audit trail through GitHub Actions logs

## Monitoring and Observability

### Workflow Logs
- Detailed execution logs in GitHub Actions
- Error reporting and diagnostics
- Performance metrics and timing
- API usage statistics

### Success Metrics
- Tasks created vs updated
- Status transition accuracy
- API error rates
- Processing time trends

### Alerting
- Workflow failure notifications
- API rate limit warnings
- Authentication error alerts
- Data consistency checks

## Future Enhancements

### Planned Features
- Webhook-based real-time processing
- Advanced filtering and routing rules
- Custom field mapping capabilities
- Multi-project support

### Integration Opportunities
- Slack notifications for status changes
- Email summaries of activity
- Dashboard for contribution metrics
- Analytics and reporting features

## Troubleshooting Guide

### Common Issues

#### Authentication Errors
- Verify GITHUB_TOKEN and JIRA_AUTH secrets
- Check token permissions and expiration
- Validate JIRA user access rights

#### API Rate Limiting
- Monitor API usage in logs
- Reduce polling frequency if needed
- Use time-based filtering to reduce load

#### Missing Events
- Check event type filtering logic
- Verify time range parameters
- Ensure user activity is within scope

#### Duplicate Tasks
- Review duplicate detection logic
- Check repository name matching
- Verify task search criteria

#### Status Transition Failures
- Validate JIRA workflow configuration
- Check custom field requirements
- Verify user permissions for transitions

### Debug Commands
```bash
# Test with dry run
python github_jira_monitor.py monitor --since-minutes 60 --dry-run

# Check specific time range
python github_jira_monitor.py monitor --since-minutes 1440  # 24 hours

# Test release checking
python github_jira_monitor.py release-check --dry-run
```

### Log Analysis
- GitHub Actions provides detailed execution logs
- Search for error patterns and API responses
- Monitor timing and performance metrics
- Track task creation and update patterns

This documentation provides comprehensive coverage of the GitHub JIRA integration system architecture, configuration, and operational procedures.
