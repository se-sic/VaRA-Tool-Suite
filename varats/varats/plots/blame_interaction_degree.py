"""Generate plots for the degree of blame interactions."""
import abc
import logging
import tempfile
import typing as tp
from collections import defaultdict
from enum import Enum
from os.path import isdir
from pathlib import Path

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plumbum as pb
from benchbuild.utils.cmd import mkdir
from graphviz import Digraph  # type: ignore
from matplotlib import style, cm
from plotly import graph_objs as go
from plotly import io as pio

from varats.data.databases.blame_diff_library_interaction_database import (
    BlameDiffLibraryInteractionDatabase,
)
from varats.data.databases.blame_interaction_degree_database import (
    BlameInteractionDegreeDatabase,
    DegreeType,
)
from varats.data.databases.blame_library_interactions_database import (
    BlameLibraryInteractionsDatabase,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import check_required_args
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.plots.bug_annotation import draw_bugs
from varats.plots.cve_annotation import draw_cves
from varats.plots.repository_churn import draw_code_churn_for_revisions
from varats.project.project_util import get_project_cls_by_name
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option, EnumChoice
from varats.utils.git_util import ShortCommitHash, FullCommitHash

LOG = logging.getLogger(__name__)


class PlotTypes(Enum):
    GRAPHVIZ = "graphviz"
    SANKEY = "sankey"


class EdgeWeightThreshold(Enum):
    LOW = 10
    MEDIUM = 30
    HIGH = 70


class Colormap(Enum):

    # https://matplotlib.org/stable/tutorials/colors/colormaps.html
    # Sequential
    GREENS = 'Greens'
    REDS = 'Reds'
    BLUES = 'Blues'
    GREYS = 'Greys'
    ORANGES = 'Oranges'
    PURPLES = 'Purples'
    YLORBR = 'YlOrBr'
    YLORRD = 'YlOrRd'
    ORRD = 'OrRd'
    PURD = 'PuRd'
    RDPU = 'RdPu'
    BUPU = 'BuPu'
    GNBU = 'GnBu'
    PUBU = 'PuBu'
    YLGNBU = 'YlGnBu'
    PUBUGN = 'PuBuGn'
    BUGN = 'BuGn'
    YLGN = 'YlGn'

    # Miscellaneous
    GST_STRN = 'gist_stern'


OPTIONAL_SHOW_INTERACTIONS: CLIOptionTy = make_cli_option(
    "--show-interactions/--hide-interactions",
    type=bool,
    default=True,
    required=False,
    metavar="show_interactions",
    help="Enables/Disables the blame interactions."
)

OPTIONAL_SHOW_DIFF: CLIOptionTy = make_cli_option(
    "--show-diff/--hide-diff",
    type=bool,
    default=False,
    required=False,
    metavar="show_diff",
    help="Enables/Disables the blame diff interactions."
)

OPTIONAL_REVISION_LENGTH: CLIOptionTy = make_cli_option(
    "--revision-length",
    type=int,
    default=10,
    required=False,
    metavar="revision_length",
    help="Sets the number of shown revision chars."
)

OPTIONAL_SHOW_EDGE_WEIGHT: CLIOptionTy = make_cli_option(
    "--show-edge-weight/--hide-edge-weight",
    type=bool,
    default=True,
    required=False,
    metavar="edge_weight",
    help="Enables/Disables the edge weights of interactions."
)

OPTIONAL_EDGE_WEIGHT_THRESHOLD: CLIOptionTy = make_cli_option(
    "--edge-weight-threshold",
    type=EnumChoice(EdgeWeightThreshold, case_sensitive=False),
    default=None,
    required=False,
    metavar="edge_weight_threshold",
    help="Sets the threshold to show edge weights. Options are: LOW, MEDIUM, "
    "and HIGH."
)

OPTIONAL_LAYOUT_ENGINE: CLIOptionTy = make_cli_option(
    "--layout-engine",
    type=click.Choice(["dot", "fdp", "sfdp", "neato", "twopi", "circo"]),
    default="fdp",
    required=False,
    metavar="layout_engine",
    help="The layout engine."
)

OPTIONAL_SHOW_ONLY_COMMIT: CLIOptionTy = make_cli_option(
    "--show-only-commit",
    type=str,
    default=None,
    required=False,
    metavar="show_only_commit",
    help="The commit whose interactions are to be shown."
)

OPTIONAL_SHOW_CHURN: CLIOptionTy = make_cli_option(
    "--show-churn/--hide-churn",
    type=bool,
    default=True,
    required=False,
    metavar="show_churn",
    help="Shows/hides the code churn."
)

OPTIONAL_EDGE_COLOR: CLIOptionTy = make_cli_option(
    "--edge-color",
    type=str,
    default="black",
    required=False,
    metavar="edge_color",
    help="The color of an edge."
)

OPTIONAL_COLORMAP: CLIOptionTy = make_cli_option(
    "--colormap",
    type=EnumChoice(Colormap),
    default=Colormap.GST_STRN,
    required=False,
    metavar="colormap",
    help="The colormap used in the plot."
)

OPTIONAL_SHOW_CVE: CLIOptionTy = make_cli_option(
    "--show-cve/--hide-cve",
    type=bool,
    default=False,
    required=False,
    metavar="show_cve",
    help="Shows/hides CVE annotations."
)

OPTIONAL_SHOW_BUGS: CLIOptionTy = make_cli_option(
    "--show-bugs/--hide-bugs",
    type=bool,
    default=False,
    required=False,
    metavar="show_bugs",
    help="Shows/hides bug annotations."
)

OPTIONAL_CVE_BUG_LINE_WIDTH: CLIOptionTy = make_cli_option(
    "--cve-bug-line-width",
    type=int,
    default=1,
    required=False,
    metavar="cve_bug_line_width",
    help="The line width of CVE/bug annotations."
)

OPTIONAL_CVE_BUG_COLOR: CLIOptionTy = make_cli_option(
    "--cve-bug-color",
    type=str,
    default="green",
    required=False,
    metavar="cve_bug_color",
    help="The color of CVE/bug annotations."
)

OPTIONAL_VERTICAL_ALIGNMENT: CLIOptionTy = make_cli_option(
    "--vertical-alignment",
    type=click.Choice(['center', 'top', 'bottom', 'baseline']),
    default="bottom",
    required=False,
    metavar="vertical_alignment",
    help="The vertical alignment of CVE/bug annotations."
)


class FractionMap:
    """Mapping of library names to fractions."""

    def __init__(self) -> None:
        self.__mapping: tp.DefaultDict[str, tp.List[float]] = defaultdict(list)

    @property
    def as_default_dict(self) -> tp.DefaultDict[str, tp.List[float]]:
        return self.__mapping

    def get_lib_num(self) -> int:
        return len(self.__mapping.keys())

    def get_lib_names(self) -> tp.List[str]:
        """Returns all library names."""

        lib_names: tp.List[str] = []
        for lib_name in self.__mapping:
            lib_names.append(lib_name)

        return lib_names

    def get_all_fraction_lists(self) -> tp.List[tp.List[float]]:
        """Returns a list containing all library fraction lists."""

        all_fraction_lists: tp.List[tp.List[float]] = []
        for fraction_list in self.__mapping.values():
            all_fraction_lists.append(fraction_list)

        return all_fraction_lists

    def get_fractions_from_lib(self, lib_name: str) -> tp.List[float]:
        return self.__mapping[lib_name]

    def add_fraction_to_lib(self, lib_name: str, fraction: float) -> None:
        self.__mapping[lib_name].append(fraction)


BaseInterFractionMapTuple = tp.Tuple[FractionMap, FractionMap]
IndexShadesMapping = tp.Dict[int, str]
LibraryColormapMapping = tp.Dict[str, tp.Any]
LibraryToIndexShadesMapping = tp.Dict[str, IndexShadesMapping]


def _get_unique_revisions(dataframe: pd.DataFrame,
                          c_map: CommitMap) -> tp.List[FullCommitHash]:
    return [
        c_map.convert_to_full_or_warn(rev)
        for rev in dataframe.revision.unique()
    ]


def _filter_data_frame(
    degree_type: DegreeType, interaction_plot_df: pd.DataFrame,
    commit_map: CommitMap
) -> tp.Tuple[tp.List[FullCommitHash], tp.List[pd.Series]]:
    """Reduce data frame to rows that match the degree type."""
    interaction_plot_df = interaction_plot_df[interaction_plot_df.degree_type ==
                                              degree_type.value]

    degree_levels = sorted(np.unique(interaction_plot_df.degree))
    interaction_plot_df = interaction_plot_df.set_index(['revision', 'degree'])

    def aggregate_data(df: pd.DataFrame) -> pd.DataFrame:
        aggregated_df = df.groupby(['revision', 'degree']).agg({
            'amount': 'sum',
            'fraction': 'sum'
        })
        return aggregated_df

    if degree_type == DegreeType.INTERACTION:
        interaction_plot_df = aggregate_data(interaction_plot_df)

    interaction_plot_df = interaction_plot_df.reindex(
        pd.MultiIndex.from_product(
            interaction_plot_df.index.levels,
            names=interaction_plot_df.index.names
        ),
        fill_value=0
    ).reset_index()

    # fix missing time_ids introduced by the product index
    interaction_plot_df['time_id'] = interaction_plot_df['revision'].apply(
        commit_map.short_time_id
    )
    interaction_plot_df.sort_values(by=['time_id'], inplace=True)

    sub_df_list = [
        interaction_plot_df.loc[interaction_plot_df.degree == x].fraction
        for x in degree_levels
    ]

    unique_revisions = _get_unique_revisions(interaction_plot_df, commit_map)

    return unique_revisions, sub_df_list


def _get_distinct_base_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return list(np.unique([str(base_lib) for base_lib in df.base_lib]))


def _get_distinct_inter_lib_names(df: pd.DataFrame) -> tp.List[str]:
    return list(np.unique([str(inter_lib) for inter_lib in df.inter_lib]))


def _generate_stackplot(
    df: pd.DataFrame, unique_revisions: tp.List[FullCommitHash],
    sub_df_list: tp.List[pd.Series], plot_kwargs: tp.Any
) -> None:
    fig = plt.figure()
    grid_spec = fig.add_gridspec(3, 1)

    if plot_kwargs["show_churn"]:
        main_axis = fig.add_subplot(grid_spec[:-1, :])
        main_axis.get_xaxis().set_visible(False)
        churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)
        x_axis = churn_axis
    else:
        main_axis = fig.add_subplot(grid_spec[:, :])
        x_axis = main_axis

    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
    fig.suptitle(plot_kwargs["fig_suptitle"], fontsize=8)

    unique_rev_strings: tp.List[str] = [
        rev.short_hash for rev in unique_revisions
    ]
    main_axis.stackplot(
        unique_rev_strings,
        sub_df_list,
        edgecolor=plot_kwargs['edge_color'],
        colors=reversed(
            cm.get_cmap(plot_kwargs['colormap'].value
                       )(np.linspace(0, 1, len(sub_df_list)))
        ),
        # TODO (se-passau/VaRA#545): remove cast with plot config rework
        labels=map(
            tp.cast(tp.Callable[[str], str], lambda x: x),
            sorted(np.unique(df['degree']))
        ),
        linewidth=plot_kwargs['line_width']
    )
    legend = main_axis.legend(
        title=plot_kwargs['legend_title'],
        loc='upper left',
        prop={
            'size': plot_kwargs['legend_size'],
            'family': 'monospace'
        }
    )
    plt.setp(
        legend.get_title(),
        fontsize=plot_kwargs['legend_size'],
        family='monospace'
    )
    legend.set_visible(plot_kwargs['show_legend'])
    # annotate CVEs
    with_cve = plot_kwargs["show_cve"]
    with_bugs = plot_kwargs["show_bugs"]
    cs = plot_kwargs["case_study"]
    project_name = cs.project_name
    commit_map = get_commit_map(project_name)
    if with_cve or with_bugs:
        project = get_project_cls_by_name(project_name)
        if with_cve:
            draw_cves(main_axis, project, unique_revisions, plot_kwargs)
        if with_bugs:
            draw_bugs(main_axis, project, unique_revisions, plot_kwargs)
    # draw churn subplot
    if plot_kwargs["show_churn"]:
        draw_code_churn_for_revisions(
            churn_axis, project_name, commit_map, unique_revisions
        )
    plt.setp(x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
    plt.setp(
        x_axis.get_xticklabels(),
        fontsize=plot_kwargs['x_tick_size'],
        fontfamily='monospace',
        rotation=270
    )


def _calc_fractions(
    unique_revisions: tp.List[FullCommitHash], all_base_lib_names: tp.List[str],
    all_inter_lib_names: tp.List[str],
    revision_to_base_names_mapping: tp.Dict[FullCommitHash, tp.List[str]],
    revision_to_inter_names_mapping: tp.Dict[FullCommitHash, tp.List[str]],
    revision_to_dataframes_mapping: tp.Dict[FullCommitHash, pd.DataFrame],
    revision_to_total_amount_mapping: tp.Dict[FullCommitHash, int]
) -> BaseInterFractionMapTuple:
    """Calculate the fractions of the base and interacting libraries for the
    fraction overview plot."""

    base_fraction_map = FractionMap()
    inter_fraction_map = FractionMap()

    for rev in unique_revisions:
        for base_name in revision_to_base_names_mapping[rev]:
            current_fraction = np.divide(
                revision_to_dataframes_mapping[rev].loc[
                    revision_to_dataframes_mapping[rev].base_lib == base_name
                ].amount.sum(), revision_to_total_amount_mapping[rev]
            )
            base_fraction_map.add_fraction_to_lib(base_name, current_fraction)

        # Add fraction value 0 to all libraries that are not yet present in a
        # revision
        absent_base_lib_names = set(all_base_lib_names) - set(
            revision_to_base_names_mapping[rev]
        )

        for base_name in absent_base_lib_names:
            base_fraction_map.add_fraction_to_lib(base_name, 0)

        for inter_name in revision_to_inter_names_mapping[rev]:
            current_fraction = np.divide(
                revision_to_dataframes_mapping[rev].loc[
                    revision_to_dataframes_mapping[rev].inter_lib == inter_name
                ].amount.sum(), revision_to_total_amount_mapping[rev]
            )
            inter_fraction_map.add_fraction_to_lib(inter_name, current_fraction)

        absent_inter_lib_names = set(all_inter_lib_names) - set(
            revision_to_inter_names_mapping[rev]
        )
        for inter_name in absent_inter_lib_names:
            inter_fraction_map.add_fraction_to_lib(inter_name, 0)

    return base_fraction_map, inter_fraction_map


def _gen_fraction_overview_legend(
    legends_axis: tp.Any, handles: tp.Any, legend_title_suffix: str,
    legend_items: tp.List[str], plot_cfg: tp.Dict[str, tp.Any]
) -> None:
    legend = legends_axis.legend(
        handles=handles,
        title=f'{plot_cfg["legend_title"]} | {legend_title_suffix}',
        # TODO (se-passau/VaRA#545): remove cast with plot config
        #  rework
        labels=map(tp.cast(tp.Callable[[str], str], lambda x: x), legend_items),
        loc='upper left',
        prop={
            'size': plot_cfg['legend_size'],
            'family': 'monospace'
        }
    )
    plt.setp(
        legend.get_title(),
        fontsize=plot_cfg['legend_size'],
        family='monospace',
    )
    legends_axis.add_artist(legend)
    legend.set_visible(plot_cfg['legend_visible'])


def _plot_fraction_overview(
    base_lib_fraction_map: FractionMap, inter_lib_fraction_map: FractionMap,
    with_churn: bool, unique_revisions: tp.List[FullCommitHash],
    plot_cfg: tp.Dict[str, tp.Any], plot_kwargs: tp.Dict[str, tp.Any]
) -> None:
    fig = plt.figure()
    grid_spec = fig.add_gridspec(3, 1)
    out_axis = fig.add_subplot(grid_spec[0, :])
    out_axis.get_xaxis().set_visible(False)
    in_axis = fig.add_subplot(grid_spec[1, :])

    if with_churn:
        in_axis.get_xaxis().set_visible(False)
        churn_axis = fig.add_subplot(grid_spec[-1, :], sharex=out_axis)
        x_axis = churn_axis
    else:
        x_axis = in_axis

    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
    fig.suptitle(
        str(plot_cfg['fig_title']) + f' - Project {plot_kwargs["project"]}',
        fontsize=8
    )

    colormap = plot_cfg['color_map'](
        np.linspace(
            0, 1,
            max(
                base_lib_fraction_map.get_lib_num(),
                inter_lib_fraction_map.get_lib_num()
            )
        )
    )

    outgoing_plot_lines = []
    ingoing_plot_lines = []

    outgoing_plot_lines += out_axis.stackplot(
        unique_revisions,
        base_lib_fraction_map.get_all_fraction_lists(),
        linewidth=plot_cfg['linewidth'],
        colors=colormap,
        edgecolor=plot_cfg['edgecolor'],
        alpha=0.7
    )

    # Setup outgoing interactions legend
    _gen_fraction_overview_legend(
        out_axis, outgoing_plot_lines, "Outgoing interactions",
        base_lib_fraction_map.get_lib_names(), plot_cfg
    )

    ingoing_plot_lines += in_axis.stackplot(
        unique_revisions,
        inter_lib_fraction_map.get_all_fraction_lists(),
        linewidth=plot_cfg['linewidth'],
        colors=colormap,
        edgecolor=plot_cfg['edgecolor'],
        alpha=0.7
    )

    # Setup ingoing interactions legend
    _gen_fraction_overview_legend(
        in_axis, ingoing_plot_lines, "Ingoing interactions",
        inter_lib_fraction_map.get_lib_names(), plot_cfg
    )

    # annotate CVEs
    with_cve = plot_kwargs.get("with_cve", False)
    with_bugs = plot_kwargs.get("with_bugs", False)
    if with_cve or with_bugs:
        if "project" not in plot_kwargs:
            LOG.error("Need a project to annotate bug or CVE data.")
        else:
            project = get_project_cls_by_name(plot_kwargs["project"])
            if with_cve:
                draw_cves(in_axis, project, unique_revisions, plot_cfg)
            if with_bugs:
                draw_bugs(in_axis, project, unique_revisions, plot_cfg)

    # draw churn subplot
    if with_churn:
        draw_code_churn_for_revisions(
            churn_axis, plot_kwargs['project'], plot_kwargs['get_cmap'](),
            unique_revisions
        )

    # Format labels of axes
    plt.setp(
        x_axis.get_xticklabels(),
        fontsize=plot_cfg['xtick_size'],
        fontfamily='monospace',
        rotation=270
    )

    axes = [out_axis, in_axis]
    if with_churn:
        axes.append(churn_axis)

    for axis in axes:
        plt.setp(axis.get_yticklabels(), fontsize=8, fontfamily='monospace')


def _get_separated_lib_names_dict(
    dataframe: pd.DataFrame
) -> tp.Dict[str, tp.List[str]]:
    """Creates a dict that contains library information about distinct base and
    interacting library names, the names of all libraries and the distinct names
    of all libraries."""

    name_dict: tp.Dict[str, tp.List[str]] = {
        "base_lib_names": _get_distinct_base_lib_names(dataframe),
        "inter_lib_names": _get_distinct_inter_lib_names(dataframe)
    }

    # Duplicated lib names are necessary to avoid cycles in the plot
    name_dict["all_lib_names"
             ] = name_dict["base_lib_names"] + name_dict["inter_lib_names"]

    name_dict["all_distinct_lib_names"] = sorted(
        set(name_dict["all_lib_names"])
    )
    return name_dict


def _build_sankey_color_mappings(
    highest_degree: int, plot_cfg: tp.Dict[str, tp.Any],
    lib_name_dict: tp.Dict[str, tp.List[str]]
) -> tp.Tuple[LibraryColormapMapping, LibraryToIndexShadesMapping]:
    """Returns a tuple of a LibraryColormapMapping and a
    LibraryToIndexShadesMapping."""

    lib_to_colormap: LibraryColormapMapping = {}
    lib_to_idx_shades: LibraryToIndexShadesMapping = dict(
        (name, {}) for name in lib_name_dict["all_distinct_lib_names"]
    )

    colormaps: tp.List[Colormap] = [c for c in Colormap]
    num_colormaps: int = len(tp.cast(tp.List[str], colormaps))

    if len(lib_name_dict["all_distinct_lib_names"]) > num_colormaps:
        LOG.warning(
            "Not enough colormaps for all libraries provided. "
            "Colormaps will be reused."
        )

    for lib_idx, lib_name in enumerate(lib_to_idx_shades):
        # If there are not enough colormaps provided, reuse them.
        if num_colormaps <= lib_idx:
            lib_idx = 0

        shade_lists = cm.get_cmap(colormaps[lib_idx].value
                                 )(np.linspace(0.25, 1, highest_degree + 1))

        lib_to_colormap[lib_name] = cm.get_cmap(colormaps[lib_idx].value)
        tmp_idx_to_shades_mapping: tp.Dict[int, str] = {}

        for shade_idx, shades in enumerate(shade_lists):
            tmp_idx_to_shades_mapping[shade_idx] = str(tuple(shades))

        lib_to_idx_shades[lib_name] = tmp_idx_to_shades_mapping

    return lib_to_colormap, lib_to_idx_shades


def _save_figure(
    figure: tp.Any, revision: FullCommitHash, project_name: str,
    plot_type: PlotTypes, plot_file_name: str, plot_dir: Path, file_type: str
) -> None:

    revision_idx = -1
    max_idx = -1
    c_map: CommitMap = get_commit_map(project_name)

    for c_hash, idx in c_map.mapping_items():
        if idx > max_idx:
            max_idx = idx
        if c_hash == revision.hash:
            revision_idx = idx

    if revision_idx == -1:
        LOG.error(
            f"The revision {revision} could not be found in the "
            f"commit map."
        )
        raise PlotDataEmpty

    max_idx_digit_num = len(str(max_idx))
    padded_idx_str = str(revision_idx).rjust(max_idx_digit_num, str(0))
    file_name = plot_file_name.rsplit('.', 1)[0]
    plot_subdir = Path(file_name)

    with pb.local.cwd(plot_dir):
        if not isdir(plot_subdir):
            mkdir(plot_subdir)

    if plot_type == PlotTypes.SANKEY:
        file_name = f"{file_name}_{padded_idx_str}.{file_type}"

        pio.write_image(
            fig=figure,
            file=str(plot_dir / plot_subdir / file_name),
            format=file_type
        )

    if plot_type == PlotTypes.GRAPHVIZ:
        file_name = f"{file_name}_{padded_idx_str}"

        figure.render(
            filename=file_name,
            directory=str(plot_dir / plot_subdir),
            format=file_type,
            cleanup=True
        )


def _collect_sankey_plotting_data(
    dataframe: pd.DataFrame, lib_name_dict: tp.Dict[str, tp.List[str]],
    lib_name_to_colormap_mapping: tp.Dict[str, tp.Any],
    lib_name_to_color_shades_mapping: tp.Dict[str, tp.Dict[int, str]]
) -> tp.Dict[str, tp.List[tp.Any]]:
    sankey_data_dict: tp.Dict[str, tp.List[tp.Any]] = {
        "sources": [],
        "targets": [],
        "fractions": [],
        "node_colors": [],
        "edge_colors": [],
        "degrees": [],
    }

    dataframe = dataframe.sort_values(["degree"])

    base_lib_name_index_mapping, inter_lib_name_index_mapping = \
        _gen_sankey_lib_name_to_idx_mapping(lib_name_dict)

    for name in lib_name_dict["all_lib_names"]:
        sankey_data_dict["node_colors"].append(
            f"rgba{tuple(lib_name_to_colormap_mapping[name](0.5))}"
        )

    for _, row in dataframe.iterrows():
        color = "rgba" + lib_name_to_color_shades_mapping[row["base_lib"]][
            row["degree"]]

        sankey_data_dict["sources"].append(
            base_lib_name_index_mapping[row["base_lib"]]
        )
        sankey_data_dict["targets"].append(
            inter_lib_name_index_mapping[row["inter_lib"]]
        )
        sankey_data_dict["fractions"].append(row["fraction"] * 100)
        sankey_data_dict["degrees"].append(row["degree"])
        sankey_data_dict["edge_colors"].append(color)

    return sankey_data_dict


def _gen_sankey_lib_name_to_idx_mapping(
    lib_name_dict: tp.Dict[str, tp.List[str]]
) -> tp.Tuple[tp.Dict[str, int], tp.Dict[str, int]]:
    base_lib_mapping: tp.Dict[str, int] = {}
    inter_lib_mapping: tp.Dict[str, int] = {}

    for idx, name in enumerate(lib_name_dict["base_lib_names"]):
        base_lib_mapping[name] = idx

    idx_offset = len(base_lib_mapping)

    for idx, name in enumerate(lib_name_dict["inter_lib_names"]):
        # Continue the index for the interacting libraries
        inter_lib_mapping[name] = idx + idx_offset

    return base_lib_mapping, inter_lib_mapping


def _build_sankey_figure(
    revision: FullCommitHash, view_mode: bool,
    data_dict: tp.Dict[str, tp.List[tp.Any]],
    library_names_dict: tp.Dict[str, tp.List[str]], plot_cfg: tp.Dict[str,
                                                                      tp.Any]
) -> go.Figure:
    layout = go.Layout(
        autosize=False, width=plot_cfg['width'], height=plot_cfg['height']
    )
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="perpendicular",
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=library_names_dict["all_lib_names"],
                    color=data_dict["node_colors"],
                    hovertemplate='Fraction ratio = %{'
                    'value}%<extra></extra> '
                ),
                link=dict(
                    source=data_dict["sources"],
                    target=data_dict["targets"],
                    value=data_dict["fractions"],
                    color=data_dict["edge_colors"],
                    customdata=data_dict["degrees"],
                    hovertemplate='Interaction has a fraction ratio '
                    'of %{value}%<br /> and a degree of '
                    '%{customdata}<extra></extra>',
                )
            )
        ]
    )
    if not view_mode:
        fig.layout = layout

    fig.update_layout(
        title_text=
        f"<b>Revision: {revision}</b><br />Library interactions from base(left)"
        f" to interacting(right) libraries. Color saturation increases with the"
        f" degree level.</b><br />{plot_cfg['fig_title']}",
        font_size=plot_cfg['font_size']
    )

    return fig


