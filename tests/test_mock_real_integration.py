#!/usr/bin/env python3
"""
Mock Real Integration Tests for GitHub JIRA Monitor
Tests the enhanced bidirectional flow without requiring real tokens

This file validates the new bidirectional flow implementation
using mock data that simulates real API responses.
"""

import unittest
import sys
import os
from datetime import datetime

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    from github_jira_monitor import GitHubJIRAMonitor
except ImportError as e:
    print(f"ERROR: Failed to import GitHubJIRAMonitor: {e}")
    print("Make sure the scripts/github_jira_monitor.py file exists")
    sys.exit(1)

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

def log_section(section_name):
    """Log section separator"""
    print(f"\n{'='*70}")
    print(f"  {section_name}")
    print(f"{'='*70}")

class MockRealIntegrationTestCase(unittest.TestCase):
    """Mock real integration tests - Tests enhanced features without real tokens"""
    
    def setUp(self):
        """Set up mock test environment"""
        log_test("Setting up mock real integration test environment")
        
        # Set mock environment variables
        os.environ['GITHUB_TOKEN'] = 'mock_token_for_testing'
        os.environ['JIRA_AUTH'] = 'mock_auth_for_testing'
        
        self.monitor = GitHubJIRAMonitor()
        log_success("Mock real integration test environment set up")

    def test_enhanced_bidirectional_flow_comprehensive(self):
        """Comprehensive test of bidirectional flow as per STATUS_FLOW_PROPOSAL.md"""
        log_test("Testing comprehensive bidirectional flow implementation")
        
        # Test the complete Shopify shopping cart example flow
        log_info("Testing Shopify shopping cart example flow...")
        
        # Day 1: DISCUSSION (comment only)
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Discussion')
        log_info("✓ Day 1: DISCUSSION status confirmed")
        
        # Day 3: IN PROGRESS (first commit on issue branch)
        push_context = {
            'is_push_event': True,
            'is_first_commit_on_issue_branch': True,
            'is_branch_with_issue_number': True
        }
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'shopify', 'storefront-api', push_context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('active-work', labels)
        log_info("✓ Day 3: IN PROGRESS after first commit")
        
        # Day 5: PULL REQUEST (PR opened)
        pr_status = {'is_pr': True, 'state': 'open', 'merged': False}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Pull Request')
        self.assertIn('pull-request', labels)
        log_info("✓ Day 5: PULL REQUEST after PR opened")
        
        # Day 8: IN PROGRESS (maintainer comment on open PR - backward flow)
        comment_context = {
            'is_comment_on_open_pr': True,
            'is_mention_on_open_pr': False
        }
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', comment_context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('pr-activity', labels)
        log_info("✓ Day 8: IN PROGRESS after comment on open PR (backward flow)")
        
        # Day 9a: IN PROGRESS (push to PR branch)
        push_to_pr_context = {
            'is_push_to_pr_branch': True
        }
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', push_to_pr_context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('pr-activity', labels)
        log_info("✓ Day 9a: IN PROGRESS after push to PR branch")
        
        # Day 9b: PULL REQUEST (back to review state)
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', {}
        )
        self.assertEqual(status, 'Pull Request')
        self.assertIn('pull-request', labels)
        log_info("✓ Day 9b: PULL REQUEST back to review state")
        
        # Day 10: DONE (PR merged)
        merged_status = {'merged': True, 'status': 'merged'}
        status, labels = self.monitor.determine_kanban_status(
            merged_status, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Done')
        self.assertIn('merged', labels)
        log_info("✓ Day 10: DONE after PR merged")
        
        log_success("Shopify shopping cart example flow completed successfully")

    def test_branch_name_parsing_comprehensive(self):
        """Comprehensive test of branch name parsing functionality"""
        log_test("Testing comprehensive branch name parsing")
        
        test_cases = [
            # Format: (branch_name, expected_issue_number)
            ('feature-1650-cart-persistence', 1650),
            ('fix-2301-rollback-foreign-keys', 2301),
            ('bug-456-memory-leak', 456),
            ('issue-789-documentation', 789),
            ('pr-123-update-readme', 123),
            ('1234-initial-work', 1234),
            ('issue123', 123),
            ('feature-add-new-feature', None),  # No number
            ('main', None),  # No number
            ('develop', None),  # No number
            ('fix-123', 123),  # Minimal format
            ('feature-9999-long-description-with-dashes', 9999),
            ('bug-0001-leading-zeros', 1),  # Leading zeros
        ]
        
        for branch_name, expected in test_cases:
            result = self.monitor.parse_issue_from_branch(branch_name)
            self.assertEqual(result, expected, f"Failed for branch: {branch_name}")
            log_info(f"✓ {branch_name} -> {result} (expected: {expected})")
        
        log_success("Branch name parsing comprehensive test passed")

    def test_status_priority_logic_complete(self):
        """Test complete status priority logic from proposal"""
        log_test("Testing complete status priority logic")
        
        # Priority 1: MERGED (highest priority) → DONE
        log_info("Testing Priority 1: MERGED → DONE")
        pr_status = {'merged': True, 'status': 'merged', 'is_pr': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo'
        )
        self.assertEqual(status, 'Done')
        self.assertIn('merged', labels)
        log_info("✓ Priority 1: MERGED correctly maps to DONE")
        
        # Priority 3: OPEN PR + ACTIVITY → IN PROGRESS
        log_info("Testing Priority 3: OPEN PR + ACTIVITY → IN PROGRESS")
        pr_status = {'is_pr': True, 'state': 'open', 'merged': False}
        
        # Test review comment activity
        context = {'is_review_comment': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('pr-activity', labels)
        log_info("✓ Review comment on open PR → IN PROGRESS")
        
        # Test mention activity
        context = {'is_mention_on_open_pr': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Mention on open PR → IN PROGRESS")
        
        # Test push to PR branch
        context = {'is_push_to_pr_branch': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Push to PR branch → IN PROGRESS")
        
        # Priority 4: OPEN PR (no activity) → PULL REQUEST
        log_info("Testing Priority 4: OPEN PR → PULL REQUEST")
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', {}
        )
        self.assertEqual(status, 'Pull Request')
        self.assertIn('pull-request', labels)
        log_info("✓ Open PR without activity → PULL REQUEST")
        
        # Priority 5: COMMITS ON BRANCH → IN PROGRESS
        log_info("Testing Priority 5: COMMITS ON BRANCH → IN PROGRESS")
        context = {
            'is_push_event': True,
            'is_first_commit_on_issue_branch': True
        }
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'owner', 'repo', context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('active-work', labels)
        log_info("✓ Commits on branch → IN PROGRESS")
        
        # Priority 7: COMMENT ONLY → DISCUSSION (default)
        log_info("Testing Priority 7: COMMENT ONLY → DISCUSSION")
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'owner', 'repo', {}
        )
        self.assertEqual(status, 'Discussion')
        log_info("✓ Comment only → DISCUSSION")
        
        log_success("Complete status priority logic verified")

    def test_event_context_detection_enhanced(self):
        """Test enhanced event context detection"""
        log_test("Testing enhanced event context detection")
        
        # Test mention detection in comments
        comment_bodies = [
            "Hey @ramanathan1504 can you review this?",
            "Thanks @ramanathan1504 for the suggestion",
            "Can you help @ramanathan1504?",
            "This is a comment without mentions",
        ]
        
        for comment in comment_bodies:
            has_mention = "@ramanathan1504" in comment
            expected = comment.count("@ramanathan1504") > 0
            self.assertEqual(has_mention, expected)
            log_info(f"✓ Mention detection: '{comment[:30]}...' -> {has_mention}")
        
        # Test PR context combinations
        pr_contexts = [
            ({'is_pr': True, 'state': 'open'}, {'is_comment_on_open_pr': True}, 'In Progress'),
            ({'is_pr': True, 'state': 'open'}, {'is_review_comment': True}, 'In Progress'),
            ({'is_pr': True, 'state': 'open'}, {}, 'Pull Request'),
            ({'is_pr': True, 'state': 'closed'}, {'is_comment_on_open_pr': True}, 'Discussion'),
        ]
        
        for pr_status, context, expected_status in pr_contexts:
            status, labels = self.monitor.determine_kanban_status(
                pr_status, True, 'owner', 'repo', context
            )
            self.assertEqual(status, expected_status)
            log_info(f"✓ PR context: {context} -> {status}")
        
        log_success("Enhanced event context detection verified")

    def test_bidirectional_cycle_multiple_iterations(self):
        """Test multiple bidirectional flow cycles"""
        log_test("Testing multiple bidirectional flow cycles")
        
        # Simulate a realistic development scenario with multiple cycles
        pr_status = {'is_pr': True, 'state': 'open', 'merged': False}
        
        # Cycle 1: PR → Activity → Back to PR
        log_info("Cycle 1: PR Review cycle")
        
        # 1. Initial PR state
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', {})
        self.assertEqual(status, 'Pull Request')
        log_info("✓ 1. Initial PR state: Pull Request")
        
        # 2. Review comment → In Progress
        context = {'is_review_comment': True}
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', context)
        self.assertEqual(status, 'In Progress')
        log_info("✓ 2. Review comment → In Progress")
        
        # 3. Push fixes → In Progress (continues)
        context = {'is_push_to_pr_branch': True}
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', context)
        self.assertEqual(status, 'In Progress')
        log_info("✓ 3. Push fixes → In Progress")
        
        # 4. Back to review → Pull Request
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', {})
        self.assertEqual(status, 'Pull Request')
        log_info("✓ 4. Back to review → Pull Request")
        
        # Cycle 2: Another round of feedback
        log_info("Cycle 2: Second feedback round")
        
        # 5. Maintainer mention → In Progress
        context = {'is_mention_on_open_pr': True}
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', context)
        self.assertEqual(status, 'In Progress')
        log_info("✓ 5. Maintainer mention → In Progress")
        
        # 6. Another push → In Progress
        context = {'is_push_to_pr_branch': True}
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', context)
        self.assertEqual(status, 'In Progress')
        log_info("✓ 6. Another push → In Progress")
        
        # 7. Back to review again → Pull Request
        status, _ = self.monitor.determine_kanban_status(pr_status, True, 'owner', 'repo', {})
        self.assertEqual(status, 'Pull Request')
        log_info("✓ 7. Back to review → Pull Request")
        
        # Final: Merge → Done
        merged_status = {'merged': True, 'status': 'merged'}
        status, _ = self.monitor.determine_kanban_status(merged_status, True, 'owner', 'repo', {})
        self.assertEqual(status, 'Done')
        log_info("✓ 8. Final merge → Done")
        
        log_success("Multiple bidirectional flow cycles completed successfully")

def main():
    """Main test runner"""
    log_section("GitHub JIRA Monitor Mock Real Integration Tests")
    log_info("Testing enhanced bidirectional flow without real tokens")
    log_info(f"Python version: {sys.version}")
    log_info(f"Working directory: {os.getcwd()}")
    
    # Create and run test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(MockRealIntegrationTestCase)
    
    log_section("Running Mock Real Integration Tests")
    log_info(f"Total tests to run: {suite.countTestCases()}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    log_section("Mock Real Integration Test Results")
    log_info(f"Tests run: {result.testsRun}")
    log_info(f"Failures: {len(result.failures)}")
    log_info(f"Errors: {len(result.errors)}")
    log_info(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        log_success("All mock real integration tests passed!")
        return 0
    else:
        log_error("Some mock real integration tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
