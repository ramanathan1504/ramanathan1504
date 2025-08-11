package com.githubeventstojira.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.githubeventstojira.model.GitHubData.CommentLike;

import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GitHubData {
    
    // Base class for any item with a user, body, and creation date
    public static abstract class CommentLike {
        public long id; // Add ID for fingerprinting
        public User user;
        public String body;
        public abstract ZonedDateTime getTimestamp();
        public abstract String getAuthorLogin();
        public abstract String getBodyText();
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Event {
        public String type;
        public Repo repo;
        public Payload payload;
        @JsonProperty("created_at") public ZonedDateTime createdAt;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Repo {
        public String name;
        public String url;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Payload {
        public String action;
        public Issue issue;
        @JsonProperty("pull_request") public PullRequest pullRequest;
        public Comment comment;
        public String ref;
        @JsonProperty("ref_type") public String refType;
        public List<Commit> commits;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Issue {
        public long number;
        public String title;
        public String body;
        @JsonProperty("html_url") public String htmlUrl;
        public String state;
        public User user;
        @JsonProperty("created_at") public ZonedDateTime createdAt;
        @JsonProperty("pull_request") public Map<String, Object> pullRequest;
        @JsonProperty("comments_url") public String commentsUrl;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PullRequest {
        public long number;
        public String state;
        public boolean merged;
        public Head head;
        public String title;
        public String body; 
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Head { public String ref; }

     @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Comment extends CommentLike {
        @JsonProperty("created_at") public ZonedDateTime createdAt;
        @Override public ZonedDateTime getTimestamp() { return createdAt; }
        @Override public String getAuthorLogin() { return user != null ? user.login : "unknown"; }
        @Override public String getBodyText() { return body; }
    }
    
   @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ReviewComment extends CommentLike {
        @JsonProperty("created_at") public ZonedDateTime createdAt;
        @Override public ZonedDateTime getTimestamp() { return createdAt; }
        @Override public String getAuthorLogin() { return user != null ? user.login : "unknown"; }
        @Override public String getBodyText() { return body; }
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Review extends CommentLike {
        public String state;
        @JsonProperty("submitted_at") public ZonedDateTime submittedAt;
        @Override public ZonedDateTime getTimestamp() { return submittedAt; }
        @Override public String getAuthorLogin() { return user != null ? user.login : "unknown"; }
        @Override public String getBodyText() {
            return String.format("[%s] %s", state, (body != null && !body.isEmpty() ? body : "No comment body."));
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class User { public String login; }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Commit { public String message; }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Release {
        @JsonProperty("tag_name") public String tagName;
        @JsonProperty("published_at") public ZonedDateTime publishedAt;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SearchResult<T> {
        @JsonProperty("total_count") public int totalCount;
        public List<T> items;
    }
}