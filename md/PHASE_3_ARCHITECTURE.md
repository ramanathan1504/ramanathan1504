# Phase 3: Code Structure & Architecture Implementation

## 🎯 **Phase 3 Scope**
**Objective**: Implement clean code architecture with proper folder structure, separation of concerns, error handling, and comprehensive testing patterns

## 📁 **Project Folder Structure**

```
ramanathan1504/
├── .github/
│   └── workflows/
│       ├── monitor.yml                    # Automated cron monitoring
│       ├── manual-process.yml             # Manual issue processing
│       └── test.yml                       # CI/CD testing pipeline
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── github_client.py               # GitHub API client
│   │   ├── jira_client.py                 # JIRA API client
│   │   └── config.py                      # Configuration management
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── event_processor.py             # GitHub event processing
│   │   ├── status_manager.py              # Kanban status logic
│   │   └── task_manager.py                # JIRA task operations
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                      # Logging utilities
│   │   ├── error_handler.py               # Error handling
│   │   └── validators.py                  # Input validation
│   └── workflows/
│       ├── __init__.py
│       ├── monitor_workflow.py            # Monitor command logic
│       ├── migration_workflow.py          # Migration command logic
│       └── manual_workflow.py             # Manual processing logic
├── scripts/
│   └── github_jira_monitor.py             # Main CLI entry point
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_github_client.py          # GitHub client tests
│   │   ├── test_jira_client.py            # JIRA client tests
│   │   ├── test_event_processor.py        # Event processing tests
│   │   ├── test_status_manager.py         # Status logic tests
│   │   └── test_task_manager.py           # Task management tests
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_real_github_api.py        # Real GitHub API tests
│   │   ├── test_real_jira_api.py          # Real JIRA API tests
│   │   └── test_end_to_end.py             # Full workflow tests
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── github_responses.py            # Mock GitHub responses
│   │   └── jira_responses.py              # Mock JIRA responses
│   └── conftest.py                        # pytest configuration
├── config/
│   ├── logging.yaml                       # Logging configuration
│   └── settings.yaml                      # Application settings
├── logs/                                  # Log files directory
├── docs/                                  # Documentation
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── TROUBLESHOOTING.md
├── requirements.txt                       # Python dependencies
├── requirements-dev.txt                   # Development dependencies
├── pytest.ini                            # pytest configuration
├── .gitignore
└── README.md
```

## 🏗️ **Architecture Patterns Applied**

### **1. Separation of Concerns Pattern**
```python
# src/core/github_client.py - Only GitHub API operations
class GitHubClient:
    def fetch_events(self) -> List[Dict]
    def get_repository(self) -> Dict
    def get_pull_request(self) -> Dict

# src/core/jira_client.py - Only JIRA API operations  
class JIRAClient:
    def search_issues(self) -> Dict
    def create_issue(self) -> str
    def update_status(self) -> bool

# src/processors/event_processor.py - Only event processing logic
class EventProcessor:
    def filter_comment_events(self) -> List[Dict]
    def classify_repository(self) -> str
    def extract_event_data(self) -> Dict
```

### **2. Strategy Pattern for Status Management**
```python
# src/processors/status_manager.py
class StatusManager:
    def __init__(self):
        self.strategies = {
            'Type-1-Fork': ForkRepositoryStrategy(),
            'Type-2-External': ExternalRepositoryStrategy()
        }
    
    def determine_status(self, repo_type: str, context: Dict) -> str:
        return self.strategies[repo_type].calculate_status(context)

class ForkRepositoryStrategy:
    def calculate_status(self, context: Dict) -> str:
        # Forward/backward flow logic for forked repos
        
class ExternalRepositoryStrategy:
    def calculate_status(self, context: Dict) -> str:
        # Always return DISCUSSION for external repos
```

### **3. Factory Pattern for Workflow Creation**
```python
# src/workflows/__init__.py
class WorkflowFactory:
    @staticmethod
    def create_workflow(workflow_type: str):
        workflows = {
            'monitor': MonitorWorkflow,
            'migrate': MigrationWorkflow,
            'manual': ManualWorkflow
        }
        return workflows[workflow_type]()
```

