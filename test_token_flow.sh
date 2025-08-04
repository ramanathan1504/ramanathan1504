#!/bin/bash
# Test Token Flow Locally
# This simulates what GitHub Actions does

echo "🧪 Testing Token Flow: YAML → Python"
echo "====================================="

# Step 1: Set environment variables (simulates GitHub Actions)
echo "Step 1: Setting environment variables..."
export GITHUB_TOKEN="your_github_token_here"
export JIRA_AUTH="your_base64_jira_auth_here"

# Step 2: Test Python script can read them
echo "Step 2: Testing Python script..."
cd scripts

# Run a simple test
python3 -c "
import os
print('✅ GITHUB_TOKEN found:', 'Yes' if os.environ.get('GITHUB_TOKEN') else 'No')
print('✅ JIRA_AUTH found:', 'Yes' if os.environ.get('JIRA_AUTH') else 'No')

# Test the monitor initialization
try:
    from github_jira_monitor import GitHubJIRAMonitor
    monitor = GitHubJIRAMonitor()
    print('✅ Monitor initialized successfully')
    print('✅ GitHub headers:', bool(monitor.get_github_headers()))
    print('✅ JIRA headers:', bool(monitor.get_jira_headers()))
except Exception as e:
    print('❌ Error:', e)
"

echo ""
echo "🔍 To use real tokens:"
echo "1. Replace 'your_github_token_here' with actual GitHub token"
echo "2. Replace 'your_base64_jira_auth_here' with actual JIRA auth"
echo "3. Run: ./test_token_flow.sh"
