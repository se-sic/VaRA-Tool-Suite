"""General plots module."""
import logging
import re
import typing as tp
from pathlib import Path

from varats.plots.plot_utils import check_required_args
from varats.tools.commit_map import create_lazy_commit_map_loader
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    import varats.plots.plot  # pylint: disable=W0611

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
    def __ensure_plots_are_loaded() -> None:
        """Ensures that all plot files are loaded into the registry."""
        if not PlotRegistry.plots_discovered:
            from varats.plots import discover  # pylint: disable=C0415
            discover()
            PlotRegistry.plots_discovered = True

    @staticmethod
    def get_plot_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        PlotRegistry.__ensure_plots_are_loaded()
        return "The following plots are available:\n  " + "\n  ".join([
            key for key in PlotRegistry.plots if key != "plot"
        ])

    @staticmethod
    def get_class_for_plot_type(
        plot_type: str
    ) -> tp.Type['varats.plots.plot.Plot']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        PlotRegistry.__ensure_plots_are_loaded()

        from varats.plots.plot import Plot  # pylint: disable=W0611
        if plot_type not in PlotRegistry.plots:
            raise LookupError(
                f"Unknown plot '{plot_type}'.\n" +
                PlotRegistry.get_plot_types_help_string()
            )

        plot_cls = PlotRegistry.plots[plot_type]
        if not issubclass(plot_cls, Plot):
            raise AssertionError()
        return plot_cls


@check_required_args(['plot_type', 'file_type', 'view', 'sep_stages'])
def render_plot(**kwargs: tp.Any) -> None:
    """Build the specified graph."""
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    if kwargs['sep_stages'] and not plot_type.supports_stage_separation():
        LOG.warning(
            f"{kwargs['plot_type']} does not support stage "
            "separation but separation flag '--sep-stages' was set."
        )

    plot = plot_type(**kwargs)
    plot.style = "ggplot"

    if kwargs["view"]:
        plot.show()
    else:
        plot.save(filetype=kwargs['file_type'])


def build_plot(**args: tp.Any) -> None:
    """
    Build the specified plot.

    First, compute missing arguments that are needed by most plots.
    """
    # pylint: disable=C0415
    from varats.paper.case_study import load_case_study_from_file
    from varats.paper.paper_config import get_paper_config
    # pylint: enable=C0415

    # Setup default result folder
    if 'result_output' not in args:
        args['plot_dir'] = str(vara_cfg()['plots']['plot_dir'])
    else:
        args['plot_dir'] = args['result_output']
        del args['result_output']  # clear parameter

    if not Path(args['plot_dir']).exists():
        LOG.error(f"Could not find output dir {args['plot_dir']}")
        return

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
        paper_config = get_paper_config()
        for case_study in paper_config.get_all_case_studies():
            project_name = case_study.project_name
            args['project'] = project_name
            args['get_cmap'] = create_lazy_commit_map_loader(
                project_name, args.get('cmap', None)
            )
            args['plot_case_study'] = case_study
            render_plot(**args)
    else:
        if 'project' in args:
            args['get_cmap'] = create_lazy_commit_map_loader(
                args['project'], args.get('cmap', None)
            )
        if 'cs_path' in args:
            case_study_path = Path(args['cs_path'])
            args['plot_case_study'] = load_case_study_from_file(case_study_path)

        render_plot(**args)