def _add_diff_amount_col_to_df(
    inter_df: pd.DataFrame, diff_df: pd.DataFrame
) -> pd.DataFrame:
    """Adds the ``amount`` of rows from ``diff_df`` to the same rows of
    ``inter_df`` in a new column named ``diff_amount``."""

    merged_df = pd.merge(
        inter_df,
        diff_df,
        on=[
            "revision", "time_id", "base_hash", "base_lib", "inter_hash",
            "inter_lib"
        ],
        how='left',
        indicator="diff_amount"
    )

    # Adds the amount from diff_df to rows that exist in both dataframes
    merged_df['diff_amount'] = np.where(
        merged_df.diff_amount == 'both', merged_df.amount_y, 0
    )

    merged_df.rename(columns={"amount_x": "amount"}, inplace=True)
    del merged_df["amount_y"]

    return merged_df


LibraryToHashesMapping = tp.Dict[str, tp.List[str]]


def _build_graphviz_edges(
    df: pd.DataFrame,
    graph: Digraph,
    show_edge_weight: bool,
    commit_map: CommitMap,
    edge_weight_threshold: tp.Optional[EdgeWeightThreshold] = None,
    show_only_interactions_of_commit: tp.Optional[str] = None
) -> LibraryToHashesMapping:

    if show_only_interactions_of_commit is not None:
        show_only_interactions_of_commit = commit_map.convert_to_full_or_warn(
            ShortCommitHash(show_only_interactions_of_commit)
        ).hash

    base_lib_names = _get_distinct_base_lib_names(df)
    inter_lib_names = _get_distinct_inter_lib_names(df)
    all_distinct_lib_names = sorted(set(base_lib_names + inter_lib_names))

    lib_to_hashes_mapping: tp.Dict[str, tp.List[str]] = {
        lib_name: [] for lib_name in all_distinct_lib_names
    }

    for _, row in df.iterrows():
        base_hash = row['base_hash']
        base_lib = row['base_lib']
        inter_hash = row['inter_hash']
        inter_lib = row['inter_lib']

        base_inter_hash_tuple = (base_hash, inter_hash)

        # Skip edges that do not connect with the specified
        # ``show_only_interactions_of_commit`` node.
        if show_only_interactions_of_commit is not None and (
            show_only_interactions_of_commit not in base_inter_hash_tuple
        ):
            continue

        label = ""
        color = "black"
        weight = row['amount']

        if 'diff_amount' in row:
            diff_weight = int(row['diff_amount'])
        else:
            diff_weight = 0

        if not edge_weight_threshold or weight >= edge_weight_threshold.value:
            if show_edge_weight:
                label = str(weight)

            if diff_weight > 0:
                color = "orange"
                plus_minus = '\u00b1'
                label = f"{label} ({plus_minus}{str(diff_weight)})"

            graph.edge(
                f'{base_hash}_{base_lib}',
                f'{inter_hash}_{inter_lib}',
                label=label,
                color=color
            )

        lib_to_hashes_mapping[base_lib].append(base_hash)
        lib_to_hashes_mapping[inter_lib].append(inter_hash)

    return lib_to_hashes_mapping


