"""
Driver module for `vara-table`.

This module automatically detects table generators and creates a separate
subcommand for each generator. For this to work, table generators must be placed
in the module `varats.table.tables`.
"""

import logging
import typing as tp

import click

from varats.paper_mgmt.paper_config import get_paper_config
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.table.tables import (
    TableGenerator,
    CommonTableOptions,
    TableConfig,
    TableArtefact,
    TableGeneratorFailed,
)
from varats.tables.discover_tables import initialize_tables
from varats.ts_utils.cli_util import initialize_cli_tool, add_cli_options

LOG = logging.getLogger(__name__)


class TableCLI(click.MultiCommand):
    """Command factory for tables."""

    def __init__(self, **attrs: tp.Any):
        initialize_tables()
        super().__init__(**attrs)

    def list_commands(self, ctx: click.Context) -> tp.List[str]:
        return list(TableGenerator.GENERATORS.keys())

    def get_command(self, ctx: click.Context,
                    cmd_name: str) -> tp.Optional[click.Command]:

        generator_cls = TableGenerator.GENERATORS[cmd_name]

        @click.pass_context
        def command_template(context: click.Context, **kwargs: tp.Any) -> None:
            # extract common arguments and table config from context
            common_options: CommonTableOptions = context.obj["common_options"]
            table_config: TableConfig = context.obj["table_config"]
            artefact_name: str = context.obj["save_artefact"]

            try:
                generator_instance = generator_cls(table_config, **kwargs)
                if artefact_name:
                    paper_config = get_paper_config()
                    if paper_config.artefacts.get_artefact(artefact_name):
                        LOG.info(
                            f"Updating existing artefact '{artefact_name}'."
                        )
                    else:
                        LOG.info(f"Creating new artefact '{artefact_name}'.")
                    artefact = TableArtefact.from_generator(
                        artefact_name, generator_instance, common_options
                    )
                    paper_config.add_artefact(artefact)
                    paper_config.store_artefacts()
                else:
                    generator_instance(common_options)
            except TableGeneratorFailed as ex:
                print(
                    f"Failed to create table generator {generator_cls.NAME}: "
                    f"{ex.message}"
                )

        # return command wrapped with options specified in the generator class
        command_definition = add_cli_options(
            command_template, *generator_cls.OPTIONS
        )
        return click.command(cmd_name)(command_definition)


@click.command(
    cls=TableCLI,
    help="Generate tables.",
    context_settings={"help_option_names": ['-h', '--help']}
)
@CommonTableOptions.cli_options
@click.option(
    "--save-artefact",
    metavar="NAME",
    help="Save the table specification in the artefact file with the "
    "given name."
)
@TableConfig.cli_options
@click.pass_context
def main(context: click.Context, **kwargs: tp.Any) -> None:
    """Entry point for the table generation tool."""
    # store common options in context so they can be passed to subcommands
    common_options = CommonTableOptions.from_kwargs(**kwargs)
    table_config = TableConfig.from_kwargs(**kwargs)
    context.ensure_object(dict)
    context.obj["common_options"] = common_options
    context.obj["table_config"] = table_config
    context.obj["save_artefact"] = kwargs["save_artefact"]

    initialize_cli_tool()
    initialize_projects()
    initialize_tables()
    initialize_plots()


if __name__ == '__main__':
    main()