### **4. Repository Pattern for Data Access**
```python
# src/core/github_client.py
class GitHubRepository:
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def get_user_events(self, since: str = None) -> List[Dict]:
        # Abstract away API details
        
    def get_fork_status(self, repo: str) -> bool:
        # Encapsulate fork detection logic
```

## 🧪 **Test File Structure & Patterns**

### **1. Unit Test Pattern (AAA - Arrange, Act, Assert)**
```python
# tests/unit/test_status_manager.py
import pytest
from unittest.mock import Mock, patch
from src.processors.status_manager import StatusManager

class TestStatusManager:
    def setup_method(self):
        """Arrange - Set up test fixtures"""
        self.status_manager = StatusManager()
        self.mock_context = {
            'pr_status': {'status': 'merged'},
            'is_fork': True,
            'repo_owner': 'kubernetes',
            'repo_name': 'kubernetes'
        }
    
    def test_merged_pr_returns_done_status(self):
        """Act & Assert - Test specific behavior"""
        result = self.status_manager.determine_status('Type-1-Fork', self.mock_context)
        assert result == 'DONE'
    
    @pytest.mark.parametrize("repo_type,expected", [
        ('Type-2-External', 'DISCUSSION'),
        ('Type-1-Fork', 'TODO')
    ])
    def test_repository_type_status_mapping(self, repo_type, expected):
        """Parameterized test for multiple scenarios"""
        result = self.status_manager.determine_status(repo_type, {})
        assert result == expected
```

### **2. Integration Test Pattern**
```python
# tests/integration/test_real_github_api.py
import pytest
import os
from src.core.github_client import GitHubClient

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'), reason="GitHub token required")
class TestRealGitHubAPI:
    def setup_method(self):
        """Setup real API client"""
        self.client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    def test_fetch_user_events_returns_valid_data(self):
        """Test actual API response structure"""
        events = self.client.fetch_events(max_pages=1)
        
        assert isinstance(events, list)
        if events:  # Only test if events exist
            assert 'type' in events[0]
            assert 'created_at' in events[0]
            assert 'repo' in events[0]
    
    @pytest.mark.slow
    def test_rate_limit_handling(self):
        """Test rate limit behavior"""
        # Test with multiple rapid requests
        pass
```

### **3. Mock Test Pattern with Fixtures**
```python
# tests/fixtures/github_responses.py
MOCK_ISSUE_COMMENT_EVENT = {
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
            "html_url": "https://github.com/kubernetes/kubernetes/issues/1650"
        }
    }
}

# tests/unit/test_event_processor.py
from tests.fixtures.github_responses import MOCK_ISSUE_COMMENT_EVENT

def test_process_comment_event_with_mock_data():
    processor = EventProcessor()
    result = processor.process_event(MOCK_ISSUE_COMMENT_EVENT)
    assert result['event_type'] == 'IssueCommentEvent'
```

## 🚨 **Error Handling & Exception Patterns**

### **1. Custom Exception Hierarchy**
```python
# src/utils/error_handler.py
class GitHubJIRAMonitorError(Exception):
    """Base exception for all monitor errors"""
    pass

class GitHubAPIError(GitHubJIRAMonitorError):
    """GitHub API specific errors"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        self.status_code = status_code
        self.response = response
        super().__init__(f"GitHub API Error: {message}")

class JIRAAPIError(GitHubJIRAMonitorError):
    """JIRA API specific errors"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(f"JIRA API Error: {message}")

class ValidationError(GitHubJIRAMonitorError):
    """Input validation errors"""
    pass

class ConfigurationError(GitHubJIRAMonitorError):
    """Configuration related errors"""
    pass
```

### **2. Error Handler Decorator Pattern**
```python
# src/utils/error_handler.py
from functools import wraps
import logging

def handle_api_errors(retry_count: int = 3, backoff_factor: int = 2):
    """Decorator for handling API errors with retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_count):
                try:
                    return func(*args, **kwargs)
                except (GitHubAPIError, JIRAAPIError) as e:
                    last_exception = e
                    if e.status_code in [429, 403]:  # Rate limit
                        wait_time = backoff_factor ** attempt
                        logging.warning(f"Rate limited, waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    elif e.status_code >= 500:  # Server error
                        logging.warning(f"Server error, retry {attempt + 1}/{retry_count}")
                        continue
                    else:
                        raise  # Don't retry for client errors
                except Exception as e:
                    logging.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator

# Usage
@handle_api_errors(retry_count=3)
def fetch_github_events(self):
    # API call logic
```

