"""
Driver module for `vara-art`.

This module handles command-line parsing and maps the commands to tool suite
internal functionality.
"""
import argparse
import logging
import textwrap
import typing as tp
from pathlib import Path

import yaml
from argparse_utils import enum_action

from varats.data.discover_reports import initialize_reports
from varats.paper_mgmt.artefacts import (
    Artefact,
    ArtefactType,
    create_artefact,
    store_artefacts,
    PlotArtefact,
    filter_plot_artefacts,
    TableArtefact,
)
from varats.paper_mgmt.paper_config import get_paper_config
from varats.plot.plots import prepare_plots
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import prepare_tables
from varats.tables.discover_tables import initialize_tables
from varats.ts_utils.html_utils import (
    CSS_IMAGE_MATRIX,
    CSS_COMMON,
    html_page,
    CSS_TABLE,
)
from varats.utils.cli_util import initialize_cli_tool
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


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
    parser = argparse.ArgumentParser("vara-art")

    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    # vara-art list
    sub_parsers.add_parser(
        'list', help="List all artefacts of the current paper config."
    )

    # vara-art show
    show_parser = sub_parsers.add_parser(
        'show', help="Show detailed insformation about artefacts."
    )
    show_parser.add_argument(
        "names", nargs='+', help="The names of the artefacts to show."
    )

    # vara-art generate
    generate_parser = sub_parsers.add_parser(
        'generate',
        help="Generate artefacts. By default, all artefacts are generated."
    )
    generate_parser.add_argument(
        "--only",
        nargs='+',
        help="Only generate artefacts with the given names."
    )

    # vara-art add
    add_parser = sub_parsers.add_parser(
        'add',
        help=(
            "Add a new artefact to the current paper config or edit an "
            "existing artefacts."
        )
    )
    add_parser.add_argument(
        "artefact_type",
        help="The type of the new artefact.",
        action=enum_action(ArtefactType, str.upper)
    )
    add_parser.add_argument(
        "name",
        help="The name for the new artefact. "
        "If an artefact with this name already exists, it is overridden.",
        type=str
    )
    add_parser.add_argument(
        "--output-path",
        help=(
            "The output file for the new artefact. This is relative to "
            "`artefacts_dir/current_config` from the current `.varats.yml`."
        ),
        type=str,
        default="."
    )
    add_parser.add_argument(
        "extra_args",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help=(
            "Provide additional arguments that will be passed to the class "
            "that generates the artefact. (do not put spaces before or after "
            "the '=' sign). If a value contains spaces, you should define it "
            'with double quotes: foo="bar baz".'
        )
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    if 'subcommand' not in args:
        parser.print_help()
        return

    if args['subcommand'] == 'list':
        _artefact_list()
    elif args['subcommand'] == 'show':
        _artefact_show(args)
    elif args['subcommand'] == 'generate':
        _artefact_generate(args)
    elif args['subcommand'] == 'add':
        _artefact_add(args)


def _artefact_list() -> None:
    paper_config = get_paper_config()

    for artefact in paper_config.artefacts:
        print(f"{artefact.name} [{artefact.artefact_type.name}]")


def _artefact_show(args: tp.Dict[str, tp.Any]) -> None:
    paper_config = get_paper_config()
    for name in args['names']:
        artefact = paper_config.artefacts.get_artefact(name)
        if artefact:
            print(f"Artefact '{name}':")
            print(textwrap.indent(yaml.dump(artefact.get_dict()), '  '))
        else:
            print(f"There is no artefact with the name {name}.")


def _artefact_generate(args: tp.Dict[str, tp.Any]) -> None:
    artefacts: tp.Iterable[Artefact]

    if 'only' in args.keys():
        artefacts = [
            art for art in get_paper_config().get_all_artefacts()
            if art.name in args['only']
        ]
    else:
        artefacts = get_paper_config().get_all_artefacts()

    for artefact in artefacts:
        LOG.info(
            f"Generating artefact {artefact.name} in location "
            f"{artefact.output_path}"
        )
        artefact.generate_artefact()

    # generate index.html
    _generate_index_html(
        artefacts,
        Path(vara_cfg()['artefacts']['artefacts_dir'].value) /
        vara_cfg()['paper_config']['current_config'].value / "index.html"
    )
    # generate plot_matrix.html
    plot_artefacts = [
        artefact for artefact in (filter_plot_artefacts(artefacts))
        if artefact.plot_kwargs.get('paper_config', False)
    ]
    _generate_html_plot_matrix(
        plot_artefacts,
        Path(vara_cfg()['artefacts']['artefacts_dir'].value) /
        vara_cfg()['paper_config']['current_config'].value / "plot_matrix.html"
    )


def _artefact_add(args: tp.Dict[str, tp.Any]) -> None:
    paper_config = get_paper_config()

    if 'extra_args' in args.keys():
        extra_args = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in args['extra_args']]
        }
    else:
        extra_args = {}

    name = args['name']
    if paper_config.artefacts.get_artefact(name):
        LOG.info(f"Updating existing artefact '{name}'.")
    else:
        LOG.info(f"Creating new artefact '{name}'.")
    artefact = create_artefact(
        args['artefact_type'], name, args['output_path'], **extra_args
    )
    paper_config.add_artefact(artefact)
    store_artefacts(paper_config.artefacts, paper_config.path)


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


