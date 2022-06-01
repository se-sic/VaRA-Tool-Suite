"""Driver module for `vara-buildsetup`."""

import os
import typing as tp
from pathlib import Path
from tempfile import TemporaryDirectory

import click
from plumbum import colors

from varats.containers.containers import (
    ImageBase,
    run_container,
    BaseImageCreationContext,
    create_dev_image,
)
from varats.tools.research_tools.research_tool import (
    ResearchTool,
    SpecificCodeBase,
    Distro,
)
from varats.tools.research_tools.vara import VaRACodeBase
from varats.tools.research_tools.vara_manager import BuildType
from varats.tools.tool_util import (
    get_research_tool,
    get_supported_research_tool_names,
)
from varats.ts_utils.cli_util import initialize_cli_tool, cli_yn_choice
from varats.ts_utils.click_param_types import EnumChoice
from varats.utils.settings import save_config, vara_cfg, bb_cfg


def update_term(text: str, enable_inline: bool = False) -> None:
    """
    Print/Update terminal text with/without producing new lines.

    Args:
        text: output text that should be printed
        enable_inline: print lines without new lines
    """
    text = text.replace(os.linesep, '').strip()
    if not text:
        return
    if enable_inline:
        _, columns = os.popen('/bin/stty size', 'r').read().split()
        print(text, end=(int(columns) - len(text) - 1) * ' ' + '\r', flush=True)
    else:
        print(text)


def print_up_to_date_message(research_tool: ResearchTool[VaRACodeBase]) -> None:
    """
    Checks if VaRA's major release version is up to date and prints a message in
    the terminal if VaRA is outdated.

    Args:
        research_tool: The loaded research tool
    """
    highest_release_version = research_tool.find_highest_sub_prj_version(
        "vara-llvm-project"
    )
    if not research_tool.is_up_to_date():
        print(
            f"{colors.LightYellow}VaRA is outdated! Newest major release "
            f"version is {colors.bold}{colors.LightBlue}"
            f"{highest_release_version}{colors.bold.reset}{colors.fg.reset}\n"
        )


def show_major_release_prompt(
    research_tool: ResearchTool[VaRACodeBase]
) -> None:
    """
    Shows a prompt if VaRA's major release version is not up to date to decide
    if the user wants to upgrade.

    Args:
        research_tool: The loaded research tool
    """

    if not research_tool.is_up_to_date():
        print_up_to_date_message(research_tool)
        user_choice = cli_yn_choice(
            question="Do you want to upgrade?", default='y'
        )
        if user_choice:
            research_tool.upgrade()
            return

        return


@click.group(context_settings={"help_option_names": ['-h', '--help']})
def main() -> None:
    """Build VaRA on cli."""
    initialize_cli_tool()


@main.command()
def config() -> None:
    """Only create a VaRA-TS config file."""
    save_config()


@click.argument(
    "research_tool", type=click.Choice(get_supported_research_tool_names())
)
@click.option(
    "--version",
    metavar="VERSION",
    type=int,
    required=False,
    help="Version to download."
)
@click.option(
    "--source-location",
    type=click.Path(path_type=Path),
    required=False,
    help="Folder to store tool sources."
)
@click.option(
    "--install-prefix",
    type=click.Path(path_type=Path),
    required=False,
    help="Tool install folder."
)
@main.command()
def init(
    version: tp.Optional[int], install_prefix: tp.Optional[Path],
    source_location: tp.Optional[Path], research_tool: str
) -> None:
    """Initialize a research tool and all its components."""
    tool = get_research_tool(research_tool)
    __build_setup_init(tool, source_location, install_prefix, version)


@click.argument(
    "research_tool", type=click.Choice(get_supported_research_tool_names())
)
@main.command()
def update(research_tool: str) -> None:
    """Update a research tool and all its components."""
    tool = get_research_tool(research_tool)
    print_up_to_date_message(tool)
    tool.upgrade()


