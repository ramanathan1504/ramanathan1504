# Hi there, I'm Ramanathan Muthu! 👋

### Senior Backend & Platform Engineer | Apache Log4j Maintainer

<p align="left">
  <a href="mailto:ramanathan@apache.org"><img src="https://img.shields.io/badge/Email-ramanathan%40apache.org-blue?style=flat-square&logo=apache" alt="Apache Email"></a>
  <a href="mailto:ramanathanbscmca@gmail.com"><img src="https://img.shields.io/badge/Email-ramanathanbscmca%40gmail.com-red?style=flat-square&logo=gmail" alt="Gmail"></a>
  <a href="https://people.apache.org/phonebook.html?uid=ramanathan"><img src="https://img.shields.io/badge/ASF-Committer%20Profile-emerald?style=flat-square" alt="ASF Profile"></a>
  <a href="https://linkedin.com/in/ramanathan1504"><img src="https://img.shields.io/badge/LinkedIn-ramanathan1504-blue?style=flat-square&logo=linkedin" alt="LinkedIn"></a>
</p>

---

## 🛠️ Tech Stack & Core Competencies

| Category | Technologies |
| :--- | :--- |
| **Languages & Core** | Java, Node.js, JVM Internals, Multi-threading, Concurrency & Thread-Safety |
| **Cloud & DevOps** | Kubernetes (K8s), AWS (ECR, NLB, CLB), Persistent Volumes (PV/PVC), Ingress Controllers, Docker, CI/CD, Linux Systems |
| **Frameworks** | Spring Boot, React.js |
| **Databases & Messaging** | Apache Kafka, PostgreSQL, Redis |

---

## 📊 Live GitHub Contributions
This chart automatically updates in real-time as I push code:

[![Ramanathan's GitHub Contributions](https://ghchart.rshah.org/ramanathan1504)](https://github.com/ramanathan1504)

---

## 🌟 Open-Source Stewardship

### [Apache Log4j](https://github.com/apache/logging-log4j2) — *Active Core Maintainer*
* **Exception Identity Tracking (Issue #3933 | PR #4133):** Designed a circular reference detection mechanism utilizing `IdentityHashMap` to handle exceptions with custom `equals`/`hashCode` overrides safely, preventing false cyclic triggers.
* **Socket & File Leak Mitigation (Issue #4127 | PR #4127):** Patched critical resource leaks in `ConfigurationSource` where failed `URLConnection` error paths bypassed cleanups, resolving socket leaks and file handle locks on Tomcat redeployments.
* **Concurrency & Thread-Safety (Issue #3926 | PR #4111):** Redesigned the `ListAppender` class for high-concurrency environments, replacing legacy synchronization with granular locking and wait/notify mechanisms to eliminate `ConcurrentModificationException`.
* **Distributed Cloud Performance (Issue #4012 | PR #4071):** Engineered a randomized compression delay for rolling log files to prevent simultaneous disk I/O spikes across distributed cloud nodes.
* **Kafka Retry Handling Correctness (PR #4125):** Patched the retry logic in `KafkaAppender` to ensure transient failures successfully recovered by retries do not trigger false-alarm error notifications to the application error handler.
* **DST & Scheduling Reliability (Issue #3660 | PR #4081):** Resolved CronExpression rollover corruption by implementing DST-safe time calculation logic for spring-forward and fallback boundaries.
* **Ecosystem Modernization (Issue #3663 | PR #3951):** Led the migration of the Log4j ecosystem to Elasticsearch 9.x, ensuring compatibility with the latest Elastic Stack versions.

### [Canonical](https://github.com/canonical) — *Recognized Contributor*
* **FIPS Security Integration (openssl-fips-java #101):** Developed a FIPS-compliant native layer to translate Java Key objects to OpenSSL 3.x EVP instances using the OpenSSL 3.x `OSSL_DECODER` API.
* **Automated Maven CLI Mapping (devpack-for-spring-cli #78):** Modified `MavenRunner` to automatically convert simple goal names to Maven's full plugin coordinate format, allowing execution of CLI goals without requiring static plugin declarations in `pom.xml`.
* **Native Interop Proposal:** Authored a technical proposal and POC to migrate native library interop from legacy JNI to the modern Java FFM (Foreign Function & Memory) API.

### [JReleaser](https://github.com/jreleaser/jreleaser) — *Recognized Contributor*
* **Pipeline Security (Issue #1930 | Merged PR #1940):** Hardened the release workflow by implementing automated GPG signing-key expiry validation, converting key expiration warnings into blocking exceptions.
* **Deployment Transparency (Issue #1650 | Merged PR #1954):** Improved staging workflows in Nexus2 by implementing secondary network lookups to log the `stagedRepositoryURI` immediately upon creation.

### [AWS Lambda](https://github.com/aws/aws-lambda-java-libs) & [Spring Kafka](https://github.com/spring-projects/spring-kafka) — *Contributor*
* **Serverless Messaging Tools (AWS Lambda #606):** Developed a session-like `WebSocketConnectionContext` helper for API Gateway events, providing a lightweight, Lambda-safe object for managing WebSocket metadata.
* **Observability Tools (Spring Kafka #2049):** Designed and implemented a `ProducerInterceptor` to enable granular logging of serialized Kafka messages.
* **Advanced Messaging Patterns (Spring Kafka #2247):** Engineered architectural patterns for implementing scheduled and deferred delivery logic inside active Kafka brokers.

---

## 💼 Professional Experience

### **Senior Full Stack Developer** | *INTEMO*
*July 2023 – Present | Chennai, TN*
* **Cloud-Native Deployment:** Implemented and managed Kubernetes (K8s) clusters on AWS. Established automated CI/CD pipelines deploying directly from AWS ECR, and utilized PV/PVC structures for stateful database storage requirements.
* **High-Availability Networking:** Orchestrated secure Layer 4 (Network Load Balancers) and Layer 7 (Application Load Balancers) strategies on AWS to manage traffic load spikes and route API transactions safely.
* **Enterprise Monitoring:** Structured centralized logging topologies utilizing Fluentd metrics collections to stream container node and ingress load records.
* **Distributed Automation Platform:** Architected an end-to-end automation engine for API-less ERP systems, handling 10,000+ daily transactions and reducing manual processing effort by ~60%.
* **JVM Runtime Manipulation:** Developed a custom Java Agent using Byte Buddy for runtime bytecode manipulation to extract non-editable values from restricted JVM classes.
* **High-Volume Virtualization:** Engineered a scalable automation engine using Docker and Xvfb to manage 8 concurrent virtual displays per node, achieving a 3x increase in processing throughput.
* **Network Packet Analysis:** Built Python-based listeners and mitmproxy scripts to intercept and analyze browser-based ERP network traffic for automated response handling and protocol reverse engineering.

### **Full Stack Developer** | *GTECHWEBSOLUTIONS*
*April 2022 – June 2023 | Chennai, TN*
* **Food Delivery Live Tracking:** Engineered a high-performance tracking system using Java 8, WebSockets, and Google Maps API, enabling real-time driver movement updates for 45-minute delivery windows.
* **ERP & HRMS Development:** Built a custom ERP platform featuring complex Leave Approval Workflows and HRA calculation engines using Spring Boot and React.js, styled with Tailwind CSS.
* **Biometric Attendance Interfacing:** Developed a Fingerprint API bridge to sync biometric hardware data with internal HRMS records, implementing real-time attendance tracking and automated payroll adjustments.
* **Timesheet & Resource Planning:** Designed a high-granularity Timesheet Management Module with custom reporting views to track developer productivity and project-specific resource allocation.

### **Senior Software Engineer** | *WEDDINGWISHLIST*
*January 2022 – April 2022 | Chennai, TN*
* **Platform Modernization:** Led the migration of a legacy multisite to a modern React/Node.js stack, resulting in a 40% improvement in page performance and sub-second navigation.

### **Junior Developer** | *GEGOSOFT*
*March 2019 – January 2022 | Madurai, TN*
* **Blockchain & Bitcoin MLM Platform:** Engineered a complex Bitcoin-based Multi-Level Marketing (MLM) engine using Node.js. Developed recursive binary and matrix referral algorithms for automated, immutable commission payouts.
* **Decentralized Exchange (DEX):** Designed and implemented a decentralized exchange interface inspired by Uniswap, utilizing Web3.js for secure wallet integration and automated liquidity pool interaction.
* **Automated Scheduling Algorithm:** Built a custom automated timetable generation algorithm (KG to 12th) using a backtracking approach and integrated Meilisearch for sub-second record retrieval.

---

## ⚡ GitHub Stats

<p align="left">
  <img src="https://github-readme-stats-fast.vercel.app/api?username=ramanathan1504&show_icons=true&theme=dark" alt="Ramanathan's Stats" width="48%" />
  <img src="https://github-readme-stats-fast.vercel.app/api/top-langs/?username=ramanathan1504&layout=compact&theme=dark" alt="Top Languages" width="48%" />
</p>

---

## 🎓 Education
* **Master of Computer Applications (MCA)** | Guru Nanak College, Chennai (Chennai, India)
* **B.Sc. in Information Technology** | NMS SVN College, Madurai (Madurai, India)