def _build_graphviz_fig(
    df: pd.DataFrame, revision: FullCommitHash, show_edge_weight: bool,
    shown_revision_length: int, commit_map: CommitMap,
    edge_weight_threshold: tp.Optional[EdgeWeightThreshold], layout_engine: str,
    show_only_interactions_of_commit: tp.Optional[str]
) -> Digraph:
    graph = Digraph(name="Digraph", strict=True, engine=layout_engine)
    graph.attr(label=f"Revision: {revision}")
    graph.attr(labelloc="t")

    if layout_engine == "fdp":
        graph.attr(splines="True")
        graph.attr(overlap="False")
        graph.attr(nodesep="1")

    lib_to_hashes_mapping = _build_graphviz_edges(
        df, graph, show_edge_weight, commit_map, edge_weight_threshold,
        show_only_interactions_of_commit
    )

    for lib_name, c_hash_list in lib_to_hashes_mapping.items():

        # 'cluster_' prefix is necessary for grouping commits to libraries
        with graph.subgraph(name="cluster_" + lib_name) as subgraph:
            subgraph.attr(label=lib_name)
            subgraph.attr(color="red")

            for c_hash in c_hash_list:

                if shown_revision_length > len(c_hash):
                    shown_revision_length = len(c_hash)

                if shown_revision_length < 1:
                    LOG.error(
                        f"The passed revision length of "
                        f"{shown_revision_length} must be at least 1."
                    )
                    raise PlotDataEmpty

                subgraph.node(
                    name=f'{c_hash}_{lib_name}',
                    label=c_hash[0:shown_revision_length]
                )
    return graph


