# Inyeon (인연)

> *You are Daniel Craig but life owes you a Vesper Lynd?*

**Inyeon** means "fated connection" in Korean - your AI-powered git companion that analyzes diffs, generates commits, reviews code, and splits changes into atomic commits.

---

## 📦 Installation

```bash
pip install git+https://github.com/suka712/inyeon-upstream.git
```

---

## 📖 Usage

### Generate Commit Messages
```bash
inyeon commit --staged                # From staged changes
inyeon commit --staged --dry-run      # Preview without committing
inyeon commit --staged --issue "#123" # Reference an issue
```

### Split into Atomic Commits (v2.0.0)
```bash
inyeon split --staged --preview           # Preview how changes will be split
inyeon split --staged --interactive       # Approve each commit individually
inyeon split --staged --execute           # Auto-commit all groups
inyeon split --staged --strategy semantic # Use specific strategy
```

**Strategies:**
- `directory` - Group by folder structure
- `semantic` - Group by code similarity (embeddings)
- `conventional` - Group by commit type (feat, fix, docs)
- `hybrid` - Combine all strategies (default)

### Code Review
```bash
inyeon review --staged # Review staged changes
inyeon review --all    # Review all uncommitted changes
```

### Analyze Diffs
```bash
git diff | inyeon analyze            # Pipe any diff
inyeon analyze -f changes.patch      # From file
inyeon analyze -c "refactoring auth" # With context
```

### Index Codebase (RAG)
```bash
inyeon index # Index for smart context retrieval
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
