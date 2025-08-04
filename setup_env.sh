#!/bin/bash
# Setup Environment Variables for Real Integration Tests

echo "🔧 GitHub JIRA Monitor - Environment Setup"
echo "=========================================="

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env file from template..."
    cp .env .env.example 2>/dev/null || echo "No template found"
    echo "✅ Created .env file"
    echo ""
    echo "📋 Please edit .env file and add your tokens:"
    echo "   - GITHUB_TOKEN: Your GitHub personal access token"
    echo "   - JIRA_AUTH: Base64 encoded JIRA credentials"
    echo ""
    echo "🔗 Helpful links:"
    echo "   GitHub tokens: https://github.com/settings/tokens"
    echo "   JIRA API tokens: https://id.atlassian.com/manage-profile/security/api-tokens"
    exit 1
fi

echo "📄 Loading environment variables from $ENV_FILE..."

# Source the .env file
set -a  # automatically export all variables
source $ENV_FILE
set +a  # stop auto-export

# Validate required variables
MISSING_VARS=()

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "your_github_token_here" ]; then
    MISSING_VARS+=("GITHUB_TOKEN")
fi

if [ -z "$JIRA_AUTH" ] || [ "$JIRA_AUTH" = "your_base64_jira_auth_here" ]; then
    MISSING_VARS+=("JIRA_AUTH")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing or placeholder values for: ${MISSING_VARS[*]}"
    echo ""
    echo "📝 Please edit $ENV_FILE and set real values for:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "💡 After setting tokens, run this script again to validate"
    exit 1
fi

echo "✅ Environment variables loaded successfully"
echo ""

# Display configuration (masked)
echo "📊 Current Configuration:"
echo "   GitHub Token: ${GITHUB_TOKEN:0:10}...${GITHUB_TOKEN: -4}"
echo "   JIRA Auth: ${JIRA_AUTH:0:20}..."
echo "   JIRA Domain: ${JIRA_DOMAIN:-osscontribution.atlassian.net}"
echo "   JIRA Project: ${JIRA_PROJECT:-OT}"
echo ""

# Test token validation
echo "🧪 Testing token validation..."
export GITHUB_TOKEN JIRA_AUTH JIRA_DOMAIN JIRA_PROJECT

# Run token validator if available
if [ -f "token_validator.py" ]; then
    echo "🔍 Running token validator..."
    python3 token_validator.py
else
    echo "⚠️  Token validator not found, skipping validation"
fi

echo ""
echo "🚀 Environment setup complete!"
echo ""
echo "💡 To run real integration tests:"
echo "   source setup_env.sh && python -m pytest tests/test_real_integration.py -v"
echo ""
echo "💡 To run all tests:"
echo "   source setup_env.sh && python -m pytest tests/ -v"
