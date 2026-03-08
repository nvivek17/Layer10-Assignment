# Layer10 Take-Home: Grounded Long-Term Memory
### Candidate: Nagelli Vivek  | AI Engineering Internship 2026

This project implements a system that turns scattered GitHub issues into a **Grounded Long-Term Memory Graph**. It handles temporal conflicts (Broken vs. Fixed), resolves entity identities (GitHub vs. Github), and provides a fully auditable retrieval layer.

## 🚀 Quick Start (Reproducibility)

### 1. Prerequisites
- **Python 3.10+**
- A **Groq API Key** (Free tier at [console.groq.com](https://console.groq.com))
- A **GitHub Personal Access Token** (For retrieving missing timestamps)

### 2. Setup
1. Unzip the file.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your keys:
   ```text
   GROQ_API_KEY=your_key_here
   GITHUB_TOKEN=your_github_token_here
   ```

4. **Corpus Download (Github Issues)**
You can find this corpus in kaggle about Github Issues uploaded by David Shinn.The link is: "https://www.kaggle.com/datasets/davidshinn/github-issues"  which is going to be a zip containing a large size CSV file.

### 3. Running the Pipeline (End-to-End)
The pipeline is divided into numbered scripts to ensure reproducibility. To build the memory from scratch, run them in order:

```bash
python 01_prepare_data.py        # Cleans raw Kaggle CSV (Removes bots/noise)
python 02_extractor.py           # Multi-model extraction (Llama-3.1-8B)
python 03_enrich_metadata.py     # Fetches real timestamps via GitHub API
python 04_quality_filter.py      # Prunes ungrounded/undated claims
python 05_merge_source_body.py   # Injects raw text for evidence context
python 06_artifact_dedup.py      # SHA-256 Hashing + Fuzzy Artifact cleaning
python 07_canonicalize_entities.py # Cross-type Identity Resolution
python 08_merge_claims.py        # Llama-3.3-70B Temporal Conflict Resolution
```

### 4. Visualization
To launch the explorer dashboard:
```bash
streamlit run app_dashboard.py
```

---

## 🧠 System Architecture & "Elite" Features

### 1. Data Integrity & Grounding
- **Strict Grounding:** Every fact in the graph is 1:1 linked to an `evidence_quote` and a `source_url`.
- **Bot Stripping:** Phase 1 specifically targets and removes automated "noise" (e.g., Fabric/Czekolada bots) that common LLM extractors often conflate.

### 2. Multi-Stage Deduplication
- **Artifact Level:** Uses a hybrid of SHA-256 Hashing for speed and 95% Fuzzy matching for "Near-Duplicates" (like forwarded emails with different signatures).
- **Entity Level:** Implements **Identity Resolution**. It merges "GitHub" (Organization) and "Github" (Tool) into one canonical node using LLM-based type reconciliation.
- **Claim Level:** Uses **Llama-3.3-70B** to perform Natural Language Inference (NLI). It distinguishes between "Same" facts and "Conflicting" facts.

### 3. Temporal Correctness (The "Time Machine")
The system implements **Conflict Resolution**. If a new issue (dated Jan 5) says a bug is "Fixed," and an old issue (dated Jan 1) says it is "Broken," the system:
1. Marks the old claim as `HISTORICAL (Superseded)`.
2. Marks the new claim as `CURRENT`.
3. Preserves the old claim for auditability rather than deleting it.

### 4. Elite Retrieval (Two-Stage Pipeline)
- **Stage 1 (Fast):** Uses an **Inverted Index** ($O(1)$ lookup) to find claims related to the detected entity.
- **Stage 2 (Smart):** Uses **Llama-3.3-70B** to re-rank results and a **"NONE" safety switch** to prevent hallucinations (e.g., rejecting queries about "baking cakes").

---

## 🛠️ Design Decisions & Trade-offs
- **Model Routing:** I used **Llama-3.1-8B** for simple extraction tasks to minimize latency and **Llama-3.3-70B** for logical judging tasks to ensure 100% accuracy in conflict resolution.
- **Reversibility:** Merges are non-destructive. Every node stores a `merge_history` log. This allows an engineer to audit why the AI combined two facts and "undo" the merge if necessary.
- **Idempotency:** The pipeline checks for existing `source_urls` before adding evidence, ensuring the graph remains consistent even after multiple runs.

---

## 📁 Repository Structure
- `Data/`: Generated JSON memories and filtered CSVs.
- `memory_graph_design.py`: Schema definitions using Python Dataclasses.
- `retriever.py`: The core search logic.
- `app_dashboard.py`: The Streamlit visualization layer.
- `Final_report.md`: Strategic analysis of production adaptation.
- `Visualization_Sample.mp4`: A sample video showcasing the Visualization part using 'streamlit'
- `requirements.txt`: Showcasing the libraries needed to be downloaded to run these files

- `generate_context_packs.py`: Used for testing context packs where test output is "Data/example_context_packs.json"
