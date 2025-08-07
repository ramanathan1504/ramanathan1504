import unittest
from unittest.mock import MagicMock, patch
from scripts.monitor_v1 import GitHubJIRAMonitor

class TestGitHubJIRAMonitorModularFlow(unittest.TestCase):
    def setUp(self):
        self.monitor = GitHubJIRAMonitor()
        self.monitor.github_user = 'ramanathan1504'
        self.monitor.github_token = 'dummy_token'
        self.monitor.jira_auth = 'dummy_auth'
        self.monitor.skip_orgs = []
        self.monitor.jira_project = 'OSS'
        self.monitor.jira_domain = 'osscontribution.atlassian.net'
        self.monitor.get_github_headers = MagicMock(return_value={'Authorization': 'token dummy_token'})
        self.monitor.get_jira_headers = MagicMock(return_value={'Authorization': 'Basic dummy_auth'})

    @patch('requests.get')
    @patch('requests.post')
    @patch('requests.put')
    def test_end_to_end_modular_workflow(self, mock_put, mock_post, mock_get):
        from datetime import datetime, timedelta, timezone
        import scripts.monitor_v1
        fixed_now = datetime(2025, 8, 7, 15, 0, 0, tzinfo=timezone.utc)
        created_at_iso = (fixed_now - timedelta(minutes=59)).isoformat().replace('+00:00', 'Z')
        with patch.object(scripts.monitor_v1, 'datetime', wraps=datetime) as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            github_events_response = MagicMock(status_code=200, json=MagicMock(return_value=[
                {'type': 'CreateEvent', 'payload': {'ref_type': 'branch', 'ref': 'feature-1234-new-feature'}, 'repo': {'name': 'externaluser/somerepo'}, 'created_at': created_at_iso},
                {'type': 'PushEvent', 'payload': {'ref': 'refs/heads/feature-1234-new-feature', 'commits': [{}]}, 'repo': {'name': 'externaluser/somerepo'}, 'created_at': created_at_iso},
                {'type': 'PullRequestEvent', 'payload': {'action': 'opened', 'pull_request': {'number': 1234}}, 'repo': {'name': 'externaluser/somerepo'}, 'created_at': created_at_iso},
                {'type': 'PullRequestEvent', 'payload': {'action': 'closed', 'pull_request': {'merged': True, 'number': 1234}}, 'repo': {'name': 'externaluser/somerepo'}, 'created_at': created_at_iso}
            ]))
            jira_search_response = MagicMock(status_code=200, json=MagicMock(return_value={'total': 0, 'issues': []}))
            mock_get.side_effect = [github_events_response, jira_search_response]
            mock_post.return_value = MagicMock(status_code=201, json=MagicMock(return_value={'key': 'OSS-1234'}))
            mock_put.return_value = MagicMock(status_code=204)

            result = self.monitor.run_core_workflow(max_pages=1, since_minutes=60, dry_run=True)
            self.assertIsInstance(result, dict)
            self.assertIn('epics_created', result)
            self.assertIn('tasks_created', result)  # or tasks_updated, depending on your logic

if __name__ == '__main__':
    unittest.main()
