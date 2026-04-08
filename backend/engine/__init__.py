"""
Execution Engine Package

Provides the ExecutionEngine protocol and implementations for running agents
either via HTTP (backend server) or locally (in-process).
"""

from .base import ExecutionEngine, EngineResult

__all__ = ["ExecutionEngine", "EngineResult"]
