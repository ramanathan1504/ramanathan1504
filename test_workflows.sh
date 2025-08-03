#!/bin/bash

# GitHub to JIRA Workflows Test Script
# Tests all workflows with dry runs first, then real execution

set -e  # Exit on any error

echo "🚀 GitHub to JIRA Workflows Test"
echo "================================="
echo "Timestamp: $(date)"
echo ""

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q requests

# Check environment variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$JIRA_AUTH" ]; then
    echo "❌ Missing required environment variables!"
    echo "Please set GITHUB_TOKEN and JIRA_AUTH"
    exit 1
fi

echo "✅ Environment setup complete"
echo "GitHub Token: ${GITHUB_TOKEN:0:10}..."
echo "JIRA Auth: ${JIRA_AUTH:0:20}..."
echo ""

# Function to run command with confirmation
run_test() {
    local description="$1"
    local command="$2"
    local is_dry_run="$3"
    
    if [ "$is_dry_run" = "true" ]; then
        echo "🧪 DRY RUN: $description"
    else
        echo "🔴 REAL RUN: $description"
    fi
    
    echo "Command: $command"
    read -p "Press Enter to continue or Ctrl+C to skip... "
    
    echo "🏃 Running..."
    eval "$command"
    echo "✅ Completed"
    echo ""
}

echo "=== PHASE 1: DRY RUN TESTS ==="
echo ""

# 1. Monitor Test (Dry Run)
run_test \
    "Monitor Workflow Test (60 minutes)" \
    "python scripts/github_jira_monitor.py monitor --since-minutes 60 --dry-run" \
    true

# 2. PR Migration Test (Dry Run)
run_test \
    "PR Migration Test (5 PRs per repo)" \
    "python scripts/github_jira_monitor.py pr-migrate --limit 5 --dry-run" \
    true

# 3. Specific Issues Test (Dry Run)
run_test \
    "Specific Issues Test (missing contributions)" \
    "python scripts/github_jira_monitor.py old-issue --issues kubernetes/kubernetes#1650,jreleaser/jreleaser#1933,jreleaser/jreleaser#1939 --dry-run" \
    true

# 4. Migration Test (Dry Run)
run_test \
    "Historical Migration Test (3 pages)" \
    "python scripts/github_jira_monitor.py migrate --max-pages 3 --dry-run" \
    true

echo "=== PHASE 2: REAL EXECUTION ==="
echo ""

# Ask for confirmation to proceed with real runs
echo "🔴 WARNING: The following commands will create real JIRA tasks!"
read -p "Continue with real execution? (y/N): " proceed
if [[ ! $proceed =~ ^[Yy]$ ]]; then
    echo "Stopped. Dry run tests completed successfully."
    exit 0
fi

# 1. Monitor Real
run_test \
    "Monitor Workflow (60 minutes)" \
    "python scripts/github_jira_monitor.py monitor --since-minutes 60" \
    false

# 2. PR Migration Real
run_test \
    "PR Migration (10 PRs per repo)" \
    "python scripts/github_jira_monitor.py pr-migrate --limit 10" \
    false

# 3. Specific Issues Real
run_test \
    "Specific Issues (missing contributions)" \
    "python scripts/github_jira_monitor.py old-issue --issues kubernetes/kubernetes#1650,jreleaser/jreleaser#1933,jreleaser/jreleaser#1939" \
    false

# Optional: Full Migration
echo "📋 Optional: Full Historical Migration"
read -p "Run full migration (5 pages)? (y/N): " run_full
if [[ $run_full =~ ^[Yy]$ ]]; then
    run_test \
        "Full Historical Migration (5 pages)" \
        "python scripts/github_jira_monitor.py migrate --max-pages 5" \
        false
fi

echo "🎉 All tests completed!"
echo "======================="
echo ""
echo "Summary:"
echo "✅ Environment validated"
echo "✅ Dry run tests passed"
echo "✅ Real workflows executed"
echo ""
echo "Expected Results:"
echo "- No duplicate JIRA tasks"
echo "- Proper Kanban organization"
echo "- Clean labeling (owner + repo)"
echo "- Complete contribution coverage"
echo "- Authored PRs/issues processed (even without comments)"
echo "- Smart content detection (comments vs authorship)"
echo ""
echo "Check JIRA: https://osscontribution.atlassian.net/projects/OT"
echo "Timestamp: $(date)"