class BlameLibraryInteraction(Plot, plot_name=None):
    """Base plot for blame library interaction plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    @staticmethod
    def _get_interaction_data(
        case_study: CaseStudy,
        commit_map: CommitMap,
        blame_diff: bool = False
    ) -> pd.DataFrame:

        project_name = case_study.project_name
        variables = [
            "time_id", "base_hash", "base_lib", "inter_hash", "inter_lib",
            "amount"
        ]

        if blame_diff:
            lib_interaction_df = \
                BlameDiffLibraryInteractionDatabase.get_data_for_project(
                    project_name, ["revision", *variables], commit_map,
                    case_study)
        else:
            lib_interaction_df = \
                BlameLibraryInteractionsDatabase.get_data_for_project(
                    project_name, ["revision", *variables], commit_map,
                    case_study)

        length = len(_get_unique_revisions(lib_interaction_df, commit_map))
        is_empty = lib_interaction_df.empty

        if not blame_diff and (is_empty or length == 1):
            # Need more than one data point
            raise PlotDataEmpty
        return lib_interaction_df

    def _graphviz_plot(self) -> tp.Optional[Digraph]:

        def _get_graphviz_project_data(
            blame_interactions: bool, blame_diff: bool
        ) -> pd.DataFrame:
            if not blame_interactions and not blame_diff:
                LOG.warning(
                    "You have to set either 'show_blame_interactions', "
                    "'show_blame_diff', or both to 'True'. Aborting."
                )
                raise PlotDataEmpty

            if blame_interactions:
                inter_df = self._get_interaction_data(cs, commit_map, False)
            else:
                inter_df = self._get_interaction_data(cs, commit_map, True)

            if blame_diff:
                diff_df = self._get_interaction_data(cs, commit_map, True)
                return _add_diff_amount_col_to_df(inter_df, diff_df)

            return inter_df

        cs: CaseStudy = self.plot_kwargs["case_study"]
        commit_map: CommitMap = get_commit_map(cs.project_name)

        df = _get_graphviz_project_data(
            self.plot_kwargs["show_interactions"],
            self.plot_kwargs["show_diff"],
        )

        df.sort_values(by=['time_id'], inplace=True)
        df.reset_index(inplace=True)
        rev = self.plot_kwargs['revision']

        dataframe = df.loc[df["revision"].apply(
            lambda x: commit_map.convert_to_full_or_warn(x)
        ) == rev]

        fig = _build_graphviz_fig(
            dataframe, rev, self.plot_kwargs["show_edge_weight"],
            self.plot_kwargs["revision_length"], commit_map,
            self.plot_kwargs["edge_weight_threshold"],
            self.plot_kwargs["layout_engine"],
            self.plot_kwargs["show_only_commit"]
        )
        return fig


class BlameDegree(Plot, plot_name=None):
    """Base plot for blame degree plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def _get_degree_data(self) -> pd.DataFrame:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name = case_study.project_name
        commit_map = get_commit_map(project_name)

        interaction_plot_df = \
            BlameInteractionDegreeDatabase.get_data_for_project(
                project_name, [
                    "revision", "time_id", "degree_type", "base_lib",
                    "inter_lib", "degree", "amount", "fraction"
                ], commit_map, case_study)

        length = len(_get_unique_revisions(interaction_plot_df, commit_map))
        is_empty = interaction_plot_df.empty

        if is_empty or length == 1:
            # Need more than one data point
            raise PlotDataEmpty
        return interaction_plot_df

    def _degree_plot(self, degree_type: DegreeType) -> None:

        project_name = self.plot_kwargs['case_study'].project_name
        fig_suptitle = f'{str(self.plot_kwargs["fig_title"])} - ' \
                       f'Project {project_name}'
        self.plot_kwargs["fig_suptitle"] = fig_suptitle

        style.use(self.style)
        commit_map: CommitMap = get_commit_map(project_name)
        interaction_plot_df = self._get_degree_data()

        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map
        )

        _generate_stackplot(
            interaction_plot_df, unique_revisions, sub_df_list, self.plot_kwargs
        )

    def _multi_lib_degree_plot(
        self,
        view_mode: bool,
        degree_type: DegreeType,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
        with_churn: bool = True
    ) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'legend_visible': True,
            'fig_title': 'MISSING figure title',
            'edgecolor': 'black',
            'color_map': cm.get_cmap('gist_stern'),
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        fig_suptitle = f'{str(plot_cfg["fig_title"])} - ' \
                       f'Project {self.plot_kwargs["project"]} | ' \
                       f'{plot_cfg["base_lib"]} --> {plot_cfg["inter_lib"]} '
        plot_cfg["fig_suptitle"] = fig_suptitle

        style.use(self.style)
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        interaction_plot_df = self._get_degree_data()

        interaction_plot_df = interaction_plot_df[(
            interaction_plot_df[['base_lib', 'inter_lib']] == [
                plot_cfg['base_lib'], plot_cfg['inter_lib']
            ]
        ).all(1)]

        def is_lib_combination_existent() -> bool:
            length = len(_get_unique_revisions(interaction_plot_df, commit_map))
            is_empty = interaction_plot_df.empty

            if is_empty or length == 1:
                return False

            return True

        if not is_lib_combination_existent():
            LOG.warning(
                f"There is no interaction from {plot_cfg['base_lib']} to "
                f"{plot_cfg['inter_lib']} or not enough data points."
            )
            raise PlotDataEmpty

        summed_df = interaction_plot_df.groupby(['revision']).sum()

        # Recalculate fractions based on the selected libraries
        for idx, row in interaction_plot_df.iterrows():
            total_amount = summed_df['amount'].loc[row['revision']]
            interaction_plot_df.at[idx,
                                   'fraction'] = row['amount'] / total_amount

        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map
        )

        _generate_stackplot(
            interaction_plot_df, unique_revisions, sub_df_list, with_churn,
            plot_cfg, self.plot_kwargs
        )

    def _fraction_overview_plot(
        self,
        view_mode: bool,
        degree_type: DegreeType,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
        with_churn: bool = True
    ) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'legend_visible': True,
            'fig_title': 'MISSING figure title',
            'edgecolor': 'black',
            'color_map': cm.get_cmap('tab10')
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)

        df = self._get_degree_data()
        df = df[df.degree_type == degree_type.value]
        df.sort_values(by=['time_id'], inplace=True)
        df.reset_index(inplace=True)
        all_base_lib_names = _get_distinct_base_lib_names(df)
        all_inter_lib_names = _get_distinct_inter_lib_names(df)
        revision_df = pd.DataFrame(df["revision"])
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        unique_revisions = _get_unique_revisions(revision_df, commit_map)
        grouped_df: pd.DataFrame = df.groupby(['revision'])
        revision_to_dataframes_mapping: tp.Dict[FullCommitHash,
                                                pd.DataFrame] = {}

        for revision in unique_revisions:
            revision_to_dataframes_mapping[revision] = grouped_df.get_group(
                revision.hash
            )

        revision_to_total_amount_mapping: tp.Dict[FullCommitHash, int] = {}
        revision_to_base_names_mapping: tp.Dict[FullCommitHash,
                                                tp.List[str]] = {}
        revision_to_inter_names_mapping: tp.Dict[FullCommitHash,
                                                 tp.List[str]] = {}

        # Collect mapping data
        for revision in unique_revisions:
            revision_to_total_amount_mapping[
                revision] = revision_to_dataframes_mapping[revision].sum(
                ).amount
            revision_to_base_names_mapping[
                revision] = _get_distinct_base_lib_names(
                    revision_to_dataframes_mapping[revision]
                )
            revision_to_inter_names_mapping[
                revision] = _get_distinct_inter_lib_names(
                    revision_to_dataframes_mapping[revision]
                )

        base_lib_fraction_map, inter_lib_fraction_map = _calc_fractions(
            unique_revisions, all_base_lib_names, all_inter_lib_names,
            revision_to_base_names_mapping, revision_to_inter_names_mapping,
            revision_to_dataframes_mapping, revision_to_total_amount_mapping
        )

        _plot_fraction_overview(
            base_lib_fraction_map, inter_lib_fraction_map, with_churn,
            unique_revisions, plot_cfg, self.plot_kwargs
        )

    def _multi_lib_interaction_sankey_plot(self, view_mode: bool) -> go.Figure:
        interaction_plot_df = self._get_degree_data()
        interaction_plot_df = interaction_plot_df[
            interaction_plot_df.degree_type == DegreeType.INTERACTION.value]

        interaction_plot_df.sort_values(by=['time_id'], inplace=True)
        interaction_plot_df.reset_index(inplace=True)
        highest_degree = interaction_plot_df["degree"].max()
        commit_map: CommitMap = get_commit_map(
            self.plot_kwargs["case_study"].project_name
        )
        rev = commit_map.convert_to_full_or_warn(self.plot_kwargs['revision'])

        df = interaction_plot_df.loc[interaction_plot_df["revision"].apply(
            lambda x: commit_map.convert_to_full_or_warn(x)
        ) == rev]

        lib_names_dict = _get_separated_lib_names_dict(df)
        lib_cm_mapping, lib_shades_mapping = _build_sankey_color_mappings(
            highest_degree, self.plot_kwargs, lib_names_dict
        )

        plotting_data_dict = _collect_sankey_plotting_data(
            df, lib_names_dict, lib_cm_mapping, lib_shades_mapping
        )
        sankey_figure = _build_sankey_figure(
            rev, view_mode, plotting_data_dict, lib_names_dict, self.plot_kwargs
        )

        return sankey_figure

    def _calc_missing_revisions(
        self, degree_type: DegreeType, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        """
        Select a set of revisions based on the gradients of the degree levels
        between revisions.

        Args:
            degree_type: the degree type to consider for gradient calculation
            boundary_gradient: the gradient threshold that needs to be exceeded
                               to include a new revision

        Returns:
            a set of revisions sampled between revisions with unusually large
            changes in degree distribution
        """
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        interaction_plot_df = self._get_degree_data()
        unique_revisions, sub_df_list = _filter_data_frame(
            degree_type, interaction_plot_df, commit_map
        )

        def head_cm_neighbours(
            lhs_cm: ShortCommitHash, rhs_cm: ShortCommitHash
        ) -> bool:
            return commit_map.short_time_id(
                lhs_cm
            ) + 1 == commit_map.short_time_id(rhs_cm)

        new_revs: tp.Set[FullCommitHash] = set()

        # build a dataframe with revision as index and degree values as columns
        # the cells contain the degree frequencies per revision
        df = pd.concat([
            series.reset_index(drop=True) for series in sub_df_list
        ],
                       axis=1)
        df["revision"] = unique_revisions
        df = df.set_index("revision")
        df_iter = df.iterrows()
        last_revision, last_row = next(df_iter)
        for revision, row in df_iter:
            # compute gradient for each degree value and see if any gradient
            # exceeds threshold
            gradient = abs(row - last_row)
            if any(gradient > boundary_gradient):
                lhs_cm = last_revision
                rhs_cm = revision
                if head_cm_neighbours(lhs_cm, rhs_cm):
                    print(
                        "Found steep gradient between neighbours " +
                        "{lhs_cm} - {rhs_cm}: {gradient}".format(
                            lhs_cm=lhs_cm,
                            rhs_cm=rhs_cm,
                            gradient=round(max(gradient), 5)
                        )
                    )
                else:
                    print(
                        "Unusual gradient between " +
                        "{lhs_cm} - {rhs_cm}: {gradient}".format(
                            lhs_cm=lhs_cm,
                            rhs_cm=rhs_cm,
                            gradient=round(max(gradient), 5)
                        )
                    )
                    new_rev_id = round((
                        commit_map.short_time_id(lhs_cm) +
                        commit_map.short_time_id(rhs_cm)
                    ) / 2.0)
                    new_rev = self.plot_kwargs['cmap'].c_hash(new_rev_id)
                    print(
                        "-> Adding {rev} as new revision to the sample set".
                        format(rev=new_rev)
                    )
                    new_revs.add(new_rev)
                print()
            last_revision = revision
            last_row = row
        return new_revs


class BlameInteractionDegree(BlameDegree, plot_name="b_interaction_degree"):
    """Plotting the degree of blame interactions."""

    NAME = 'b_interaction_degree'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        if not self.plot_kwargs["legend_title"]:
            self.plot_kwargs["legend_title"] = "Interaction degrees"
        if not self.plot_kwargs["fig_title"]:
            self.plot_kwargs["fig_title"] = "Blame interactions"

        self._degree_plot(DegreeType.INTERACTION)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.INTERACTION, boundary_gradient
        )


