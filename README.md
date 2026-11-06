<h1 align="left">Hi, I'm Ramanathan Muthu 👋</h1>

<h3 align="left">Infrastructure Architect · Apache Log4j Committer · Performance Engineer</h3>

I maintain the logging library that a large share of the Java ecosystem runs on, and I work on making JVM backends fast, concurrent and reliable.

<p align="left">
  <a href="https://github.com/sponsors/ramanathan1504"><img src="https://img.shields.io/badge/Sponsor-❤-ea4aaa?style=flat-square&logo=githubsponsors&logoColor=white" alt="Sponsor"></a>
  <a href="https://people.apache.org/phonebook.html?uid=ramanathan"><img src="https://img.shields.io/badge/ASF-Committer-D22128?style=flat-square&logo=apache&logoColor=white" alt="ASF Committer"></a>
  <a href="mailto:ramanathan@apache.org"><img src="https://img.shields.io/badge/ramanathan%40apache.org-555?style=flat-square&logo=apache&logoColor=white" alt="Apache Email"></a>
  <a href="mailto:ramanathanbscmca@gmail.com"><img src="https://img.shields.io/badge/Gmail-ramanathanbscmca-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Gmail"></a>
  <a href="https://linkedin.com/in/ramanathan1504"><img src="https://img.shields.io/badge/LinkedIn-ramanathan1504-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
</p>

---

## 🪵 Apache Log4j at a glance

<p align="left">
  <a href="https://github.com/apache/logging-log4j2/pulls?q=is%3Apr+author%3Aramanathan1504+is%3Amerged"><img src="https://img.shields.io/github/issues-search/apache/logging-log4j2?query=is%3Apr%20author%3Aramanathan1504%20is%3Amerged&label=merged%20PRs&style=flat-square&color=2ea44f" alt="Merged PRs"></a>
  <a href="https://github.com/apache/logging-log4j2/commits/2.x/?author=ramanathan1504"><img src="https://img.shields.io/github/commit-activity/t/apache/logging-log4j2/2.x?authorFilter=ramanathan1504&label=2.x%20commits&style=flat-square&color=fb8c00" alt="Commits on 2.x"></a>
  <a href="https://github.com/apache/logging-log4j2/pulls?q=is%3Apr+reviewed-by%3Aramanathan1504"><img src="https://img.shields.io/github/issues-search/apache/logging-log4j2?query=is%3Apr%20reviewed-by%3Aramanathan1504&label=PRs%20reviewed&style=flat-square&color=0969da" alt="PRs reviewed"></a>
  <a href="https://github.com/apache/logging-log4j2/issues?q=author%3Aramanathan1504"><img src="https://img.shields.io/github/issues-search/apache/logging-log4j2?query=author%3Aramanathan1504&label=issues%20%2B%20PRs%20opened&style=flat-square&color=6e7781" alt="Issues and PRs opened"></a>
  <img src="https://img.shields.io/badge/releases%20managed-2.26.1%20·%202.25.5-8250df?style=flat-square" alt="Releases managed">
  <a href="https://insights.linuxfoundation.org/project/apache-logging-log4j2"><img src="https://img.shields.io/badge/LFX%20Insights-Log4j%20activity-003366?style=flat-square&logo=linuxfoundation&logoColor=white" alt="LFX Insights"></a>
</p>

