package com.githubeventstojira.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class JiraData {
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SearchResult {
        public int total;
        public List<Issue> issues;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Issue {
        public String id;
        public String key;
        public JsonNode fields;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Field {
        public String id;
        public String name;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Transition {
        public String id;
        public String name;
        public Status to;
    }
    
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Status { public String name; }
}