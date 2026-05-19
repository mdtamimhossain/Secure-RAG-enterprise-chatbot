# Codemars RAG Evaluation

This folder contains a lightweight local evaluation system for the Codemars
enterprise RAG chatbot.

Run it with:

```powershell
.\.venv\Scripts\python.exe -m backend.evaluation.run_eval
```

The evaluator checks:

- retrieval department accuracy
- RBAC leakage prevention
- guardrail blocking
- source visibility
- casual-message behavior
- short follow-up memory

The local runner uses a deterministic fake LLM so evaluations do not require
Groq, OpenAI, or paid API calls. It is meant to catch system behavior issues
before using heavier tools such as Ragas or LangSmith evals.

An evaluation score below 100% is useful: it shows the next system weakness to
improve. For example, a failed finance retrieval case means the next retrieval
quality step should focus on hybrid search, keyword fallback, or reranking.
