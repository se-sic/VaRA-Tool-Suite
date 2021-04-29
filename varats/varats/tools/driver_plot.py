"""
Driver module for `vara-plot`.

This module automatically detects plot generators and creates a separate
subcommand for each generator. For this to work, plot generators must be placed
in the module `varats.plot.plots`.
"""

import argparse
import logging
import typing as tp
from pathlib import Path

import click as click

from varats.data.discover_reports import initialize_reports
from varats.plot.plots import (
    PlotRegistry,
    build_plots,
    PlotGenerator,
    CommonPlotOptions,
    PlotConfig,
)
from varats.plots.discover_plots import initialize_plots
from varats.projects.discover_projects import initialize_projects
from varats.utils.cli_util import initialize_cli_tool, add_cli_options

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

    @click.pass_context
    def command_template(context, **kwargs):
        # extract common arguments and plot config from context
        common_options: CommonPlotOptions
        plot_config: PlotConfig
        common_options, plot_config = context.obj

        generator_instance = generator_cls(plot_config, **kwargs)
        generator_instance(common_options)

    # wrap command with options specified in the generator class
    command = add_cli_options(command_template, *generator_cls.OPTIONS)
    main.command(generator_name)(command)


#  Old code begins here --------------------------------------------------------
def old_main() -> None:
    """
    Main function for the graph generator.

    `vara-plot`
    """
    initialize_cli_tool()
    initialize_projects()
    initialize_reports()
    initialize_plots()
    parser = argparse.ArgumentParser("vara-plot")
    parser.add_argument(
        "plot_type",
        help="Plot to generate." + PlotRegistry.get_plot_types_help_string()
    )
    parser.add_argument(
        "-r", "--result-output", help="Set the output folder for plot files"
    )
    parser.add_argument("-p", "--project", help="Project name")
    parser.add_argument(
        "-c", "--cmap", help="Path to commit map", default=None, type=Path
    )
    parser.add_argument(
        "-v",
        "--view",
        help="Show the plot instead of saving it",
        action='store_true',
        default=False
    )
    parser.add_argument("--cs-path", help="Path to case_study", default=None)
    parser.add_argument(
        "--paper-config",
        help="Generate plots for all case studies in the current paper config",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--sep-stages",
        help="Separate different stages of case study in the plot.",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--report-type",
        help="The report type to generate the plot for."
        "Plots may ignore this option.",
        default="EmptyReport"
    )
    parser.add_argument(
        "extra_args",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help=(
            "Provide additional arguments that will be passed to the plot "
            "class. (do not put spaces before or after the '=' sign). "
            "If a value contains spaces, you should define it "
            'with double quotes: foo="bar baz".'
        )
    )

    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

    __plot(args)


def __plot(args: tp.Dict[str, tp.Any]) -> None:
    if 'extra_args' in args.keys():
        extra_args = {
            e[0].replace('-', '_'): e[1]
            for e in [arg.split("=") for arg in args['extra_args']]
        }
    else:
        extra_args = {}

    build_plots(**args, **extra_args)


if __name__ == '__main__':
    main()
