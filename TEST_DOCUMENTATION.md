# Test System Documentation

## Overview

The GitHub JIRA Monitor uses a comprehensive dual-mode testing strategy that separates concerns between development validation and production readiness. This approach ensures fast feedback during development while maintaining confidence in production deployments.

## Table of Contents

1. [Test Architecture](#test-architecture)
2. [Mock Test Suite](#mock-test-suite)
3. [Real Integration Test Suite](#real-integration-test-suite)
4. [Test Execution](#test-execution)
5. [CI/CD Integration](#cicd-integration)
6. [Test Maintenance](#test-maintenance)
7. [Troubleshooting](#troubleshooting)

## Test Architecture

### Dual-Mode Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Test Framework                       │
├─────────────────────────────────────────────────────────┤
│  Mock Tests              │  Real Integration Tests      │
│  ┌─────────────────┐     │  ┌─────────────────┐        │
│  │ • Fast (< 1s)   │     │  │ • Comprehensive │        │
│  │ • No API calls  │     │  │ • Real APIs     │        │
│  │ • 15 test cases │     │  │ • 8 test cases  │        │
│  │ • Business logic│     │  │ • End-to-end    │        │
│  │ • CI/CD ready   │     │  │ • Pre-deploy    │        │
│  └─────────────────┘     │  └─────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Test Files Structure

```
tests/
├── test_github_jira_monitor.py      # Mock tests (15 tests)
├── test_real_integration.py         # Real integration tests (8 tests)
├── README.md                        # Test execution guide
└── test_results/                    # Generated test reports
    ├── mock_test_results.xml
    ├── integration_test_results.xml
    └── coverage_report.html
```

## Mock Test Suite

### Purpose
Mock tests validate business logic without external dependencies, providing:
- **Fast Feedback**: Complete test suite runs in under 1 second
- **Reliable Results**: No network dependencies or rate limits
- **Complete Coverage**: All business logic paths tested
- **CI/CD Friendly**: Suitable for every commit and pull request

### Test Cases (15 total)

#### Initialization Tests
1. **test_mock_monitor_initialization**
   - Validates monitor setup with mock environment
   - Verifies all configuration attributes
   - Tests environment variable handling

#### GitHub Integration Tests
2. **test_mock_fetch_github_events**
   - Tests GitHub API event fetching logic
   - Validates request parameters and headers
   - Tests response parsing and error handling

3. **test_mock_filter_comment_events**
   - Tests comment event filtering logic
   - Validates event type recognition
   - Tests filtering accuracy

4. **test_mock_filter_authorship_events**
   - Tests authorship event filtering
   - Validates user attribution logic
   - Tests contribution recognition

#### Repository Analysis Tests
5. **test_mock_should_skip_repo**
   - Tests repository skipping logic
   - Validates organization filtering
   - Tests user repository handling

6. **test_mock_check_fork_status**
   - Tests fork detection logic
   - Validates API response handling
   - Tests error scenarios

#### Pull Request Tests
7. **test_mock_check_pr_status**
   - Tests PR status checking logic
   - Validates PR link detection
   - Tests state determination

8. **test_mock_determine_kanban_status**
   - Tests Kanban status determination
   - Validates workflow logic
   - Tests label assignment

#### JIRA Integration Tests
9. **test_mock_get_issue_details**
   - Tests GitHub issue data extraction
   - Validates data formatting
   - Tests error handling

10. **test_mock_search_existing_jira_task**
    - Tests JIRA task search logic
    - Validates query construction
    - Tests duplicate detection

11. **test_mock_create_jira_task_complete_logic**
    - Tests complete task creation flow
    - Validates payload construction
    - Tests integration points

12. **test_mock_update_jira_status**
    - Tests JIRA status update logic
    - Validates transition handling
    - Tests workflow management

#### Processing Tests
13. **test_mock_process_comment_event_complete**
    - Tests end-to-end comment processing
    - Validates complete workflow
    - Tests decision logic

14. **test_mock_run_monitor_dry_run**
    - Tests monitor execution in dry run mode
    - Validates statistics collection
    - Tests batch processing

#### Error Handling Tests
15. **test_mock_error_handling_scenarios**
    - Tests various error conditions
    - Validates graceful degradation
    - Tests error reporting

### Mock Test Execution

```bash
# Run all mock tests
python tests/test_github_jira_monitor.py

# Run with verbose output
python tests/test_github_jira_monitor.py --verbose

# Expected output:
============================================================
  GitHub JIRA Monitor Mock Test Suite
============================================================
[INFO 2025-01-08 10:00:00] Test mode: mock
[INFO 2025-01-08 10:00:00] Verbose: False
...
[SUCCESS 2025-01-08 10:00:01] ✓ All tests passed!
```

## Real Integration Test Suite

### Purpose
Real integration tests validate production readiness by:
- **API Connectivity**: Testing actual GitHub and JIRA APIs
- **Authentication**: Validating credentials and permissions
- **Rate Limiting**: Testing API limits and throttling
- **End-to-End Flows**: Validating complete workflows
- **Environment Validation**: Testing production configuration

### Test Cases (8 total)

#### Environment Validation
1. **test_real_monitor_initialization**
   - Tests monitor setup with real credentials
   - Validates environment variable handling
   - Tests configuration loading

2. **test_real_github_api_connectivity**
   - Tests GitHub API authentication
   - Validates API access and permissions
   - Checks rate limit status

3. **test_real_jira_api_connectivity**
   - Tests JIRA API authentication
   - Validates project access
   - Checks permission levels

#### API Integration Tests
4. **test_real_github_events_fetch**
   - Tests real GitHub event fetching
   - Validates data structure and content
   - Tests pagination handling

5. **test_real_github_events_filtering**
   - Tests event filtering with real data
   - Validates filtering accuracy
   - Tests edge cases

6. **test_real_jira_project_access**
   - Tests JIRA project access and permissions
   - Validates issue creation capabilities
   - Tests workflow transitions

#### Production Validation
7. **test_real_monitor_run_dry**
   - Tests complete monitor execution
   - Validates dry run mode safety
   - Tests statistics accuracy

8. **test_real_rate_limiting**
   - Tests API rate limit handling
   - Validates throttling behavior
   - Tests recovery mechanisms

### Real Test Execution

```bash
# Set up environment
export GITHUB_TOKEN="your_github_token"
export JIRA_AUTH="your_base64_encoded_credentials"

# Run all real integration tests
python tests/test_real_integration.py

# Run quick validation only
python tests/test_real_integration.py --quick

# Run with verbose output
python tests/test_real_integration.py --verbose

# Expected output:
============================================================
  GitHub JIRA Monitor Real Integration Tests - FULL Mode
============================================================
[INFO 2025-01-08 10:00:00] Test mode: full
[INFO 2025-01-08 10:00:00] All required environment variables found
...
[SUCCESS 2025-01-08 10:00:30] ✓ All real integration tests passed!
```

## Test Execution

### Local Development Workflow

#### 1. During Development (Mock Tests)
```bash
# Fast feedback during coding
python tests/test_github_jira_monitor.py

# With verbose output for debugging
python tests/test_github_jira_monitor.py --verbose
```

#### 2. Before Commit (Mock Tests + Quick Integration)
```bash
# Run mock tests
python tests/test_github_jira_monitor.py

# Quick integration validation
python tests/test_real_integration.py --quick
```

#### 3. Before Deployment (Full Test Suite)
```bash
# Complete mock test suite
python tests/test_github_jira_monitor.py --verbose

# Complete integration test suite
python tests/test_real_integration.py --verbose
```

### Environment Setup for Real Tests

#### 1. GitHub Token Setup
```bash
# Create GitHub Personal Access Token
# Go to: GitHub Settings → Developer settings → Personal access tokens
# Required scopes: read:user, repo (if accessing private repos)

export GITHUB_TOKEN="ghp_your_token_here"
```

#### 2. JIRA Authentication Setup
```bash
# Get JIRA API token
# Go to: JIRA Account → Security → API tokens → Create token

# Encode credentials (email:token)
echo -n "your.email@domain.com:your_jira_api_token" | base64

# Set environment variable
export JIRA_AUTH="encoded_credentials_here"
```

#### 3. Validation
```bash
# Quick environment check
python tests/test_real_integration.py --quick
```

## CI/CD Integration

### GitHub Actions Configuration

#### Mock Tests (Every Push/PR)
```yaml
name: Mock Tests

on: [push, pull_request]

jobs:
  mock-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run mock tests
      run: |
        python tests/test_github_jira_monitor.py --verbose
        echo "Mock test exit code: $?"
```

#### Integration Tests (Main Branch Only)
```yaml
name: Integration Tests

on:
  push:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run integration tests
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        JIRA_AUTH: ${{ secrets.JIRA_AUTH }}
      run: |
        python tests/test_real_integration.py --verbose
        echo "Integration test exit code: $?"
```

### Testing Strategy by Branch

| Branch Type | Mock Tests | Quick Integration | Full Integration |
|-------------|------------|-------------------|------------------|
| Feature branches | ✅ | ❌ | ❌ |
| Pull requests | ✅ | ✅ | ❌ |
| Main branch | ✅ | ✅ | ✅ |
| Release tags | ✅ | ✅ | ✅ |

## Test Maintenance

### Adding New Tests

#### Mock Test Addition
1. **Identify Test Scenario**: Determine what business logic needs testing
2. **Create Test Method**: Add method to `MockTestCase` class
3. **Setup Mocks**: Use `unittest.mock` to simulate external dependencies
4. **Assert Results**: Validate expected behavior
5. **Add Logging**: Include appropriate log messages

Example:
```python
def test_mock_new_feature(self):
    """Test new feature logic"""
    log_test("Testing new feature")
    
    # Setup mocks
    with patch('module.external_call') as mock_call:
        mock_call.return_value = expected_result
        
        # Test logic
        monitor = GitHubJIRAMonitor()
        result = monitor.new_feature()
        
        # Assertions
        self.assertEqual(result, expected_value)
        mock_call.assert_called_once()
    
    log_success("New feature logic verified")
```

#### Real Test Addition
1. **Identify Integration Point**: Determine what API integration needs testing
2. **Create Test Method**: Add method to `RealIntegrationTestCase` class
3. **Handle Environment**: Ensure proper credential handling
4. **Test API Interaction**: Validate actual API behavior
5. **Assert Results**: Validate expected responses

### Test Data Management

#### Mock Data
- Store mock response data in test files
- Use realistic data structures
- Version mock data with API changes

#### Test Credentials
- Use separate test accounts when possible
- Rotate credentials regularly
- Document credential requirements

### Performance Monitoring

#### Mock Test Performance
- Target: Complete suite < 1 second
- Monitor test execution time
- Optimize slow tests

#### Integration Test Performance
- Target: Complete suite < 60 seconds
- Monitor API response times
- Handle rate limiting gracefully

## Troubleshooting

### Common Mock Test Issues

#### Import Errors
```
Error: ImportError: No module named 'github_jira_monitor'
Solution: 
- Check sys.path configuration
- Verify scripts/ directory structure
- Ensure __init__.py files exist
```

#### Mock Patching Issues
```
Error: Mock patch target not found
Solution:
- Use full module path in patch
- Import target module before patching
- Check for typos in patch paths
```

#### Assertion Failures
```
Error: AssertionError in business logic tests
Solution:
- Review actual vs expected behavior
- Update test expectations if logic changed
- Check mock return values
```

### Common Integration Test Issues

#### Authentication Failures
```
Error: 401 Unauthorized from GitHub/JIRA
Solution:
- Verify token validity and format
- Check token permissions/scopes
- Regenerate tokens if expired
```

#### Rate Limiting
```
Error: 429 Too Many Requests
Solution:
- Reduce test frequency
- Use test-specific tokens with higher limits
- Implement test throttling
```

#### Environment Issues
```
Error: Missing environment variables
Solution:
- Set GITHUB_TOKEN and JIRA_AUTH
- Use .env file for local development
- Verify base64 encoding for JIRA_AUTH
```

### Debugging Strategies

#### Mock Test Debugging
1. **Enable Verbose Mode**: Use `--verbose` flag
2. **Add Debug Prints**: Insert temporary log statements
3. **Check Mock Calls**: Verify mock.assert_called_with()
4. **Isolate Tests**: Run single test methods

#### Integration Test Debugging
1. **Check API Responses**: Log actual API responses
2. **Verify Credentials**: Test credentials manually
3. **Monitor Rate Limits**: Check API usage
4. **Use Dry Run Mode**: Test logic without side effects

### Test Environment Reset

#### Clean Test State
```bash
# Reset Python cache
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reset test databases (if applicable)
rm -rf test_data/

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Environment Verification
```bash
# Verify Python environment
python --version
pip list

# Verify test files
python -m py_compile tests/test_github_jira_monitor.py
python -m py_compile tests/test_real_integration.py

# Quick test run
python tests/test_github_jira_monitor.py
```

---

This comprehensive test documentation provides everything needed to understand, execute, and maintain the dual-mode test framework for the GitHub JIRA Monitor project.