### **3. Context Manager for Resource Management**
```python
# src/utils/error_handler.py
class APISession:
    """Context manager for API sessions with proper cleanup"""
    def __init__(self, client_type: str):
        self.client_type = client_type
        self.session = None
    
    def __enter__(self):
        logging.info(f"Starting {self.client_type} API session")
        self.session = requests.Session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
        
        if exc_type:
            logging.error(f"{self.client_type} session error: {exc_val}")
            return False  # Re-raise exception
        
        logging.info(f"{self.client_type} session completed successfully")
        return True

# Usage
def fetch_data(self):
    with APISession('GitHub') as session:
        response = session.get(url, headers=headers)
        # Automatic cleanup on exit
```

## 📝 **YAML Echo Patterns**

### **1. Informational Echo Pattern**
```yaml
# .github/workflows/monitor.yml
- name: Display Configuration
  run: |
    echo "🔧 GitHub JIRA Monitor Configuration:"
    echo "   📅 Triggered: ${{ github.event_name }}"
    echo "   ⏰ Since Minutes: ${{ github.event.inputs.since_minutes || '20' }}"
    echo "   🧪 Dry Run: ${{ github.event.inputs.dry_run || 'false' }}"
    echo "   🐍 Python Version: 3.9"
    echo "   📦 Dependencies: requests, base64"
    echo ""
```

### **2. Error Reporting Echo Pattern**
```yaml
- name: Validate Inputs
  run: |
    EXIT_CODE=0
    
    echo "🔍 Validating input parameters..."
    
    # Validate issue number
    if ! [[ "${{ github.event.inputs.issue_number }}" =~ ^[0-9]+$ ]]; then
      echo "❌ ERROR: Issue number must be numeric"
      echo "   Provided: '${{ github.event.inputs.issue_number }}'"
      EXIT_CODE=1
    else
      echo "✅ Issue number valid: ${{ github.event.inputs.issue_number }}"
    fi
    
    # Validate repository names
    if [ -z "${{ github.event.inputs.repo_name }}" ]; then
      echo "❌ ERROR: Repository name is required"
      EXIT_CODE=1
    else
      echo "✅ Repository name valid: ${{ github.event.inputs.repo_name }}"
    fi
    
    if [ -z "${{ github.event.inputs.owner_name }}" ]; then
      echo "❌ ERROR: Owner name is required"
      EXIT_CODE=1
    else
      echo "✅ Owner name valid: ${{ github.event.inputs.owner_name }}"
    fi
    
    if [ $EXIT_CODE -ne 0 ]; then
      echo ""
      echo "💡 Input format examples:"
      echo "   Issue number: 1650"
      echo "   Repository name: kubernetes"
      echo "   Owner name: kubernetes"
      exit $EXIT_CODE
    fi
    
    echo ""
    echo "🎯 All inputs validated successfully!"
```

### **3. Progress Reporting Echo Pattern**
```yaml
- name: Execute Monitor
  run: |
    echo "🚀 Starting GitHub JIRA Monitor execution..."
    echo "📊 Processing workflow: ${{ github.workflow }}"
    echo "🔄 Run number: ${{ github.run_number }}"
    echo ""
    
    # Execute the actual command
    python scripts/github_jira_monitor.py monitor --since-minutes 20
    
    RESULT=$?
    echo ""
    if [ $RESULT -eq 0 ]; then
      echo "✅ Monitor execution completed successfully"
    else
      echo "❌ Monitor execution failed with exit code: $RESULT"
      exit $RESULT
    fi
```

## 🖨️ **Python Print Patterns**

