# Inyeon (인연)

> *You are Daniel Craig but life owes you a Vesper Lynd?*

**Inyeon** means "fated connection" in Korean - your AI-powered git companion that analyzes diffs, generates commits, and reviews code with multi-agent intelligence.

---

## ⚡ Quick Start

```bash
# Install from source
pip install git+https://github.com/suka712/inyeon-upstream.git

# Index your codebase (one-time setup for smart context)
inyeon index

# Generate conventional commit messages
inyeon commit --staged

# Get AI-powered code review
inyeon review --staged

# Analyze any diff
git diff | inyeon analyze
```

---

## 🎯 Features

- **Multi-Agent Intelligence** - Specialized agents for commits, reviews, and task orchestration
- **RAG-Powered Context** - Understands your entire codebase via ChromaDB embeddings
- **Flexible LLM Support** - Use Gemini API (cloud) or Ollama (local)
- **Conventional Commits** - Auto-generates properly formatted commit messages
- **Smart Code Review** - AI insights on code quality, patterns, and potential issues
- **Docker-Ready** - Deploy with one command via docker-compose

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (Typer)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ CommitAgent │  │ ReviewAgent │  │ AgentOrchestrator   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └────────────────┼────────────────────┘             │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    LangGraph                          │  │
│  │         (Multi-step agentic workflows)                │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          ▼                                  │
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
| **LLM** | Gemini 2.5 Flash, Ollama (Qwen2.5-Coder) |
| **RAG** | ChromaDB, Gemini Embeddings |
| **Deploy** | Docker, Railway |

---

## 📡 API Endpoints

| **Endpoint** | **Purpose** |
|--------------|-------------|
| `POST /api/v1/analyze` | Analyze git diff |
| `POST /api/v1/generate-commit` | Generate commit message |
| `POST /api/v1/agent/review` | AI code review |
| `POST /api/v1/agent/orchestrate` | Auto-route to appropriate agent |
| `POST /api/v1/rag/index` | Index codebase for RAG |
| `POST /api/v1/rag/search` | Semantic code search |

**Live API Docs:** https://inyeon-upstream-production.up.railway.app/docs

---

## 💻 Local Development

```bash
# Clone the repository
git clone https://github.com/suka712/inyeon-upstream.git
cd inyeon-upstream

# Set up Python environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in development mode
pip install -e ".[dev]"

# Start services with Docker
docker-compose up
```

---

## 📬 Contact

For contributions or inquiries, contact **Anh Tran** at anhdtran.forwork@gmail.com