class BlameInteractionDegreeGenerator(
    PlotGenerator,
    generator_name="interaction-degree-plot",
    plot=BlameInteractionDegree,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE,
        PlotGenerator.REQUIRE_MULTI_CASE_STUDY,
        OPTIONAL_SHOW_CHURN,
        OPTIONAL_EDGE_COLOR,
        OPTIONAL_COLORMAP,
        OPTIONAL_SHOW_CVE,
        OPTIONAL_SHOW_BUGS,
        OPTIONAL_CVE_BUG_LINE_WIDTH,
        OPTIONAL_CVE_BUG_COLOR,
        OPTIONAL_VERTICAL_ALIGNMENT,
    ]
):
    """Generates interaction-degree plot(s) for the selected case study(ies)."""

    @check_required_args("report_type", "case_study")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_studies: tp.List[CaseStudy] = plot_kwargs["case_study"]
        self.__fig_title: str = plot_config.fig_title
        self.__legend_title: str = plot_config.legend_title
        self.__legend_size: int = plot_config.legend_size
        self.__show_legend: bool = plot_config.show_legend
        self.__line_width: int = plot_config.line_width
        self.__x_tick_size: int = plot_config.x_tick_size
        self.__label_size: int = plot_config.label_size
        self.__show_churn: bool = plot_kwargs["show_churn"]
        self.__edge_color: str = plot_kwargs["edge_color"]
        self.__colormap: Colormap = plot_kwargs["colormap"]
        self.__show_cve: bool = plot_kwargs["show_cve"]
        self.__show_bugs: bool = plot_kwargs["show_bugs"]
        self.__cve_bug_line_width: int = plot_kwargs["cve_bug_line_width"]
        self.__cve_bug_color: str = plot_kwargs["cve_bug_color"]
        self.__vertical_alignment: str = plot_kwargs["vertical_alignment"]

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=cs,
                fig_title=self.__fig_title,
                legend_title=self.__legend_title,
                legend_size=self.__legend_size,
                show_legend=self.__show_legend,
                line_width=self.__line_width,
                x_tick_size=self.__x_tick_size,
                label_size=self.__label_size,
                show_churn=self.__show_churn,
                edge_color=self.__edge_color,
                colormap=self.__colormap,
                show_cve=self.__show_cve,
                show_bugs=self.__show_bugs,
                cve_bug_line_width=self.__cve_bug_line_width,
                cve_bug_color=self.__cve_bug_color,
                vertical_alignment=self.__vertical_alignment
            ) for cs in self.__case_studies
        ]


