package com.githubeventstojira.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.githubeventstojira.model.GitHubData;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

public class GitHubApiService {
    // Check if a repository has any releases
    public boolean hasReleases(String owner, String repo) throws IOException {
        List<GitHubData.Release> releases = fetchReleases(owner, repo, 1);
        return !releases.isEmpty();
    }
    // List branches for a repository
    public List<GitHubData.Branch> listBranches(String owner, String repo) throws IOException {
        String url = String.format("%s/repos/%s/%s/branches", API_BASE, owner, repo);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    // List commits for a repository or branch
    public List<GitHubData.Commit> listCommits(String owner, String repo, String branch) throws IOException {
        String url = String.format("%s/repos/%s/%s/commits", API_BASE, owner, repo);
        HttpUrl.Builder urlBuilder = Objects.requireNonNull(HttpUrl.parse(url)).newBuilder();
        if (branch != null && !branch.isEmpty()) {
            urlBuilder.addQueryParameter("sha", branch);
        }
        Request request = newAuthenticatedRequest().url(urlBuilder.build()).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    // List forks for a repository
    public List<GitHubData.Fork> listForks(String owner, String repo) throws IOException {
        String url = String.format("%s/repos/%s/%s/forks", API_BASE, owner, repo);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    // List comments on a pull request (not review comments)
    public List<GitHubData.Comment> getPullRequestComments(String owner, String repo, long prNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/issues/%d/comments", API_BASE, owner, repo, prNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }
    private static final Logger logger = LoggerFactory.getLogger(GitHubApiService.class);
    private final OkHttpClient client;
    private final ObjectMapper mapper;
    private final String token;
    private final String user;
    private static final String API_BASE = "https://api.github.com";

    public GitHubApiService(String token, String user) {
        this.client = new OkHttpClient();
        this.mapper = new ObjectMapper().registerModule(new JavaTimeModule());
        this.token = token;
        this.user = user;
    }

    private Request.Builder newAuthenticatedRequest() {
        return new Request.Builder()
                .addHeader("Authorization", "token " + this.token)
                .addHeader("Accept", "application/vnd.github.v3+json");
    }

    public List<GitHubData.Event> fetchGitHubEvents(int maxPages, int perPage) throws IOException {
        List<GitHubData.Event> allEvents = new ArrayList<>();
        String urlTemplate =  API_BASE + "/users/" + this.user + "/events";

        for (int page = 1; page <= maxPages; page++) {
            HttpUrl url = Objects.requireNonNull(HttpUrl.parse(urlTemplate)).newBuilder()
                    .addQueryParameter("per_page", String.valueOf(perPage))
                    .addQueryParameter("page", String.valueOf(page))
                    .build();

            Request request = newAuthenticatedRequest().url(url).build();
            try (Response response = client.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    logger.error("GitHub API error fetching events: {} - {}", response.code(), response.body() != null ? response.body().string() : "No body");
                    break;
                }
                List<GitHubData.Event> pageEvents = mapper.readValue(response.body().string(), new TypeReference<>() {});
                if (pageEvents.isEmpty() || pageEvents.size() < perPage) {
                    allEvents.addAll(pageEvents);
                    break;
                }
                allEvents.addAll(pageEvents);
            }
        }
        logger.info("✅ Total events fetched: {}", allEvents.size());
        return allEvents;
    }

    public Optional<GitHubData.Issue> getIssueDetails(String owner, String repo, long issueNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/issues/%d", API_BASE, owner, repo, issueNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return Optional.of(mapper.readValue(response.body().string(), GitHubData.Issue.class));
            }
            logger.warn("    ⚠️  Could not fetch issue #{}: {}", issueNum, response.code());
            return Optional.empty();
        }
    }

    public Optional<GitHubData.PullRequest> getPullRequestDetails(String owner, String repo, long prNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/pulls/%d", API_BASE, owner, repo, prNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return Optional.of(mapper.readValue(response.body().string(), GitHubData.PullRequest.class));
            }
            return Optional.empty();
        }
    }
    
    public List<GitHubData.Comment> getIssueComments(String owner, String repo, long issueNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/issues/%d/comments", API_BASE, owner, repo, issueNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    public List<GitHubData.ReviewComment> getPullRequestReviewComments(String owner, String repo, long prNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/pulls/%d/comments", API_BASE, owner, repo, prNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    public List<GitHubData.Review> getPullRequestReviews(String owner, String repo, long prNum) throws IOException {
        String url = String.format("%s/repos/%s/%s/pulls/%d/reviews", API_BASE, owner, repo, prNum);
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    public List<GitHubData.PullRequest> searchPullRequestsForIssue(String owner, String repo, long issueNum) throws IOException {
        String query = String.format("%d in:body is:pr repo:%s/%s", issueNum, owner, repo);
        HttpUrl url = Objects.requireNonNull(HttpUrl.parse(API_BASE + "/search/issues")).newBuilder()
                .addQueryParameter("q", query)
                .build();
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                GitHubData.SearchResult<GitHubData.PullRequest> result = mapper.readValue(response.body().string(), new TypeReference<>() {});
                return result.items;
            }
        }
        return Collections.emptyList();
    }

    public List<GitHubData.Release> fetchReleases(String owner, String repo, int perPage) throws IOException {
        String url = String.format("%s/repos/%s/%s/releases", API_BASE, owner, repo);
        HttpUrl httpUrl = Objects.requireNonNull(HttpUrl.parse(url)).newBuilder()
                .addQueryParameter("per_page", String.valueOf(perPage))
                .build();
        Request request = newAuthenticatedRequest().url(httpUrl).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }
}