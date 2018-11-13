"""
Data wrappers for commit reports generated by VaRA
"""

import yaml
import pandas as pd
import os

from PyQt5.QtWidgets import QWidget, QGridLayout


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
        self.hash = raw_yaml['hash']

    def __str__(self):
        return "{} = {}".format(self.id, self.hash)


class RegionToFunctionEdge(object):

    def __init__(self, from_region: str, to_function: str):
        self._from = from_region
        self._to = to_function

    def __str__(self):
        return "{} -> {}".format(self._from, self._to)


class RegionToRegionEdge(object):

    def __init__(self, raw_yaml):
        self._from = raw_yaml['from']
        self._to = raw_yaml['to']

    def __str__(self):
        return "{} -> {}".format(self._from, self._to)

    @property
    def edge_from(self):
        return self._from

    @property
    def edge_to(self):
        return self._to


class FunctionGraphEdges(object):

    def __init__(self, raw_yaml):
        self.fid = raw_yaml['function-id']
        self.cg_edges = []

        cg_edges = raw_yaml['call-graph-edges']
        if cg_edges is not None:
            for edge in cg_edges:
                for callee in edge['to-functions']:
                    self.cg_edges.append(RegionToFunctionEdge(
                        edge['from-region'], callee))

        self.cf_edges = []
        cf_edges = raw_yaml['control-flow-edges']
        if cf_edges is not None:
            for edge in cf_edges:
                self.cf_edges.append(RegionToRegionEdge(edge))

        self.df_relations = []
        df_edges = raw_yaml['data-flow-relations']
        if df_edges is not None:
            for edge in df_edges:
                self.df_relations.append(RegionToRegionEdge(edge))

    def __str__(self):
        repr_str = "FName: {}:\n\t CG-Edges [".format(self.fid)
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
                self.graph_info[f_edge.fid] = f_edge

    @property
    def path(self) -> str:
        """
        Path to CommitReport file.
        """
        return self._path

    def calc_max_cf_edges(self):
        """
        Calulate the highest amount of control-flow interactions of a single
        commit region.
        """
        cf_map = dict()
        self.init_cf_map_with_edges(cf_map)

        total = 0
        for from_to_pair in cf_map.values():
            total = max(max(from_to_pair[0], from_to_pair[1]), total)

        return total

    def calc_max_df_edges(self):
        """
        Calulate the highest amount of data-flow interactions of a single
        commit region.
        """
        df_map = dict()
        self.init_df_map_with_edges(df_map)

        total = 0
        for from_to_pair in df_map.values():
            total = max(max(from_to_pair[0], from_to_pair[1]), total)

        return total

    def __str__(self):
        return "FInfo:\n\t{}\nRegionMappings:\n\t{}\n" \
            .format(self.finfos.keys(), self.region_mappings.keys())

    def __repr__(self):
        return "CR: " + os.path.basename(self.path)

    def __lt__(self, other):
        return self.path < other.path

    def init_cf_map_with_edges(self, cf_map):
        """
        Initialize control-flow map with edges and from/to counters.
        """
        # if any information is missing add all from the original
        # report to avoid errors.
        for reg_mapping in self.region_mappings.values():
            cf_map[reg_mapping.id] = [0, 0]

        for func_g_edge in self.graph_info.values():
            for cf_edge in func_g_edge.cf_edges:
                cf_map[cf_edge.edge_from][0] += 1
                cf_map[cf_edge.edge_to][1] += 1

    def init_df_map_with_edges(self, df_map):
        """
        Initialize data-flow map with edges and from/to counters.
        """
        # if any information is missing add all from the original report
        # to avoid errors.
        for reg_mapping in self.region_mappings.values():
            df_map[reg_mapping.id] = [0, 0]

        for func_g_edge in self.graph_info.values():
            for df_edge in func_g_edge.df_relations:
                df_map[df_edge.edge_from][0] += 1
                df_map[df_edge.edge_to][1] += 1


class CommitReportMeta(object):

    def __init__(self):
        self.finfos = dict()
        self.region_mappings = dict()
        self.__cf_ylimit = 0
        self.__df_ylimit = 0

    def merge(self, commit_report: CommitReport):
        self.finfos.update(commit_report.finfos)
        self.region_mappings.update(commit_report.region_mappings)
        self.__cf_ylimit = max(self.__cf_ylimit,
                               commit_report.calc_max_cf_edges())
        self.__df_ylimit = max(self.__df_ylimit,
                               commit_report.calc_max_df_edges())

    @property
    def cf_ylimit(self):
        return self.__cf_ylimit

    @property
    def df_ylimit(self):
        return self.__df_ylimit

    def __str__(self):
        return "FInfo:\n\t{}\nRegionMappings:\n\t{}\n" \
            .format(self.finfos.keys(), self.region_mappings.keys())


class CommitMap(object):
    """
    Provides a mapping from commit hash to additional informations.
    """

    def __init__(self, path):
        self.__hash_to_id = dict()
        with open(path, "r") as c_map_file:
            for line in c_map_file.readlines():
                slices = line.strip().split(', ')
                self.__hash_to_id[slices[1]] = int(slices[0])

    def time_id(self, c_hash):
        """
        Convert a commit hash to a time id that allows a total order on the
        commits, based on the c_map, e.g., created from the analyzed git
        history.
        """
        return self.__hash_to_id[c_hash]


###############################################################################
# Connection Generators
###############################################################################

def generate_inout_cfg_cf(commit_report: CommitReport,
                          cr_meta: CommitReportMeta = None) -> pd.DataFrame:
    """
    Generates a pandas dataframe that contains the commit
    region control-flow interaction information.
    """
    cf_map = dict()  # RM -> [from, to]

    # Add all from meta commit report and ...
    if cr_meta is not None:
        for reg_mapping in cr_meta.region_mappings.values():
            cf_map[reg_mapping.id] = [0, 0]

    commit_report.init_cf_map_with_edges(cf_map)

    rows = []
    for item in cf_map.items():
        total = item[1][0] + item[1][1]

        rows.append([item[0], item[1][0], "From", total])
        rows.append([item[0], item[1][1], "To", total])

    rows.sort(key=lambda row: (row[0], -row[3], -row[1], row[2]))

    return pd.DataFrame(rows, columns=['Region', 'Amount',
                                       'Direction', 'TSort'])


def generate_inout_cfg_df(commit_report: CommitReport,
                          cr_meta: CommitReportMeta = None) -> pd.DataFrame:
    """
    Generates a pandas dataframe that contains the commit region
    data-flow interaction information.
    """
    df_map = dict()  # RM -> [from, to]

    # Add all from meta commit report and ...
    if cr_meta is not None:
        for reg_mapping in cr_meta.region_mappings.values():
            df_map[reg_mapping.id] = [0, 0]

    commit_report.init_df_map_with_edges(df_map)

    rows = []
    for item in df_map.items():
        total = item[1][0] + item[1][1]
        rows.append([item[0], item[1][0], "From", total])
        rows.append([item[0], item[1][1], "To", total])

    rows.sort(key=lambda row: (row[0], -row[3], -row[1], row[2]))

    return pd.DataFrame(rows, columns=['Region', 'Amount',
                                       'Direction', 'TSort'])
