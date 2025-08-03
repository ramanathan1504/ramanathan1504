# GitHub to JIRA Integration

Automated workflows to monitor GitHub comments and create JIRA tasks for contribution tracking.

## Overview

This system provides comprehensive GitHub-JIRA integration with:
- **Automated monitoring** of recent GitHub comments (cron-based)
- **Manual migration** workflows for historical data
- **Targeted processing** of specific issues/PRs
- **Smart Kanban organization** with workflow-specific behaviors
- **Perfect deduplication** to prevent duplicate tasks
- **Authorship detection** - creates tasks for authored PRs even without comments
- **Enhanced content handling** - supports both commented and authored contributions

## Quick Start

### 1. Setup Environment Variables

```bash
export GITHUB_TOKEN="your_github_token"
export JIRA_AUTH="your_base64_encoded_jira_auth"
```

### 2. Test Locally

```bash
# Activate virtual environment
python3 -m venv venv
source venv/bin/activate
pip install requests

# Run test script
./test_workflows.sh
```

### 3. Use GitHub Actions

Four automated workflows available:
- **Monitor** (cron every 10 minutes)
- **Migration** (manual, historical comments)
- **PR Migration** (manual, specific or scan mode)
- **Specific Issues** (manual, targeted processing)

## Workflows

### 1. Monitor Workflow
- **Trigger**: Automatic (every 10 minutes) or manual
- **Purpose**: Process recent comments (last 15 minutes)
- **Kanban**: Merged PRs → "Done", Active PRs → "Pull Request"

### 2. Migration Workflow  
- **Trigger**: Manual only
- **Purpose**: Process all historical comments
- **Kanban**: Merged PRs → "Done", Active PRs → "Pull Request"

### 3. PR Migration Workflow
- **Trigger**: Manual only
- **Mode**: `specific-prs` or `repo-scan`
- **Purpose**: Process authored PRs
- **Kanban**: All PRs → "Pull Request" (with status labels)

### 4. Specific Issues Workflow
- **Trigger**: Manual only
- **Purpose**: Process specific issue/PR numbers
- **Input**: `owner/repo#123,owner/repo#456`
- **Smart Detection**: Creates tasks for authored PRs/issues even without comments
- **Content Handling**: Uses authorship info when no comments exist
- **Kanban**: PRs → "Pull Request", Issues → appropriate column

## Kanban Organization

### Column Assignment Rules:
- **Done**: Merged contributions (monitor/migrate workflows only)
- **Pull Request**: All PRs with status labels (merged/open/closed)
- **Discussion**: General issue discussions
- **To Do**: New issues and tasks

### Labels:
- Repository owner + repo name (e.g., `kubernetes`, `kubernetes`)
- Status indicators: `merged`, `open`, `closed`, `pull-request`
- Fork indicators: `fork-repo`, `external-repo`

## Enhanced Processing

### Authorship Detection
The system now intelligently handles both commented and authored contributions:

- **Comments**: Creates tasks when you comment on issues/PRs
- **Authorship**: Creates tasks for PRs/issues you authored (even without comments)
- **Smart Content**: Uses appropriate content based on contribution type:
  - For comments: Uses your comment text
  - For authorship: Uses "Authored this PR/issue" with full description
- **Combined Cases**: When you both authored AND commented, includes both

### Example Scenarios:
1. **PR #1939**: You authored but never commented → ✅ Creates task with authorship info
2. **Issue #456**: You commented → ✅ Creates task with comment content  
3. **PR #789**: You authored AND commented → ✅ Creates task with both authorship + comments

## Local Testing

Use the test script for comprehensive validation:

```bash
./test_workflows.sh
```

This script will:
1. Validate environment setup
2. Run dry tests for all workflows
3. Execute real workflows with confirmation
4. Provide summary of results

## Configuration

Edit `scripts/github_jira_monitor.py` for:
- **GitHub user**: `self.github_user = 'your_username'`
- **Skip organizations**: `self.skip_orgs = ['org1', 'org2']`
- **JIRA settings**: Domain and project configuration

## Expected Results

After running workflows:
- ✅ No duplicate JIRA tasks
- ✅ Proper Kanban column assignment
- ✅ Clean labeling (owner + repo only)
- ✅ Complete contribution coverage
- ✅ Workflow-specific behaviors

## JIRA Project

Monitor results at: https://osscontribution.atlassian.net/projects/OT

## Architecture

```
GitHub Events API → Python Script → JIRA REST API
       ↓                ↓              ↓
   Comments/PRs    Processing     Task Creation
                  Deduplication   Kanban Status
                  Fork Detection  Label Assignment
```

## Files Structure

```
├── scripts/
│   └── github_jira_monitor.py    # Main Python implementation
├── .github/workflows/
│   ├── github-jira-monitor.yml   # Automated monitoring
│   ├── github-jira-migrate.yml   # Historical migration
│   ├── github-jira-pr-migrate.yml # PR processing
│   └── github-jira-old-issue.yml # Specific targeting
├── test_workflows.sh             # Local testing script
└── README.md                     # This file
```

## License

MIT License - see LICENSE file for details.

