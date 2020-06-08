"""Driver module for `vara-plot`."""

import argparse
import logging
import typing as tp
from pathlib import Path

from varats.paper.case_study import load_case_study_from_file
from varats.paper.paper_config import get_paper_config
from varats.plots.plot import PlotDataEmpty
from varats.plots.plots import PlotRegistry, build_plot
from varats.settings import vara_cfg
from varats.tools.commit_map import create_lazy_commit_map_loader
from varats.utils.cli_util import initialize_cli_tool

LOG = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for the graph generator.

    `vara-plot`
    """
    initialize_cli_tool()
    parser = argparse.ArgumentParser("vara-plot")
    parser.add_argument(
        "plot_type",
        help="Plot to generate." + PlotRegistry.get_plot_types_help_string()
    )
    parser.add_argument(
        "-r", "--result-output", help="Folder with result files"
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

    # Setup default result folder
    if 'result_output' not in args:
        args['plot_dir'] = str(vara_cfg()['plots']['plot_dir'])
    else:
        args['plot_dir'] = args['result_output']
        del args['result_output']  # clear parameter

    if not Path(args['plot_dir']).exists():
        LOG.error(f"Could not find output dir {args['plot_dir']}")
        return

    LOG.info(f"Writing plots to: {args['plot_dir']}")

    if args['paper_config']:
        paper_config = get_paper_config()
        for case_study in paper_config.get_all_case_studies():
            project_name = case_study.project_name
            args['project'] = project_name
            args['get_cmap'] = create_lazy_commit_map_loader(
                project_name, args.get('cmap', None)
            )
            args['plot_case_study'] = case_study
            try:
                build_plot(**args, **extra_args)
            except PlotDataEmpty:
                LOG.error(
                    f"Could not build plot for {project_name}: "
                    f"There was no data."
                )
    else:
        if 'project' in args:
            args['get_cmap'] = create_lazy_commit_map_loader(
                args['project'], args.get('cmap', None)
            )
        if 'cs_path' in args:
            case_study_path = Path(args['cs_path'])
            args['plot_case_study'] = load_case_study_from_file(case_study_path)
        else:
            args['plot_case_study'] = None

        build_plot(**args, **extra_args)


if __name__ == '__main__':
    main()
