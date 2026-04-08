# Inyeon (인연)

> *You are Daniel Craig but life owes you a Vesper Lynd?*

**Inyeon** means "fated connection" in Korean - your AI-powered git companion that analyzes diffs, generates commits, reviews code, splits changes, resolves conflicts, generates PRs and changelogs, and orchestrates the full workflow in one command.

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

### Generate PR Descriptions (v3.0.0)

```bash
inyeon pr                  # Generate from branch diff vs main
inyeon pr --branch develop # Compare against different base branch
inyeon pr --staged         # Generate from staged changes only
inyeon pr --json           # Output raw JSON
```

### Resolve Merge Conflicts (v3.0.0)

```bash
inyeon resolve --all               # Resolve all conflicted files
inyeon resolve --file path/to/file # Resolve a single file
inyeon resolve --all --json        # Output raw JSON
```

### Generate Changelogs (v3.0.0)

```bash
inyeon changelog --from v2.0.0                        # Changelog since a tag
inyeon changelog --last 7                             # Changelog from last 7 days
inyeon changelog --from v2.0.0 --output CHANGELOG.md  # Write to file
inyeon changelog --json                               # Output raw JSON
```

### Full Workflow Automation (v3.0.0)

```bash
inyeon auto --staged              # Split → commit → review → PR in one command
inyeon auto --all --dry-run       # Preview the full pipeline
inyeon auto --staged --no-review  # Skip code review step
inyeon auto --staged --no-pr      # Skip PR generation step
inyeon auto --staged --json       # Output raw JSON
```

**Cost-optimized short-circuits:**

- Skips split for single-file changes
- Skips review for small diffs (< 500 chars)
- As few as 2 LLM calls for simple changes

### Git Hooks (v3.0.0)

```bash
inyeon hook install  # Install prepare-commit-msg hook
inyeon hook remove   # Remove hook (only if installed by Inyeon)
inyeon hook status   # Check hook installation status
```

### Analyze Diffs

```bash
git diff | inyeon analyze            # Pipe any diff
inyeon analyze -f changes.patch      # From file
inyeon analyze -c "refactoring auth" # With context
```

### Index Codebase (RAG)

```bash
inyeon index         # Index for smart context retrieval
inyeon index --stats # Show index statistics
inyeon index --clear # Clear the index
```

### Switch LLM Provider (v3.5.0)

```bash
inyeon providers                          # List available providers on the backend
inyeon commit --staged --provider openai  # Use OpenAI for this command
inyeon review --all --provider gemini     # Use Gemini for this command
```

Set a default provider via environment variable:

```bash
export INYEON_LLM_PROVIDER=openai   # All commands use OpenAI by default
inyeon commit --staged              # Uses OpenAI
inyeon commit --staged -p gemini    # Override to Gemini for this command
```

### Streaming Output (v4.0.0)

All commands stream real-time agent progress by default:

```bash
inyeon commit --staged                # Live progress: node completions, reasoning steps
inyeon commit --staged --no-stream    # Classic mode: spinner until done
```

### Local / Offline Mode (v4.0.0)

Run agents directly in the CLI process without a backend server:

```bash
inyeon commit --staged --local                    # Uses Ollama by default
inyeon commit --staged --local --provider gemini  # Uses Gemini API (still "local" — no backend)
inyeon auto --staged --local                      # Full pipeline in-process
```

Requires a running LLM provider (e.g., `ollama serve` for Ollama, or an API key for Gemini/OpenAI).

### Utilities

```bash
inyeon version   # Show version
inyeon health    # Check backend & LLM connection status
inyeon providers # List available LLM providers
```

> **Tip:** All commands accept `--api <url>` to override the backend URL and `--provider` / `-p` to select an LLM provider per-request.

---

## 🎯 Features

- **Full Workflow Automation** - Split, commit, review, and generate PRs in one command
- **Real-Time Streaming** - SSE-powered live progress for all agent operations
- **Offline Mode** - Run agents locally without a backend server (`--local`)
- **7 Specialized Agents** - Commit, review, split, PR, conflict resolution, changelog, orchestrator
- **Cost Optimization** - Smart diff truncation, response caching, and short-circuit logic
- **Atomic Commit Splitting** - 4 clustering strategies (directory, semantic, conventional, hybrid)
- **AI Conflict Resolution** - Understands both sides and produces merged code
- **Changelog Generation** - Groups commits by conventional type with narrative summaries
- **Git Hook Integration** - Auto-generate commit messages via prepare-commit-msg hook
- **RAG-Powered Context** - Understands your codebase via ChromaDB embeddings
- **Flexible LLM** - OpenAI, Gemini (cloud) or Ollama (local)
- **Conventional Commits** - Auto-generates properly formatted messages

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────┐
│                     CLI (Typer)                     │
│   commit  split  review  pr  resolve  changelog     │
│              --stream (SSE)  --local                │
└──────────┬──────────────────────────┬───────────────┘
           │ HTTP (default)           │ --local
           ▼                          ▼
