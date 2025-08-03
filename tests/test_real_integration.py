#!/usr/bin/env python3
"""
Real Integration Tests for GitHub JIRA Monitor
Uses actual GitHub/JIRA tokens for production validation

Requirements:
- GITHUB_TOKEN: GitHub personal access token
- JIRA_AUTH: Base64 encoded JIRA credentials (user:token)

Usage:
    python test_real_integration.py                    # Run all real tests
    python test_real_integration.py --verbose          # Run with verbose output
    python test_real_integration.py --quick            # Run quick validation only
"""

import unittest
import sys
import os
import argparse
from datetime import datetime

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    from github_jira_monitor import GitHubJIRAMonitor
except ImportError as e:
    print(f"ERROR: Failed to import GitHubJIRAMonitor: {e}")
    print("Make sure the scripts/github_jira_monitor.py file exists")
    sys.exit(1)

# Enhanced logging functions for better test visibility
def log_test(message):
    """Log test information with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[TEST {timestamp}] {message}")

def log_info(message):
    """Log informational message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO {timestamp}] {message}")

def log_success(message):
    """Log success message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SUCCESS {timestamp}] ✓ {message}")

def log_error(message):
    """Log error message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR {timestamp}] ✗ {message}")

def log_warning(message):
    """Log warning message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WARNING {timestamp}] ⚠ {message}")

def log_section(section_name):
    """Log section separator"""
    print(f"\n{'='*70}")
    print(f"  {section_name}")
    print(f"{'='*70}")

class RealIntegrationTestCase(unittest.TestCase):
    """Real integration tests - Uses actual GitHub/JIRA tokens"""
    
    def setUp(self):
        """Set up real test environment with actual tokens"""
        log_test("Setting up real integration test environment")
        
        # Check for required environment variables
        required_vars = ['GITHUB_TOKEN', 'JIRA_AUTH']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            log_error(f"Missing required environment variables: {', '.join(missing_vars)}")
            self.skipTest(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        log_info("All required environment variables found")
        
        # Validate token format (basic check)
        github_token = os.getenv('GITHUB_TOKEN')
        jira_auth = os.getenv('JIRA_AUTH')
        
        if not github_token.startswith(('ghp_', 'github_pat_', 'gho_')):
            log_warning("GitHub token format may be invalid (expected to start with ghp_, github_pat_, or gho_)")
        
        if len(jira_auth) < 10:
            log_error("JIRA auth appears too short")
            self.skipTest("JIRA auth appears too short")
        
        log_success("Real integration test environment validated")

    def test_real_monitor_initialization(self):
        """Test monitor initialization with real environment"""
        log_test("Testing monitor initialization with real environment")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Verify initialization
            self.assertIsNotNone(monitor)
            self.assertIsNotNone(monitor.github_token)
            self.assertIsNotNone(monitor.jira_auth)
            
            log_success("Monitor initialized successfully with real environment")
            log_info(f"GitHub user: {monitor.github_user}")
            log_info(f"JIRA domain: {monitor.jira_domain}")
            log_info(f"JIRA project: {monitor.jira_project}")
            log_info(f"Skip organizations: {', '.join(monitor.skip_orgs)}")
            
        except Exception as e:
            log_error(f"Monitor initialization failed: {e}")
            self.fail(f"Monitor initialization test failed: {e}")

    def test_real_github_api_connectivity(self):
        """Test GitHub API connectivity and authentication"""
        log_test("Testing GitHub API connectivity")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Test basic GitHub API call
            log_info("Testing GitHub API authentication...")
            import requests
            
            headers = {'Authorization': f'token {monitor.github_token}'}
            response = requests.get('https://api.github.com/user', headers=headers)
            
            self.assertEqual(response.status_code, 200)
            user_data = response.json()
            
            log_success("GitHub API authentication successful")
            log_info(f"Authenticated as: {user_data.get('login')}")
            log_info(f"User type: {user_data.get('type')}")
            log_info(f"API rate limit remaining: {response.headers.get('X-RateLimit-Remaining')}")
            
        except Exception as e:
            log_error(f"GitHub API connectivity test failed: {e}")
            self.fail(f"GitHub API connectivity test failed: {e}")

    def test_real_jira_api_connectivity(self):
        """Test JIRA API connectivity and authentication"""
        log_test("Testing JIRA API connectivity")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Test basic JIRA API call
            log_info("Testing JIRA API authentication...")
            import requests
            import base64
            
            # Decode JIRA auth for testing
            auth_string = base64.b64decode(monitor.jira_auth).decode('utf-8')
            username, token = auth_string.split(':', 1)
            
            auth = (username, token)
            jira_url = f"https://{monitor.jira_domain}/rest/api/3/myself"
            
            response = requests.get(jira_url, auth=auth)
            
            self.assertEqual(response.status_code, 200)
            user_data = response.json()
            
            log_success("JIRA API authentication successful")
            log_info(f"Authenticated as: {user_data.get('displayName')}")
            log_info(f"Email: {user_data.get('emailAddress')}")
            log_info(f"Account ID: {user_data.get('accountId')}")
            
        except Exception as e:
            log_error(f"JIRA API connectivity test failed: {e}")
            self.fail(f"JIRA API connectivity test failed: {e}")

    def test_real_github_events_fetch(self):
        """Test fetching real GitHub events"""
        log_test("Testing real GitHub events fetch")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Fetch limited events to avoid rate limits
            log_info("Fetching recent GitHub events (limited to 1 page)")
            events = monitor.fetch_github_events(max_pages=1)
            
            self.assertIsInstance(events, list)
            log_success(f"Successfully fetched {len(events)} GitHub events")
            
            if events:
                # Verify event structure
                sample_event = events[0]
                self.assertIn('type', sample_event)
                self.assertIn('created_at', sample_event)
                log_info(f"Sample event type: {sample_event.get('type')}")
                log_info(f"Sample event date: {sample_event.get('created_at')}")
                
                # Count event types
                event_types = {}
                for event in events[:10]:  # Check first 10 events
                    event_type = event.get('type')
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                
                log_info("Event type distribution:")
                for event_type, count in event_types.items():
                    log_info(f"  {event_type}: {count}")
            else:
                log_warning("No recent events found")
            
        except Exception as e:
            log_error(f"GitHub events fetch failed: {e}")
            self.fail(f"GitHub events fetch test failed: {e}")

    def test_real_github_events_filtering(self):
        """Test filtering real GitHub events"""
        log_test("Testing real GitHub events filtering")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Fetch and filter events
            log_info("Fetching and filtering GitHub events...")
            events = monitor.fetch_github_events(max_pages=1)
            
            comment_events = monitor.filter_comment_events(events)
            authorship_events = monitor.filter_authorship_events(events)
            
            log_success(f"Event filtering completed")
            log_info(f"Total events: {len(events)}")
            log_info(f"Comment events: {len(comment_events)}")
            log_info(f"Authorship events: {len(authorship_events)}")
            
            # Verify filtering logic
            for event in comment_events:
                self.assertIn(event['type'], ['IssueCommentEvent', 'PullRequestReviewCommentEvent'])
            
            if comment_events:
                log_info("Sample comment event types:")
                for event in comment_events[:3]:
                    log_info(f"  {event['type']} - {event.get('created_at')}")
            
        except Exception as e:
            log_error(f"GitHub events filtering failed: {e}")
            self.fail(f"GitHub events filtering test failed: {e}")

    def test_real_monitor_run_dry(self):
        """Test running monitor in dry run mode with real data"""
        log_test("Testing monitor run in dry mode with real data")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Run monitor in dry run mode for last 60 minutes
            log_info("Running monitor in dry run mode (last 60 minutes)")
            stats = monitor.run_monitor(since_minutes=60, dry_run=True)
            
            # Verify stats structure
            self.assertIsInstance(stats, dict)
            self.assertIn('total', stats)
            self.assertIn('processed', stats)
            self.assertIn('created', stats)
            self.assertIn('skipped', stats)
            self.assertIn('errors', stats)
            
            log_success("Monitor dry run completed successfully")
            log_info(f"Total events: {stats['total']}")
            log_info(f"Processed: {stats['processed']}")
            log_info(f"Would create: {stats['created']}")
            log_info(f"Skipped: {stats['skipped']}")
            log_info(f"Errors: {stats['errors']}")
            
            # Analyze results
            if stats['total'] > 0:
                processed_rate = (stats['processed'] / stats['total']) * 100
                log_info(f"Processing rate: {processed_rate:.1f}%")
            
            if stats['errors'] > 0:
                log_warning(f"Found {stats['errors']} errors during processing")
            
        except Exception as e:
            log_error(f"Monitor dry run failed: {e}")
            self.fail(f"Monitor dry run test failed: {e}")

    def test_real_jira_project_access(self):
        """Test JIRA project access and permissions"""
        log_test("Testing JIRA project access")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Test project access
            log_info(f"Testing access to JIRA project: {monitor.jira_project}")
            import requests
            import base64
            
            auth_string = base64.b64decode(monitor.jira_auth).decode('utf-8')
            username, token = auth_string.split(':', 1)
            auth = (username, token)
            
            # Get project details
            project_url = f"https://{monitor.jira_domain}/rest/api/3/project/{monitor.jira_project}"
            response = requests.get(project_url, auth=auth)
            
            self.assertEqual(response.status_code, 200)
            project_data = response.json()
            
            log_success("JIRA project access successful")
            log_info(f"Project name: {project_data.get('name')}")
            log_info(f"Project key: {project_data.get('key')}")
            log_info(f"Project type: {project_data.get('projectTypeKey')}")
            
            # Test issue creation permissions (dry run)
            log_info("Testing issue creation permissions...")
            createmeta_url = f"https://{monitor.jira_domain}/rest/api/3/issue/createmeta"
            params = {'projectKeys': monitor.jira_project, 'expand': 'projects.issuetypes.fields'}
            
            response = requests.get(createmeta_url, auth=auth, params=params)
            self.assertEqual(response.status_code, 200)
            
            createmeta = response.json()
            if createmeta.get('projects'):
                log_success("Issue creation permissions verified")
                log_info(f"Available issue types: {len(createmeta['projects'][0].get('issuetypes', []))}")
            else:
                log_warning("No issue creation permissions found")
            
        except Exception as e:
            log_error(f"JIRA project access test failed: {e}")
            self.fail(f"JIRA project access test failed: {e}")

    def test_real_rate_limiting(self):
        """Test API rate limiting behavior"""
        log_test("Testing API rate limiting behavior")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Check GitHub rate limits
            log_info("Checking GitHub API rate limits...")
            import requests
            
            headers = {'Authorization': f'token {monitor.github_token}'}
            response = requests.get('https://api.github.com/rate_limit', headers=headers)
            
            self.assertEqual(response.status_code, 200)
            rate_data = response.json()
            
            core_limit = rate_data['resources']['core']
            log_success("GitHub rate limit information retrieved")
            log_info(f"Core API limit: {core_limit['limit']}")
            log_info(f"Core API remaining: {core_limit['remaining']}")
            log_info(f"Core API reset time: {datetime.fromtimestamp(core_limit['reset'])}")
            
            # Warn if rate limit is low
            if core_limit['remaining'] < 100:
                log_warning(f"GitHub API rate limit is low: {core_limit['remaining']} remaining")
            
        except Exception as e:
            log_error(f"Rate limiting test failed: {e}")
            self.fail(f"Rate limiting test failed: {e}")

    def test_real_bidirectional_flow_features(self):
        """Test the new bidirectional flow features with real environment"""
        log_test("Testing bidirectional flow features")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Test 1: Branch name parsing functionality
            log_info("Testing branch name parsing...")
            test_branches = [
                'feature-1650-cart-persistence',
                'fix-2301-rollback-foreign-keys', 
                'bug-456-memory-leak',
                'main'  # Should return None
            ]
            
            for branch in test_branches:
                issue_num = monitor.parse_issue_from_branch(branch)
                if branch == 'main':
                    self.assertIsNone(issue_num)
                    log_info(f"✓ {branch} -> None (correct)")
                else:
                    self.assertIsNotNone(issue_num)
                    log_info(f"✓ {branch} -> {issue_num}")
            
            log_success("Branch name parsing functionality verified")
            
            # Test 2: Enhanced status determination
            log_info("Testing enhanced status determination...")
            
            # Test merged PR status
            pr_status_merged = {'merged': True, 'status': 'merged'}
            status, labels = monitor.determine_kanban_status(
                pr_status_merged, True, 'test-owner', 'test-repo'
            )
            self.assertEqual(status, 'Done')
            self.assertIn('merged', labels)
            log_info("✓ Merged PR correctly assigned to 'Done' status")
            
            # Test open PR with activity
            pr_status_open = {'is_pr': True, 'state': 'open', 'merged': False}
            event_context = {
                'is_review_comment': True,
                'is_comment_on_open_pr': True
            }
            status, labels = monitor.determine_kanban_status(
                pr_status_open, True, 'test-owner', 'test-repo', event_context
            )
            self.assertEqual(status, 'In Progress')
            self.assertIn('pr-activity', labels)
            log_info("✓ Open PR with activity correctly moved to 'In Progress'")
            
            # Test open PR without activity
            status, labels = monitor.determine_kanban_status(
                pr_status_open, True, 'test-owner', 'test-repo', {}
            )
            self.assertEqual(status, 'Pull Request')
            self.assertIn('pull-request', labels)
            log_info("✓ Open PR without activity stays in 'Pull Request'")
            
            log_success("Enhanced status determination verified")
            
            # Test 3: Event context detection
            log_info("Testing event context detection...")
            
            # Simulate comment with mention
            comment_body = "Hey @ramanathan1504 can you review this?"
            has_mention = f"@{monitor.github_user}" in comment_body
            self.assertTrue(has_mention)
            log_info("✓ User mention detection works")
            
            # Test push event context
            push_context = {
                'is_push_event': True,
                'is_first_commit_on_issue_branch': True
            }
            status, labels = monitor.determine_kanban_status(
                {}, True, 'test-owner', 'test-repo', push_context
            )
            self.assertEqual(status, 'In Progress')
            self.assertIn('active-work', labels)
            log_info("✓ Push event correctly triggers 'In Progress' status")
            
            log_success("Event context detection verified")
            
        except Exception as e:
            log_error(f"Bidirectional flow features test failed: {e}")
            self.fail(f"Bidirectional flow features test failed: {e}")

    def test_real_enhanced_event_processing(self):
        """Test enhanced event processing with real GitHub events"""
        log_test("Testing enhanced event processing")
        
        try:
            monitor = GitHubJIRAMonitor()
            
            # Fetch recent events to test processing
            log_info("Fetching recent events for enhanced processing test...")
            events = monitor.fetch_github_events(max_pages=1)
            
            if not events:
                log_warning("No recent events found, skipping enhanced processing test")
                return
            
            log_info(f"Testing enhanced processing on {len(events)} events")
            
            # Test PR-branch context detection (mock test)
            log_info("Testing PR-branch context detection...")
            
            # This tests the method without requiring actual open PRs
            context = monitor.check_pr_branch_context('microsoft', 'vscode', 'feature-123-test')
            self.assertIsInstance(context, dict)
            self.assertIn('is_pr_branch', context)
            self.assertIn('is_pr_related', context)
            log_info("✓ PR-branch context detection method works")
            
            # Count different event types and test processing capability
            event_types = {}
            push_events = 0
            comment_events = 0
            
            for event in events:
                event_type = event.get('type')
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
                if event_type == 'PushEvent':
                    push_events += 1
                elif event_type in ['IssueCommentEvent', 'PullRequestReviewCommentEvent']:
                    comment_events += 1
            
            log_info("Event type distribution:")
            for event_type, count in event_types.items():
                log_info(f"  {event_type}: {count}")
            
            log_info(f"Found {push_events} PushEvents and {comment_events} CommentEvents")
            
            # Test enhanced processing if we have suitable events
            if push_events > 0:
                log_info("Testing PushEvent processing...")
                # Find a push event to test
                for event in events:
                    if event.get('type') == 'PushEvent':
                        # Test the process_push_event method (dry run)
                        result, success = monitor.process_push_event(event, dry_run=True)
                        self.assertIsInstance(result, str)
                        self.assertIsInstance(success, bool)
                        log_info(f"✓ PushEvent processing: {result} (success: {success})")
                        break
            
            log_success("Enhanced event processing verified")
            
        except Exception as e:
            log_error(f"Enhanced event processing test failed: {e}")
            self.fail(f"Enhanced event processing test failed: {e}")

class QuickValidationTestCase(unittest.TestCase):
    """Quick validation tests for CI/CD pipelines"""
    
    def test_quick_environment_check(self):
        """Quick environment validation"""
        log_test("Quick environment validation")
        
        # Check environment variables
        required_vars = ['GITHUB_TOKEN', 'JIRA_AUTH']
        for var in required_vars:
            self.assertTrue(os.getenv(var), f"Missing {var}")
        
        # Quick monitor initialization
        monitor = GitHubJIRAMonitor()
        self.assertIsNotNone(monitor)
        
        log_success("Quick environment validation passed")

def create_test_suite(test_mode='full'):
    """Create test suite based on mode"""
    suite = unittest.TestSuite()
    
    if test_mode == 'quick':
        log_section("Adding Quick Validation Tests")
        quick_tests = unittest.TestLoader().loadTestsFromTestCase(QuickValidationTestCase)
        suite.addTests(quick_tests)
        log_info(f"Added {quick_tests.countTestCases()} quick validation tests")
    else:
        log_section("Adding Full Integration Tests")
        real_tests = unittest.TestLoader().loadTestsFromTestCase(RealIntegrationTestCase)
        suite.addTests(real_tests)
        log_info(f"Added {real_tests.countTestCases()} real integration tests")
        
        if test_mode == 'all':
            quick_tests = unittest.TestLoader().loadTestsFromTestCase(QuickValidationTestCase)
            suite.addTests(quick_tests)
            log_info(f"Added {quick_tests.countTestCases()} quick validation tests")
    
    return suite

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description='GitHub JIRA Monitor Real Integration Tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables Required:
  GITHUB_TOKEN    GitHub personal access token (ghp_* or github_pat_*)
  JIRA_AUTH       Base64 encoded JIRA credentials (user:token)

Test Modes:
  Default         Run full integration test suite
  --quick         Run quick validation tests only
  --all           Run all tests including quick validation
        """
    )
    
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation tests only')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests including quick validation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine test mode
    if args.quick:
        test_mode = 'quick'
    elif args.all:
        test_mode = 'all'
    else:
        test_mode = 'full'
    
    # Print test configuration
    log_section(f"GitHub JIRA Monitor Real Integration Tests - {test_mode.upper()} Mode")
    log_info(f"Test mode: {test_mode}")
    log_info(f"Verbose: {args.verbose}")
    log_info(f"Python version: {sys.version}")
    log_info(f"Working directory: {os.getcwd()}")
    
    # Environment check
    log_info("Checking environment variables...")
    required_vars = ['GITHUB_TOKEN', 'JIRA_AUTH']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        log_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        log_error("Please set the required environment variables before running real tests")
        return 1
    else:
        log_success("All required environment variables found")
    
    # Create and run test suite
    suite = create_test_suite(test_mode)
    
    # Configure test runner
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    
    log_section("Running Real Integration Tests")
    log_info(f"Total tests to run: {suite.countTestCases()}")
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    log_section("Real Integration Test Results")
    log_info(f"Tests run: {result.testsRun}")
    log_info(f"Failures: {len(result.failures)}")
    log_info(f"Errors: {len(result.errors)}")
    log_info(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        log_success("All real integration tests passed!")
        return 0
    else:
        log_error("Some real integration tests failed!")
        
        # Print failure details
        if result.failures:
            log_error("Failures:")
            for test, trace in result.failures:
                log_error(f"  {test}: {trace.split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            log_error("Errors:")
            for test, trace in result.errors:
                log_error(f"  {test}: {trace.split('Exception:')[-1].strip()}")
        
        return 1

if __name__ == '__main__':
    sys.exit(main())