def _generate_html_plot_matrix(
    artefacts: tp.Iterable[PlotArtefact], outfile: Path
) -> None:
    """
    Generates a html overview for the given artefacts.

    Args:
        artefacts: the artefacts to include in the overview
        outfile: the path to store the overview in
    """

    columns: tp.List[str] = []
    for case_study in get_paper_config().get_all_case_studies():
        images: tp.List[str] = []
        for artefact in artefacts:
            kwargs = dict(artefact.plot_kwargs)
            kwargs['project'] = case_study.project_name
            kwargs['plot_case_study'] = case_study
            plot_name = artefact.plot_type_class(**kwargs).plot_file_name(
                artefact.file_format
            )
            if not (artefact.output_path / plot_name).exists():
                LOG.info(f"Could not find image {plot_name}")
                continue
            image_path = (artefact.output_path /
                          plot_name).relative_to(outfile.parent)
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
    artefact_info = f"{artefact.name} ({artefact.artefact_type.name})"
    list_entries: tp.List[str] = []
    entries = _get_artefact_files_info(artefact)
    for entry in entries:
        artefact_file = entry["file_name"]
        artefact_file_path = _locate_artefact_file(
            Path(artefact_file), artefact.output_path, cwd
        )
        if artefact_file_path:
            list_entries.append(
                __INDEX_ENTRY_TEMPLATE.format(
                    project=entry["project"],
                    link=str(artefact_file_path),
                    name=artefact_file
                )
            )
    return artefact_info, "\n".join(list_entries)


def _get_artefact_files_info(artefact: Artefact) -> tp.List[tp.Dict[str, str]]:
    if artefact.artefact_type == ArtefactType.PLOT:
        artefact = tp.cast(PlotArtefact, artefact)
        plots = prepare_plots(
            plot_type=artefact.plot_type,
            result_output=artefact.output_path,
            file_format=artefact.file_format,
            **artefact.plot_kwargs
        )
        return [{
            "file_name": plot.plot_file_name(artefact.file_format),
            "project": plot.plot_kwargs.get("project", "[UNKNOWN]")
        } for plot in plots]

    if artefact.artefact_type == ArtefactType.TABLE:
        artefact = tp.cast(TableArtefact, artefact)
        tables = prepare_tables(
            table_type=artefact.table_type,
            result_output=artefact.output_path,
            file_format=artefact.file_format,
            **artefact.table_kwargs
        )
        return [{
            "file_name": table.table_file_name(),
            "project": table.table_kwargs.get("project", "[UNKNOWN]")
        } for table in tables]

    raise AssertionError(
        f"Missing implementation for artefact type {artefact.artefact_type}"
    )


def _locate_artefact_file(artefact_file: Path, output_path: Path,
                          cwd: Path) -> tp.Optional[Path]:
    if not (output_path / artefact_file).exists():
        LOG.info(f"Could not find artefact file {artefact_file}")
        return None
    return (output_path / artefact_file).relative_to(cwd)


if __name__ == '__main__':
    main()