┌────────────────────┐  ┌──────────────────────────┐
│   HttpEngine       │  │     LocalEngine          │
│ (APIClient → SSE)  │  │  (in-process agents)     │
└────────┬───────────┘  └──────────┬───────────────┘
         │                         │
         ▼                         ▼
┌────────────────────────────────────────────────────┐
│              LangGraph Agent Layer                 │
│                                                    │
│  CommitAgent  SplitAgent  PRAgent  ReviewAgent     │
│  ConflictAgent  ChangelogAgent  Orchestrator       │
│                                                    │
│  run()  →  graph.ainvoke()  (blocking)             │
│  run_stream()  →  graph.astream()  (SSE events)    │
└──────────────────────┬─────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │  LLM Factory │  │     Cost Optimization       │ │
│  │OpenAI/Gemini/│  │  Truncation  Cache  Batch   │ │
│  │    Ollama    │  │                             │ │
│  └──────────────┘  └─────────────────────────────┘ │
│                                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │   Clustering Engine   │   RAG (ChromaDB)    │   │
│  └─────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| **Layer** | **Technology** |
| --------- | -------------- |
| **CLI** | Typer, Rich |
| **Backend** | FastAPI, Pydantic |
| **Agents** | LangGraph |
| **Clustering** | scikit-learn, NumPy |
| **LLM** | OpenAI GPT-4.1, Gemini 2.5 Flash, Ollama |
| **RAG** | ChromaDB, Gemini Embeddings |
| **Deploy** | Docker, Railway |

---

## 📡 API Endpoints

| **Endpoint** | **Purpose** |
| ------------ | ----------- |
| `GET /health` | Health check (LLM status) |
| `GET /providers` | List available LLM providers |
| `POST /api/v1/generate-commit` | Generate commit message |
| `POST /api/v1/analyze` | Analyze a diff |
| `POST /api/v1/agent/run` | Run commit agent directly |
| `POST /api/v1/agent/split` | Split diff into atomic commits |
| `POST /api/v1/agent/review` | AI code review |
| `POST /api/v1/agent/pr` | Generate PR description |
| `POST /api/v1/agent/resolve` | Resolve merge conflicts |
| `POST /api/v1/agent/changelog` | Generate changelog |
| `POST /api/v1/agent/orchestrate` | Auto-route to agent |
| `GET /api/v1/agent/list` | List available agents |
| `POST /api/v1/agent/stream/commit` | Stream commit agent (SSE) |
| `POST /api/v1/agent/stream/review` | Stream review agent (SSE) |
| `POST /api/v1/agent/stream/pr` | Stream PR agent (SSE) |
| `POST /api/v1/agent/stream/split` | Stream split agent (SSE) |
| `POST /api/v1/agent/stream/resolve` | Stream conflict agent (SSE) |
| `POST /api/v1/agent/stream/changelog` | Stream changelog agent (SSE) |
| `POST /api/v1/rag/index` | Index codebase |
| `POST /api/v1/rag/search` | Semantic code search |
| `POST /api/v1/rag/stats` | Index statistics |
| `POST /api/v1/rag/clear` | Clear index for repo |

**Live Docs:** [FastAPI Swagger UI](https://inyeon-upstream-production.up.railway.app/docs)

---

## ⚙️ Configuration

All settings use the `INYEON_` prefix and can be set via environment variables or a `.env` file.

| **Variable** | **Default** | **Description** |
| ------------ | ----------- | --------------- |
| `INYEON_LLM_PROVIDER` | `ollama` | LLM backend (`ollama`, `gemini`, or `openai`) |
| `INYEON_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `INYEON_OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama model name |
| `INYEON_OLLAMA_TIMEOUT` | `120` | Ollama request timeout (seconds) |
| `INYEON_GEMINI_API_KEY` | — | Google Gemini API key (required for `gemini` provider) |
| `INYEON_GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `INYEON_OPENAI_API_KEY` | — | OpenAI API key (required for `openai` provider) |
| `INYEON_OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model name |
| `INYEON_API_URL` | — | Backend URL for CLI (overrides `--api` flag) |
| `INYEON_MAX_DIFF_CHARS` | `30000` | Max diff size before truncation |
| `INYEON_ENABLE_CACHE` | `true` | Enable response caching |

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
inyeon auto --staged --dry-run --api http://localhost:8000

# Run tests
pytest tests/ -v
```

---

## 📬 Contact

For contributions or inquiries, contact **Anh Tran** at [anhdtran.forwork@gmail.com](mailto:anhdtran.forwork@gmail.com)