class BlameInteractionDegreeMultiLib(
    BlameDegree, plot_name="b_interaction_degree_multi_lib"
):
    """
    Plotting the degree of blame interactions between two libraries.

    Pass the selected base library (base_lib) and interacting library
    (inter_lib) as key-value pairs after the plot name. E.g., base_lib=Foo
    inter_lib=Bar
    """

    NAME = 'b_interaction_degree_multi_lib'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        if 'base_lib' not in self.plot_kwargs or \
                'inter_lib' not in self.plot_kwargs:
            LOG.warning("No library names were provided.")
            raise PlotDataEmpty

        base_lib = self.plot_kwargs['base_lib']
        inter_lib = self.plot_kwargs['inter_lib']

        extra_plot_cfg = {
            'legend_title': 'Interaction degrees',
            'fig_title': 'Blame interactions',
            'base_lib': base_lib,
            'inter_lib': inter_lib
        }
        # TODO (se-passau/VaRA#545): make params configurable in user call
        #  with plot config rework
        self._multi_lib_degree_plot(
            view_mode, DegreeType.INTERACTION, extra_plot_cfg
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.INTERACTION, boundary_gradient
        )


class BlameInteractionFractionOverview(
    BlameDegree, plot_name="b_interaction_fraction_overview"
):
    """Plotting the fraction distribution of in-/outgoing blame interactions
    from all project libraries."""

    NAME = 'b_interaction_fraction_overview'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Fraction ratio',
            'fig_title': 'Distribution of fractions'
        }
        # TODO (se-passau/VaRA#545): make params configurable in user call
        #  with plot config rework
        self._fraction_overview_plot(
            view_mode, DegreeType.INTERACTION, extra_plot_cfg
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.INTERACTION, boundary_gradient
        )