### **1. Structured Logging Pattern**
```python
# src/utils/logger.py
import logging
from datetime import datetime

class MonitorLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def info_banner(self, title: str, details: Dict = None):
        """Print formatted information banner"""
        print(f"\n{'='*50}")
        print(f"🔍 {title}")
        print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if details:
            for key, value in details.items():
                print(f"📋 {key}: {value}")
        print('='*50)
    
    def success(self, message: str, details: Dict = None):
        """Print success message with optional details"""
        print(f"✅ SUCCESS: {message}")
        if details:
            for key, value in details.items():
                print(f"   📊 {key}: {value}")
    
    def error(self, message: str, exception: Exception = None):
        """Print error message with exception details"""
        print(f"❌ ERROR: {message}")
        if exception:
            print(f"   🔧 Exception Type: {type(exception).__name__}")
            print(f"   📝 Exception Message: {str(exception)}")
    
    def progress(self, current: int, total: int, item: str = "items"):
        """Print progress indicator"""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * current // total) if total > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\r🔄 Progress: |{bar}| {current}/{total} {item} ({percentage:.1f}%)", end='')
        if current == total:
            print()  # New line when complete

# Usage in code
logger = MonitorLogger(__name__)

def process_events(events: List[Dict]):
    logger.info_banner("Event Processing", {
        "Total Events": len(events),
        "Event Types": list(set(e.get('type') for e in events))
    })
    
    for i, event in enumerate(events, 1):
        logger.progress(i, len(events), "events")
        # Process event
    
    logger.success("Event processing completed", {
        "Processed": len(events),
        "Duration": "2.3s"
    })
```

### **2. Status Reporting Pattern**
```python
# src/processors/status_manager.py
def determine_kanban_status(self, pr_status: Dict, is_fork: bool, repo_owner: str, repo_name: str):
    """Determine status with detailed reporting"""
    
    print(f"\n📊 Status Analysis for {repo_owner}/{repo_name}")
    print(f"🔍 Repository Type: {'Type-1 (Fork)' if is_fork else 'Type-2 (External)'}")
    print(f"📋 PR Status: {pr_status}")
    
    # Status determination logic
    if not is_fork:
        result = "DISCUSSION"
        print(f"📝 Logic: External repository → {result}")
        return result
    
    if pr_status.get('status') == 'merged':
        result = "DONE"
        print(f"📝 Logic: Merged PR (highest priority) → {result}")
        return result
    
    if pr_status.get('is_pr'):
        result = "PULL REQUEST"
        print(f"📝 Logic: Has open PR → {result}")
        return result
    
    result = "TODO"
    print(f"📝 Logic: Default fork behavior → {result}")
    return result
```

## 📋 **Clear Comments Pattern**

### **1. Function Documentation Pattern**
```python
def process_specific_issue(self, repo_owner: str, repo_name: str, issue_number: int, dry_run: bool = False):
    """
    Process a specific GitHub issue/PR and create corresponding JIRA task.
    
    This function handles both automated monitoring and manual processing workflows.
    It implements the complete status flow logic from the STATUS_FLOW_PROPOSAL.
    
    Args:
        repo_owner (str): GitHub repository owner (e.g., 'kubernetes')
        repo_name (str): GitHub repository name (e.g., 'kubernetes') 
        issue_number (int): GitHub issue/PR number (e.g., 1650)
        dry_run (bool): If True, simulate operations without making changes
        
    Returns:
        Tuple[str, bool]: (result_status, success_flag)
            - result_status: 'created', 'updated', 'skipped', 'error'
            - success_flag: True if operation succeeded, False otherwise
            
    Raises:
        GitHubAPIError: When GitHub API requests fail
        JIRAAPIError: When JIRA API operations fail
        ValidationError: When input parameters are invalid
        
    Example:
        >>> monitor = GitHubJIRAMonitor()
        >>> result, success = monitor.process_specific_issue('kubernetes', 'kubernetes', 1650)
        >>> print(f"Result: {result}, Success: {success}")
    """
```

