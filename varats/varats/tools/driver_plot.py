"""
Driver module for `vara-plot`.

This module automatically detects plot generators and creates a separate
subcommand for each generator. For this to work, plot generators must be placed
in the module `varats.plot.plots`.
"""

import logging
import typing as tp

import click as click

from varats.data.discover_reports import initialize_reports
from varats.plot.plots import (
    PlotGenerator,
    CommonPlotOptions,
    PlotConfig,
    PlotGeneratorInitFailed,
)
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.ts_utils.cli_util import initialize_cli_tool, add_cli_options

LOG = logging.getLogger(__name__)


@click.group()
@PlotConfig.cli_options
@CommonPlotOptions.cli_options
@click.pass_context
def main(context: click.Context, **kwargs: tp.Any) -> None:
    """Entry point for the plot generation tool."""
    # store common options in context so they can be passed to subcommands
    common_options = CommonPlotOptions.from_kwargs(**kwargs)
    plot_config = PlotConfig()
    context.obj = (common_options, plot_config)

    initialize_cli_tool()
    initialize_projects()
    initialize_reports()


# plot discovery also discovers plot generators
initialize_plots()

# create a click command for each generator
for generator_name, generator_cls in PlotGenerator.GENERATORS.items():

    def generate_command(
        generator: tp.Type[PlotGenerator]
    ) -> tp.Callable[..., None]:

        @click.pass_context
        def command_template(context: click.Context, **kwargs: tp.Any) -> None:
            # extract common arguments and plot config from context
            common_options: CommonPlotOptions
            plot_config: PlotConfig
            common_options, plot_config = context.obj

            try:
                generator_instance = generator(plot_config, **kwargs)
                generator_instance(common_options)
            except PlotGeneratorInitFailed as ex:
                print(
                    f"Failed to create plot generator {generator.NAME}: "
                    f"{ex.message}"
                )

        # return command wrapped with options specified in the generator class
        return add_cli_options(command_template, *generator_cls.OPTIONS)

    main.command(generator_name)(generate_command(generator_cls))

if __name__ == '__main__':
    main()
