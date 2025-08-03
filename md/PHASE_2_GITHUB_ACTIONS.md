# Phase 2: GitHub Actions YAML Implementation

## 🎯 **Phase 2 Scope**
**Objective**: Create GitHub Actions workflows for automated cron monitoring and manual issue processing

## 🔄 **Workflow 1: Automated Cron Monitor**

### **File**: `.github/workflows/monitor.yml`

```yaml
name: GitHub JIRA Monitor - Automated

on:
  schedule:
    # Run every 10 minutes
    - cron: '*/10 * * * *'
  workflow_dispatch:
    inputs:
      since_minutes:
        description: 'Minutes to look back for events'
        required: false
        default: '20'
        type: string
      dry_run:
        description: 'Run in dry mode (no actual changes)'
        required: false
        default: false
        type: boolean

jobs:
  monitor:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests base64
        
    - name: Run GitHub JIRA Monitor
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        JIRA_AUTH: ${{ secrets.JIRA_AUTH }}
      run: |
        if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
          if [ "${{ github.event.inputs.dry_run }}" = "true" ]; then
            python scripts/github_jira_monitor.py monitor --since-minutes ${{ github.event.inputs.since_minutes }} --dry-run
          else
            python scripts/github_jira_monitor.py monitor --since-minutes ${{ github.event.inputs.since_minutes }}
          fi
        else
          # Automated cron run
          python scripts/github_jira_monitor.py monitor --since-minutes 20
        fi
        
    - name: Upload logs
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: monitor-logs-${{ github.run_number }}
        path: |
          *.log
          logs/
        retention-days: 7
```

## 🔧 **Workflow 2: Manual Issue Processing**

### **File**: `.github/workflows/manual-process.yml`

```yaml
name: GitHub JIRA Monitor - Manual Processing

on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'Issue/PR number (e.g., 1650)'
        required: true
        type: string
      repo_name:
        description: 'Repository name (e.g., kubernetes)'
        required: true
        type: string
      owner_name:
        description: 'Repository owner (e.g., kubernetes)'
        required: true
        type: string
      dry_run:
        description: 'Run in dry mode (no actual changes)'
        required: false
        default: false
        type: boolean

jobs:
  process-manual:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests base64
        
    - name: Validate inputs
      run: |
        echo "Processing issue: ${{ github.event.inputs.issue_number }}"
        echo "Repository: ${{ github.event.inputs.owner_name }}/${{ github.event.inputs.repo_name }}"
        echo "Dry run: ${{ github.event.inputs.dry_run }}"
        
        # Validate issue number is numeric
        if ! [[ "${{ github.event.inputs.issue_number }}" =~ ^[0-9]+$ ]]; then
          echo "Error: Issue number must be numeric"
          exit 1
        fi
        
        # Validate repo and owner names are not empty
        if [ -z "${{ github.event.inputs.repo_name }}" ] || [ -z "${{ github.event.inputs.owner_name }}" ]; then
          echo "Error: Repository name and owner name are required"
          exit 1
        fi
        
    - name: Process specific issue
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        JIRA_AUTH: ${{ secrets.JIRA_AUTH }}
      run: |
        # Format the issue URL for old-issue command
        ISSUE_URL="${{ github.event.inputs.owner_name }}/${{ github.event.inputs.repo_name }}#${{ github.event.inputs.issue_number }}"
        
        if [ "${{ github.event.inputs.dry_run }}" = "true" ]; then
          python scripts/github_jira_monitor.py old-issue --issues "$ISSUE_URL" --dry-run
        else
          python scripts/github_jira_monitor.py old-issue --issues "$ISSUE_URL"
        fi
        
    - name: Upload processing logs
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: manual-process-logs-${{ github.run_number }}
        path: |
          *.log
          logs/
        retention-days: 7
        
    - name: Create job summary
      if: always()
      run: |
        echo "## Manual Processing Summary" >> $GITHUB_STEP_SUMMARY
        echo "- **Issue**: #${{ github.event.inputs.issue_number }}" >> $GITHUB_STEP_SUMMARY
        echo "- **Repository**: ${{ github.event.inputs.owner_name }}/${{ github.event.inputs.repo_name }}" >> $GITHUB_STEP_SUMMARY
        echo "- **Dry Run**: ${{ github.event.inputs.dry_run }}" >> $GITHUB_STEP_SUMMARY
        echo "- **Status**: ${{ job.status }}" >> $GITHUB_STEP_SUMMARY
        echo "- **Run Time**: $(date)" >> $GITHUB_STEP_SUMMARY
```

## 🔧 **Enhanced Python Function for Both Workflows**

### **Addition to `github_jira_monitor.py`**:

