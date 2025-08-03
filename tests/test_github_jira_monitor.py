#!/usr/bin/env python3
"""
Test cases for GitHub to JIRA Comment Monitor
"""

import os
import sys
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from github_jira_monitor import GitHubJIRAMonitor

class TestGitHubJIRAMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test_github_token',
            'JIRA_AUTH': 'test_jira_auth'
        })
        self.env_patcher.start()
        
        self.monitor = GitHubJIRAMonitor()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_initialization(self):
        """Test monitor initialization"""
        self.assertEqual(self.monitor.github_user, 'ramanathan1504')
        self.assertEqual(self.monitor.skip_orgs, ['intemo_dev'])
        self.assertEqual(self.monitor.jira_domain, 'osscontribution.atlassian.net')
        self.assertEqual(self.monitor.jira_project, 'OT')
        self.assertEqual(self.monitor.github_token, 'test_github_token')
        self.assertEqual(self.monitor.jira_auth, 'test_jira_auth')
    
    def test_should_skip_repo(self):
        """Test repository skipping logic"""
        # Should skip own repos
        self.assertTrue(self.monitor.should_skip_repo('ramanathan1504'))
        
        # Should skip org repos
        self.assertTrue(self.monitor.should_skip_repo('intemo_dev'))
        
        # Should not skip external repos
        self.assertFalse(self.monitor.should_skip_repo('facebook'))
        self.assertFalse(self.monitor.should_skip_repo('microsoft'))
    
    def test_filter_comment_events(self):
        """Test comment event filtering"""
        events = [
            {'type': 'IssueCommentEvent', 'id': 1},
            {'type': 'PushEvent', 'id': 2},
            {'type': 'IssueCommentEvent', 'id': 3},
            {'type': 'WatchEvent', 'id': 4}
        ]
        
        comment_events = self.monitor.filter_comment_events(events)
        
        self.assertEqual(len(comment_events), 2)
        self.assertEqual(comment_events[0]['id'], 1)
        self.assertEqual(comment_events[1]['id'], 3)
    
    @patch('requests.get')
    def test_check_fork_status_found(self, mock_get):
        """Test fork status check when fork exists"""
        # Mock successful fork response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'fork': True}
        mock_get.return_value = mock_response
        
        result = self.monitor.check_fork_status('facebook/react')
        
        self.assertTrue(result)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_check_fork_status_not_found(self, mock_get):
        """Test fork status check when fork doesn't exist"""
        # Mock 404 response (no fork)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.monitor.check_fork_status('facebook/react')
        
        self.assertFalse(result)
    
    @patch('requests.get')
    def test_get_issue_details_success(self, mock_get):
        """Test successful issue details fetching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'number': 123,
            'title': 'Test Issue',
            'body': 'Test issue description'
        }
        mock_get.return_value = mock_response
        
        result = self.monitor.get_issue_details('https://github.com/owner/repo/issues/123')
        
        self.assertEqual(result['number'], 123)
        self.assertEqual(result['title'], 'Test Issue')
        self.assertEqual(result['body'], 'Test issue description')
    
    @patch('requests.get')
    def test_search_existing_jira_task_found(self, mock_get):
        """Test JIRA task search when task exists"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 1,
            'issues': [{'key': 'OT-123'}]
        }
        mock_get.return_value = mock_response
        
        result = self.monitor.search_existing_jira_task('https://github.com/owner/repo/issues/123')
        
        self.assertEqual(result, 'OT-123')
    
    @patch('requests.get')
    def test_search_existing_jira_task_not_found(self, mock_get):
        """Test JIRA task search when task doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total': 0,
            'issues': []
        }
        mock_get.return_value = mock_response
        
        result = self.monitor.search_existing_jira_task('https://github.com/owner/repo/issues/123')
        
        self.assertIsNone(result)
    
    def test_process_comment_event_skip_own_repo(self):
        """Test processing comment event for own repository"""
        event = {
            'repo': {
                'full_name': 'ramanathan1504/my-repo',
                'owner': {'login': 'ramanathan1504'}
            },
            'payload': {
                'comment': {'body': 'Test comment'},
                'issue': {
                    'html_url': 'https://github.com/ramanathan1504/my-repo/issues/1',
                    'title': 'Test Issue',
                    'number': 1
                }
            }
        }
        
        result, success = self.monitor.process_comment_event(event, dry_run=True)
        
        self.assertEqual(result, 'skipped')
        self.assertTrue(success)
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.check_fork_status')
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.create_jira_task')
    def test_process_comment_event_external_repo(self, mock_create_task, mock_check_fork):
        """Test processing comment event for external repository"""
        # Mock fork check
        mock_check_fork.return_value = False
        mock_create_task.return_value = True
        
        event = {
            'repo': {
                'full_name': 'facebook/react',
                'owner': {'login': 'facebook'}
            },
            'payload': {
                'comment': {'body': 'Great feature!'},
                'issue': {
                    'html_url': 'https://github.com/facebook/react/issues/123',
                    'title': 'Add new hook',
                    'number': 123
                }
            },
            'created_at': '2025-08-03T10:00:00Z'
        }
        
        result, success = self.monitor.process_comment_event(event, dry_run=True)
        
        self.assertEqual(result, 'discussion')
        self.assertTrue(success)
        mock_check_fork.assert_called_once_with('facebook/react')
    
    @patch('requests.get')
    def test_fetch_github_events_success(self, mock_get):
        """Test successful GitHub events fetching"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'type': 'IssueCommentEvent',
                'created_at': '2025-08-03T10:00:00Z',
                'id': 1
            },
            {
                'type': 'PushEvent',
                'created_at': '2025-08-03T09:00:00Z',
                'id': 2
            }
        ]
        mock_get.return_value = mock_response
        
        events = self.monitor.fetch_github_events(max_pages=1)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['id'], 1)
        self.assertEqual(events[1]['id'], 2)
    
    @patch('requests.get')
    def test_fetch_github_events_rate_limited(self, mock_get):
        """Test GitHub events fetching with rate limiting"""
        # First call returns 403 (rate limited), second call succeeds
        responses = [
            Mock(status_code=403),
            Mock(status_code=200, json=lambda: [{'id': 1}])
        ]
        mock_get.side_effect = responses
        
        with patch('time.sleep') as mock_sleep:
            events = self.monitor.fetch_github_events(max_pages=1)
            
            # Should have waited for rate limit
            mock_sleep.assert_called_with(60)
    
    def create_sample_event_data(self):
        """Create sample event data for testing"""
        return {
            'repo_name': 'facebook/react',
            'issue_url': 'https://github.com/facebook/react/issues/123',
            'issue_title': 'Add new React hook',
            'issue_number': 123,
            'comment_body': 'Great feature! Thanks for implementing this.',
            'created_at': '2025-08-03T10:00:00Z'
        }
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.get_issue_details')
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.search_existing_jira_task')
    @patch('requests.post')
    def test_create_jira_task_contribution(self, mock_post, mock_search, mock_get_issue):
        """Test creating JIRA task for contribution"""
        # Mock dependencies
        mock_search.return_value = None  # No existing task
        mock_get_issue.return_value = {
            'body': 'This adds a new React hook for state management'
        }
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'key': 'OT-123'}
        mock_post.return_value = mock_response
        
        event_data = self.create_sample_event_data()
        result = self.monitor.create_jira_task(event_data, is_fork=True, dry_run=False)
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Verify the payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['fields']['project']['key'], 'OT')
        self.assertEqual(payload['fields']['summary'], '123 - Add new React hook')
        self.assertIn('github-forked', payload['fields']['labels'])
        self.assertIn('contribution', payload['fields']['labels'])
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.get_issue_details')
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.search_existing_jira_task')
    def test_create_jira_task_dry_run(self, mock_search, mock_get_issue):
        """Test creating JIRA task in dry run mode"""
        mock_search.return_value = None
        mock_get_issue.return_value = {'body': 'Test issue body'}
        
        event_data = self.create_sample_event_data()
        result = self.monitor.create_jira_task(event_data, is_fork=False, dry_run=True)
        
        self.assertTrue(result)
        # No actual API calls should be made in dry run mode
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.update_jira_task')
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.search_existing_jira_task')
    def test_create_jira_task_update_existing(self, mock_search, mock_update):
        """Test updating existing JIRA task"""
        mock_search.return_value = 'OT-123'  # Existing task found
        mock_update.return_value = True
        
        event_data = self.create_sample_event_data()
        result = self.monitor.create_jira_task(event_data, is_fork=False, dry_run=False)
        
        self.assertTrue(result)
        mock_update.assert_called_once_with('OT-123', event_data['comment_body'], False)

