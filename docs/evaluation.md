# CoursePilot AI — AI Evaluation Framework & Metrics

This document defines the quantitative and qualitative evaluation methodology for the AI sub-systems in CoursePilot AI.

---

## 1. Overview of AI Components

CoursePilot AI utilizes AI across three primary tiers:
1. **Syllabus & Graph Extraction**: Unstructured PDF syllabus to prerequisite DAG.
2. **Diagnostic Evaluation & Gap Detector**: Probabilistic mastery inference and prerequisite chain traversal.
3. **RAG Tutor & Plan Generator**: Grounded conversational tutoring and adaptive recovery schedule generation.

---

## 2. Evaluation Metrics & Benchmarks

### 2.1 Prerequisite Extraction & Knowledge Graph
Evaluates whether extracted topic dependencies match accredited computer science curriculum standards (e.g., ACM/IEEE CS Curricula).

| Metric | Target | Description | Formula / Measurement |
| :--- | :--- | :--- | :--- |
| **Topic Identification Recall** | $\ge 90\%$ | Proportion of syllabus concepts captured | $\frac{|T_{\text{extracted}} \cap T_{\text{ground\_truth}}|}{|T_{\text{ground\_truth}}|}$ |
| **Prerequisite Edge Precision** | $\ge 85\%$ | Correctness of directional dependencies | $\frac{|\text{Valid Edges}|}{|\text{Total Proposed Edges}|}$ |
| **Graph Acyclicity (DAG Validity)** | $100\%$ | Generated graph must contain zero invalid cycles | Cycle detection algorithm verification |

### 2.2 Diagnostic Assessment & Gap Calibration
Evaluates whether the diagnostic accurately predicts areas where the student subsequently struggles.

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Gap Detection Accuracy** | $\ge 88\%$ | True positive rate in flagging weak foundational prerequisites |
| **Brier Score (Confidence Calibration)** | $\le 0.15$ | Measures accuracy of probabilistic mastery estimates |
| **False Negative Prerequisite Rate** | $\le 5\%$ | Rate at which a truly missing prerequisite is omitted from the plan |

### 2.3 RAG Performance (RAG Triad)
Evaluated using standard LLM-as-a-judge frameworks (e.g., Ragas, TruLens) using local Qwen Instruct or benchmark models.

| Metric | Target | Definition |
| :--- | :--- | :--- |
| **Context Relevance** | $\ge 85\%$ | Chunks retrieved from pgvector directly address the student query |
| **Faithfulness (Groundedness)** | $\ge 95\%$ | The tutor response is strictly derived from retrieved course material without hallucinating outside concepts |
| **Answer Relevance** | $\ge 90\%$ | The response directly answers the student's learning confusion |
| **Citation Accuracy** | $\ge 95\%$ | Source page and section references accurately correspond to the underlying PDF |

### 2.4 Study Plan Viability
Evaluates the feasibility and pedagogical structure of synthesized study schedules.

| Criterion | Target | Verification Method |
| :--- | :--- | :--- |
| **Topological Adherence** | $100\%$ | No advanced topic scheduled before its unmastered prerequisite |
| **Workload Balance** | Daily std dev $\le 30$ mins | Distribution of estimated study hours across target period |
| **Recoverability Index** | $\ge 80\%$ | Student survey rating on plan achievability |

---

## 3. Benchmark Dataset & Automated Test Harness

- **Test Suite Directory**: `sample_data/eval_inputs/`
- **Gold Standard Dataset**: Hand-labeled DSA syllabus (CS201 standard syllabus) with 25 topics, 38 validated prerequisite edges, and 50 curated diagnostic questions with expert explanations.
- **Evaluation Runner**: `pytest backend/app/tests/eval_rag.py` (Planned in future iteration).

