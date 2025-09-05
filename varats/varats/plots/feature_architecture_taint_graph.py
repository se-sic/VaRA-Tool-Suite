import logging
import typing as tp
from collections import Counter
from pathlib import Path

import pygraphviz as pgv
from pygraphviz import AGraph
from rich import region

from varats.data.reports.architecture_report import (
    FeatureArchitectureTaintReport,
)
from varats.experiments.vara.feature_architecture_taint_report_experiment import (
    FeatureArchitectureTaintReportExperiment,
)
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY

LOG = logging.getLogger(__name__)


def create_feature_architecture_taint_graph(
    report: FeatureArchitectureTaintReport,
    with_root: bool = True,
    detailed: bool = False
) -> AGraph:
    """Create a feature architecture taint graph for the given project."""
    graph = pgv.AGraph(directed=True, compound=True)
    graph.node_attr["shape"] = "box"
    subgraphs: tp.Dict[str, AGraph] = {}
    i = 0
    LOG.setLevel(logging.INFO)
    LOG.info(
        f"Creating feature architecture taint graph for: {report.filename}"
    )
    feature_induced_edges = []
    root_connections: tp.Dict[str, tp.Set[str]] = {}
    for func_entry in report.function_entries.values():
        outer_module = func_entry.file_name
        if outer_module not in subgraphs:
            fg = graph.add_subgraph(name=f"cluster_{i}", label=outer_module)
            i += 1
            subgraphs[outer_module] = fg
        else:
            fg = subgraphs[outer_module]
        for region_entry in func_entry.interactions:
            for a_region, features in region_entry.incommingRegions.items():
                if a_region not in subgraphs:
                    subgraphs[a_region] = graph.add_subgraph(
                        name=f"cluster_{i}", label=a_region
                    )
                    i += 1
                for feature in features:
                    subgraphs[a_region].add_node(f"{a_region}:{feature}")
                    for f in region_entry.features:
                        if feature == "root":
                            if outer_module not in root_connections.keys():
                                root_connections[outer_module] = set()
                            root_connections[outer_module].add(a_region)
                        if f != "root" or feature != "root" or with_root:
                            if not fg.has_node(f"{outer_module}:{f}"):
                                fg.add_node(f"{outer_module}:{f}")
                            if not detailed:
                                feature_induced_edges.append((
                                    f"{a_region}:{feature}",
                                    f"{outer_module}:root"
                                ))
                            else:
                                feature_induced_edges.append((
                                    f"{a_region}:{feature}",
                                    f"{outer_module}:{f}"
                                ))
    weighted_edges = Counter(feature_induced_edges)
    for (u, v), k in weighted_edges.items():
        if u == v:
            continue
        v_region = v.split(":")[0]
        u_region = u.split(":")[0]
        if v_region not in root_connections.keys(
        ) or u_region not in root_connections[v_region]:
            if not v_region == u_region:
                graph.add_edge(
                    u,
                    v,
                    color="red",
                    label=f"{k}",
                    lhead=subgraphs[v_region].name
                )
            else:
                graph.add_edge(u, v, color="red", label=f"{k}")
        elif not detailed and weighted_edges[
            (f"{u_region}:root", f"{v_region}:root")] < k:
            if not v_region == u_region:
                graph.add_edge(
                    u,
                    v,
                    label=f"{k}",
                    color="orange",
                    lhead=subgraphs[v_region].name
                )
            else:
                graph.add_edge(u, v, label=f"{k}", color="orange")
        else:
            if not v_region == u_region:
                graph.add_edge(
                    u, v, label=f"{k}", lhead=subgraphs[v_region].name
                )
            else:
                graph.add_edge(u, v, label=f"{k}")
    return graph


class FeatureArchitectureTaintGraph(
    Plot, plot_name="feature_architecture_taint_graph"
):
    """Create a feature architecture taint graph for the given project."""

    def __init__(
        self, plot_config: PlotConfig, report: FeatureArchitectureTaintReport,
        **kwargs: tp.Any
    ) -> None:
        super().__init__(plot_config, **kwargs)
        self.report_file = report

    def plot(self, view_mode: bool) -> None:
        pass

    def save(self, plot_dir: Path, filetype: str = 'svg') -> None:
        """Create the feature architecture taint graph."""
        graph = create_feature_architecture_taint_graph(
            self.report_file, detailed=self.plot_kwargs["detailed"]
        )
        graph.layout(prog="dot")
        graph.draw(
            plot_dir / f"{self.report_file.path.stem}_with_root.svg",
            prog="dot"
        )
        graph.write(plot_dir / f"{filetype}.dot")
        graph = create_feature_architecture_taint_graph(self.report_file, False)
        graph.draw(
            plot_dir / ("no_root" + self.plot_file_name(filetype)), prog="dot"
        )


class FeatureArchitectureTaintGraphPlotGenerator(
    PlotGenerator,
    generator_name="FeatureArchitectureTaintGraph",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option(
            "-dt",
            "--detailed",
            is_flag=True,
            help="Plot detailed dependencies."
        )
    ]
):
    """Plot generator for the feature architecture taint graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            FeatureArchitectureTaintGraph(
                self.plot_config,
                FeatureArchitectureTaintReport(path.full_path()),
                **self.plot_kwargs
            ) for path in get_processed_revisions_files(
                self.plot_kwargs["case_study"].project_name,
                FeatureArchitectureTaintReportExperiment,
                FeatureArchitectureTaintReport,
                only_newest=True
            )
        ]
