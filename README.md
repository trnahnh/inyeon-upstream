# Inyeon

**Inyeon** (인연, "fated connection") — AI-powered git workflow tool. Analyze diffs, generate conventional commits, all running locally with Ollama.

## Quick Start
```bash
# Prerequisites: Python 3.11+, Ollama
ollama pull qwen2.5-coder:7b

# Install
git clone https://github.com/suka712/inyeon-upstream.git
cd inyeon-upstream
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Run
uvicorn backend.main:app --port 8000
inyeon health
```

## Usage
```bash
# Analyze diffs
git diff --cached | inyeon analyze
git diff | inyeon analyze -c "Refactoring auth module"

# Generate commits
inyeon commit --staged
inyeon commit --staged --dry-run --issue "#234"
```

## Commands

| Command   | Description                    |
| --------- | ------------------------------ |
| `analyze` | Analyze diff from stdin/file   |
| `commit`  | Generate commit message        |
| `health`  | Check service status           |

**analyze**: `-f FILE`, `-c CONTEXT`, `-j` (JSON output)

**commit**: `-s` (staged), `-a` (all), `-i ISSUE`, `-n` (dry-run), `-j` (JSON)

## Configuration

| Variable              | Default                  |
| --------------------- | ------------------------ |
| `INYEON_API_URL`      | `http://localhost:8000`  |
| `INYEON_TIMEOUT`      | `120`                    |
| `INYEON_OLLAMA_URL`   | `http://localhost:11434` |
| `INYEON_OLLAMA_MODEL` | `qwen2.5-coder:7b`       |

## API

| Method | Endpoint                  |
| ------ | ------------------------- |
| GET    | `/health`                 |
| POST   | `/api/v1/analyze`         |
| POST   | `/api/v1/generate-commit` |

Docs: `http://localhost:8000/docs`

---

Built with [Ollama](https://ollama.com/), [FastAPI](https://fastapi.tiangolo.com/), [Typer](https://typer.tiangolo.com/)