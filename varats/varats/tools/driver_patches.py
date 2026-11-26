"""Driver module for ``vara-patches``."""

from pathlib import Path

import click

from varats.ts_utils.cli_util import initialize_cli_tool
from varats.utils.settings import bb_cfg, save_config, vara_cfg

PatchSource = dict[str, str]


def _patch_sources() -> list[PatchSource]:
    """Return the configured remote patch sources."""
    return list(vara_cfg()["patch_provider"]["repositories"].value or [])


def _source_name(path: str) -> str:
    """Derive a local checkout name from a patch repository path."""
    name = Path(path.rstrip("/")).name.removesuffix(".git")
    if not name:
        raise click.BadParameter("Could not derive a local source name.")
    return name


def _source_matches(source: PatchSource, identifier: str) -> bool:
    """Check whether an identifier refers to a configured source."""
    return identifier in (source["remote"], source["local"])


@click.group(
    "vara-patches",
    help="Manage patch repositories.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
def main() -> None:
    """Manage patch repositories."""
    initialize_cli_tool()
    bb_cfg()


@main.command("list")
def list_sources() -> None:
    """List all registered patch sources."""
    sources = _patch_sources()
    if not sources:
        click.echo("No patch sources registered.")
        return

    for source in sources:
        click.echo(
            f"{source['local']}\t{source['remote']}\t{source['refspec']}"
        )


@main.command("register")
@click.argument("path")
@click.argument("local", required=False)
@click.argument("refspec", required=False)
def register(path: str, local: str | None, refspec: str | None) -> None:
    """Register a patch repository at PATH [LOCAL] [REFSPEC]."""
    local_name = local or _source_name(path)
    source: PatchSource = {
        "remote": path,
        "local": local_name,
        "refspec": refspec or "origin/HEAD",
    }
    sources = _patch_sources()
    if any(existing["local"] == local_name for existing in sources):
        raise click.ClickException(
            f"A patch source named '{local_name}' is already registered."
        )
    if any(existing["remote"] == path for existing in sources):
        raise click.ClickException(
            f"Patch source '{path}' is already registered."
        )

    sources.append(source)
    vara_cfg()["patch_provider"]["repositories"] = sources
    save_config()
    click.echo(f"Registered patch source '{local_name}'.")


@main.command("unregister")
@click.argument("source")
def unregister(source: str) -> None:
    """Remove a patch source identified by its LOCAL name or PATH."""
    sources = _patch_sources()
    remaining_sources = [
        configured_source
        for configured_source in sources
        if not _source_matches(configured_source, source)
    ]
    if len(remaining_sources) == len(sources):
        raise click.ClickException(f"No patch source matches '{source}'.")

    vara_cfg()["patch_provider"]["repositories"] = remaining_sources
    save_config()
    click.echo(f"Unregistered patch source '{source}'.")


if __name__ == "__main__":
    main()
