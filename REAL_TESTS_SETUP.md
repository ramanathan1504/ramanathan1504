# Real Integration Tests Setup Guide

This guide helps you set up real tokens for running integration tests that connect to actual GitHub and JIRA APIs.

## Quick Setup

### Option 1: Interactive Setup (Recommended)
```bash
python3 env_setup.py
```
This will guide you through setting up your tokens interactively.

### Option 2: Manual Setup
1. Copy the `.env` file and edit it:
```bash
cp .env .env.local
# Edit .env with your real tokens
```

2. Load and test environment:
```bash
source setup_env.sh
```

## Getting Your Tokens

### GitHub Token
1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `user`, `notifications`
4. Copy the token (starts with `ghp_`)

### JIRA API Token
1. Go to [Atlassian Account Security](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Copy the token
4. Encode as base64: `base64("your-email@domain.com:your-api-token")`

Or use the helper:
```bash
python3 env_setup.py --create-jira
```

## Environment Variables

Set these in your `.env` file:

```bash
# GitHub Personal Access Token
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# JIRA Auth (base64 encoded email:token)
JIRA_AUTH=dGVzdEBleGFtcGxlLmNvbTp5b3VyX2FwaV90b2tlbl9oZXJl

# JIRA Configuration
JIRA_DOMAIN=osscontribution.atlassian.net
JIRA_PROJECT=OT
```

## Running Tests

### Validate Tokens First
```bash
python3 token_validator.py
```

### Run Real Integration Tests
```bash
# Load environment and run specific real tests
source .env && python -m pytest tests/test_real_integration.py -v

# Run all tests (including mocked ones)
source .env && python -m pytest tests/ -v

# Run only the tests that failed before
source .env && python -m pytest tests/test_real_integration.py::RealIntegrationTestCase::test_real_github_api_connectivity -v
source .env && python -m pytest tests/test_real_integration.py::RealIntegrationTestCase::test_real_jira_api_connectivity -v
```

### Quick Validation
```bash
source .env && python -m pytest tests/test_real_integration.py::QuickValidationTestCase::test_quick_environment_check -v
```

## Expected Results

After setting up real tokens, these previously failing tests should pass:

1. ✅ `test_real_github_api_connectivity` - Tests GitHub API authentication
2. ✅ `test_real_jira_api_connectivity` - Tests JIRA API authentication  
3. ✅ `test_real_jira_project_access` - Tests JIRA project permissions

The other 33 tests should continue to pass as they work with both mock and real data.

## Troubleshooting

### GitHub 401 Unauthorized
- Check token format (should start with `ghp_`, `github_pat_`, etc.)
- Verify token has required scopes: `repo`, `user`, `notifications`
- Make sure token hasn't expired

### JIRA Authentication Issues
- Verify base64 encoding: `echo "email:token" | base64`
- Check domain format: `yourcompany.atlassian.net` (no https://)
- Ensure API token has proper permissions
- Test with: `curl -u email:token https://yourcompany.atlassian.net/rest/api/3/myself`

### Base64 Padding Errors
```bash
# Fix padding if needed
python3 -c "import base64; print(base64.b64encode(b'email:token').decode())"
```

## Security Notes

- ⚠️  **Never commit real tokens to git**
- ✅ `.env` is already in `.gitignore`
- ✅ Use environment variables in CI/CD
- ✅ Rotate tokens regularly
- ✅ Use minimal required scopes

## Files Created

- `.env` - Environment variables (add your real tokens here)
- `env_setup.py` - Interactive setup helper
- `setup_env.sh` - Shell script to load and validate environment
- This guide - `REAL_TESTS_SETUP.md`
