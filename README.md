# GitHub JIRA Integration System

A comprehensive system for tracking GitHub contributions in JIRA with complete lifecycle management from discussion to release.

## 🎯 Quick Start

### 1. Setup Environment Variables
```bash
# GitHub Personal Access Token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# JIRA Authentication (base64 encoded username:password)
export JIRA_AUTH="base64_encoded_credentials"
```

### 2. Configure GitHub Secrets
In your GitHub repository settings → Secrets and variables → Actions:
- `GH_TOKEN`: Your GitHub Personal Access Token
- `JIRA_AUTH`: Base64 encoded JIRA credentials

### 3. Initial Migration (One-time only)
Use the **One-Time Migration Workflow** for historical data:
1. Go to Actions → "One-Time GitHub JIRA Migration"
2. Click "Run workflow" 
3. Choose operation: `migrate`, `pr-migrate`, or `old-issue`
4. Configure parameters and run
5. **Archive this workflow after completion**

### 4. Ongoing Monitoring
The **Ongoing Monitor Workflow** runs automatically:
- Every 10 minutes: Monitor GitHub activity
- Every hour: Check for releases
- Manual triggers available for immediate updates

## 📁 Project Structure

```
.
├── .github/workflows/
│   ├── github-jira-monitor.yml              # Ongoing monitoring (keep active)
│   └── github-jira-one-time-migration.yml   # One-time migration (archive after use)
├── scripts/
│   └── github_jira_monitor.py               # Core Python logic
├── tests/
│   └── test_github_jira_monitor.py          # Comprehensive test suite
├── docs/
│   └── github-jira-integration-documentation.md  # Complete documentation
├── run_tests.py                             # Test runner
└── README.md                                # This file
```

## 🔄 Workflows

### Ongoing Monitor (`github-jira-monitor.yml`)
**Purpose**: Continuous monitoring and lifecycle tracking
**Status**: Keep active permanently
**Triggers**: 
- Automatic (every 10 min + hourly)
- Manual with options

**Operations**:
- `monitor` - Real-time GitHub activity monitoring
- `release-check` - Update Done → Released status  
- `both` - Combined monitoring and release checking

### One-Time Migration (`github-jira-one-time-migration.yml`)
**Purpose**: Initial setup and historical data migration
**Status**: Archive after completion
**Triggers**: Manual only

**Operations**:
- `migrate` - Historical comment migration
- `pr-migrate` - Specific repository PR migration
- `old-issue` - Specific issue migration

## 🎛️ Status Flow

Complete 6-stage Kanban workflow:
```
Discussion → Todo → In Progress → Pull Request → Done → Released
```

### Status Assignment Logic
- **Discussion**: Mentions in external repositories
- **Todo**: Mentions in forked repositories, assigned issues
- **In Progress**: Push events, review comments received
- **Pull Request**: PRs you create
- **Done**: Merged PRs, completed issues
- **Released**: Code deployed/released

## 🧠 Smart Features

### Event Detection
- **Comments**: Issues/PRs comments with mention detection
- **Reviews**: Code review comments triggering In Progress
- **Authorship**: Your PRs/issues tracked automatically
- **Pushes**: Code commits updating status to In Progress
- **Releases**: Automatic Done → Released transitions

### Intelligence
- **Fork Detection**: Different status for forked vs external repos
- **Duplicate Prevention**: Repository-specific task matching
- **Context Awareness**: Smart status transitions based on activity
- **Mention Parsing**: @ramanathan1504 detection with smart routing

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py
```

### Test Coverage
- Event detection and filtering
- Status determination logic
- Mention detection
- JIRA integration
- Release detection
- Duplicate prevention
- Error handling
- Performance testing
- Integration scenarios

## � Documentation

### Complete Guide
See `docs/github-jira-integration-documentation.md` for:
- Detailed architecture
- Configuration options
- API integration details
- Troubleshooting guide
- Performance considerations
- Security best practices

### Quick References

#### Manual Test Commands
```bash
# Test monitoring (dry run)
cd scripts
python github_jira_monitor.py monitor --since-minutes 60 --dry-run

# Test release checking
python github_jira_monitor.py release-check --dry-run

# Test historical migration
python github_jira_monitor.py migrate --max-pages 2 --dry-run
```

#### Workflow Manual Triggers
1. **Ongoing Monitor**: Actions → "Ongoing GitHub JIRA Monitor" → Run workflow
2. **Migration**: Actions → "One-Time GitHub JIRA Migration" → Run workflow

## 🎯 Usage Workflow

### Initial Setup
1. ✅ Configure GitHub secrets (`GH_TOKEN`, `JIRA_AUTH`)
2. ✅ Run one-time migration for historical data
3. ✅ Enable ongoing monitoring workflow
4. ✅ Archive migration workflow
5. ✅ Monitor JIRA for new tasks

### Daily Operations
- Monitoring runs automatically every 10 minutes
- Release checking runs automatically every hour  
- Manual triggers available for immediate updates
- Check JIRA board for new tasks and status updates

### Maintenance
- Monitor workflow logs for errors
- Update tokens when they expire
- Review and adjust time ranges if needed
- Run tests before making changes

## 🔧 Customization

### Environment Configuration
```python
# In github_jira_monitor.py
self.github_user = 'ramanathan1504'      # Your GitHub username
self.skip_orgs = ['intemo_dev']          # Organizations to skip
self.jira_domain = 'osscontribution.atlassian.net'  # JIRA domain
self.jira_project = 'OT'                 # JIRA project key
```

### Scheduling
```yaml
# In github-jira-monitor.yml
schedule:
  - cron: '*/10 * * * *'  # Every 10 minutes (monitoring)
  - cron: '0 * * * *'     # Every hour (release check)
```

## 🚨 Troubleshooting

### Common Issues
1. **Authentication Errors**: Check `GH_TOKEN` and `JIRA_AUTH` secrets
2. **Rate Limiting**: Reduce polling frequency or check API usage
3. **Missing Events**: Verify time ranges and event filtering
4. **Duplicate Tasks**: Check repository matching logic

### Debug Mode
Use `dry_run: true` in workflow inputs to test without creating tasks.

### Logs
Check GitHub Actions logs for detailed execution information and error messages.

## 🔒 Security

- Secrets stored securely in GitHub repository settings
- No hardcoded credentials in code
- API tokens with minimal required permissions
- Audit trail through GitHub Actions logs

## 📈 Monitoring

Track system health through:
- GitHub Actions workflow success/failure
- JIRA task creation patterns
- API rate limit usage
- Processing time trends

## 🚀 Future Enhancements

- Webhook-based real-time processing
- Multi-project JIRA support
- Advanced filtering rules
- Dashboard and analytics
- Slack/email notifications

## 📞 Support

1. Check the comprehensive documentation in `docs/`
2. Run test suite to verify setup: `python run_tests.py`
3. Review workflow logs in GitHub Actions
4. Test with dry-run mode before making changes

---

**System Status**: ✅ Production Ready  
**Last Updated**: August 3, 2025  
**Version**: 2.0 (Separated workflows)

