package com.githubeventstojira.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.githubeventstojira.model.JiraData;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

public class JiraApiService {
    private static final Logger logger = LoggerFactory.getLogger(JiraApiService.class);
    private final OkHttpClient client;
    private final ObjectMapper mapper;
    private final String domain;
    private final String projectKey;
    private final String authHeader;
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    public JiraApiService(String domain, String project, String auth) {
        this.client = new OkHttpClient();
        this.mapper = new ObjectMapper();
        this.domain = domain;
        this.projectKey = project;
        this.authHeader = "Basic " + auth;
    }

    private Request.Builder newAuthenticatedRequest() {
        return new Request.Builder()
                .addHeader("Authorization", this.authHeader)
                .addHeader("Accept", "application/json");
    }

    public Optional<JiraData.SearchResult> searchIssues(String jql, int maxResults) throws IOException {
        HttpUrl url = new HttpUrl.Builder()
                .scheme("https")
                .host(domain)
                .addPathSegments("rest/api/2/search")
                .addQueryParameter("jql", jql)
                .addQueryParameter("maxResults", String.valueOf(maxResults))
                .build();
        Request request = newAuthenticatedRequest().url(url).build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return Optional.of(mapper.readValue(response.body().string(), JiraData.SearchResult.class));
            }
            logger.error("⚠️ JIRA search failed: {} - {}", response.code(), response.body().string());
            return Optional.empty();
        }
    }

    public Optional<String> createIssue(ObjectNode payload) throws IOException {
        RequestBody body = RequestBody.create(payload.toString(), JSON);
        Request request = newAuthenticatedRequest()
                .url("https://" + domain + "/rest/api/2/issue")
                .post(body)
                .build();
        try (Response response = client.newCall(request).execute()) {
            String responseBody = response.body().string();
            if (response.isSuccessful()) {
                return Optional.of(mapper.readTree(responseBody).get("key").asText());
            }
            logger.error("❌ Failed to create JIRA task: {} - {}", response.code(), responseBody);
            return Optional.empty();
        }
    }

    public boolean updateIssueStatus(String issueKey, String targetStatusName) throws IOException {
        Request transitionsRequest = newAuthenticatedRequest()
                .url(String.format("https://" + domain + "/rest/api/2/issue/%s/transitions", issueKey))
                .build();
        List<JiraData.Transition> transitions;
        try (Response response = client.newCall(transitionsRequest).execute()) {
            if (!response.isSuccessful()) return false;
            transitions = mapper.convertValue(mapper.readTree(response.body().string()).get("transitions"), new TypeReference<>() {});
        }

        Optional<String> transitionId = transitions.stream()
                .filter(t -> t.to.name.equalsIgnoreCase(targetStatusName))
                .map(t -> t.id)
                .findFirst();

        if (transitionId.isEmpty()) {
            logger.warn("    ⚠️  No transition found to move {} to {}", issueKey, targetStatusName);
            return false;
        }

        ObjectNode transitionPayload = mapper.createObjectNode();
        transitionPayload.set("transition", mapper.createObjectNode().put("id", transitionId.get()));
        RequestBody body = RequestBody.create(transitionPayload.toString(), JSON);

        Request updateRequest = newAuthenticatedRequest()
                .url(String.format("https://" + domain + "/rest/api/2/issue/%s/transitions", issueKey))
                .post(body)
                .build();
        try (Response response = client.newCall(updateRequest).execute()) {
            return response.isSuccessful();
        }
    }
    
    public boolean addComment(String issueKey, String comment) throws IOException {
        ObjectNode payload = mapper.createObjectNode().put("body", comment);
        RequestBody body = RequestBody.create(payload.toString(), JSON);
        Request request = newAuthenticatedRequest()
                .url(String.format("https://" + domain + "/rest/api/2/issue/%s/comment", issueKey))
                .post(body)
                .build();
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                logger.error("      ❌ Failed to add comment to {}: {} - {}", issueKey, response.code(), response.body().string());
            }
            return response.isSuccessful();
        }
    }

    public List<JiraData.Field> getAllFields() throws IOException {
        Request request = newAuthenticatedRequest().url("https://" + domain + "/rest/api/2/field").build();
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                return mapper.readValue(response.body().string(), new TypeReference<>() {});
            }
        }
        return Collections.emptyList();
    }

    public boolean attachToEpic(String taskKey, String epicKey, String epicLinkFieldId) throws IOException {
        ObjectNode fields = mapper.createObjectNode().put(epicLinkFieldId, epicKey);
        ObjectNode payload = mapper.createObjectNode().set("fields", fields);
        RequestBody body = RequestBody.create(payload.toString(), JSON);
        Request request = newAuthenticatedRequest()
            .url(String.format("https://" + domain + "/rest/api/2/issue/%s", taskKey))
            .put(body)
            .build();
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                logger.error("    ❌ Failed to attach Epic: {} {}", response.code(), response.body().string());
            }
            return response.isSuccessful();
        }
    }
    public List<String> getIssueComments(String issueKey) throws IOException {
        Request request = newAuthenticatedRequest()
                .url(String.format("https://" + domain + "/rest/api/2/issue/%s?fields=comment", issueKey))
                .build();
        
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                JsonNode root = mapper.readTree(response.body().string());
                JsonNode commentsNode = root.at("/fields/comment/comments");
                if (commentsNode.isArray()) {
                    return StreamSupport.stream(commentsNode.spliterator(), false)
                            .map(commentNode -> commentNode.get("body").asText(""))
                            .collect(Collectors.toList());
                }
            }
        }
        return Collections.emptyList();
    }
}