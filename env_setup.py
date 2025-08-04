#!/usr/bin/env python3
"""
Environment Setup Helper for GitHub JIRA Monitor
Helps encode JIRA credentials and validate token formats
"""

import os
import base64
import sys
from pathlib import Path

def load_env_file(env_path=".env"):
    """Load environment variables from .env file"""
    env_vars = {}
    
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def create_jira_auth(email, api_token):
    """Create base64 encoded JIRA auth string"""
    auth_string = f"{email}:{api_token}"
    base64_auth = base64.b64encode(auth_string.encode()).decode()
    return base64_auth

def validate_github_token(token):
    """Validate GitHub token format"""
    if not token or token == "your_github_token_here":
        return False, "Token not set"
    
    valid_prefixes = ['ghp_', 'github_pat_', 'gho_', 'ghs_', 'ghu_']
    
    if not any(token.startswith(prefix) for prefix in valid_prefixes):
        return False, f"Invalid format. Expected prefixes: {', '.join(valid_prefixes)}"
    
    if len(token) < 20:
        return False, "Token too short"
    
    return True, "Valid format"

def validate_jira_auth(jira_auth):
    """Validate JIRA auth format"""
    if not jira_auth or jira_auth == "your_base64_jira_auth_here":
        return False, "JIRA auth not set"
    
    try:
        decoded = base64.b64decode(jira_auth).decode('utf-8')
        if ':' not in decoded:
            return False, "Invalid format. Should be base64(email:token)"
        
        email, token = decoded.split(':', 1)
        if '@' not in email:
            return False, "Invalid email format in decoded auth"
        
        if len(token) < 10:
            return False, "API token too short"
        
        return True, f"Valid format (email: {email})"
    
    except Exception as e:
        return False, f"Base64 decode error: {e}"

def update_env_file(env_path=".env", updates=None):
    """Update .env file with new values"""
    if updates is None:
        updates = {}
    
    # Read existing content
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Update lines
    updated_keys = set()
    for i, line in enumerate(lines):
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=', 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}\n"
                updated_keys.add(key)
    
    # Add new keys
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)

