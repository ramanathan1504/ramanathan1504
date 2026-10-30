# Hi, I'm Ramanathan Muthu 👋

### Java Backend Architect & Developer · Apache Log4j Maintainer

I build reliable, concurrent JVM backends and contribute to the open-source libraries that run them.

<p align="left">
  <a href="mailto:ramanathan@apache.org"><img src="https://img.shields.io/badge/Email-ramanathan%40apache.org-blue?style=flat-square&logo=apache" alt="Apache Email"></a>
  <a href="mailto:ramanathanbscmca@gmail.com"><img src="https://img.shields.io/badge/Email-ramanathanbscmca%40gmail.com-red?style=flat-square&logo=gmail" alt="Gmail"></a>
  <a href="https://people.apache.org/phonebook.html?uid=ramanathan"><img src="https://img.shields.io/badge/ASF-Committer%20Profile-emerald?style=flat-square" alt="ASF Profile"></a>
  <a href="https://linkedin.com/in/ramanathan1504"><img src="https://img.shields.io/badge/LinkedIn-ramanathan1504-blue?style=flat-square&logo=linkedin" alt="LinkedIn"></a>
</p>

---

## 🛠️ Stack

| | |
| :--- | :--- |
| **Core** | Java, JVM internals, concurrency & thread-safety |
| **Frameworks** | Spring Boot, Spring Security, Spring Cloud, Spring Data JPA |
| **Data & Messaging** | Apache Kafka, PostgreSQL, Redis |
| **Platform** | Docker, Kubernetes, AWS, CI/CD, Linux |

---

## 🌟 Open Source

### [Apache Log4j](https://github.com/apache/logging-log4j2) — *Maintainer*
* **Exception cycle detection** ([#4133](https://github.com/apache/logging-log4j2/pull/4133)) — identity-based tracking, safe with custom `equals`/`hashCode`.
* **Resource leak fix** ([#4127](https://github.com/apache/logging-log4j2/pull/4127)) — closed socket and file-handle leaks in `ConfigurationSource` error paths.
* **Thread-safe `ListAppender`** ([#4111](https://github.com/apache/logging-log4j2/pull/4111)) — granular locking, no more `ConcurrentModificationException`.
* **Randomized rollover compression** ([#4071](https://github.com/apache/logging-log4j2/pull/4071)) — avoids I/O spikes across cluster nodes.
* **Kafka appender retries** ([#4125](https://github.com/apache/logging-log4j2/pull/4125)) — recovered failures no longer raise false errors.
* **DST-safe `CronExpression`** ([#4081](https://github.com/apache/logging-log4j2/pull/4081)) — correct scheduling across clock changes.
* **Elasticsearch 9.x** ([#3951](https://github.com/apache/logging-log4j2/pull/3951)) — migrated the ecosystem to the latest Elastic Stack.

### [Canonical](https://github.com/canonical) — *Contributor*
* **FIPS native layer** (openssl-fips-java #101) — Java `Key` → OpenSSL 3.x `EVP` via `OSSL_DECODER`.
* **Maven goal mapping** (devpack-for-spring-cli #78) — run plugin goals without declaring them in `pom.xml`.
* **JNI → FFM proposal** — POC moving native interop to the Java Foreign Function & Memory API.

### [JReleaser](https://github.com/jreleaser/jreleaser) — *Contributor*
* **GPG key expiry check** ([#1940](https://github.com/jreleaser/jreleaser/pull/1940)) — expired signing keys now fail the release.
* **Nexus2 staging URI** ([#1954](https://github.com/jreleaser/jreleaser/pull/1954)) — logs `stagedRepositoryURI` as soon as it's created.

### [AWS Lambda Java](https://github.com/aws/aws-lambda-java-libs) & [Spring Kafka](https://github.com/spring-projects/spring-kafka) — *Contributor*
* **WebSocket context helper** (aws-lambda-java-libs #606) — lightweight metadata access for API Gateway events.
* **Producer logging interceptor** (spring-kafka #2049) — logs serialized Kafka records.
* **Deferred delivery patterns** (spring-kafka #2247) — scheduled message delivery on Kafka.
