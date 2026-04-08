"""Shared streaming display using Rich Live."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


def render_stream(events: Iterator[dict], console: Console) -> dict | None:
    """Consume SSE events, render live progress, return final result data.

    Returns the RESULT event's data dict, or None if an error occurred.
    """
    steps: list[str] = []
    current_node = ""
    result_data: dict | None = None
    agent_name = ""

    def _build_display() -> Panel:
        content = Text()
        for step in steps:
            content.append(f"  {step}\n", style="dim")
        if current_node:
            content.append(f"  > {current_node}...\n", style="bold cyan")
        title = f"[bold]{agent_name}[/bold]" if agent_name else "Agent"
        return Panel(content, title=title, border_style="blue", expand=False)

    with Live(_build_display(), console=console, refresh_per_second=8) as live:
        for event in events:
            event_type = event.get("event", "")

            if event_type == "agent_start":
                agent_name = event.get("agent", "agent")
                live.update(_build_display())

            elif event_type == "node_complete":
                node = event.get("node", "")
                if current_node:
                    steps.append(current_node)
                current_node = ""
                steps.append(f"[green]\u2713[/green] {node}")
                live.update(_build_display())

            elif event_type == "node_start":
                current_node = event.get("node", "")
                live.update(_build_display())

            elif event_type == "reasoning":
                step = event.get("data", {}).get("step", "")
                if step:
                    steps.append(f"  {step}")
                    live.update(_build_display())

            elif event_type == "progress":
                msg = event.get("data", {}).get("message", "")
                if msg:
                    steps.append(msg)
                    live.update(_build_display())

            elif event_type == "result":
                result_data = event.get("data", {})

            elif event_type == "error":
                error_msg = event.get("data", {}).get("error", "Unknown error")
                console.print(f"[red]Error:[/red] {error_msg}")
                return None

            elif event_type == "done":
                break

    return result_data


def render_local_stream(
    async_iter: AsyncIterator[Any],
    console: Console,
) -> dict | None:
    """Stream events from a local async iterator and render them in real-time.

    Usage: render_local_stream(engine.generate_commit_stream(diff), console)
    """
    import queue
    import threading

    _SENTINEL = object()
    q: queue.Queue = queue.Queue()

    def _run():
        async def _consume():
            try:
                async for event in async_iter:
                    q.put(event.model_dump())
            except Exception as exc:
                q.put({"event": "error", "data": {"error": str(exc)}})
            finally:
                q.put(_SENTINEL)

        asyncio.run(_consume())

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    def _event_iter():
        while True:
            item = q.get()
            if item is _SENTINEL:
                return
            yield item

    return render_stream(_event_iter(), console)
