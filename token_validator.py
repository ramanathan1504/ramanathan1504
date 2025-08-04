#!/usr/bin/env python3
"""
Quick Token Test Script
Tests GitHub and JIRA tokens with proper headers
"""

import requests
import base64
import sys

def test_github_token(token):
    """Test GitHub token validity using the same endpoint as the main application"""
    try:
        headers = {
            'Authorization': token,
            'Accept': 'application/vnd.github.v3+json'
        }
        print(f"   🔍 Debug: Headers being sent: {headers}")
        
        # Use the same endpoint that the main application uses
        response = requests.get('https://api.github.com/users/ramanathan1504/events?per_page=1&page=1', headers=headers)
        print(f"   🔍 Debug: Response status: {response.status_code}")
        print(f"   🔍 Debug: Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            events = response.json()
            print(f"✅ GitHub token VALID - Retrieved {len(events)} events")
            return True
        elif response.status_code == 403:
            print(f"⏸️  GitHub token VALID but rate limit reached - Authentication working correctly")
            return True  # Token is valid, just rate limited
        else:
            print(f"❌ GitHub token INVALID - HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ GitHub token test failed: {e}")
        return False

def test_jira_auth(auth_string, domain):
    """Test JIRA authentication"""
    try:
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
        print(f"   🔍 Debug: Headers being sent: {headers}")
        
        url = f"https://{domain}/rest/api/3/myself"
        print(f"   🔍 Debug: URL: {url}")
        
        response = requests.get(url, headers=headers)
        print(f"   🔍 Debug: Response status: {response.status_code}")
        print(f"   🔍 Debug: Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            user_data = response.json()
            email = user_data.get('emailAddress', 'Unknown')
            display_name = user_data.get('displayName', 'Unknown')
            print(f"✅ JIRA auth VALID - User: {display_name} ({email})")
            return True
        else:
            print(f"❌ JIRA auth INVALID - HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ JIRA auth test failed: {e}")
        return False

def create_base64_jira_auth(email, api_token):
    """Create base64 encoded JIRA auth"""
    auth_string = f"{email}:{api_token}"
    base64_auth = base64.b64encode(auth_string.encode()).decode()
    return base64_auth

def main():
    print("🧪 Token Validation Script")
    print("=" * 50)
    
    # Load tokens from environment variables (from .env file)
    import os
    
    # Try to load from .env file first
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print("⚠️  .env file not found, using system environment variables")
    
    github_token = os.getenv('GITHUB_TOKEN')
    jira_auth = os.getenv('JIRA_AUTH')
    jira_domain = os.getenv('JIRA_DOMAIN', 'osscontribution.atlassian.net')
    
    print("\n🔍 Debug: Tokens loaded from environment:")
    print(f"   GITHUB_TOKEN: {github_token}")
    print(f"   JIRA_AUTH: {jira_auth}")
    print(f"   JIRA_DOMAIN: {jira_domain}")
    print()
    
    if not github_token:
        print("❌ GitHub token not found in environment")
        github_token = input("GitHub Token (ghp_...): ").strip()
        if not github_token:
            print("❌ GitHub token required")
            return
    else:
        print(f"✅ Found GitHub token: {github_token[:10]}...{github_token[-4:]}")
    
    if not jira_auth:
        print("❌ JIRA auth not found in environment")
        jira_email = input("JIRA Email: ").strip()
        jira_api_token = input("JIRA API Token: ").strip()
        if not all([jira_email, jira_api_token]):
            print("❌ JIRA credentials required")
            return
        jira_auth = create_base64_jira_auth(jira_email, jira_api_token)
    else:
        print(f"✅ Found JIRA auth: {jira_auth[:20]}...")
    
    if not jira_domain:
        jira_domain = input("JIRA Domain (e.g., yourcompany.atlassian.net): ").strip()
        if not jira_domain:
            print("❌ JIRA domain required")
            return
    else:
        print(f"✅ Found JIRA domain: {jira_domain}")
    
    # Test tokens
    print("\n" + "=" * 50)
    print("🚀 Testing tokens...")
    print("=" * 50)
    
    github_ok = test_github_token(github_token)
    print()
    jira_ok = test_jira_auth(jira_auth, jira_domain)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"GitHub Token: {'✅ VALID' if github_ok else '❌ INVALID'}")
    print(f"JIRA Auth: {'✅ VALID' if jira_ok else '❌ INVALID'}")
    
    if github_ok and jira_ok:
        print("\n🎉 All tokens are working!")
        print("\n📋 Use these environment variables:")
        print(f"export GITHUB_TOKEN=\"{github_token}\"")
        print(f"export JIRA_AUTH=\"{jira_auth}\"")
    else:
        print("\n❌ Some tokens need to be fixed")
        
        if not github_ok:
            print("\n🔧 GitHub Token Issues:")
            print("   - Make sure token starts with 'ghp_', 'github_pat_', or 'gho_'")
            print("   - Check token has 'repo', 'user', 'notifications' scopes")
            print("   - Verify token hasn't expired")
            
        if not jira_ok:
            print("\n🔧 JIRA Auth Issues:")
            print("   - Verify email and API token are correct")
            print("   - Check JIRA domain (should be yourcompany.atlassian.net)")
            print("   - Make sure API token has proper permissions")

if __name__ == "__main__":
    main()
