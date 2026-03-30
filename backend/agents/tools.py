import os
import subprocess
from typing import Any, Callable


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_ollama_format(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs) -> str:
        return await self.func(**kwargs)


def _safe_resolve(path: str, repo_path: str) -> str:
    repo_root = os.path.realpath(repo_path)
    resolved = os.path.realpath(os.path.join(repo_root, path))
    if not resolved.startswith(repo_root + os.sep) and resolved != repo_root:
        raise PermissionError(f"Path escapes repository root: {path}")
    return resolved


async def read_file(path: str, repo_path: str = ".") -> str:
    try:
        full_path = _safe_resolve(path, repo_path)
    except PermissionError as e:
        return f"Error: {e}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 10000:
            content = content[:10000] + "\n... (truncated)"
        return content
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


async def list_files(directory: str = ".", repo_path: str = ".") -> str:
    try:
        full_path = _safe_resolve(directory, repo_path)
    except PermissionError as e:
        return f"Error: {e}"

    try:
        files = os.listdir(full_path)
        return "\n".join(files[:50])
    except Exception as e:
        return f"Error listing directory: {e}"


async def get_git_log(count: int = 5, repo_path: str = ".") -> str:
    count = max(1, min(count, 50))
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout or "No commits found"
    except Exception as e:
        return f"Error getting git log: {e}"


AGENT_TOOLS = [
    Tool(
        name="read_file",
        description="Read the contents of a file from the repository.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                },
            },
            "required": ["path"],
        },
        func=read_file,
    ),
    Tool(
        name="list_files",
        description="List files in a directory.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path",
                    "default": ".",
                },
            },
        },
        func=list_files,
    ),
    Tool(
        name="get_git_log",
        description="Get recent commit messages.",
        parameters={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of commits to retrieve",
                    "default": 5,
                },
            },
        },
        func=get_git_log,
    ),
]
