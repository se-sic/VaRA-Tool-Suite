"""General plots module."""
import logging
import re
import typing as tp
from pathlib import Path

from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.plot.plot_utils import check_required_args
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    import varats.plot.plot  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


class PlotRegistry(type):
    """Registry for all supported plots."""

    to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    plots: tp.Dict[str, tp.Type[tp.Any]] = {}
    plots_discovered = False

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(PlotRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = PlotRegistry.to_snake_case_pattern.sub('_', name).lower()
        PlotRegistry.plots[key] = cls

    @staticmethod
    def get_plot_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plots are available:\n  " + "\n  ".join([
            key for key in PlotRegistry.plots if key != "plot"
        ])

    @staticmethod
    def get_class_for_plot_type(
        plot_type: str
    ) -> tp.Type['varats.plot.plot.Plot']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        from varats.plot.plot import Plot  # pylint: disable=W0611
        if plot_type not in PlotRegistry.plots:
            raise LookupError(
                f"Unknown plot '{plot_type}'.\n" +
                PlotRegistry.get_plot_types_help_string()
            )

        plot_cls = PlotRegistry.plots[plot_type]
        if not issubclass(plot_cls, Plot):
            raise AssertionError()
        return plot_cls


def build_plots(**args: tp.Any) -> None:
    """
    Build the specfied plot(s).

    Args:
        **args: the arguments for the plot(s)
    """
    for plot in prepare_plots(**args):
        build_plot(plot)


def build_plot(plot: 'varats.plot.plot.Plot') -> None:
    """
    Builds the given plot.

    Args:
        plot: the plot to build
    """
    if plot.plot_kwargs["view"]:
        plot.show()
    else:
        plot.save(filetype=plot.plot_kwargs['file_type'])


@check_required_args(['plot_type', 'sep_stages'])
def prepare_plot(**kwargs: tp.Any) -> 'varats.plot.plot.Plot':
    """
    Instantiate a plot with the given args.

    Args:
        **kwargs: the arguments for the plot

    Returns:
        the instantiated plot
    """
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    if kwargs['sep_stages'] and not plot_type.supports_stage_separation():
        LOG.warning(
            f"{kwargs['plot_type']} does not support stage "
            "separation but separation flag '--sep-stages' was set."
        )

    plot = plot_type(**kwargs)
    plot.style = "ggplot"
    return plot


def prepare_plots(**args: tp.Any) -> tp.Iterable['varats.plot.plot.Plot']:
    """
    Instantiate the specified plot(s).

    First, compute missing arguments that are needed by most plots.

    Args:
        **args: the arguments for the plot(s)

    Returns:
        an iterable of instantiated plots
    """
    # pylint: disable=C0415
    from varats.paper.case_study import load_case_study_from_file
    from varats.paper_mgmt.paper_config import get_paper_config
    # pylint: enable=C0415

    # Setup default result folder
    if 'result_output' not in args:
        args['plot_dir'] = str(vara_cfg()['plots']['plot_dir'])
    else:
        args['plot_dir'] = args['result_output']
        del args['result_output']  # clear parameter

    if not Path(args['plot_dir']).exists():
        LOG.error(f"Could not find output dir {args['plot_dir']}")
        return []

    if 'file_type' not in args:
        args['file_type'] = 'png'
    if 'view' not in args:
        args['view'] = False
    if 'sep_stages' not in args:
        args['sep_stages'] = False
    if 'paper_config' not in args:
        args['paper_config'] = False

    LOG.info(f"Writing plots to: {args['plot_dir']}")

    args['plot_case_study'] = None

    if args['paper_config']:
        plots: tp.List['varats.plot.plot.Plot'] = []
        paper_config = get_paper_config()
        for case_study in paper_config.get_all_case_studies():
            project_name = case_study.project_name
            args['project'] = project_name
            args['get_cmap'] = create_lazy_commit_map_loader(
                project_name, args.get('cmap', None)
            )
            args['plot_case_study'] = case_study
            plots.append(prepare_plot(**args))
        return plots

    if 'project' in args:
        args['get_cmap'] = create_lazy_commit_map_loader(
            args['project'], args.get('cmap', None)
        )
    if 'cs_path' in args:
        case_study_path = Path(args['cs_path'])
        args['plot_case_study'] = load_case_study_from_file(case_study_path)

    return [prepare_plot(**args)]
