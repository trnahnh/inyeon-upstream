from importlib.metadata import version, PackageNotFoundError

import typer

from cli.commands import analyze, auto, changelog, commit, agent, hook, index, pr, resolve, review, split

try:
    _pkg_version = version("inyeon")
except PackageNotFoundError:
    _pkg_version = "3.5.0"


app = typer.Typer(
    name="inyeon",
    help="Your Daniel Craig's Vesper Lynd, the most powerful Git workflow assistant.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(analyze.app, name="analyze")
app.add_typer(auto.app, name="auto")
app.add_typer(changelog.app, name="changelog")
app.add_typer(commit.app, name="commit")
app.add_typer(agent.app, name="agent")
app.add_typer(hook.app, name="hook")
app.add_typer(index.app, name="index")
app.add_typer(pr.app, name="pr")
app.add_typer(resolve.app, name="resolve")
app.add_typer(review.app, name="review")
app.add_typer(split.app, name="split")


@app.command("version")
def show_version():
    typer.echo(f"inyeon v{_pkg_version}")


@app.command()
def health(
    api_url: str = typer.Option(
        None,
        "--api",
        help="Backend API URL",
        envvar="INYEON_API_URL",
    ),
):
    """Check backend connection status."""
    from rich.console import Console
    from cli.api_client import APIClient, APIError

    console = Console()

    try:
        client = APIClient(base_url=api_url)
        result = client.health_check()

        status = result.get("status", "unknown")
        if status == "healthy":
            console.print(f"[green]✓ Backend:[/green] {client.base_url}")
        else:
            console.print(f"[yellow]! Backend:[/yellow] {status}")

        llm = result.get("llm", {})
        if llm.get("connected"):
            console.print(f"[green]✓ LLM:[/green] {llm.get('provider')}")
        else:
            console.print("[red]✗ LLM:[/red] Not connected")

    except APIError as e:
        console.print(f"[red]✗ Backend:[/red] {e}")
        raise typer.Exit(1)


@app.command("providers")
def list_providers(
    api_url: str = typer.Option(
        None,
        "--api",
        help="Backend API URL",
        envvar="INYEON_API_URL",
    ),
):
    """List available LLM providers on the backend."""
    from rich.console import Console
    from cli.api_client import APIClient, APIError

    console = Console()

    try:
        client = APIClient(base_url=api_url)
        result = client.list_providers()

        default = result.get("default", "unknown")
        console.print(f"[bold]Default provider:[/bold] {default}\n")
        console.print("[bold]Available providers:[/bold]")
        for p in result.get("available", []):
            marker = "[green]●[/green]" if p["name"] == default else "[dim]○[/dim]"
            console.print(f"  {marker} {p['name']} ({p['model']})")

    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
