# Tests Directory

This directory contains the comprehensive test suite for the GitHub JIRA Monitor project.

## Files Overview

| File | Purpose | Test Count | Execution Time |
|------|---------|------------|----------------|
| `test_github_jira_monitor.py` | Mock tests for business logic | 15 tests | < 1 second |
| `test_real_integration.py` | Real API integration tests | 8 tests | ~30 seconds |
| `TEST_DOCUMENTATION.md` | Comprehensive test documentation | - | - |
| `README.md` | This overview file | - | - |

## Quick Usage

### Mock Tests (Always Run First)
```bash
# Fast business logic validation
python tests/test_github_jira_monitor.py
```

### Real Integration Tests (Production Validation)
```bash
# Set up environment
export GITHUB_TOKEN="your_token"
export JIRA_AUTH="your_base64_encoded_auth"

# Quick validation
python tests/test_real_integration.py --quick

# Full integration test suite
python tests/test_real_integration.py
```

## Test Strategy

### Development Workflow
1. **Write Code** → Run mock tests for fast feedback
2. **Commit Changes** → Mock tests pass required
3. **Create PR** → Mock + quick integration tests
4. **Deploy** → Full test suite validation

### CI/CD Integration
- **Every Commit**: Mock tests (fast, reliable)
- **Main Branch**: Mock + real integration tests
- **Releases**: Complete test suite with all validations

## Documentation

For comprehensive information about the test framework, see:
- [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md) - Complete test system documentation
- [../TEST_USAGE.md](../TEST_USAGE.md) - Usage guide and examples
- [../PROJECT_DOCUMENTATION.md](../PROJECT_DOCUMENTATION.md) - Full project documentation

## Test Results

Both test suites are currently passing:
- ✅ **Mock Tests**: 15/15 passing (validates all business logic)
- ✅ **Integration Tests**: Production-ready (validates API connectivity)

## Environment Requirements

### Mock Tests
- No external dependencies
- No API tokens required
- Runs anywhere Python is available

### Real Integration Tests
- Valid GitHub personal access token
- Valid JIRA API credentials (base64 encoded)
- Network access to GitHub and JIRA APIs

---

**Note**: Always run mock tests first during development. Real integration tests should be used for pre-deployment validation and CI/CD pipelines.