📊 **Most active Log4j contributor right now**: about **50%** of all project activity over the last 3 months and **40%** over the last 6 months, per [LFX Insights](https://insights.linuxfoundation.org/project/apache-logging-log4j2).

- 🚀 **Release manager**: shipped [2.26.1](https://github.com/apache/logging-log4j2/releases/tag/rel%2F2.26.1) and [2.25.5](https://github.com/apache/logging-log4j2/releases/tag/rel%2F2.25.5) to Maven Central in the same week. 2.26.1 unblocked Apache Spark's upgrade.
- 🛡️ **Security team**: member of the Apache Logging Services security team (`security@logging.apache.org`), working on vulnerability triage.
- 🔍 **Reviewer**: 100+ pull requests reviewed, most of them from other contributors.

---

## 🌟 Selected contributions

### [Apache Log4j](https://github.com/apache/logging-log4j2) — *Committer*
| PR | What it does |
| :--- | :--- |
| [#4171](https://github.com/apache/logging-log4j2/pull/4171) | **Native W3C Trace Context in `LogEvent`**: a `TraceContextProvider` SPI for `traceId`/`spanId` that removes the async MDC map-cloning overhead |
| [#4133](https://github.com/apache/logging-log4j2/pull/4133) | **Stack traces for broken exception identity**: `IdentityHashMap`-based fix, cross-referenced by Apache Spark and OpenSearch |
| [#4186](https://github.com/apache/logging-log4j2/pull/4186) | **MDC filtering in JSON Template Layout**: allow/deny key filters, and MDC can no longer overwrite ECS fields |
| [#4111](https://github.com/apache/logging-log4j2/pull/4111) | **Thread-safe `ListAppender`**: redesigned for concurrent tests |
| [#4071](https://github.com/apache/logging-log4j2/pull/4071) | **Max compression delay for rollover**: spreads compression I/O across nodes |
| [#4070](https://github.com/apache/logging-log4j2/pull/4070) | **Web context isolation**: keeps `ServletContext` storage apart from the legacy external context to avoid Spring Boot collisions |
| [#4116](https://github.com/apache/logging-log4j2/pull/4116) | **Properties config filter fix**: correct `onMatch`/`onMismatch` handling and a modernized builder API |
| [#4124](https://github.com/apache/logging-log4j2/pull/4124) | **Disruptor `LinkageError` diagnostics**: clear errors for incompatible LMAX Disruptor versions |
| [#3951](https://github.com/apache/logging-log4j2/pull/3951) | **Elasticsearch 9.x**: upgraded `elasticsearch-java` |

### Beyond Log4j
| Project | Contribution |
| :--- | :--- |
| [Canonical](https://github.com/canonical) · openssl-fips-java #101 | **FIPS native layer**: Java `Key` → OpenSSL 3.x `EVP_PKEY` via `OSSL_DECODER`, plus a JNI → FFM (Foreign Function & Memory API) proposal |
| [Canonical](https://github.com/canonical) · devpack-for-spring-cli #78 | **Maven goal mapping**: run plugin goals without declaring them in `pom.xml` |
| [JReleaser](https://github.com/jreleaser/jreleaser) · [#1940](https://github.com/jreleaser/jreleaser/pull/1940), [#1954](https://github.com/jreleaser/jreleaser/pull/1954) | **Release pipeline hardening**: an expired GPG key now fails the release, and the Nexus2 staging URI is logged as soon as it's created |
| [AWS Lambda Java](https://github.com/aws/aws-lambda-java-libs) · #606 | **`WebSocketConnectionContext`**: lightweight metadata access for API Gateway WebSocket events |
| [Spring Kafka](https://github.com/spring-projects/spring-kafka) · #2049, #2247 | **Producer logging interceptor** for serialized records, and **deferred delivery** patterns |

---

## 🛠️ What I work with

| | |
| :--- | :--- |
| **Core** | Java 21, JVM internals, GC & memory, concurrency, lock-free structures (LMAX Disruptor) |
| **Performance** | JMH, JProfiler, async logging, allocation & latency tuning |
| **Data & Messaging** | Apache Kafka, PostgreSQL, Redis, Debezium CDC |
| **Platform** | Docker, Kubernetes, AWS, CI/CD, Maven/Gradle, Linux |
| **Observability** | Log4j, W3C Trace Context, OpenTelemetry, Micrometer, ECS / JSON logging |

---

<p align="left">
  💖 If Log4j keeps your services running, consider <a href="https://github.com/sponsors/ramanathan1504"><b>sponsoring my open source work</b></a>.
</p>
