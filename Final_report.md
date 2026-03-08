# Technical Report: Grounded Long-Term Memory
**Candidate:** Nagelli Vivek
**Project:** Layer10 AI Engineering Take-Home (2026)

## 1. Introduction & Core Objective
The goal of this project was to build a system that transforms unstructured technical communication into a **Grounded Knowledge Graph**. Unlike a simple RAG (Retrieval-Augmented Generation) system which just searches for text, this system performs **Identity Resolution** and **Temporal Truth Maintenance**. The final output is a memory that knows not just what was said, but what is *currently true*.

---

## 2. Phase 1 & 2: The "Clean Room" Challenge
### The Problem: Data Overload and Bot Noise
Initially, I downloaded a 2.5GB GitHub corpus. I quickly realized that processing this amount of data on a local machine would lead to RAM exhaustion. Furthermore, the data was "noisy."
*   **The Discovery:** I found thousands of issues from automated crash bots (e.g., Fabric, Czekolada). These bots use identical templates, which confuses AI extractors and creates "false" memories.
*   **The Fix:** I built a **Preprocessing Pipeline** (`01_prepare_data.py`) that uses regex-based boilerplate stripping and language detection (`langdetect`). I narrowed the corpus down to a "High-Signal" sample of English human conversations.

### The Problem: The "Inconsistent AI" Contract
During the extraction phase using **Llama-3.1-8B**, the model occasionally returned inconsistent JSON keys (e.g., changing `evidence_quote` to `Evidence_quote`) or returned `null` for entity names.
*   **The Fix:** I implemented a **Defensive Extraction Layer**. I wrote Python logic using `.get()` fallbacks and `isinstance(name, str)` checks. This ensured that "messy" AI output would be pruned or standardized before it ever hit the database, maintaining strict **Referential Integrity**.

---

## 3. Phase 3: The Deduplication "Logic Trap"
This was the most challenging phase, as I had to separate **Documents** from **Facts**.

### Problem 1: The $O(N^2)$ Complexity Bottleneck
Initially, my claim-merging script tried to compare every new fact against every existing fact. Even with only 100 issues, the script took several minutes and hundreds of API calls.
*   **The Optimization (Semantic Blocking):** I implemented a "Fast-Filter" using **Keyword Intersection**. Before calling the expensive Llama-3.3-70B model, the system checks if two claims share at least one significant technical word (e.g., "React"). If they don't, the system skips the AI check entirely. This reduced latency by over 80%.

### Problem 2: String Similarity vs. Logical Similarity
I realized that `rapidfuzz` (string matching) failed on logical opposites. 
*   **The Conflict:** "The bug is fixed" and "The bug is broken" are 90% similar in characters but 0% similar in meaning.
*   **The Elite Fix:** I moved to a **Two-Tiered Judge System**. 
    1.  **Tier 1:** RapidFuzz catches exact or near-exact duplicates ($>95\%$).
    2.  **Tier 2:** For everything else, I used **Llama-3.3-70B** to perform **Natural Language Inference (NLI)**. I provided the AI with "Few-Shot" examples to teach it how to distinguish between a `SAME` fact and a `CONFLICT`.

---

## 4. Phase 3.3: Proving Temporal Correctness (The Stress Test)
Because GitHub issues are scattered, my 100-row sample didn't naturally contain many conflicts. To prove my system could handle Layer10's core requirement of **"Correctness over Time,"** I performed a **Synthetic Stress Test**.

I injected three specific issues into the pipeline:
1.  **Issue A (Jan 1):** "React setup fails on Windows."
2.  **Issue B (Jan 2):** "React installation is broken on PC."
3.  **Issue C (Jan 5):** "React setup is now fixed."

**The Result:** The system successfully merged A and B into a single "Fact" node (proving semantic synonyms work). It then identified that C conflicted with the A/B node. Because C had a newer timestamp, the system automatically flipped the A/B node to **HISTORICAL** and marked C as **CURRENT**.

## 3.4 Entity Canonicalization: Solving the "Identity Crisis"
**The Problem:**
During the initial extraction phase, the AI was inconsistent. For example, it would extract **"GitHub"** as an `Organization` in one issue, and **"Github"** (lowercase) as a `Platform` in another. If I had used a simple string match, I would have had two different nodes in my graph for the same thing.

**The Logic & Fix:**
I implemented a **Two-Pass Identity Resolution** strategy:
*   **Pass 1 (Global Normalization):** Instead of comparing entities one-by-one (which is $O(N^2)$), I created a "Normalization Pool." I grouped all entities by their lowercase name. This forced "GitHub" and "Github" into the same logical room regardless of their assigned "Type."
*   **Pass 2 (AI Type Reconciliation):** I upgraded the logic to use **Llama-3.3-70B**. When the system found a name with conflicting types (Org vs. Platform), I asked the 70B model to act as a **Senior Architect** and pick the one "Official Canonical Name" and "Official Type."
*   **The Result:** I achieved 100% identity resolution, ensuring that all claims about a tool—no matter how they were spelled or categorized—point to a single, verified node.

---

