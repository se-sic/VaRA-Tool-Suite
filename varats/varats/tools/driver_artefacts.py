"""
Driver module for `vara-art`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import logging
import textwrap
import typing as tp
from collections import defaultdict
from pathlib import Path

import click
import yaml
from rich.progress import Progress

from varats.data.discover_reports import initialize_reports
from varats.paper_mgmt.artefacts import Artefact, initialize_artefact_types
from varats.paper_mgmt.paper_config import get_paper_config
from varats.plot.plots import PlotArtefact
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.tables.discover_tables import initialize_tables
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.html_util import (
    CSS_IMAGE_MATRIX,
    CSS_COMMON,
    html_page,
    CSS_TABLE,
)

LOG = logging.getLogger(__name__)


@click.group(
    help="Manage artefacts.",
    context_settings={"help_option_names": ['-h', '--help']}
)
def main() -> None:
    """
    Main function for working with artefacts.

    `vara-art`
    """
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()
    initialize_tables()
    initialize_plots()
    initialize_artefact_types()


# function name `list` would shadow built-in `list`
@main.command(
    name="list", help="List all artefacts of the current paper config."
)
def list_() -> None:
    """List the available artefacts."""
    paper_config = get_paper_config()

    for artefact in paper_config.artefacts:
        print(f"{artefact.name} [{artefact.ARTEFACT_TYPE}]")


@main.command(help="Show detailed information about artefacts.")
@click.argument("name")
def show(name: str) -> None:
    """
    Show detailed information about artefacts.

    Args:
        name: the name of the artefact
    """
    paper_config = get_paper_config()
    artefact = paper_config.artefacts.get_artefact(name)
    if artefact:
        print(f"Artefact '{name}':")
        print(textwrap.indent(yaml.dump(artefact.get_dict()), '  '))
    else:
        print(f"There is no artefact with the name {name}.")


@main.command(
    help="Generate artefacts. By default, all artefacts are generated."
)
@click.option(
    "--only",
    multiple=True,
    help="Only generate artefacts with the given names."
)
def generate(only: tp.Optional[str]) -> None:
    """
    Generate artefacts.

    By default, all artefacts are generated.

    Args:
        only: generate only this artefact
    """
    if not Artefact.base_output_dir().exists():
        Artefact.base_output_dir().mkdir(parents=True)
    artefacts: tp.Iterable[Artefact]

    if only:
        artefacts = [
            art for art in get_paper_config().get_all_artefacts()
            if art.name in only
        ]
    else:
        artefacts = get_paper_config().get_all_artefacts()

    with Progress() as progress:
        for artefact in progress.track(
            list(artefacts), description="Generating artefacts"
        ):
            LOG.info(
                f"Generating artefact {artefact.name} in location "
                f"{artefact.output_dir}"
            )
            artefact.generate_artefact(progress)

    # generate index.html
    _generate_index_html(artefacts, Artefact.base_output_dir() / "index.html")
    # generate plot_matrix.html
    plot_artefacts = list(_filter_plot_artefacts(artefacts))
    _generate_html_plot_matrix(
        plot_artefacts,
        Artefact.base_output_dir() / "plot_matrix.html"
    )


__INDEX_TABLE_TEMPLATE = """      <h2>{heading}</h2>
      <p><table>
        <thead>
          <tr>
            <th>Project</th>
            <th>File</th>
          </tr>
        </thead>
        <tbody>
{list}
        </tbody>
      </table></p>"""

__INDEX_ENTRY_TEMPLATE = \
    """        <tr>
          <td>{project}</td>
          <td><a href="{link}">{name}</a></td>
        </tr>"""

__COLUMN_TEMPLATE = """    <div class="column">
{}
    </div>"""

__IMAGE_TEMPLATE = """        <img src="{}" />"""

__INDEX_LINKS = """  <ul>
    <li><a href=".">artefacts folder</a></li>
    <li><a href="plot_matrix.html">plot matrix</a></li>
  </ul>"""


def _filter_plot_artefacts(
    artefacts: tp.Iterable[Artefact]
) -> tp.Iterable[PlotArtefact]:
    return [
        artefact for artefact in artefacts
        if isinstance(artefact, PlotArtefact)
    ]


def _generate_html_plot_matrix(
    artefacts: tp.Iterable[PlotArtefact], outfile: Path
) -> None:
    """
    Generates a html overview for the given artefacts.

    Args:
        artefacts: the artefacts to include in the overview
        outfile: the path to store the overview in
    """
    files: tp.Dict[str, tp.Dict[str, Path]] = defaultdict(dict)
    for artefact in artefacts:
        file_infos = artefact.get_artefact_file_infos()
        for file_info in file_infos:
            if file_info.case_study:
                file_path = _locate_artefact_file(
                    Path(file_info.file_name), artefact.output_dir,
                    outfile.parent
                )
                if not file_path:
                    continue
                files[file_info.case_study.project_name][artefact.name
                                                        ] = file_path

    columns: tp.List[str] = []
    for case_study in get_paper_config().get_all_case_studies():
        images: tp.List[str] = []
        for artefact in artefacts:

            image_path = files[case_study.project_name].get(artefact.name, None)
            if not image_path:
                continue
            images.append(__IMAGE_TEMPLATE.format(str(image_path)))
        if images:
            columns.append(__COLUMN_TEMPLATE.format("\n".join(images)))
    html = html_page(
        "Results", "\n".join(columns), [CSS_COMMON, CSS_IMAGE_MATRIX]
    )

    with open(outfile, "w") as file:
        file.write(html)


def _generate_index_html(
    artefacts: tp.Iterable[Artefact], outfile: Path
) -> None:
    """
    Generates a html overview for the given artefacts.

    Args:
        artefacts: the artefacts to include in the overview
        outfile: the path to store the overview in
    """
    columns: tp.List[str] = []
    for artefact in artefacts:
        artefact_info, artefact_html = _generate_artefact_html(
            artefact, outfile.parent
        )
        columns.append(
            __INDEX_TABLE_TEMPLATE.format(
                heading=artefact_info, list=artefact_html
            )
        )

    title = f"Artefacts for paper config \"{get_paper_config().path.name}\""
    content = __INDEX_LINKS
    content += __COLUMN_TEMPLATE.format("\n".join(columns))
    html = html_page(title, content, [CSS_COMMON, CSS_TABLE])

    with open(outfile, "w") as file:
        file.write(html)


def _generate_artefact_html(artefact: Artefact,
                            cwd: Path) -> tp.Tuple[str, str]:
    artefact_info = f"{artefact.name} ({artefact.ARTEFACT_TYPE})"
    list_entries: tp.List[str] = []
    file_infos = artefact.get_artefact_file_infos()
    for file_info in file_infos:
        artefact_file = file_info.file_name
        artefact_file_path = _locate_artefact_file(
            Path(artefact_file), artefact.output_dir, cwd
        )
        if artefact_file_path:
            list_entries.append(
                __INDEX_ENTRY_TEMPLATE.format(
                    project=file_info.case_study.project_name
                    if file_info.case_study else "[UNKNOWN]",
                    link=str(artefact_file_path),
                    name=artefact_file
                )
            )
    return artefact_info, "\n".join(list_entries)


def _locate_artefact_file(artefact_file: Path, output_dir: Path,
                          cwd: Path) -> tp.Optional[Path]:
    if not (output_dir / artefact_file).exists():
        LOG.info(f"Could not find artefact file {artefact_file}")
        return None
    return (output_dir / artefact_file).relative_to(cwd)


if __name__ == '__main__':
    main()
