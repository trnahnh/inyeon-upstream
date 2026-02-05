# Inyeon (인연)

> *You are Daniel Craig but life owes you a Vesper Lynd?*

**Inyeon** means "fated connection" in Korean - your AI-powered git companion that analyzes diffs, generates commits, reviews code, and splits changes into atomic commits.

---

## ⚡ Quick Start

```bash
# Install
pip install git+https://github.com/suka712/inyeon-upstream.git

# Generate commit messages
inyeon commit --staged

# Split large changes into atomic commits (v2.0.0)
inyeon split --staged --preview
inyeon split --staged --interactive

# Code review
inyeon review --staged

# Analyze any diff
git diff | inyeon analyze

# Index codebase for smart context
inyeon index
```

---

## 🎯 Features

- **Atomic Commit Splitting** - Intelligently group changes into smaller, logical commits
- **Multi-Agent Intelligence** - Specialized agents for commits, reviews, splits, and orchestration
- **4 Clustering Strategies** - Directory, semantic, conventional, or hybrid grouping
- **RAG-Powered Context** - Understands your codebase via ChromaDB embeddings
- **Flexible LLM** - Gemini API (cloud) or Ollama (local)
- **Conventional Commits** - Auto-generates properly formatted messages

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (Typer)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │CommitAgent│ │ReviewAgent│ │SplitAgent │ │Orchestrator │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘  │
│        └─────────────┼─────────────┼──────────────┘         │
│                      ▼             ▼                        │
│  ┌──────────────────────┐  ┌────────────────────────────┐   │
│  │      LangGraph       │  │     Clustering Engine      │   │
│  │  (Agentic workflows) │  │ Directory/Semantic/Hybrid  │   │
│  └──────────┬───────────┘  └────────────────────────────┘   │
│             ▼                                               │
│  ┌──────────────┐  ┌─────────────────────────────────────┐  │
│  │ LLM Factory  │  │           RAG Layer                 │  │
│  │ Gemini/Ollama│  │  ChromaDB + Gemini Embeddings       │  │
│  └──────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| **Layer** | **Technology** |
|-----------|----------------|
| **CLI** | Typer, Rich |
| **Backend** | FastAPI, Pydantic |
| **Agents** | LangGraph |
| **Clustering** | scikit-learn, NumPy |
| **LLM** | Gemini 2.5 Flash, Ollama |
| **RAG** | ChromaDB, Gemini Embeddings |
| **Deploy** | Docker, Railway |

---

## 📡 API Endpoints

| **Endpoint** | **Purpose** |
|--------------|-------------|
| `POST /api/v1/generate-commit` | Generate commit message |
| `POST /api/v1/agent/split` | Split diff into atomic commits |
| `POST /api/v1/agent/review` | AI code review |
| `POST /api/v1/agent/orchestrate` | Auto-route to agent |
| `POST /api/v1/rag/index` | Index codebase |
| `POST /api/v1/rag/search` | Semantic code search |

**Live Docs:** https://inyeon-upstream-production.up.railway.app/docs

---

## 💻 Local Development

```bash
git clone https://github.com/suka712/inyeon-upstream.git
cd inyeon-upstream
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"

# Run backend
uvicorn backend.main:app --port 8000

# Test CLI (new terminal)
inyeon split --staged --preview --api http://localhost:8000
```

---

## 📬 Contact

For contributions or inquiries, contact **Anh Tran** at anhdtran.forwork@gmail.com