```python
def process_specific_issue(self, repo_owner: str, repo_name: str, issue_number: int, dry_run: bool = False) -> Tuple[str, bool]:
    """
    Process a specific issue/PR by owner, repo name, and issue number
    This function works for both automated monitoring and manual processing
    """
    try:
        print(f"\n=== Processing Specific Issue ===")
        print(f"Repository: {repo_owner}/{repo_name}")
        print(f"Issue/PR: #{issue_number}")
        print(f"Dry Run: {dry_run}")
        print()
        
        # Check if should skip (skip own repos and specified orgs)
        if self.should_skip_repo(repo_owner):
            print(f"✅ SKIPPED: Own/org repo - {repo_owner}/{repo_name}")
            return 'skipped', True
        
        # Check fork status
        is_fork = self.check_fork_status(f"{repo_owner}/{repo_name}")
        
        # Get issue details
        issue_url = f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}"
        issue_details = self.get_issue_details(issue_url)
        
        if not issue_details:
            print(f"❌ Could not fetch issue details for #{issue_number}")
            return 'error', False
        
        issue_title = issue_details.get('title', 'No title')
        issue_body = issue_details.get('body', 'No description available')
        
        print(f"📋 Issue Title: {issue_title}")
        print(f"🔍 Fork Status: {'Yes' if is_fork else 'No'}")
        
        # Check PR status to determine Kanban column
        pr_status = self.check_pr_status(repo_owner, repo_name, issue_number)
        
        # Create event context for status determination
        event_context = {
            'event_type': 'manual_processing',
            'is_review_comment': False,
            'is_push_event': False,
            'is_own_issue_comment': False
        }
        
        kanban_status, labels = self.determine_kanban_status(pr_status, is_fork, repo_owner, repo_name, event_context)
        
        print(f"📊 Status Analysis:")
        print(f"   PR Status: {pr_status}")
        print(f"   Kanban Column: {kanban_status}")
        print(f"   Labels: {labels}")
        
        # Check for existing task
        existing_key = self.search_existing_jira_task(issue_url, issue_number, repo_name)
        
        if existing_key:
            print(f"🔄 Found existing JIRA task: {existing_key}")
            # Update existing task status if needed
            success = self.update_jira_status(existing_key, kanban_status, dry_run)
            if success:
                return 'updated', True
            else:
                return 'error', False
        
        # Create new task
        event_data = {
            'repo_name': f"{repo_owner}/{repo_name}",
            'repo_owner': repo_owner,
            'issue_url': issue_url,
            'issue_title': issue_title,
            'issue_number': issue_number,
            'comment_body': 'Manual processing - no specific comment',
            'created_at': datetime.now().isoformat()
        }
        
        success = self.create_jira_task(event_data, is_fork, dry_run, kanban_status, labels)
        
        if success:
            return 'created', True
        else:
            return 'error', False
            
    except Exception as e:
        print(f"❌ Error processing specific issue: {e}")
        return 'error', False

def run_old_issue_migration(self, issue_list: List[str], dry_run: bool = False) -> Dict:
    """
    Enhanced old issue migration that works with both formats:
    1. Full URLs: https://github.com/owner/repo/issues/123
    2. Short format: owner/repo#123
    """
    print("=== Starting Old Issue Migration ===")
    print(f"Issues to process: {len(issue_list)}")
    print(f"Dry Run: {dry_run}")
    print()
    
    stats = {'total': len(issue_list), 'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    
    for issue_spec in issue_list:
        try:
            # Parse issue specification
            if issue_spec.startswith('https://github.com/'):
                # Full URL format
                parts = issue_spec.replace('https://github.com/', '').split('/')
                if len(parts) >= 4:
                    repo_owner = parts[0]
                    repo_name = parts[1]
                    issue_number = int(parts[3])
                else:
                    print(f"⚠️  Invalid URL format: {issue_spec}")
                    stats['errors'] += 1
                    continue
            elif '#' in issue_spec:
                # Short format: owner/repo#123
                repo_part, issue_part = issue_spec.split('#')
                repo_owner, repo_name = repo_part.split('/')
                issue_number = int(issue_part)
            else:
                print(f"⚠️  Invalid issue format: {issue_spec}")
                stats['errors'] += 1
                continue
            
            print(f"\n--- Processing {repo_owner}/{repo_name}#{issue_number} ---")
            
            result, success = self.process_specific_issue(repo_owner, repo_name, issue_number, dry_run)
            stats['processed'] += 1
            
            if result == 'skipped':
                stats['skipped'] += 1
            elif result == 'created' and success:
                stats['created'] += 1
            elif result == 'updated' and success:
                stats['updated'] += 1
            else:
                stats['errors'] += 1
                
        except Exception as e:
            print(f"❌ Error processing {issue_spec}: {e}")
            stats['errors'] += 1
    
    print(f"\n=== Old Issue Migration Summary ===")
    print(f"Total Issues: {stats['total']}")
    print(f"Processed: {stats['processed']}")
    print(f"JIRA Tasks Created: {stats['created']}")
    print(f"JIRA Tasks Updated: {stats['updated']}")
    print(f"Skipped (own repos): {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    return stats
```

## 🔐 **Required Secrets Setup**

### **GitHub Repository Secrets**:
```
GITHUB_TOKEN: Your GitHub Personal Access Token
JIRA_AUTH: Base64 encoded JIRA credentials (email:api_token)
```

### **Setting up secrets**:
```bash
# GitHub Token (already available in repository)
# GITHUB_TOKEN is automatically provided by GitHub Actions

# JIRA Auth (manually add to repository secrets)
echo -n "your-email@domain.com:your-jira-api-token" | base64
# Copy the output and add as JIRA_AUTH secret
```

## 📋 **Usage Examples**

### **Automated Cron Monitoring**:
- **Automatic**: Runs every 10 minutes automatically
- **Manual trigger**: Go to Actions → "GitHub JIRA Monitor - Automated" → Run workflow
- **Custom parameters**: Set since_minutes and dry_run when manually triggered

### **Manual Issue Processing**:
- Go to Actions → "GitHub JIRA Monitor - Manual Processing" → Run workflow
- **Input examples**:
  - Issue number: `1650`
  - Repository name: `kubernetes`
  - Owner name: `kubernetes`
  - Dry run: `false`

## ✅ **Phase 2 Deliverables**

1. **Automated Cron Workflow** ✅ (10-minute intervals)
2. **Manual Processing Workflow** ✅ (on-demand with inputs)
3. **Enhanced Python Function** ✅ (works for both workflows)
4. **Input Validation** ✅ (error handling for invalid inputs)
5. **Logging & Artifacts** ✅ (upload logs for debugging)
6. **Job Summaries** ✅ (GitHub Actions summary reports)

**Phase 2 Complete - Ready for Phase 3!**
