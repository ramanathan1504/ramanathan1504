package com.githubeventstojira;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.githubeventstojira.model.GitHubData;
import com.githubeventstojira.model.JiraData;
import com.githubeventstojira.service.GitHubApiService;
import com.githubeventstojira.service.JiraApiService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.IOException;
import java.time.Duration;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class GitHubJiraMonitor {
    // region Setup and Initialization
    private static final Logger logger = LoggerFactory.getLogger(GitHubJiraMonitor.class);
    private final String githubUser;
    private final String jiraProject;
    private final List<String> skipOrgs;
    private final GitHubApiService gitHubApiService;
    private final JiraApiService jiraApiService;
    private final ObjectMapper mapper = new ObjectMapper();
    private String epicLinkFieldId;

    private final String jiraAssignee;
    public GitHubJiraMonitor() {
        this.githubUser = Objects.requireNonNull(System.getenv("GH_USER"), "Environment variable GH_USER must be set.");
        this.jiraProject = Objects.requireNonNull(System.getenv("JIRA_PROJECT"), "Environment variable JIRA_PROJECT must be set.");
        String githubToken = Objects.requireNonNull(System.getenv("GH_TOKEN"), "Environment variable GH_TOKEN must be set.");
        String jiraDomain = Objects.requireNonNull(System.getenv("JIRA_DOMAIN"), "Environment variable JIRA_DOMAIN must be set.");
        String jiraAuth = Objects.requireNonNull(System.getenv("JIRA_AUTH"), "Environment variable JIRA_AUTH must be set.");
        String skipOrgsEnv = System.getenv("SKIP_ORGS");
        if (skipOrgsEnv == null) skipOrgsEnv = "";
        this.skipOrgs = new ArrayList<>(Arrays.asList(skipOrgsEnv.split(",")));
        if (!this.skipOrgs.contains("intemo-dev")) this.skipOrgs.add("intemo-dev");
        this.skipOrgs.removeIf(String::isEmpty);
        this.gitHubApiService = new GitHubApiService(githubToken, this.githubUser);
        this.jiraApiService = new JiraApiService(jiraDomain, jiraProject, jiraAuth);
        this.jiraAssignee = System.getenv("JIRA_ASSIGNEE") != null ? System.getenv("JIRA_ASSIGNEE") : this.githubUser;
    }
    // endregion

    public void runCoreWorkflow(int sinceMinutes, int perPage, int maxPages) throws IOException {
        ZonedDateTime since = ZonedDateTime.now().minusMinutes(sinceMinutes);
        Map<String, Map<Long, GroupedIssueData>> groupedData = gatherAndGroupGitHubData(perPage, maxPages, since);
        if (groupedData.isEmpty()) {
            logger.warn("⚠️  No data found to process from recent events.");
        }
        createJiraObjectsFromGroupedData(groupedData);
    updatePullRequestStatusByLatestActivity(groupedData);
    updateReleasedTasks();

    // ...existing code...
    }

    private Map<String, Map<Long, GroupedIssueData>> gatherAndGroupGitHubData(int perPage, int maxPages, ZonedDateTime since) throws IOException {
        logger.info("\n📊 Step 1: Gathering all GitHub events...");
        List<GitHubData.Event> allEvents = gitHubApiService.fetchGitHubEvents(maxPages, perPage);
        List<GitHubData.Event> filteredEvents = allEvents.stream()
                .filter(e -> e.createdAt != null && e.createdAt.isAfter(since))
                .collect(Collectors.toList());

        logger.info("\n🗂️  Step 2: Grouping {} events by owner/repo/issue...", filteredEvents.size());
        Map<String, Map<Long, GroupedIssueData>> groupedData = new LinkedHashMap<>();
        for (GitHubData.Event event : filteredEvents) {
            if (event.repo == null || event.repo.name == null || !event.repo.name.contains("/")) continue;
            String owner = event.repo.name.split("/")[0];
            if (shouldSkipRepo(owner)) continue;

            for (long issueNum : extractIssueNumbersFromEvent(event)) {
                groupedData.computeIfAbsent(event.repo.name, k -> new LinkedHashMap<>())
                           .computeIfAbsent(issueNum, k -> new GroupedIssueData())
                           .events.add(event);
            }
        }

        logger.info("\n📈 Step 3: Analyzing status for each issue...");
        for (var repoEntry : groupedData.entrySet()) {
            String repoFullName = repoEntry.getKey();
            String owner = repoFullName.split("/")[0];
            String name = repoFullName.split("/")[1];
            for (var issueEntry : repoEntry.getValue().entrySet()) {
                long issueNum = issueEntry.getKey();
                GroupedIssueData data = issueEntry.getValue();
                logger.info("  🔍 Analyzing issue #{} in {}", issueNum, repoFullName);
                data.issueDetails = gitHubApiService.getIssueDetails(owner, name, issueNum).orElse(null);
                data.prInfo = analyzePrStatusForIssue(owner, name, issueNum);
                
                var statusTuple = determineFinalStatus(data);
                data.finalStatus = (String) statusTuple.get("status");
                data.statusReasons = (List<String>) statusTuple.get("reasons");

                logger.info("    📊 Final Status: {}", data.finalStatus);
                logger.info("    📝 Reasons: {}", String.join(", ", data.statusReasons));
            
            }
        }
        return groupedData;
    }
    private void createJiraObjectsFromGroupedData(Map<String, Map<Long, GroupedIssueData>> groupedData) throws IOException {
        logger.info("\n🎯 === CREATING JIRA OBJECTS (Process Later Queue System) ===");
        Map<String, String> createdEpicsCache = new HashMap<>();
        Map<Long, String> issueToJiraKeyCache = new HashMap<>();
        
        List<GroupedIssueDataContainer> pullRequestsToProcessLater = new ArrayList<>();

        logger.info("\n--- STAGE 1: Processing Core Issues and Queuing PRs ---");
        for (var repoEntry : groupedData.entrySet()) {
            String repoFullName = repoEntry.getKey();
            String owner = repoEntry.getKey().split("/")[0];
            String name = repoEntry.getKey().split("/")[1];
            if (shouldSkipRepo(owner)) continue;

            logger.info("\n📦 Scanning repository: {}", repoFullName);
            String epicKey = getOrCreateEpicForOwner(owner, createdEpicsCache);
            
            for (var issueEntry : repoEntry.getValue().entrySet()) {
                GroupedIssueData data = issueEntry.getValue();
                if (data.issueDetails != null) {
                    if (data.issueDetails.pullRequest == null) {
                        logger.info("  -> Processing plain issue #{}...", data.issueDetails.number);
                        createAndPostJiraTask(owner, name, data, epicKey)
                            .ifPresent(newKey -> issueToJiraKeyCache.put(data.issueDetails.number, newKey));
                    } else {
                        logger.info("  -> Queuing pull request #{} for later processing...", data.issueDetails.number);
                        pullRequestsToProcessLater.add(new GroupedIssueDataContainer(owner, name, data, epicKey));
                    }
                }
            }
        }

        logger.info("\n--- STAGE 2: Processing {} Queued Pull Requests ---", pullRequestsToProcessLater.size());
        for (GroupedIssueDataContainer prContainer : pullRequestsToProcessLater) {
            GroupedIssueData data = prContainer.data;
            long prNum = data.issueDetails.number;
            logger.info("  🔗 Dequeuing and processing pull request #{}...", prNum);

            Optional<Long> linkedIssueNumOpt = findLinkedIssueInTitleOrBody(data.issueDetails.title, data.issueDetails.body);
            if (linkedIssueNumOpt.isPresent()) {
                long linkedIssueNum = linkedIssueNumOpt.get();
                logger.info("    🔗 PR #{} links to issue #{}.", prNum, linkedIssueNum);
                
                String existingKey = issueToJiraKeyCache.get(linkedIssueNum);
                if (existingKey != null) {
                    logger.info("    ✅ Found task {} in local cache for linked issue. Updating it.", existingKey);
                    updateJiraTaskForPrActivity(existingKey, data);
                    continue;
                }

                String linkedIssueUrl = String.format("https://github.com/%s/%s/issues/%d", prContainer.owner, prContainer.name, linkedIssueNum);
                Optional<String> existingKeyOpt = searchExistingJiraTask(linkedIssueUrl, linkedIssueNum, prContainer.name, prContainer.owner);
                if (existingKeyOpt.isPresent()) {
                    logger.info("    ✅ Found existing task {} via API for linked issue. Updating it.", existingKeyOpt.get());
                    updateJiraTaskForPrActivity(existingKeyOpt.get(), data);
                    continue;
                }

                logger.warn("    ⚠️ No Jira task found for linked issue #{}. Proactively creating it now...", linkedIssueNum);
                Optional<GitHubData.Issue> originalIssueDetails = gitHubApiService.getIssueDetails(prContainer.owner, prContainer.name, linkedIssueNum);
                if (originalIssueDetails.isPresent()) {
                    GroupedIssueData originalIssueData = new GroupedIssueData();
                    originalIssueData.issueDetails = originalIssueDetails.get();
                    originalIssueData.finalStatus = data.finalStatus;
                    
                    createAndPostJiraTask(prContainer.owner, prContainer.name, originalIssueData, prContainer.epicKey)
                        .ifPresent(newKey -> {
                            try {
                                updateJiraTaskForPrActivity(newKey, data);
                            } catch (IOException e) {
                                logger.error("Failed to update newly created task {} for PR activity.", newKey, e);
                            }
                        });
                } else {
                     logger.error("    ❌ Could not fetch details for original issue #{}. Creating standalone task for PR #{}.", linkedIssueNum, prNum);
                     createAndPostJiraTask(prContainer.owner, prContainer.name, data, prContainer.epicKey);
                }
            } else {
                logger.info("    ℹ️ No issue link found in PR #{}. Processing as a standalone item.", prNum);
                createAndPostJiraTask(prContainer.owner, prContainer.name, data, prContainer.epicKey);
            }
        }
    }
    
    public void updateReleasedTasks() throws IOException {
        logger.info("\n--- FINAL STEP: Checking for Released Tasks (label-based) ---");
        String jql = String.format("project = \"%s\" AND status = \"Done\"", this.jiraProject);
        Optional<JiraData.SearchResult> resultOpt = jiraApiService.searchIssues(jql, 50);

        if (resultOpt.isEmpty() || resultOpt.get().total == 0) {
            logger.info("✅ No tasks found in 'Done' status to check for release.");
            return;
        }

        logger.info("📊 Found {} tasks in 'Done' status. Checking each for a real release...", resultOpt.get().total);
        for (JiraData.Issue task : resultOpt.get().issues) {
            JsonNode descriptionNode = task.fields.get("description");
            if (descriptionNode == null || !descriptionNode.isTextual()) continue;

            String description = descriptionNode.asText();
            Matcher matcher = Pattern.compile("\\*Repository:\\*\\s*([\\w.-]+)/([\\w.-]+)").matcher(description);
            if (matcher.find()) {
                String owner = matcher.group(1);
                String repo = matcher.group(2);
                logger.info("  🔍 Checking real release for task {} (repo: {}/{})", task.key, owner, repo);
                boolean hasRelease = false;
                try {
                    hasRelease = gitHubApiService.hasReleases(owner, repo);
                } catch (Exception e) {
                    logger.warn("    ⚠️ Error checking releases for {}/{}: {}", owner, repo, e.getMessage());
                }

                // Get current labels
                List<String> labels = new ArrayList<>();
                JsonNode labelsNode = task.fields.get("labels");
                if (labelsNode != null && labelsNode.isArray()) {
                    for (JsonNode labelNode : labelsNode) {
                        labels.add(labelNode.asText());
                    }
                }

                if (!hasRelease) {
                    // Add 'release log' label if not present, remove 'release' if present
                    if (!labels.contains("release log")) {
                        labels.add("release log");
                        logger.info("    🏷️  Adding 'release log' label to task {}.", task.key);
                    }
                    labels.remove("release");
                } else {
                    // Add 'release' label if not present, remove 'release log' if present
                    if (!labels.contains("release")) {
                        labels.add("release");
                        logger.info("    🏷️  Adding 'release' label to task {}.", task.key);
                    }
                    labels.remove("release log");
                }

                // Update labels if changed
                Set<String> newLabels = new LinkedHashSet<>(labels);
                if (!newLabels.equals(new LinkedHashSet<>(labels))) {
                    // Actually, always update to ensure sync
                    jiraApiService.updateIssueLabels(task.key, new ArrayList<>(newLabels));
                } else {
                    jiraApiService.updateIssueLabels(task.key, new ArrayList<>(newLabels));
                }
            }
        }
    }

    private Optional<String> createAndPostJiraTask(String owner, String name, GroupedIssueData data, String epicKey) throws IOException {
        GitHubData.Issue details = data.issueDetails;
        if (details == null) return Optional.empty();

        if (searchExistingJiraTask(details.htmlUrl, details.number, name, owner).isPresent()) {
            return Optional.empty();
        }

        String firstCommentBody = (details.body != null && !details.body.isEmpty()) ? details.body : "No description provided.";
        String taskSummary = String.format("#%d - %s", details.number, details.title);
        String description = buildCleanJiraDescription(owner, name, details, firstCommentBody);

    ObjectNode payload = mapper.createObjectNode();
    ObjectNode fields = payload.putObject("fields");
    fields.putObject("project").put("key", this.jiraProject);
    fields.put("summary", taskSummary);
    fields.put("description", description);
    fields.putObject("issuetype").put("name", "Task");
    fields.putArray("labels").add(name);
    // Assign the user
    fields.putObject("assignee").put("name", this.jiraAssignee);

        Optional<String> newKeyOpt = jiraApiService.createIssue(payload);
        if (newKeyOpt.isPresent()) {
            String newKey = newKeyOpt.get();
            logger.info("    ✅ Created task: {}", newKey);

            List<GitHubData.CommentLike> allComments = getAllComments(owner, name, details.number, data.prInfo.hasPr || details.pullRequest != null);
            for (GitHubData.CommentLike comment : allComments) {
                String formattedComment = String.format(
                    "*GitHub Comment by @%s at %s:*\n\n%s",
                    comment.getAuthorLogin(),
                    comment.getTimestamp().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")),
                    comment.getBodyText());
                jiraApiService.addComment(newKey, formattedComment);
            }

            if (epicKey != null) attachEpicPostCreation(newKey, epicKey);
            
            String jiraStatus = mapStatusToJiraWorkflow(data.finalStatus);
            if (jiraStatus != null) {
                jiraApiService.updateIssueStatus(newKey, jiraStatus);
            }
        }
        return newKeyOpt;
    }
    
    private void updateJiraTaskForPrActivity(String existingTaskKey, GroupedIssueData prData) throws IOException {
    String newStatus = mapStatusToJiraWorkflow(prData.finalStatus);
    jiraApiService.updateIssueStatus(existingTaskKey, newStatus);
    // Assign the user
    jiraApiService.updateIssueLabels(existingTaskKey, null); // No label change, but triggers update
    jiraApiService.updateIssueAssignee(existingTaskKey, this.jiraAssignee);
    logger.info("    🔄 Silently updated status for task {} to '{}' and assigned to '{}' based on PR activity.", existingTaskKey, newStatus, this.jiraAssignee);
    }
    
    // region Helper Methods

    /**
     * For each issue, checks if the latest activity is PR/PR commit (set status to PULL REQUEST),
     * or if a comment/PR review is latest after PR/commit (set to IN PROGRESS).
     * This is run before updateReleasedTasks().
     */
    private void updatePullRequestStatusByLatestActivity(Map<String, Map<Long, GroupedIssueData>> groupedData) {
        logger.info("\n--- SPECIAL STATUS CHECK: Updating status based on latest PR/commit/comment activity ---");
        for (var repoEntry : groupedData.entrySet()) {
            for (var issueEntry : repoEntry.getValue().entrySet()) {
                GroupedIssueData data = issueEntry.getValue();
                if (data.issueDetails == null) continue;

                boolean isPr = data.issueDetails.pullRequest != null;

                // Gather all relevant events with timestamps
                List<ActivityEvent> activities = new ArrayList<>();
                for (GitHubData.Event e : data.events) {
                    ZonedDateTime ts = e.createdAt;
                    if (ts == null) continue;
                    String type = e.type;
                    if ("PullRequestEvent".equals(type)) {
                        activities.add(new ActivityEvent(ts, "PR"));
                    } else if ("PushEvent".equals(type)) {
                        activities.add(new ActivityEvent(ts, "PR_COMMIT"));
                    } else if ("PullRequestReviewCommentEvent".equals(type)) {
                        activities.add(new ActivityEvent(ts, "PR_REVIEW_COMMENT"));
                    } else if ("IssueCommentEvent".equals(type)) {
                        activities.add(new ActivityEvent(ts, "COMMENT"));
                    }
                }
                if (activities.isEmpty()) continue;
                // Sort by timestamp
                activities.sort(Comparator.comparing(a -> a.timestamp));
                ActivityEvent latest = activities.get(activities.size() - 1);

                // Find if there was a PR/commit before the latest comment/review
                boolean hadPrOrCommit = activities.stream().anyMatch(a ->
                    ("PR".equals(a.kind) || "PR_COMMIT".equals(a.kind)) && a.timestamp.isBefore(latest.timestamp)
                );

                if ("PR".equals(latest.kind) || "PR_COMMIT".equals(latest.kind)) {
                    data.finalStatus = "PULL REQUEST";
                    data.statusReasons = List.of("Latest activity is PR or PR commit");
                } else if (("PR_REVIEW_COMMENT".equals(latest.kind) || "COMMENT".equals(latest.kind)) && hadPrOrCommit) {
                    data.finalStatus = "IN PROGRESS";
                    data.statusReasons = List.of("Latest activity is comment/review after PR or commit");
                } else if ("COMMENT".equals(latest.kind) && !isPr) {
                    // If it's a regular issue and latest is a comment, set IN PROGRESS
                    data.finalStatus = "IN PROGRESS";
                    data.statusReasons = List.of("Latest activity is comment on issue");
                }
            }
        }
    }

    // Helper class for activity events
    private static class ActivityEvent {
        ZonedDateTime timestamp;
        String kind;
        ActivityEvent(ZonedDateTime timestamp, String kind) {
            this.timestamp = timestamp;
            this.kind = kind;
        }
    }
    
    private List<GitHubData.CommentLike> getAllComments(String owner, String repo, long number, boolean isPr) throws IOException {
        List<GitHubData.CommentLike> allComments = new ArrayList<>();
        allComments.addAll(gitHubApiService.getIssueComments(owner, repo, number));
        if (isPr) {
            allComments.addAll(gitHubApiService.getPullRequestReviewComments(owner, repo, number));
            allComments.addAll(gitHubApiService.getPullRequestReviews(owner, repo, number));
        }
        allComments.sort(Comparator.comparing(GitHubData.CommentLike::getTimestamp));
        return allComments;
    }

    private boolean checkReleaseStatus(String owner, String repo) throws IOException {
        List<GitHubData.Release> releases = gitHubApiService.fetchReleases(owner, repo, 5);
        if (releases.isEmpty()) {
            return false;
        }
        GitHubData.Release latestRelease = releases.get(0);
        if (latestRelease.publishedAt != null) {
            long daysSinceRelease = Duration.between(latestRelease.publishedAt, ZonedDateTime.now()).toDays();
            return daysSinceRelease <= 30;
        }
        return false;
    }

    private String buildCleanJiraDescription(String owner, String name, GitHubData.Issue details, String firstComment) {
        return String.format(
            "*Repository:* %s/%s\n" +
            "*Issue/PR:* #%d - %s\n" +
            "*Author:* @%s\n" +
            "*URL:* %s\n\n" +
            "----\n\n" +
            "*Original Issue Description:*\n\n{noformat}\n%s\n{noformat}",
            owner, name, 
            details.number, details.title,
            details.user != null ? details.user.login : "unknown",
            details.htmlUrl,
            firstComment
        );
    }

    private Optional<Long> findLinkedIssueInTitleOrBody(String title, String body) {
        Pattern pattern = Pattern.compile("(?i)(?:closes|fixes|resolves)\\s+#(\\d+)", Pattern.DOTALL);
        if (title != null && !title.isEmpty()) {
            Matcher titleMatcher = pattern.matcher(title);
            if (titleMatcher.find()) { return Optional.of(Long.parseLong(titleMatcher.group(1))); }
        }
        if (body != null && !body.isEmpty()) {
            Matcher bodyMatcher = pattern.matcher(body);
            if (bodyMatcher.find()) { return Optional.of(Long.parseLong(bodyMatcher.group(1))); }
        }
        return Optional.empty();
    }
    
    private Optional<String> searchExistingJiraTask(String issueUrl, long issueNumber, String repoName, String repoOwner) throws IOException {
        String escapedUrl = issueUrl.replace("\\", "\\\\").replace("\"", "\\\"");
        String summaryPattern = "#" + issueNumber;
        String jql = String.format(
            "project = \"%s\" AND issuetype = Task AND (description ~ \"%s\" OR summary ~ \"%s\")",
            this.jiraProject, escapedUrl, summaryPattern);
        
        Optional<JiraData.SearchResult> resultOpt = jiraApiService.searchIssues(jql, 10);
        if (resultOpt.isPresent() && resultOpt.get().total > 0) {
            for (JiraData.Issue issue : resultOpt.get().issues) {
                JsonNode fields = issue.fields;
                String description = fields.has("description") ? fields.get("description").asText("").toLowerCase() : "";
                String summary = fields.has("summary") ? fields.get("summary").asText("").toLowerCase() : "";
                
                if (description.contains(issueUrl.toLowerCase())) { return Optional.of(issue.key); }
                if (summary.contains(summaryPattern.toLowerCase()) && summary.contains(repoName.toLowerCase()) && (summary.contains(repoOwner.toLowerCase()) || description.contains(repoOwner.toLowerCase()))) {
                    return Optional.of(issue.key);
                }
            }
        }
        return Optional.empty();
    }

    private boolean shouldSkipRepo(String repoOwner) {
        return repoOwner.equalsIgnoreCase(this.githubUser) || this.skipOrgs.stream().anyMatch(org -> org.equalsIgnoreCase(repoOwner));
    }

    private Set<Long> extractIssueNumbersFromEvent(GitHubData.Event event) {
        Set<Long> numbers = new HashSet<>();
        if (event.payload == null) return numbers;
        if (event.payload.issue != null) numbers.add(event.payload.issue.number);
        if (event.payload.pullRequest != null) numbers.add(event.payload.pullRequest.number);
        if (event.payload.comment != null && event.payload.comment.body != null) {
            Matcher m = Pattern.compile("#(\\d+)").matcher(event.payload.comment.body);
            while (m.find()) numbers.add(Long.parseLong(m.group(1)));
        }
        return numbers;
    }

    private String getOrCreateEpicForOwner(String owner, Map<String, String> cache) throws IOException {
        if (cache.containsKey(owner)) return cache.get(owner);
        String jql = String.format("project = \"%s\" AND issuetype = Epic AND summary ~ \"%s\"", jiraProject, owner);
        Optional<JiraData.SearchResult> result = jiraApiService.searchIssues(jql, 1);
        if (result.isPresent() && result.get().total > 0) {
            String key = result.get().issues.get(0).key;
            cache.put(owner, key);
            return key;
        }
        ObjectNode payload = mapper.createObjectNode();
        ObjectNode fields = payload.putObject("fields");
        fields.putObject("project").put("key", jiraProject);
        fields.put("summary", owner);
        fields.put("description", "Epic for tracking GitHub contributions to repositories owned by " + owner);
        fields.putObject("issuetype").put("name", "Epic");
        Optional<String> newKey = jiraApiService.createIssue(payload);
        newKey.ifPresent(key -> cache.put(owner, key));
        return newKey.orElse(null);
    }

    /**
     * DEFINITIVE FIX: This method is now smarter and gets complete data.
     */
    private PRInfo analyzePrStatusForIssue(String owner, String repo, long issueNum) throws IOException {
        PRInfo info = new PRInfo();
        
        // First, check if the item is a PR itself by calling the reliable Pulls API
        Optional<GitHubData.PullRequest> prOpt = gitHubApiService.getPullRequestDetails(owner, repo, issueNum);
        if (prOpt.isPresent()) {
            GitHubData.PullRequest pr = prOpt.get();
            info.hasPr = true; 
            info.isPrItself = true; 
            info.prNumber = pr.number;
            info.prState = pr.state; 
            info.isMerged = pr.merged;
            if (pr.head != null) info.prBranch = pr.head.ref;
            return info;
        }

        // If it's a plain issue, search for linked PRs that mention it
        List<GitHubData.PullRequest> linkedPrs = gitHubApiService.searchPullRequestsForIssue(owner, repo, issueNum);
        if (!linkedPrs.isEmpty()) {
            GitHubData.PullRequest foundPr = linkedPrs.get(0);
            
            // CRITICAL STEP: Get the FULL details of the found PR to get the correct 'merged' status
            Optional<GitHubData.PullRequest> fullPrDetails = gitHubApiService.getPullRequestDetails(owner, repo, foundPr.number);
            if(fullPrDetails.isPresent()){
                GitHubData.PullRequest pr = fullPrDetails.get();
                info.hasPr = true; 
                info.isPrItself = false; 
                info.prNumber = pr.number;
                info.prState = pr.state; 
                info.isMerged = pr.merged;
                if (pr.head != null) info.prBranch = pr.head.ref;
            }
        }
        return info;
    }
    
    /**
     * DEFINITIVE FIX: This method has been completely rewritten to match your Status Flow proposal exactly.
     */
    private Map<String, Object> determineFinalStatus(GroupedIssueData data) {
        List<String> reasons = new ArrayList<>();
        String status;
        PRInfo prInfo = data.prInfo;

        // Priority 1: MERGED -> DONE
        if (prInfo != null && prInfo.isMerged) {
            status = "DONE";
            reasons.add("PR merged");
        }
        // Priority 3: BACKWARD FLOW (OPEN PR + ACTIVITY) -> IN PROGRESS
        else if (prInfo != null && "open".equals(prInfo.prState) && hasRecentPrActivity(data)) {
            status = "IN PROGRESS";
            reasons.add("Activity (comment/push) on an open PR");
        }
        // Priority 4: FORWARD FLOW (OPEN PR, NO ACTIVITY) -> PULL REQUEST
        else if (prInfo != null && "open".equals(prInfo.prState)) {
            status = "PULL REQUEST";
            reasons.add("Open PR exists");
        }
        // Priority 5: COMMITS ON BRANCH -> IN PROGRESS
        else if (hasPushEvents(data)) {
            status = "IN PROGRESS";
            reasons.add("Commits on branch");
        }
        // Priority 6: BRANCH CREATED -> TODO
        else if (hasBranchCreationEvent(data)) {
            status = "TODO";
            reasons.add("Branch created");
        }
        // Priority 7: COMMENT ONLY / FALLBACK (includes closed PRs) -> DISCUSSION
        else {
            status = "DISCUSSION";
            reasons.add("Comment activity only");
            
        }
        return Map.of("status", status, "reasons", reasons);
    }
    
    private boolean hasRecentPrActivity(GroupedIssueData data) {
        // Exclude the initial "opened" event from counting as activity
        return data.events.stream().anyMatch(e -> {
            if (e.payload != null && "opened".equals(e.payload.action)) return false;
            return "IssueCommentEvent".equals(e.type) || 
                   "PullRequestReviewCommentEvent".equals(e.type) ||
                   "PushEvent".equals(e.type);
        });
    }
    private boolean hasPushEvents(GroupedIssueData data) {
        return data.events.stream().anyMatch(e -> "PushEvent".equals(e.type));
    }
    private boolean hasBranchCreationEvent(GroupedIssueData data) {
        return data.events.stream().anyMatch(e -> 
            e.payload != null && 
            "CreateEvent".equals(e.type) && 
            "branch".equals(e.payload.refType));
    }

    private String getEpicLinkFieldId() throws IOException {
        if (this.epicLinkFieldId != null) return this.epicLinkFieldId;
        Optional<String> fieldId = jiraApiService.getAllFields().stream()
            .filter(f -> "Epic Link".equalsIgnoreCase(f.name))
            .map(f -> f.id).findFirst();
        fieldId.ifPresent(id -> this.epicLinkFieldId = id);
        return fieldId.orElse(null);
    }

    private void attachEpicPostCreation(String taskKey, String epicKey) throws IOException {
        String fieldId = getEpicLinkFieldId();
        if (fieldId != null) {
            jiraApiService.attachToEpic(taskKey, epicKey, fieldId);
        }
    }

    /**
     * DEFINITIVE FIX: This method now correctly maps DISCUSSION to a sensible default
     * like "Backlog" to avoid placing it in "To Do" incorrectly.
     */
    private String mapStatusToJiraWorkflow(String internalStatus) {
        switch (internalStatus) {
            case "DONE": return "DONE";
            case "IN PROGRESS": return "IN PROGRESS";
            case "PULL REQUEST": return "PULL REQUEST";
            case "TODO": return "TODO";
            case "DISCUSSION": return "DISCUSSION"; // Map to Jira 'Discuss' status
            default: return "DISCUSSION";
        }
    }
    // endregion
    // region Inner Classes
    static class GroupedIssueData {
        GitHubData.Issue issueDetails;
        List<GitHubData.Event> events = new ArrayList<>();
        PRInfo prInfo = new PRInfo(); // <<-- FIX for NullPointerException
        String finalStatus;
        List<String> statusReasons;
    }
    static class PRInfo {
        boolean hasPr = false;
        boolean isPrItself = false;
        boolean isMerged = false;
        long prNumber;
        String prState;
        String prBranch;
    }
    static class GroupedIssueDataContainer {
        String owner, name, epicKey;
        GroupedIssueData data;
        GroupedIssueDataContainer(String owner, String name, GroupedIssueData data, String epicKey) {
            this.owner = owner;
            this.name = name;
            this.data = data;
            this.epicKey = epicKey;
        }
    }
    // endregion
}