class BlameLibraryInteractions(
    BlameDegree, plot_name="b_multi_lib_interaction_sankey_plot"
):
    """
    Plotting the dependencies of blame interactions from all project libraries
    either as interactive plot in the browser or as static image.

    To plot in interactive mode, select view_mode=True and pass the selected
    revision as key-value pair after the plot name. E.g., revision=Foo
    """

    NAME = 'b_multi_lib_interaction_sankey_plot'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)
        self.__figure = go.Figure()

    def plot(self, view_mode: bool) -> None:
        self.__figure = self._multi_lib_interaction_sankey_plot(view_mode)

    def show(self) -> None:
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning(
                f"No data for project {self.plot_kwargs['case_study'].project_name}."
            )
            return
        self.__figure.show()

    def save(self, plot_dir: Path, filetype: str = 'png') -> None:
        project_name: str = self.plot_kwargs["case_study"].project_name
        commit_map: CommitMap = get_commit_map(project_name)

        try:
            self.plot(False)
            _save_figure(
                self.__figure,
                commit_map.convert_to_full_or_warn(
                    self.plot_kwargs["revision"]
                ), project_name, PlotTypes.SANKEY,
                self.plot_file_name(filetype), plot_dir, filetype
            )
        except PlotDataEmpty:
            LOG.warning(f"No data for project {project_name}.")
            return

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.INTERACTION, boundary_gradient
        )


class SankeyLibraryInteractionsGeneratorRev(
    PlotGenerator,
    generator_name="sankey-plot-rev",
    plot=BlameLibraryInteractions,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE, PlotGenerator.REQUIRE_CASE_STUDY,
        PlotGenerator.REQUIRE_REVISION
    ]
):
    """Generates a single sankey plot for the selected revision in the case
    study."""

    @check_required_args("report_type", "case_study", "revision")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_study: CaseStudy = plot_kwargs["case_study"]
        self.__revision: ShortCommitHash = ShortCommitHash(
            plot_kwargs["revision"]
        )
        self.__fig_title: str = plot_config.fig_title
        self.__width: int = plot_config.width
        self.__height: int = plot_config.height
        self.__font_size: int = plot_config.font_size

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=self.__case_study,
                revision=self.__revision,
                fig_title=self.__fig_title,
                width=self.__width,
                height=self.__height,
                font_size=self.__font_size,
            )
        ]


class SankeyLibraryInteractionsGeneratorCS(
    PlotGenerator,
    generator_name="sankey-plot-cs",
    plot=BlameLibraryInteractions,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE,
        PlotGenerator.REQUIRE_MULTI_CASE_STUDY
    ]
):
    """Generates a sankey plot for every revision in every given case study."""

    @check_required_args("report_type", "case_study")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_studies: tp.List[CaseStudy] = plot_kwargs["case_study"]
        self.__fig_title: str = plot_config.fig_title
        self.__width: int = plot_config.width
        self.__height: int = plot_config.height
        self.__font_size: int = plot_config.font_size

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=cs,
                revision=rev,
                fig_title=self.__fig_title,
                width=self.__width,
                height=self.__height,
                font_size=self.__font_size,
            ) for cs in self.__case_studies for rev in cs.revisions
        ]


