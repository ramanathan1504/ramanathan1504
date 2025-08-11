package com.githubeventstojira.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.ZonedDateTime;
import java.util.List;

/**
 * This file contains a complete set of DTOs (Data Transfer Objects)
 * to accurately model the JSON structure of various GitHub Webhook Events.
 * Each class is annotated with @JsonIgnoreProperties(ignoreUnknown = true)
 * to make the parsing robust against new or unexpected fields from the API.
 */
public class GitHubEventData {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Event {
        public String id;
        public String type;
        public Actor actor;
        public Repo repo;
        public Payload payload;
        @JsonProperty("public") public boolean isPublic;
        @JsonProperty("created_at") public ZonedDateTime createdAt;
        public Org org;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Actor {
        public long id;
        public String login;
        @JsonProperty("display_login") public String displayLogin;
        @JsonProperty("avatar_url") public String avatarUrl;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Repo {
        public long id;
        public String name;
        public String url;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Org {
        public long id;
        public String login;
        @JsonProperty("avatar_url") public String avatarUrl;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Payload {
        // Common fields
        public String action;
        
        // IssueCommentEvent, PullRequestReviewCommentEvent
        public Issue issue;
        public Comment comment;

        // PullRequestEvent, PullRequestReviewEvent, PullRequestReviewCommentEvent
        @JsonProperty("pull_request") public PullRequest pullRequest;
        
        // PullRequestReviewEvent
        public Review review;

        // PushEvent
        public String ref;
        public List<Commit> commits;

        // CreateEvent, DeleteEvent
        @JsonProperty("ref_type") public String refType;
        @JsonProperty("master_branch") public String masterBranch;

        // ForkEvent
        public Forkee forkee;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Issue {
        public long id;
        public long number;
        public String title;
        public String body;
        public User user;
        public String state;
        @JsonProperty("html_url") public String htmlUrl;
        @JsonProperty("comments_url") public String commentsUrl;
        @JsonProperty("created_at") public ZonedDateTime createdAt;
        public List<Label> labels;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PullRequest {
        public long id;
        public long number;
        public String state;
        public String title;
        public String body;
        public User user;
        public boolean merged;
        @JsonProperty("html_url") public String htmlUrl;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Comment {
        public long id;
        public String body;
        public User user;
        @JsonProperty("created_at") public ZonedDateTime createdAt;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Review {
        public long id;
        public String state;
        public String body;
        public User user;
        @JsonProperty("submitted_at") public ZonedDateTime submittedAt;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Commit {
        public String sha;
        public String message;
        public Author author;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Forkee {
        public long id;
        public String name;
        @JsonProperty("full_name") public String fullName;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class User {
        public long id;
        public String login;
        @JsonProperty("avatar_url") public String avatarUrl;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Label {
        public long id;
        public String name;
        public String color;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Author {
        public String name;
        public String email;
    }
}