def interactive_setup():
    """Interactive environment setup"""
    print("🔧 GitHub JIRA Monitor - Interactive Environment Setup")
    print("=" * 60)
    print()
    
    # Load existing values
    env_vars = load_env_file()
    
    # GitHub Token
    print("📝 GitHub Token Setup")
    print("Get your token from: https://github.com/settings/tokens")
    print("Required scopes: repo, user, notifications")
    print()
    
    current_github = env_vars.get('GITHUB_TOKEN', '')
    if current_github and current_github != 'your_github_token_here':
        print(f"Current token: {current_github[:10]}...{current_github[-4:]}")
        use_current = input("Use current token? (y/n): ").lower().strip()
        if use_current == 'y':
            github_token = current_github
        else:
            github_token = input("Enter new GitHub token: ").strip()
    else:
        github_token = input("Enter GitHub token: ").strip()
    
    # Validate GitHub token
    valid, msg = validate_github_token(github_token)
    if valid:
        print(f"✅ GitHub token: {msg}")
    else:
        print(f"⚠️  GitHub token: {msg}")
    
    print()
    
    # JIRA Setup
    print("📝 JIRA Setup")
    print("Get API token from: https://id.atlassian.com/manage-profile/security/api-tokens")
    print()
    
    current_jira = env_vars.get('JIRA_AUTH', '')
    if current_jira and current_jira != 'your_base64_jira_auth_here':
        valid_jira, jira_msg = validate_jira_auth(current_jira)
        if valid_jira:
            print(f"Current JIRA auth: {jira_msg}")
            use_current = input("Use current JIRA auth? (y/n): ").lower().strip()
            if use_current == 'y':
                jira_auth = current_jira
            else:
                jira_auth = None
        else:
            print(f"Current JIRA auth invalid: {jira_msg}")
            jira_auth = None
    else:
        jira_auth = None
    
    if jira_auth is None:
        jira_email = input("Enter JIRA email: ").strip()
        jira_token = input("Enter JIRA API token: ").strip()
        jira_auth = create_jira_auth(jira_email, jira_token)
        print(f"Generated JIRA auth: {jira_auth[:20]}...")
    
    # Validate JIRA auth
    valid, msg = validate_jira_auth(jira_auth)
    if valid:
        print(f"✅ JIRA auth: {msg}")
    else:
        print(f"⚠️  JIRA auth: {msg}")
    
    print()
    
    # JIRA Domain and Project
    jira_domain = env_vars.get('JIRA_DOMAIN', 'osscontribution.atlassian.net')
    jira_project = env_vars.get('JIRA_PROJECT', 'OT')
    
    print(f"JIRA Domain [{jira_domain}]: ", end="")
    new_domain = input().strip()
    if new_domain:
        jira_domain = new_domain
    
    print(f"JIRA Project [{jira_project}]: ", end="")
    new_project = input().strip()
    if new_project:
        jira_project = new_project
    
    print()
    
    # Save to .env file
    updates = {
        'GITHUB_TOKEN': github_token,
        'JIRA_AUTH': jira_auth,
        'JIRA_DOMAIN': jira_domain,
        'JIRA_PROJECT': jira_project
    }
    
    update_env_file('.env', updates)
    print("✅ Environment configuration saved to .env")
    print()
    
    # Set environment variables for current session
    for key, value in updates.items():
        os.environ[key] = value
    
    print("🧪 Testing token validation...")
    
    # Test tokens if token_validator is available
    try:
        from token_validator import test_github_token, test_jira_auth
        
        print("Testing GitHub token...")
        github_ok = test_github_token(github_token)
        
        print("\nTesting JIRA auth...")
        jira_ok = test_jira_auth(jira_auth, jira_domain)
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print("=" * 50)
        print(f"GitHub Token: {'✅ VALID' if github_ok else '❌ INVALID'}")
        print(f"JIRA Auth: {'✅ VALID' if jira_ok else '❌ INVALID'}")
        
        if github_ok and jira_ok:
            print("\n🎉 All tokens are working!")
            print("\n🚀 Ready to run real integration tests:")
            print("   source .env && python -m pytest tests/test_real_integration.py -v")
        else:
            print("\n❌ Some tokens need to be fixed")
            
    except ImportError:
        print("⚠️  Token validator not available, skipping validation")
    
    print()

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Usage:")
        print("  python env_setup.py                 # Interactive setup")
        print("  python env_setup.py --validate      # Validate existing tokens")
        print("  python env_setup.py --create-jira   # Create JIRA auth only")
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == '--validate':
        # Validate existing environment
        env_vars = load_env_file()
        
        print("🔍 Validating existing environment...")
        print()
        
        github_valid, github_msg = validate_github_token(env_vars.get('GITHUB_TOKEN'))
        jira_valid, jira_msg = validate_jira_auth(env_vars.get('JIRA_AUTH'))
        
        print(f"GitHub Token: {'✅' if github_valid else '❌'} {github_msg}")
        print(f"JIRA Auth: {'✅' if jira_valid else '❌'} {jira_msg}")
        print()
        
        if github_valid and jira_valid:
            print("🎉 All tokens are valid!")
        else:
            print("❌ Some tokens need attention. Run without arguments for interactive setup.")
    
    elif len(sys.argv) > 1 and sys.argv[1] == '--create-jira':
        # Create JIRA auth only
        print("🔧 JIRA Auth Creator")
        print("=" * 30)
        
        email = input("JIRA Email: ").strip()
        token = input("JIRA API Token: ").strip()
        
        if email and token:
            jira_auth = create_jira_auth(email, token)
            print(f"\nGenerated JIRA_AUTH:")
            print(jira_auth)
            print(f"\nAdd this to your .env file:")
            print(f"JIRA_AUTH={jira_auth}")
        else:
            print("❌ Email and token required")
    
    else:
        # Interactive setup
        interactive_setup()

if __name__ == "__main__":
    main()