class BlameCommitInteractionsGraphviz(
    BlameLibraryInteraction, plot_name="b_multi_lib_interaction_graphviz"
):
    """
    Plotting the interactions between all commits of multiple libraries.

    To view one plot, select view_mode=True and pass the selected revision as
    key-value pair after the plot name. E.g., revision=Foo. When the layout
    engine fdp is chosen, the additional graph attributes 'splines=True',
    'overlap=False', and 'nodesep=1' are added.
    """

    NAME = 'b_multi_lib_interaction_graphviz'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)
        self.__figure = Digraph()

    def plot(self, view_mode: bool) -> None:
        self.__figure = self._graphviz_plot()

    def show(self) -> None:
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning(
                f"No data for project {self.plot_kwargs['case_study'].project_name}."
            )
            return
        self.__figure.view(tempfile.mktemp())

    def save(self, plot_dir: Path, filetype: str = 'png') -> None:
        project_name: str = self.plot_kwargs["case_study"].project_name
        commit_map: CommitMap = get_commit_map(project_name)

        try:
            self.plot(False)
            _save_figure(
                self.__figure,
                commit_map.convert_to_full_or_warn(
                    self.plot_kwargs["revision"]
                ),
                self.plot_kwargs['case_study'].project_name, PlotTypes.GRAPHVIZ,
                self.plot_file_name(filetype), plot_dir, filetype
            )
        except PlotDataEmpty:
            LOG.warning(f"No data for project {project_name}.")
            return

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class GraphvizLibraryInteractionsGeneratorRev(
    PlotGenerator,
    generator_name="graphviz-plot-rev",
    plot=BlameCommitInteractionsGraphviz,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE, PlotGenerator.REQUIRE_CASE_STUDY,
        PlotGenerator.REQUIRE_REVISION, OPTIONAL_SHOW_INTERACTIONS,
        OPTIONAL_SHOW_DIFF, OPTIONAL_SHOW_EDGE_WEIGHT,
        OPTIONAL_EDGE_WEIGHT_THRESHOLD, OPTIONAL_REVISION_LENGTH,
        OPTIONAL_LAYOUT_ENGINE, OPTIONAL_SHOW_ONLY_COMMIT
    ]
):
    """Generates a single graphviz plot for the selected revision in the case
    study."""

    @check_required_args("report_type", "case_study", "revision")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_study: CaseStudy = plot_kwargs["case_study"]
        self.__revision: ShortCommitHash = ShortCommitHash(
            plot_kwargs["revision"]
        )
        self.__show_interactions: bool = plot_kwargs["show_interactions"]
        self.__show_diff: bool = plot_kwargs["show_diff"]
        self.__show_edge_weight: bool = plot_kwargs["show_edge_weight"]
        self.__edge_weight_threshold: tp.Optional[
            EdgeWeightThreshold] = plot_kwargs["edge_weight_threshold"]
        self.__revision_length: int = plot_kwargs["revision_length"]
        self.__layout_engine: str = plot_kwargs["layout_engine"]
        self.__show_only_commit: tp.Optional[str] = plot_kwargs[
            "show_only_commit"]

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=self.__case_study,
                revision=self.__revision,
                show_interactions=self.__show_interactions,
                show_diff=self.__show_diff,
                show_edge_weight=self.__show_edge_weight,
                edge_weight_threshold=self.__edge_weight_threshold,
                revision_length=self.__revision_length,
                layout_engine=self.__layout_engine,
                show_only_commit=self.__show_only_commit,
            )
        ]


class GraphvizLibraryInteractionsGeneratorCS(
    PlotGenerator,
    generator_name="graphviz-plot-cs",
    plot=BlameCommitInteractionsGraphviz,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE,
        PlotGenerator.REQUIRE_MULTI_CASE_STUDY, OPTIONAL_SHOW_INTERACTIONS,
        OPTIONAL_SHOW_DIFF, OPTIONAL_SHOW_EDGE_WEIGHT,
        OPTIONAL_EDGE_WEIGHT_THRESHOLD, OPTIONAL_REVISION_LENGTH,
        OPTIONAL_LAYOUT_ENGINE, OPTIONAL_SHOW_ONLY_COMMIT
    ]
):
    """Generates a graphviz plot for every revision in the case study."""

    @check_required_args("report_type", "case_study")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_studies: tp.List[CaseStudy] = plot_kwargs["case_study"]
        self.__show_interactions: bool = plot_kwargs["show_interactions"]
        self.__show_diff: bool = plot_kwargs["show_diff"]
        self.__show_edge_weight: bool = plot_kwargs["show_edge_weight"]
        self.__edge_weight_threshold: tp.Optional[
            EdgeWeightThreshold] = plot_kwargs["edge_weight_threshold"]
        self.__revision_length: int = plot_kwargs["revision_length"]
        self.__layout_engine: str = plot_kwargs["layout_engine"]
        self.__show_only_commit: tp.Optional[str] = plot_kwargs[
            "show_only_commit"]

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=cs,
                revision=rev,
                show_interactions=self.__show_interactions,
                show_diff=self.__show_diff,
                show_edge_weight=self.__show_edge_weight,
                edge_weight_threshold=self.__edge_weight_threshold,
                revision_length=self.__revision_length,
                layout_engine=self.__layout_engine,
                show_only_commit=self.__show_only_commit,
            ) for cs in self.__case_studies for rev in cs.revisions
        ]


class BlameAuthorDegree(BlameDegree, plot_name="b_author_degree"):
    """Plotting the degree of authors for all blame interactions."""

    NAME = 'b_author_degree'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_title': 'Author interaction degrees',
            'fig_title': 'Author blame interactions'
        }
        # TODO (se-passau/VaRA#545): make params configurable in user call
        #  with plot config rework
        self._degree_plot(view_mode, DegreeType.AUTHOR, extra_plot_cfg)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.AUTHOR, boundary_gradient
        )


class BlameMaxTimeDistribution(BlameDegree, plot_name="b_maxtime_distribution"):
    """Plotting the degree of max times differences for all blame
    interactions."""

    NAME = 'b_maxtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Max time distribution',
            'edgecolor': None,
        }
        # TODO (se-passau/VaRA#545): make params configurable in user call
        #  with plot config rework
        self._degree_plot(view_mode, DegreeType.MAX_TIME, extra_plot_cfg)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.MAX_TIME, boundary_gradient
        )


class BlameAvgTimeDistribution(BlameDegree, plot_name="b_avgtime_distribution"):
    """Plotting the degree of avg times differences for all blame
    interactions."""

    NAME = 'b_avgtime_distribution'

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': False,
            'fig_title': 'Average time distribution',
            'edgecolor': None,
        }
        # TODO (se-passau/VaRA#545): make params configurable in user call
        #  with plot config rework
        self._degree_plot(view_mode, DegreeType.AVG_TIME, extra_plot_cfg)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return self._calc_missing_revisions(
            DegreeType.AVG_TIME, boundary_gradient
        )
