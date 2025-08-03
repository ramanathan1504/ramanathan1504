# Test Usage Guide

## Quick Start

The GitHub JIRA Monitor uses a **dual-mode test framework** for comprehensive validation:

### Mock Tests (Development & CI/CD)
Fast tests with no external dependencies:
```bash
python tests/test_github_jira_monitor.py           # Run all 15 mock tests
python tests/test_github_jira_monitor.py --verbose # Verbose output
```

### Real Integration Tests (Production Validation)
Tests with actual GitHub/JIRA APIs:
```bash
# Set up environment first
export GITHUB_TOKEN="your_github_token"
export JIRA_AUTH="your_base64_encoded_credentials"

python tests/test_real_integration.py              # Full integration tests
python tests/test_real_integration.py --quick      # Quick validation only
python tests/test_real_integration.py --verbose    # Verbose output
```

## Test Architecture

```
tests/
├── test_github_jira_monitor.py     # Mock tests (15 tests, <1s execution)
├── test_real_integration.py        # Real tests (8 tests, ~30s execution)
├── TEST_DOCUMENTATION.md           # Comprehensive test documentation
└── README.md                       # This file
```

## When to Use Each Test Type

| Scenario | Mock Tests | Real Tests |
|----------|------------|------------|
| Local development | ✅ Always | ❌ Not needed |
| Pull requests | ✅ Required | ✅ Quick mode |
| Pre-deployment | ✅ Required | ✅ Full suite |
| CI/CD pipelines | ✅ Every build | ✅ Main branch only |

## Environment Setup

### For Mock Tests (No setup required)
Mock tests run with simulated data and require no external credentials.

### For Real Integration Tests

1. **GitHub Token**:
   ```bash
   # Go to GitHub Settings → Developer settings → Personal access tokens
   export GITHUB_TOKEN="ghp_your_token_here"
   ```

2. **JIRA Authentication**:
   ```bash
   # Get JIRA API token from Account Settings → Security → API tokens
   # Encode email:token to base64
   echo -n "your.email@domain.com:your_api_token" | base64
   export JIRA_AUTH="encoded_result_here"
   ```

3. **Verification**:
   ```bash
   python tests/test_real_integration.py --quick
   ```

## Test Execution Examples

### Development Workflow
```bash
# During active development
python tests/test_github_jira_monitor.py

# Before committing changes
python tests/test_github_jira_monitor.py --verbose
```

### Pre-deployment Validation
```bash
# Complete validation
python tests/test_github_jira_monitor.py --verbose
python tests/test_real_integration.py --verbose
```

### CI/CD Integration
```bash
# In GitHub Actions (mock tests always run)
python tests/test_github_jira_monitor.py

# Integration tests (with secrets)
python tests/test_real_integration.py --quick
```
- ✅ Success/error indicators
- ✅ Progress tracking
- ✅ Detailed error reporting

### Mock Tests Include
- ✅ Monitor initialization with mocked APIs
- ✅ GitHub issue processing simulation
- ✅ GitHub PR processing simulation
- ✅ Error handling scenarios

### Real Tests Include
- ✅ Actual GitHub API connectivity
- ✅ Actual JIRA API connectivity
- ✅ Repository access validation
- ✅ Project permissions verification

## Environment Variables

For real integration tests, you need these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | `ghp_xxxxxxxxxxxx` |
| `JIRA_URL` | JIRA server URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | JIRA user email | `user@company.com` |
| `JIRA_TOKEN` | JIRA API token | `xxxxxxxxxxxx` |
| `GITHUB_REPO` | GitHub repository | `owner/repo` |

## Workflow Integration

### In GitHub Actions
```yaml
# Mock tests (always run)
- name: Run Mock Tests
  run: python3 tests/test_github_jira_monitor.py --mock --verbose

# Real tests (only with secrets)
- name: Run Integration Tests
  if: env.GITHUB_TOKEN != ''
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    JIRA_URL: ${{ secrets.JIRA_URL }}
    JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
    JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
    GITHUB_REPO: ${{ github.repository }}
  run: python3 tests/test_github_jira_monitor.py --real --verbose
```

## Exit Codes
- `0` - All tests passed
- `1` - Some tests failed
- Tests are skipped (not failed) when environment variables are missing

## Example Output

### Mock Tests
```
============================================================
  GitHub JIRA Monitor Test Suite - MOCK Mode
============================================================
[INFO 2025-01-08 10:00:00] Test mode: mock
[INFO 2025-01-08 10:00:00] Verbose: True
[TEST 2025-01-08 10:00:01] Setting up mock test environment
[SUCCESS 2025-01-08 10:00:01] ✓ Mock environment variables configured
[TEST 2025-01-08 10:00:01] Testing monitor initialization with mocks
[SUCCESS 2025-01-08 10:00:01] ✓ Monitor initialized successfully
```

### Real Tests
```
============================================================
  GitHub JIRA Monitor Test Suite - REAL Mode
============================================================
[INFO 2025-01-08 10:00:00] Test mode: real
[INFO 2025-01-08 10:00:00] Checking environment for real tests...
[SUCCESS 2025-01-08 10:00:00] ✓ All required environment variables found
[TEST 2025-01-08 10:00:01] Testing real GitHub API connection
[SUCCESS 2025-01-08 10:00:02] ✓ Successfully connected to GitHub repository: my-repo
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `scripts/github_jira_monitor.py` exists
2. **Missing Tokens**: Real tests will be skipped if environment variables are missing
3. **Invalid Tokens**: Tests will fail with authentication errors if tokens are invalid
4. **Rate Limits**: Real tests limit API calls to avoid GitHub/JIRA rate limits

### Getting Help
```bash
python3 tests/test_github_jira_monitor.py --help
```
