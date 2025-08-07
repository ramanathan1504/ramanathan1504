import subprocess
import sys
import os

def test_monitor_yml_workflow(monkeypatch):
    """
    Simulate how the GitHub Actions workflow would invoke the modular monitor script.
    This test checks that the CLI entry point works with the same arguments as the YAML.
    """
    # Set required env vars
    monkeypatch.setenv('GH_USER', 'octocat')
    monkeypatch.setenv('GH_TOKEN', 'dummy')
    monkeypatch.setenv('JIRA_DOMAIN', 'example.atlassian.net')
    monkeypatch.setenv('JIRA_PROJECT', 'OSS')
    monkeypatch.setenv('JIRA_AUTH', 'dummy')
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    # Run as the workflow would: python -m scripts.monitor_v1 --dry_run True --since_minutes 10
    result = subprocess.run([
        sys.executable, "-m", "scripts.monitor_v1", '--dry_run', 'True', '--since_minutes', '10'
    ], cwd=".", capture_output=True, text=True, env=env)
    assert result.returncode == 0
    assert "WORKFLOW COMPLETE" in result.stdout
    # Also test: python -m scripts.monitor_v1 (no args)
    result2 = subprocess.run([
        sys.executable, "-m", "scripts.monitor_v1"
    ], cwd=".", capture_output=True, text=True, env=env)
    assert result2.returncode == 0
    assert "WORKFLOW COMPLETE" in result2.stdout