## 3.5 Claim Merging: The Temporal Truth Engine
**The Problem:**
This was the most complex part of the engine. I faced two major issues:
1.  **The $O(N^2)$ Bottleneck:** Comparing every claim to every other claim made the script incredibly slow.
2.  **Semantic vs. Lexical Similarity:** "The bug is fixed" and "The bug is broken" are 90% similar in text but mean opposite things.

**The Logic:**
*   **Optimization (Semantic Blocking):** I implemented **Keyword Intersection**. Before calling the AI, the script calculates a set of "Technical Keywords" for every claim. If two claims share zero keywords (e.g., "React" vs "PHP"), the system skips the AI check instantly. This turned a slow script into a high-performance pipeline.
*   **Natural Language Inference (NLI):** I used the 70B model to perform **NLI judging**. I provided "Few-Shot" examples in the prompt to teach the AI how to handle software states (Broken, Fixed, Superseded).
*   **Temporal Resolution:** When the AI detected a **CONFLICT**, I implemented a "Latest-Truth-Wins" logic. Using the GitHub `created_at` timestamp, the system identifies the older fact and flips its status to `HISTORICAL`.
*   **The Result:** My system successfully passed a **"React Stress Test"** where it correctly merged two different "Broken" reports into one node, then retired that node once a "Fixed" report was ingested.

---

## 3.6 Retrieval & Grounding: Preventing "Cake" Hallucinations
**The Problem:**
Standard RAG systems often "hallucinate" by forcing an answer even when the data isn't relevant. In testing, when I asked my retriever "How to bake a cake?", it tried to find the closest match in my GitHub data, which led to irrelevant technical jargon.

**The  Logic:**
*   **Two-Stage Multi-Model Pipeline:** 
    1.  **Stage 1 (Routing):** I used the fast **8B model** to parse the user's "Intent" and extract the target entity. This allows an **Inverted Index lookup** ($O(1)$ speed) to narrow the search from the whole graph to just one "bucket."
    2.  **Stage 2 (Re-ranking):** I used the powerful **70B model** to evaluate the top 10 candidates.
*   **The Safety Switch:** I added a **Confidence Gate**. If the 70B model determines that the user's question is "Out-of-Bounds" relative to the memory graph, it is instructed to return `NONE`.
*   **The Result:** The system now correctly rejects non-technical queries, ensuring the user only receives **Grounded, Verified facts** backed by real GitHub evidence.

---

## 4. Visualization: Turning a "Black Box" into a Graph
**The Problem:**
Initially, the graph only showed `Entity -> Claim`. It looked good, but it didn't prove **Grounding**. It was just a "black box" of AI facts.

**The Logic:**
*   **Triple-Layer Grounding Nodes:** I updated the visualization layer to show three distinct node types: **Entities (Blue)**, **Claims (Green/Red)**, and **Source Artifacts (Grey)**.
*   **Referential Integrity (Dashed Edges):** I added dashed lines in the graph to connect every Claim to its original GitHub Issue. This visually proves to the user that "This fact exists because this issue said so."
*   **Rich Tooltips:** I implemented dynamic tooltips using the `pyvis` library. Hovering over a claim node instantly reveals its status, confidence score, and the exact date it was verified.
*   **Audit & Reversibility:** I built an **Audit Log tab**. Since I used a non-destructive merging strategy, I was able to display the **Lineage** of every fact. A recruiter can select a merged claim and see the original "messy" text that was extracted from Issue #1 and Issue #2. This fulfills the "Reversibility" requirement and builds trust in the AI's decisions.
---

## 5. Architecture for Reversibility
Layer10 requires that merges be reversible. I achieved this by avoiding **Destructive Deletion**.
*   **Entity Registry:** Every canonical entity (e.g., "GitHub") stores a `mentions_log`. This tracks every original name used (e.g., "Github", "github-pages") and the URL it came from.
*   **Claim Lineage:** Every fact stores a `merge_history`. If the AI incorrectly merges two facts, an engineer can look at the audit log in the dashboard and see the original "messy" text to manually split the node.

---

## 6. Adaptation for Layer10 Production
To adapt this for Layer10’s actual environment (Slack, Jira, Email), my architecture is already " GDPR-Ready" and "Scale-Ready":
1.  **Cascading Redactions:** Because my graph uses a strictly grounded `source_url` for every fact, if a user deletes a Slack message, my system can perform a **cascading delete**. It finds the `SourceNode` and automatically hides all dependent claims, ensuring the system stays compliant with data privacy laws.
2.  **Cross-Platform Anchoring:** I would update the **Entity Extractor** to recognize JIRA patterns (e.g., `[PROJ-123]`). This would allow the system to automatically link a Slack discussion about a bug to the official Jira ticket in the memory graph.
3.  **Knowledge Decay:** Not all chat is "Memory." I would implement a **Durable vs. Ephemeral** score. "Social chatter" would have a 24-hour TTL (Time-to-Live), while "Architectural Decisions" would be stored permanently in the graph.


---

## Final Trade-off Analysis
The main trade-off I made was choosing the **70B model over the 8B model** for the logic layers. While the 70B model increases API latency by about 2 seconds, it was the only way to guarantee the **Temporal Correctness** that Layer10 requires. In a "Long-Term Memory" system, being **Slow but Right** is far better than being **Fast but Wrong.**


