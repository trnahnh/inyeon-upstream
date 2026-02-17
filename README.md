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
inyeon commit --all                   # From all uncommitted changes
inyeon commit --staged --dry-run      # Preview without committing
inyeon commit --staged --issue "#123" # Reference an issue
inyeon commit --staged --json         # Output raw JSON
```

### Split into Atomic Commits (v2.0.0)
```bash
inyeon split --staged --preview           # Preview how changes will be split
inyeon split --staged --interactive       # Approve each commit individually
inyeon split --staged --execute           # Auto-commit all groups
inyeon split --staged --strategy semantic # Use specific strategy
inyeon split --all --strategy directory   # Split all changes by folder
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
inyeon review --json   # Output raw JSON
```

### Analyze Diffs
```bash
git diff | inyeon analyze            # Pipe any diff
inyeon analyze -f changes.patch      # From file
inyeon analyze -c "refactoring auth" # With context
```

### Index Codebase (RAG)
```bash
inyeon index          # Index for smart context retrieval
inyeon index --stats  # Show index statistics
inyeon index --clear  # Clear the index
```

### Utilities
```bash
inyeon version        # Show version
inyeon health         # Check backend & LLM connection status
```

> **Tip:** All commands accept `--api <url>` to override the backend URL, or set `INYEON_API_URL` env var.

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
| `GET /health` | Health check (LLM status) |
| `POST /api/v1/generate-commit` | Generate commit message |
| `POST /api/v1/analyze` | Analyze a diff |
| `POST /api/v1/agent/run` | Run commit agent directly |
| `POST /api/v1/agent/split` | Split diff into atomic commits |
| `POST /api/v1/agent/review` | AI code review |
| `POST /api/v1/agent/orchestrate` | Auto-route to agent |
| `GET /api/v1/agent/list` | List available agents |
| `POST /api/v1/rag/index` | Index codebase |
| `POST /api/v1/rag/search` | Semantic code search |
| `POST /api/v1/rag/stats` | Index statistics |
| `POST /api/v1/rag/clear` | Clear index for repo |

**Live Docs:** https://inyeon-upstream-production.up.railway.app/docs

---

## ⚙️ Configuration

All settings use the `INYEON_` prefix and can be set via environment variables or a `.env` file.

| **Variable** | **Default** | **Description** |
|--------------|-------------|-----------------|
| `INYEON_LLM_PROVIDER` | `ollama` | LLM backend (`ollama` or `gemini`) |
| `INYEON_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `INYEON_OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama model name |
| `INYEON_OLLAMA_TIMEOUT` | `120` | Ollama request timeout (seconds) |
| `INYEON_GEMINI_API_KEY` | — | Google Gemini API key (required for `gemini` provider) |
| `INYEON_GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `INYEON_API_URL` | — | Backend URL for CLI (overrides `--api` flag) |

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