### **2. Complex Logic Comments Pattern**
```python
def determine_kanban_status(self, pr_status: Dict, is_fork: bool, repo_owner: str, repo_name: str):
    """
    Implement the status flow logic from STATUS_FLOW_PROPOSAL.md
    
    Status Priority Order (highest to lowest):
    1. MERGED (highest priority) → DONE
    2. RELEASED → RELEASED  
    3. OPEN PR + ACTIVITY → IN PROGRESS
    4. OPEN PR → PULL REQUEST
    5. COMMITS ON BRANCH → IN PROGRESS
    6. BRANCH CREATED → TODO
    7. COMMENT ONLY → DISCUSSION
    """
    
    # Phase 1: Repository Type Classification
    # External repositories (Type-2) always go to DISCUSSION
    if not is_fork:
        # User doesn't have a fork of this repository
        # All activity on external repos is treated as discussion
        return "DISCUSSION", self._generate_labels(repo_owner, repo_name, "external")
    
    # Phase 2: Fork Repository Status Flow (Type-1)
    # Priority 1: Check for merged status (highest priority)
    # This fixes the critical bug where merged PRs were incorrectly marked "In Progress"
    if pr_status.get('status') == 'merged':
        # Merged PRs always win, regardless of other activity
        # Check if there's a recent release to move to RELEASED
        if self._has_recent_release(repo_owner, repo_name):
            return "RELEASED", self._generate_labels(repo_owner, repo_name, "released")
        else:
            return "DONE", self._generate_labels(repo_owner, repo_name, "merged")
    
    # Priority 2: Check for open PR with activity (backward flow)
    # This implements the backward flow: PULL REQUEST → IN PROGRESS
    if self._has_open_pr_with_activity(pr_status):
        # User is actively working on feedback for an open PR
        return "IN PROGRESS", self._generate_labels(repo_owner, repo_name, "in-progress")
    
    # Priority 3: Check for open PR (forward flow)
    # This implements: IN PROGRESS → PULL REQUEST
    if pr_status.get('is_pr') or pr_status.get('has_linked_pr'):
        return "PULL REQUEST", self._generate_labels(repo_owner, repo_name, "pull-request")
    
    # Priority 4: Check for development activity
    # This implements: TODO → IN PROGRESS
    if self._has_development_activity():
        return "IN PROGRESS", self._generate_labels(repo_owner, repo_name, "in-progress")
    
    # Priority 5: Default entry point for forked repos
    # This implements: DISCUSSION → TODO (when branch created)
    # For now, comment-only scenarios default to TODO for forked repos
    return "TODO", self._generate_labels(repo_owner, repo_name, "todo")
```

### **3. Configuration Comments Pattern**
```python
# config/settings.yaml with inline comments
# GitHub JIRA Monitor Configuration
# This file contains all configurable parameters for the monitor system

github:
  # GitHub API configuration
  user: "ramanathan1504"           # Target GitHub username for monitoring
  rate_limit_buffer: 100           # Keep 100 requests as buffer before hitting limit
  max_pages_per_request: 10        # Maximum pages to fetch in single API call
  
  # Repository filtering
  skip_orgs:                       # Organizations to skip during processing
    - "intemo_dev"                 # Internal organization repositories
  skip_repos:                      # Specific repositories to exclude
    - "ramanathan1504/private-*"   # All private repositories (pattern matching)

jira:
  # JIRA integration settings
  domain: "osscontribution.atlassian.net"  # JIRA instance domain
  project: "OT"                            # JIRA project key for tasks
  
  # Status mapping configuration
  statuses:
    discussion: "Discussion"        # External repository discussions
    todo: "Todo"                   # Initial status for forked repo work
    in_progress: "In Progress"     # Active development status  
    pull_request: "Pull Request"   # Code review status
    done: "Done"                   # Merged/completed status
    released: "Released"           # Production release status

# Workflow timing configuration
monitor:
  default_lookback_minutes: 20     # Default time window for monitoring
  cron_interval_minutes: 10        # Automated monitoring frequency
  
# Error handling configuration
error_handling:
  max_retries: 3                   # Maximum retry attempts for API calls
  backoff_factor: 2                # Exponential backoff multiplier
  timeout_seconds: 30              # API request timeout
```

## ✅ **Phase 3 Deliverables**

1. **Clean Folder Structure** ✅ (Separation of concerns by domain)
2. **Architecture Patterns** ✅ (Strategy, Factory, Repository patterns)
3. **Test Structure & Patterns** ✅ (Unit, Integration, Mock patterns)
4. **Error Handling Framework** ✅ (Custom exceptions, decorators, context managers)
5. **YAML Echo Patterns** ✅ (Informational, error, progress reporting)
6. **Python Print Patterns** ✅ (Structured logging, status reporting)
7. **Clear Comments Documentation** ✅ (Function docs, logic explanation, configuration)

**Phase 3 Complete - Ready for Phase 4!**
