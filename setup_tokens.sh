#!/bin/bash
# GitHub JIRA Monitor - Real Token Setup Script
# This script helps you set up environment variables for real integration testing

echo "🔧 GitHub JIRA Monitor - Real Token Setup"
echo "=========================================="
echo ""

# Function to read input securely
read_token() {
    local prompt="$1"
    local var_name="$2"
    echo -n "$prompt: "
    read -s token
    echo ""
    export $var_name="$token"
    echo "✓ $var_name set successfully"
}

# GitHub Token Setup
echo "1. GitHub Personal Access Token"
echo "   - Go to GitHub.com → Settings → Developer settings → Personal access tokens"
echo "   - Generate token with 'repo', 'user', 'notifications' scopes"
echo "   - Token should start with 'ghp_', 'github_pat_', or 'gho_'"
echo ""
read_token "Enter your GitHub token" "GITHUB_TOKEN"
echo ""

# JIRA Auth Setup
echo "2. JIRA Authentication"
echo "   - You need your JIRA email and API token"
echo "   - Get API token from: https://id.atlassian.com/manage-profile/security/api-tokens"
echo ""
echo -n "Enter your JIRA email: "
read jira_email
echo -n "Enter your JIRA API token: "
read -s jira_token
echo ""

# Create base64 encoded auth
jira_auth=$(echo -n "$jira_email:$jira_token" | base64)
export JIRA_AUTH="$jira_auth"
echo "✓ JIRA_AUTH created and set successfully"
echo ""

# Validate tokens
echo "3. Validating Tokens..."
echo "📊 Running token validation..."

# Test GitHub token
echo -n "Testing GitHub token... "
github_response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user)
if [ "$github_response" = "200" ]; then
    echo "✅ GitHub token valid"
else
    echo "❌ GitHub token invalid (HTTP $github_response)"
fi

# Test JIRA token
echo -n "Testing JIRA token... "
# Note: This would need the JIRA domain to test properly
echo "⚠️  JIRA validation requires domain configuration"

echo ""
echo "🚀 Environment Setup Complete!"
echo ""
echo "You can now run:"
echo "  python -m pytest tests/test_real_integration.py -v"
echo "  python tests/test_real_integration.py --quick"
echo ""
echo "Current environment:"
echo "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "  JIRA_AUTH: ${JIRA_AUTH:0:20}..."
