package com.githubeventstojira;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Parameters;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.concurrent.Callable;

@Command(name = "github-jira-monitor", mixinStandardHelpOptions = true,
        version = "GitHub JIRA Monitor 1.1",
        description = "Processes GitHub events and creates/updates JIRA tasks using positional arguments.")
public class App implements Callable<Integer> {

    private static final Logger logger = LoggerFactory.getLogger(App.class);

    @Parameters(index = "0", description = "Minutes to look back for events.")
    private int sinceMinutes;

    @Parameters(index = "1", description = "Number of results to fetch per page.")
    private int perPage;

    @Parameters(index = "2", description = "Maximum number of pages to fetch.")
    private int maxPages;

    public static void main(String[] args) {
        int exitCode = new CommandLine(new App()).execute(args);
        System.exit(exitCode);
    }

    @Override
    public Integer call() {
        try {
            GitHubJiraMonitor monitor = new GitHubJiraMonitor();
            logger.info("\n=== STARTING RUN: Processing events from the last {} minutes ===", sinceMinutes);
            logger.info("GitHub API settings: {} pages max, {} results per page.", maxPages, perPage);
            monitor.runCoreWorkflow(sinceMinutes, perPage, maxPages);
            logger.info("\n✅ Workflow completed successfully!");
            return 0;
        } catch (Exception e) {
            logger.error("\n❌ CORE WORKFLOW FAILED: {}", e.getMessage(), e);
            return 1;
        }
    }
}