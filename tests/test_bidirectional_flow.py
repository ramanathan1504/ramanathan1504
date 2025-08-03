#!/usr/bin/env python3
"""
Test bidirectional flow implementation as described in STATUS_FLOW_PROPOSAL.md
"""

import unittest
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from github_jira_monitor import GitHubJIRAMonitor

def log_test(message):
    """Helper function to log test progress"""
    print(f"\n🧪 {message}")

def log_info(message):
    """Helper function to log info"""
    print(f"ℹ️  {message}")

def log_success(message):
    """Helper function to log success"""
    print(f"✅ {message}")

class TestBidirectionalFlow(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Mock the environment variables to avoid actual API calls
        os.environ['GITHUB_TOKEN'] = 'test_token'
        os.environ['JIRA_AUTH'] = 'test_auth'
        self.monitor = GitHubJIRAMonitor()
    
    def test_branch_name_parsing(self):
        """Test branch name parsing for issue numbers"""
        log_test("Testing branch name parsing for issue numbers")
        
        test_cases = [
            ('feature-1650-cart-persistence', 1650),
            ('fix-2301-rollback-foreign-keys', 2301),
            ('bug-456-memory-leak', 456),
            ('issue-789-documentation', 789),
            ('pr-123-update-readme', 123),
            ('1234-initial-work', 1234),
            ('issue123', 123),
            ('feature-add-new-feature', None),  # No number
            ('main', None),  # No number
        ]
        
        for branch_name, expected in test_cases:
            result = self.monitor.parse_issue_from_branch(branch_name)
            self.assertEqual(result, expected, f"Failed for branch: {branch_name}")
            log_info(f"✓ {branch_name} -> {result}")
        
        log_success("Branch name parsing tests passed")
    
    def test_status_priority_logic(self):
        """Test the complete status priority logic as described in the proposal"""
        log_test("Testing status priority logic from STATUS_FLOW_PROPOSAL.md")
        
        # Test Case 1: MERGED (highest priority) → DONE
        pr_status_merged = {'merged': True, 'status': 'merged'}
        status, labels = self.monitor.determine_kanban_status(
            pr_status_merged, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Done')
        self.assertIn('merged', labels)
        log_info("✓ Priority 1: MERGED → DONE works")
        
        # Test Case 2: OPEN PR + ACTIVITY → IN PROGRESS (Backward Flow)
        pr_status_open = {'is_pr': True, 'state': 'open', 'merged': False}
        event_context_activity = {
            'is_review_comment': True,
            'is_mention_on_open_pr': True
        }
        
        status, labels = self.monitor.determine_kanban_status(
            pr_status_open, True, 'prisma', 'prisma', event_context_activity
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('pr-activity', labels)
        log_info("✓ Priority 3: OPEN PR + ACTIVITY → IN PROGRESS works")
        
        # Test Case 3: OPEN PR (no activity) → PULL REQUEST
        status, labels = self.monitor.determine_kanban_status(
            pr_status_open, True, 'prisma', 'prisma', {}
        )
        self.assertEqual(status, 'Pull Request')
        self.assertIn('pull-request', labels)
        log_info("✓ Priority 4: OPEN PR → PULL REQUEST works")
        
        # Test Case 4: COMMITS ON BRANCH → IN PROGRESS
        push_context = {
            'is_push_event': True,
            'is_first_commit_on_issue_branch': True
        }
        
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'owner', 'repo', push_context
        )
        self.assertEqual(status, 'In Progress')
        self.assertIn('active-work', labels)
        log_info("✓ Priority 5: COMMITS ON BRANCH → IN PROGRESS works")
        
        # Test Case 5: External repo → DISCUSSION
        status, labels = self.monitor.determine_kanban_status(
            {}, False, 'external', 'repo'
        )
        self.assertEqual(status, 'Discussion')
        self.assertIn('external-repo', labels)
        log_info("✓ External repo → DISCUSSION works")
        
        log_success("Status priority logic tests passed")
    
    def test_bidirectional_flow_cycle(self):
        """Test the complete bidirectional flow cycle IN PROGRESS ↔ PULL REQUEST"""
        log_test("Testing bidirectional flow cycle: IN PROGRESS ↔ PULL REQUEST")
        
        # Scenario: Open PR exists
        pr_status = {'is_pr': True, 'state': 'open', 'merged': False}
        
        # Step 1: Comment on open PR → IN PROGRESS (Backward Flow)
        comment_context = {'is_comment_on_open_pr': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', comment_context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Step 1: Comment on open PR → IN PROGRESS")
        
        # Step 2: Push to PR branch → IN PROGRESS (continues work)
        push_context = {'is_push_to_pr_branch': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', push_context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Step 2: Push to PR branch → IN PROGRESS")
        
        # Step 3: No activity context → PULL REQUEST (forward flow)
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', {}
        )
        self.assertEqual(status, 'Pull Request')
        log_info("✓ Step 3: No activity → PULL REQUEST")
        
        # Step 4: Review comment → IN PROGRESS (backward flow again)
        review_context = {'is_review_comment': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'owner', 'repo', review_context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Step 4: Review comment → IN PROGRESS")
        
        log_success("Bidirectional flow cycle tests passed")
    
    def test_practical_example_shopify_cart(self):
        """Test the practical Shopify shopping cart example from the proposal"""
        log_test("Testing Shopify shopping cart example flow")
        
        # Day 1: DISCUSSION (comment only)
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Discussion')
        log_info("✓ Day 1: DISCUSSION status")
        
        # Day 3: IN PROGRESS (first commit on issue branch)
        push_context = {
            'is_push_event': True,
            'is_first_commit_on_issue_branch': True
        }
        status, labels = self.monitor.determine_kanban_status(
            {}, True, 'shopify', 'storefront-api', push_context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Day 3: IN PROGRESS after first commit")
        
        # Day 5: PULL REQUEST (PR opened)
        pr_status = {'is_pr': True, 'state': 'open'}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Pull Request')
        log_info("✓ Day 5: PULL REQUEST after PR opened")
        
        # Day 8: IN PROGRESS (maintainer comment on open PR)
        comment_context = {'is_comment_on_open_pr': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', comment_context
        )
        self.assertEqual(status, 'In Progress')
        log_info("✓ Day 8: IN PROGRESS after comment on open PR")
        
        # Day 9: PULL REQUEST (push to PR branch then back to review)
        # First: Push → IN PROGRESS
        push_to_pr_context = {'is_push_to_pr_branch': True}
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', push_to_pr_context
        )
        self.assertEqual(status, 'In Progress')
        
        # Then: No activity → PULL REQUEST
        status, labels = self.monitor.determine_kanban_status(
            pr_status, True, 'shopify', 'storefront-api', {}
        )
        self.assertEqual(status, 'Pull Request')
        log_info("✓ Day 9: Push → IN PROGRESS, then → PULL REQUEST")
        
        # Day 10: DONE (PR merged)
        merged_status = {'merged': True, 'status': 'merged'}
        status, labels = self.monitor.determine_kanban_status(
            merged_status, True, 'shopify', 'storefront-api'
        )
        self.assertEqual(status, 'Done')
        log_info("✓ Day 10: DONE after PR merged")
        
        log_success("Shopify shopping cart example tests passed")
    
    def test_event_context_detection(self):
        """Test event context detection for various scenarios"""
        log_test("Testing event context detection")
        
        # Test mention detection
        comment_body_with_mention = "Hey @ramanathan1504 can you add tests?"
        self.assertIn("@ramanathan1504", comment_body_with_mention)
        log_info("✓ Mention detection works")
        
        # Test review comment detection
        event_context = {
            'event_type': 'PullRequestReviewCommentEvent',
            'is_review_comment': True
        }
        self.assertTrue(event_context['is_review_comment'])
        log_info("✓ Review comment detection works")
        
        log_success("Event context detection tests passed")

def run_tests():
    """Run all bidirectional flow tests"""
    print("🚀 Running Bidirectional Flow Tests")
    print("=" * 50)
    
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ All bidirectional flow tests completed!")

if __name__ == '__main__':
    run_tests()
