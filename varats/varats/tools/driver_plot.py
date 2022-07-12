"""
Driver module for `vara-plot`.

This module automatically detects plot generators and creates a separate
subcommand for each generator. For this to work, plot generators must be placed
in the module `varats.plot.plots`.
"""

import logging
import typing as tp

import click

from varats.paper_mgmt.paper_config import get_paper_config
from varats.plot.plots import (
    PlotGenerator,
    CommonPlotOptions,
    PlotConfig,
    PlotGeneratorFailed,
    PlotArtefact,
)
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.tables.discover_tables import initialize_tables
from varats.ts_utils.cli_util import initialize_cli_tool, add_cli_options

LOG = logging.getLogger(__name__)


class PlotCLI(click.MultiCommand):
    """Command factory for plots."""

    def __init__(self, **attrs: tp.Any):
        initialize_plots()
        super().__init__(**attrs)

    def list_commands(self, ctx: click.Context) -> tp.List[str]:
        return list(PlotGenerator.GENERATORS.keys())

    def get_command(self, ctx: click.Context,
                    cmd_name: str) -> tp.Optional[click.Command]:

        generator_cls = PlotGenerator.GENERATORS[cmd_name]

        @click.pass_context
        def command_template(context: click.Context, **kwargs: tp.Any) -> None:
            # extract common arguments and plot config from context
            common_options: CommonPlotOptions = context.obj["common_options"]
            plot_config: PlotConfig = context.obj["plot_config"]
            artefact_name: str = context.obj["save_artefact"]

            try:
                generator_instance = generator_cls(plot_config, **kwargs)
                if artefact_name:
                    paper_config = get_paper_config()
                    if paper_config.artefacts.get_artefact(artefact_name):
                        LOG.info(
                            f"Updating existing artefact '{artefact_name}'."
                        )
                    else:
                        LOG.info(f"Creating new artefact '{artefact_name}'.")
                    artefact = PlotArtefact.from_generator(
                        artefact_name, generator_instance, common_options
                    )
                    paper_config.add_artefact(artefact)
                    paper_config.store_artefacts()
                else:
                    generator_instance(common_options)
            except PlotGeneratorFailed as ex:
                print(
                    f"Failed to create plot generator {generator_cls.NAME}: "
                    f"{ex.message}"
                )

        # return command wrapped with options specified in the generator class
        command_definition = add_cli_options(
            command_template, *generator_cls.OPTIONS
        )
        return click.command(cmd_name)(command_definition)


@click.command(
    cls=PlotCLI,
    help="Generate plots.",
    context_settings={"help_option_names": ['-h', '--help']}
)
@CommonPlotOptions.cli_options
@click.option(
    "--save-artefact",
    metavar="NAME",
    help="Save the plot specification in the artefact file with the given name."
)
@PlotConfig.cli_options
@click.pass_context
def main(context: click.Context, **kwargs: tp.Any) -> None:
    """Entry point for the plot generation tool."""
    # store common options in context so they can be passed to subcommands
    common_options = CommonPlotOptions.from_kwargs(**kwargs)
    plot_config = PlotConfig.from_kwargs(**kwargs)
    context.ensure_object(dict)
    context.obj["common_options"] = common_options
    context.obj["plot_config"] = plot_config
    context.obj["save_artefact"] = kwargs["save_artefact"]

    initialize_cli_tool()
    initialize_projects()
    initialize_tables()
    initialize_plots()


if __name__ == '__main__':
    main()