@click.argument(
    "research_tool", type=click.Choice(get_supported_research_tool_names())
)
@click.option(
    "--container",
    type=EnumChoice(ImageBase, case_sensitive=False),
    help="Build the tool in a container using the specified base image."
)
@click.option(
    "--install-prefix",
    type=click.Path(path_type=Path),
    required=False,
    help="Tool install folder."
)
@click.option(
    "--source-location",
    type=click.Path(path_type=Path),
    required=False,
    help="Folder to store tool sources."
)
@click.option(
    "--build-folder-suffix", required=False, help="Folder to use for building."
)
@click.option(
    "--build-type",
    type=EnumChoice(BuildType, case_sensitive=False),
    default=BuildType.DEV,
    help="Build type to use for the tool build configuration."
)
@main.command()
def build(
    research_tool: str, build_type: BuildType,
    build_folder_suffix: tp.Optional[str], source_location: tp.Optional[Path],
    install_prefix: tp.Optional[Path], container: tp.Optional[ImageBase]
) -> None:
    """Build a research tool and all its components."""
    tool = get_research_tool(research_tool, source_location)
    show_major_release_prompt(tool)

    if container:
        _build_in_container(tool, container, build_type, install_prefix)
    else:
        tool.build(
            build_type, __get_install_prefix(tool, install_prefix),
            build_folder_suffix
        )

        if not tool.verify_build(build_type, build_folder_suffix):
            print(f"{tool.name} was not built correctly.")
            return

        if tool.verify_install(__get_install_prefix(tool, install_prefix)):
            print(f"{tool.name} was correctly installed.")
        else:
            print(f"Could not install {tool.name} correctly.")


def __build_setup_init(
    tool: ResearchTool[SpecificCodeBase], source_location: tp.Optional[Path],
    raw_install_prefix: tp.Optional[Path], version: tp.Optional[int]
) -> None:

    if source_location and not source_location.exists():
        source_location.mkdir(parents=True)

    distro = Distro.get_current_distro()
    if distro:
        if not tool.get_dependencies().has_dependencies_for_distro(distro):
            missing_deps = tool.get_dependencies(
            ).get_missing_dependencies_for_distro(distro)
            print(
                f"The following dependencies "
                f"have to be installed: {missing_deps}"
            )
            return

    tool.setup(
        source_location,
        install_prefix=__get_install_prefix(tool, raw_install_prefix),
        version=version
    )


def __get_install_prefix(
    tool: ResearchTool[SpecificCodeBase], raw_install_prefix: tp.Optional[Path]
) -> Path:
    if raw_install_prefix:
        install_prefix = raw_install_prefix
    elif tool.has_install_location():
        install_prefix = tool.install_location()
    else:
        install_prefix = Path(str(os.getcwd()) + f"/tools/{tool.name}/")

    if not install_prefix.exists():
        install_prefix.mkdir(parents=True)

    return install_prefix


def _build_in_container(
    tool: ResearchTool[SpecificCodeBase],
    image_base: ImageBase,
    build_type: BuildType,
    install_prefix: tp.Optional[Path] = None
) -> None:
    vara_cfg()["container"]["research_tool"] = tool.name
    image_name = f"{image_base.image_name}_{build_type.name}"

    if not install_prefix:
        install_prefix = Path(
            str(tool.install_location()) + "_" + image_base.name
        )

    if not install_prefix.exists():
        install_prefix.mkdir(parents=True)

    source_mount = 'tools_src/'
    install_mount = 'tools/'

    click.echo("Preparing container image.")
    create_dev_image(image_base, tool)

    with TemporaryDirectory() as tmpdir:
        image_context = BaseImageCreationContext(image_base, Path(tmpdir))
        source_mount = str(image_context.varats_root / source_mount)
        install_mount = str(image_context.varats_root / install_mount)
        bb_cfg()["container"]["mounts"].value[:] += [
            # mount tool src dir
            [str(tool.source_location()), source_mount],
            # mount install dir
            [str(install_prefix), install_mount]
        ]

    click.echo(
        f"Building {tool.name} ({build_type.name}) "
        f"in a container ({image_base.name})."
    )

    run_container(
        image_name, f"build_{tool.name}", None, [
            "build",
            tool.name.lower(),
            f"--build-type={build_type.name}",
            f"--source-location={source_mount}",
            f"--install-prefix={install_mount}",
            f"--build-folder-suffix={image_base.name}",
        ]
    )


if __name__ == '__main__':
    main()
