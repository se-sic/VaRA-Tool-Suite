"""
Data wrappers for commit reports generated by VaRA
"""

import yaml
import seaborn as sns
import pandas as pd

from PyQt5.QtWidgets import QWidget, QGridLayout

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg \
    as FigureCanvas

class FunctionInfo(object):

    def __init__(self, raw_yaml):
        self.name = raw_yaml['function-name']
        self.id = raw_yaml['id']
        self.region_id = raw_yaml['region-id']

    def __str__(self):
        return "{} ({}): {}".format(self.name, self.id, self.region_id)


class RegionMapping(object):

    def __init__(self, raw_yaml):
        self.id = raw_yaml['id']
        self.representation = raw_yaml['representation']

    def __str__(self):
        return "{} = {}".format(self.id, self.representation)


class RegionToFunctionEdge(object):

    def __init__(self, raw_yaml):
        self._from = raw_yaml['from-region']
        self._to = raw_yaml['to-functions']

    def __str__(self):
        return "{} -> {}".format(self._from, self._to)


class RegionToRegionEdge(object):

    def __init__(self, raw_yaml):
        self._from = raw_yaml['from']
        self._to = raw_yaml['to']

    def __str__(self):
        return "{} -> {}".format(self._from, self._to)


class FunctionGraphEdges(object):

    def __init__(self, raw_yaml):
        self.fname = raw_yaml['function-name']
        self.cg_edges = []

        cg_edges = raw_yaml['call-graph-edges']
        if cg_edges is not None:
            for edge in cg_edges:
                self.cg_edges.append(RegionToFunctionEdge(edge))

        self.cf_edges = []
        cf_edges = raw_yaml['control-flow-edges']
        if cf_edges is not None:
            for edge in cf_edges:
                self.cf_edges.append(RegionToRegionEdge(edge))

        # TODO parsing
        self.df_relations = []

    def __str__(self):
        repr_str = "FName: {}:\n\t CG-Edges [".format(self.fname)
        sep = ""
        for cg_edge in self.cg_edges:
            repr_str += sep + str(cg_edge)
            sep = ", "
        repr_str += "]"

        repr_str += "\n\t CF-Edges ["
        sep = ""
        for cf_edge in self.cf_edges:
            repr_str += sep + str(cf_edge)
            sep = ", "
        repr_str += "]"

        return repr_str


class CommitReport(object):

    def __init__(self, path: str):
        with open(path, "r") as stream:
            self._path = path
            documents = yaml.load_all(stream)

            raw_infos = next(documents)
            self.finfos = dict()
            for raw_finfo in raw_infos['function-info']:
                finfo = FunctionInfo(raw_finfo)
                self.finfos[finfo.name] = finfo

            self.region_mappings = dict()
            for raw_r_mapping in raw_infos['region-mapping']:
                r_mapping = RegionMapping(raw_r_mapping)
                self.region_mappings[r_mapping.id] = r_mapping

            gedges = next(documents)
            self.graph_info = dict()
            # TODO: parse this into a full graph
            for raw_fg_edge in gedges:
                f_edge = FunctionGraphEdges(raw_fg_edge)
                self.graph_info[f_edge.fname] = f_edge

    def __str__(self):
        return "FInfo:\n\t{}\nRegionMappings:\n\t{}\n" \
            .format(self.finfos.keys(), self.region_mappings.keys())

    @property
    def path(self) -> str:
        """
        Path to CommitReport file.
        """
        return self._path


class CRBarPlotWidget(QWidget):
    """
    Bar plotting widget for CommitReports
    """

    def __init__(self, parent):
        super(CRBarPlotWidget, self).__init__(parent)

        self.fig = plt.figure()
        plot_cfg_barplot(self.fig, None)
        self.canvas = FigureCanvas(self.fig)

        layout = QGridLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def __del__(self):
        """
        Clean up matplotlib figures.
        """
        if self.fig is not None:
            plt.close(self.fig)

    def update_plot(self, commit_report: CommitReport):
        """
        Update the canvas with a new plot, generated from updated data.
        """
        plot_cfg_barplot(self.fig, commit_report)
        self.canvas.draw()


def plot_cfg_barplot(fig, commit_report: CommitReport):
    """
    Generates a bar plot that visualizes the IN/OUT
    control-flow edges of regions.
    """
    if commit_report is None:
        return
    #TODO: replace with actual bar plots
    d = {'col1': [1, 2], 'col2': [3, 4]}
    df = pd.DataFrame(data=d)
    plt.figure(fig.number)
    bar_p = sns.barplot(x="col1", y="col2", palette="Set3", data=df)
    fig.add_subplot(bar_p)
