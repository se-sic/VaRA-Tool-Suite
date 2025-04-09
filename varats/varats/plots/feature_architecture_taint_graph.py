import typing as tp
from pathlib import Path

import pygraphviz as pgv
from pygraphviz import AGraph

from varats.data.reports.architecture_report import (
    FeatureArchitectureTaintReport,
)
from varats.experiments.vara.feature_architecture_taint_report_experiment import (
    FeatureArchitectureTaintReportExperiment,
)
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY


def create_feature_architecture_taint_graph(
    report: FeatureArchitectureTaintReport, with_root: bool = True
) -> AGraph:
    """Create a feature architecture taint graph for the given project."""
    graph = pgv.AGraph()
    graph.node_attr["shape"] = "box"
    subgraphs: tp.Dict[str, AGraph] = {}
    i = 0
    for func_entry in report.function_entries.values():
        outer_module = func_entry.file_name
        outer_feature = func_entry.feature
        if outer_module not in subgraphs:
            fg = graph.add_subgraph(name=f"cluster_{i}", label=outer_module)
            i += 1
            subgraphs[outer_module] = fg
        else:
            fg = subgraphs[outer_module]
        for module, features in func_entry.interactions.items():
            for feature in features:
                if module not in subgraphs:
                    subgraphs[module] = graph.add_subgraph(
                        name=f"cluster_{i}", label=module
                    )
                    i += 1
                subgraphs[module].add_node(f"{module}:{feature}")
                if feature != "root" or with_root:
                    graph.add_edge(
                        f"{module}:{feature}",
                        f"{outer_module}:{outer_feature}",
                        lhead=fg.name
                    )
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
        graph = create_feature_architecture_taint_graph(self.report_file)
        graph.layout(prog="dot")
        graph.draw(plot_dir / f"with_root.svg", prog="dot")
        graph.write(plot_dir / f"{filetype}.dot")
        graph = create_feature_architecture_taint_graph(self.report_file, False)
        graph.draw(plot_dir / f"with_out_root.svg", prog="dot")


class FeatureArchitectureTaintGraphPlotGenerator(
    PlotGenerator,
    generator_name="FeatureArchitectureTaintGraph",
    options=[REQUIRE_CASE_STUDY]
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