class TestIntegration(unittest.TestCase):
    """Integration tests that test the full workflow"""
    
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test_github_token',
            'JIRA_AUTH': 'test_jira_auth'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        self.env_patcher.stop()
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.fetch_github_events')
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.process_comment_event')
    def test_run_monitor_with_comments(self, mock_process, mock_fetch):
        """Test running monitor with comment events"""
        # Mock events
        mock_fetch.return_value = [
            {'type': 'IssueCommentEvent', 'id': 1},
            {'type': 'IssueCommentEvent', 'id': 2},
            {'type': 'PushEvent', 'id': 3}
        ]
        
        # Mock processing results
        mock_process.side_effect = [
            ('discussion', True),
            ('contribution', True)
        ]
        
        monitor = GitHubJIRAMonitor()
        stats = monitor.run_monitor(dry_run=True)
        
        self.assertEqual(stats['total'], 2)  # 2 comment events
        self.assertEqual(stats['processed'], 2)
        self.assertEqual(stats['created'], 2)
        self.assertEqual(stats['skipped'], 0)
        self.assertEqual(stats['errors'], 0)
    
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.fetch_github_events')
    def test_run_monitor_no_comments(self, mock_fetch):
        """Test running monitor with no comment events"""
        # Mock events with no comments
        mock_fetch.return_value = [
            {'type': 'PushEvent', 'id': 1},
            {'type': 'WatchEvent', 'id': 2}
        ]
        
        monitor = GitHubJIRAMonitor()
        stats = monitor.run_monitor(dry_run=True)
        
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['processed'], 0)
        self.assertEqual(stats['created'], 0)

class TestCommandLineInterface(unittest.TestCase):
    """Test command line interface"""
    
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test_github_token',
            'JIRA_AUTH': 'test_jira_auth'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        self.env_patcher.stop()
    
    @patch('sys.argv', ['github_jira_monitor.py', 'monitor', '--dry-run'])
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.run_monitor')
    def test_cli_monitor_dry_run(self, mock_run_monitor):
        """Test CLI monitor command with dry run"""
        mock_run_monitor.return_value = {'errors': 0}
        
        from github_jira_monitor import main
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_run_monitor.assert_called_once_with(since_minutes=15, dry_run=True)
            mock_exit.assert_not_called()
    
    @patch('sys.argv', ['github_jira_monitor.py', 'migrate', '--max-pages', '5', '--dry-run'])
    @patch('scripts.github_jira_monitor.GitHubJIRAMonitor.run_migration')
    def test_cli_migrate_with_options(self, mock_run_migration):
        """Test CLI migrate command with options"""
        mock_run_migration.return_value = {'errors': 0}
        
        from github_jira_monitor import main
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_run_migration.assert_called_once_with(max_pages=5, dry_run=True)
            mock_exit.assert_not_called()

if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
