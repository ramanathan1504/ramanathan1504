# GitHub JIRA Monitor - Token Setup Guide

## 🔑 Getting Your GitHub Personal Access Token

### 1. Create GitHub Personal Access Token
1. Go to **GitHub.com** → Click your profile picture → **Settings**
2. Scroll down to **Developer settings** (left sidebar)
3. Click **Personal access tokens** → **Tokens (classic)**
4. Click **Generate new token** → **Generate new token (classic)**

### 2. Configure Token Permissions
Select these scopes:
- ✅ **repo** (Full control of private repositories)
  - repo:status
  - repo_deployment
  - public_repo
- ✅ **user** (Read user information)
  - user:email
- ✅ **notifications** (Access notifications)

### 3. Token Format
Your token will start with:
- `ghp_` (Personal access token)
- `github_pat_` (Fine-grained personal access token)
- `gho_` (OAuth token)

**Example:** `ghp_1234567890abcdef1234567890abcdef12345678`

### 4. Copy and Save Token
⚠️ **IMPORTANT:** Copy the token immediately - you won't see it again!

---

## 🏢 Getting Your JIRA API Token

### 1. Create JIRA API Token
1. Go to **https://id.atlassian.com/manage-profile/security/api-tokens**
2. Click **Create API token**
3. Give it a label (e.g., "GitHub Integration")
4. Copy the generated token

### 2. Create Base64 Encoded Auth
You need to encode your JIRA email and API token:

```bash
# Format: email:api_token
echo -n "your-email@domain.com:your-jira-api-token" | base64
```

**Example:**
```bash
echo -n "john@company.com:ATATT3xFfGF0..." | base64
# Output: am9obkBjb21wYW55LmNvbTpBVEFUVDN4RmZHRjA...
```

---

## 🔧 Setting Up GitHub Repository Secrets

### 1. Navigate to Repository Settings
1. Go to your repository: `https://github.com/ramanathan1504/ramanathan1504`
2. Click **Settings** tab (top of repository)
3. Click **Secrets and variables** → **Actions** (left sidebar)

### 2. Add Repository Secrets
Click **New repository secret** for each:

#### Secret 1: GH_TOKEN
- **Name:** `GH_TOKEN`
- **Value:** Your GitHub personal access token (e.g., `ghp_1234...`)

#### Secret 2: JIRA_AUTH
- **Name:** `JIRA_AUTH`  
- **Value:** Your base64 encoded JIRA auth (e.g., `am9obkBjb21wYW55...`)

---

## 🚀 Testing Your Setup

### Option 1: Run GitHub Actions Workflow
1. Go to **Actions** tab in your repository
2. Click **One-Time GitHub JIRA Migration**
3. Click **Run workflow**
4. Set **dry_run** to `true`
5. Choose operation: `migrate`
6. Click **Run workflow**

### Option 2: Test Locally
```bash
# Set environment variables
export GITHUB_TOKEN="your_github_token_here"
export JIRA_AUTH="your_base64_jira_auth_here"

# Test the monitor
cd scripts
python github_jira_monitor.py migrate --max-pages 1 --dry-run
```

---

## 🔍 Troubleshooting

### GitHub Token Issues
- **401 Unauthorized:** Token is invalid or expired
- **403 Forbidden:** Token doesn't have required permissions
- **404 Not Found:** Repository access denied

### JIRA Auth Issues
- **401 Unauthorized:** Email/token combination is wrong
- **Incorrect padding:** Base64 encoding is malformed

### Quick Validation Commands
```bash
# Test GitHub token
curl -H "Authorization: token YOUR_GITHUB_TOKEN" https://api.github.com/user

# Test JIRA auth (replace DOMAIN with your JIRA domain)
curl -H "Authorization: Basic YOUR_BASE64_JIRA_AUTH" https://YOUR_DOMAIN.atlassian.net/rest/api/3/myself
```

---

## 📋 Environment Variables Summary

Your workflow needs these exact secret names:
- `GH_TOKEN` → Your GitHub personal access token
- `JIRA_AUTH` → Base64 encoded `email:api_token`

The workflow will automatically use them as:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
  JIRA_AUTH: ${{ secrets.JIRA_AUTH }}
```
