# Inyeon

> "You are Daniel Craig but life owes you a Vesper Lynd? Let Inyeon be your Casino Royale."

**Inyeon** (인연, meaning "fated connection") is a CLI tool that brings AI-powered intelligence to your git workflow. Analyze diffs, generate professional commit messages, and ship code with confidence.

## Features

- **AI Diff Analysis** — Go beyond syntax highlighting. Understand *what* changed, *why* it matters, and *what* could break.
- **Conventional Commits** — Auto-generate team-ready commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) spec.
- **Privacy-First** — Runs on your infrastructure with [Ollama](https://ollama.com/). Your code never leaves your machine.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/download) with `qwen2.5-coder:7b` model

```bash
# Install Ollama and pull the model
ollama pull qwen2.5-coder:7b

Installation

# Clone the repository
git clone https://github.com/suka712/inyeon-upstream.git
cd inyeon-upstream

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install
pip install -e .

Start the Backend

uvicorn backend.main:app --port 8000

Verify Installation

inyeon health

Usage

Analyze a Diff

# Analyze staged changes
git diff --cached | inyeon analyze

# Analyze last commit
git diff HEAD~1 | inyeon analyze

# Analyze with context
git diff | inyeon analyze -c "Refactoring auth module"

Output:
╭─────────────────────────────── Summary ────────────────────────────────╮
│ Refactored auth to use bcrypt instead of MD5 for password hashing.    │
╰────────────────────────────────────────────────────────────────────────╯

Impact: HIGH
Categories: security, refactor

Breaking Changes:
• Existing password hashes are incompatible

Files Changed:
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File          ┃ Type     ┃ Summary                          ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ auth/hash.py  │ modified │ Replaced MD5 with bcrypt         │
└───────────────┴──────────┴──────────────────────────────────┘

Generate Commit Messages

# Generate from staged changes
inyeon commit --staged

# Preview without committing
inyeon commit --staged --dry-run

# Include issue reference
inyeon commit --staged --issue "#234"

Output:
╭──────────────────────────── feat(auth) ────────────────────────────────╮
│ feat(auth): implement bcrypt password hashing                          │
│                                                                        │
│ Replace MD5 with bcrypt for secure password storage.                   │
│ Add per-user salts and password length validation.                     │
│                                                                        │
│ BREAKING CHANGE: Users must reset passwords after migration.           │
│ Refs: #234                                                             │
╰────────────────────────────────────────────────────────────────────────╯

Create this commit? [y/n]:

Commands

| Command        | Description                           |
|----------------|---------------------------------------|
| inyeon analyze | Analyze a git diff from stdin or file |
| inyeon commit  | Generate and create a commit message  |
| inyeon health  | Check backend and Ollama connection   |
| inyeon version | Show version information              |

Options

analyze
| Option        | Description                          |
|---------------|--------------------------------------|
| -f, --file    | Read diff from file instead of stdin |
| -c, --context | Additional context for analysis      |
| -j, --json    | Output raw JSON                      |

commit
| Option        | Description                  |
|---------------|------------------------------|
| -s, --staged  | Use staged changes           |
| -a, --all     | Use all uncommitted changes  |
| -i, --issue   | Issue reference (e.g., #234) |
| -n, --dry-run | Preview without committing   |
| -j, --json    | Output raw JSON              |

Configuration

Environment Variables

| Variable            | Default                | Description               |
|---------------------|------------------------|---------------------------|
| INYEON_API_URL      | http://localhost:8000  | Backend API URL           |
| INYEON_TIMEOUT      | 120                    | Request timeout (seconds) |
| INYEON_OLLAMA_URL   | http://localhost:11434 | Ollama API URL            |
| INYEON_OLLAMA_MODEL | qwen2.5-coder:7b       | Ollama model name         |

Config File

Create .env in the project root:

INYEON_API_URL=http://localhost:8000
INYEON_OLLAMA_MODEL=qwen2.5-coder:7b

Architecture

┌─────────────┐     HTTP      ┌─────────────┐     HTTP      ┌─────────────┐
│  inyeon CLI │──────────────▶│   FastAPI   │──────────────▶│   Ollama    │
│   (local)   │               │   Backend   │               │   (local)   │
└─────────────┘               └─────────────┘               └─────────────┘

- CLI — Typer-based command line interface
- Backend — FastAPI server handling LLM requests
- Ollama — Local LLM inference (qwen2.5-coder:7b)

Development

# Install with dev dependencies
pip install -e ".[dev]"

# Run backend with auto-reload
uvicorn backend.main:app --reload --port 8000

# Run tests
pytest

API Endpoints

| Method | Endpoint                | Description             |
|--------|-------------------------|-------------------------|
| GET    | /health                 | Health check            |
| POST   | /api/v1/analyze         | Analyze git diff        |
| POST   | /api/v1/generate-commit | Generate commit message |

Interactive docs available at http://localhost:8000/docs
```


Built with https://ollama.com/, https://fastapi.tiangolo.com/, and https://typer.tiangolo.com/.