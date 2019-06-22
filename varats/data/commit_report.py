"""
Data wrappers for commit reports generated by VaRA
"""

import typing as tp
import os
import re
from pathlib import Path
import yaml
import pandas as pd

from varats.data.file_status import FileStatusExtension
from varats.data.version_header import VersionHeader


class FunctionInfo():

    def __init__(self, raw_yaml):
        self.__name = raw_yaml['function-name']
        self.__id = raw_yaml['id']
        self.__region_id = raw_yaml['region-id']

    @property
    def name(self):
        return self.__name

    @property
    def id(self):
        return self.__id

    @property
    def region_id(self):
        return self.__region_id

    def __str__(self):
        return "{} ({}): {}".format(self.name, self.id, self.region_id)


class RegionMapping():

    def __init__(self, raw_yaml):
        self.id = raw_yaml['id']
        self.hash = raw_yaml['hash']

    def __str__(self):
        return "{} = {}".format(self.id, self.hash)


class RegionToFunctionEdge():

    def __init__(self, from_region: str, to_function: str):
        self._from = from_region
        self._to = to_function

    @property
    def region(self) -> str:
        return self._from

    @property
    def function(self) -> str:
        return self._to

    def __str__(self):
        return "{} -> {}".format(self._from, self._to)


class RegionToRegionEdge():

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


class FunctionGraphEdges():

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


class CommitReport():

    __FILE_NAME_REGEX = re.compile(
        r"(?P<project_name>.*)-(?P<binary_name>.*)-" +
        r"(?P<file_commit_hash>.*)_(?P<UUID>[0-9a-fA-F\-]*)" +
        r"(?P<EXT>(\.yaml|\.failed))$")

    __RESULT_FILE_TEMPLATE = \
        "{project_name}-{binary_name}-{project_version}_{project_uuid}.{ext}"

    def __init__(self, path: str):
        with open(path, "r") as stream:
            self._path = path
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("CommitReport")
            version_header.raise_if_version_is_less_than(3)

            raw_infos = next(documents)
            self.finfos: tp.Dict[str, FunctionInfo] = dict()
            for raw_finfo in raw_infos['function-info']:
                finfo = FunctionInfo(raw_finfo)
                self.finfos[finfo.name] = finfo

            self.region_mappings: tp.Dict[str, RegionMapping] = dict()
            raw_region_mapping = raw_infos['region-mapping']
            if raw_region_mapping is not None:
                for raw_r_mapping in raw_region_mapping:
                    r_mapping = RegionMapping(raw_r_mapping)
                    self.region_mappings[r_mapping.id] = r_mapping

            gedges = next(documents)
            self.graph_info: tp.Dict[str, FunctionGraphEdges] = dict()
            # TODO: parse this into a full graph
            for raw_fg_edge in gedges:
                f_edge = FunctionGraphEdges(raw_fg_edge)
                self.graph_info[f_edge.fid] = f_edge

    @staticmethod
    def is_result_file(file_name: str) -> bool:
        """ Check if the passed file name is a result file. """
        match = CommitReport.__FILE_NAME_REGEX.search(file_name)
        return match is not None

    @staticmethod
    def is_result_file_success(file_name: str) -> bool:
        """ Check if the passed file name is a (successful) result file. """
        return CommitReport.is_result_file_status(file_name,
                                                  FileStatusExtension.success)

    @staticmethod
    def is_result_file_failed(file_name: str) -> bool:
        """ Check if the passed file name is a (failed) result file. """
        return CommitReport.is_result_file_status(file_name,
                                                  FileStatusExtension.failure)

    @staticmethod
    def is_result_file_status(file_name: str,
                              extension_type: FileStatusExtension) -> bool:
        """ Check if the passed file name is a (failed) result file. """
        match = CommitReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return match.group("EXT") == (
                "." + CommitReport.__get_file_ext(extension_type))
        return False

    @staticmethod
    def get_commit_hash_from_result_file(file_name: str) -> str:
        """ Get the commit hash from a result file name. """
        match = CommitReport.__FILE_NAME_REGEX.search(file_name)
        if match:
            return match.group("file_commit_hash")

        raise ValueError('File {file_name} name was wrongly formated.'.format(
            file_name=file_name))

    @staticmethod
    def __get_file_ext(extension_type: FileStatusExtension) -> str:
        if extension_type is FileStatusExtension.success:
            return "yaml"

        if extension_type is FileStatusExtension.failure:
            return "failed"

        raise NotImplementedError

    @staticmethod
    def get_file_name(project_name: str, binary_name: str,
                      project_version: str, project_uuid: str,
                      extension_type: FileStatusExtension):
        """
        Generates a filename for a commit report
        """
        ext = CommitReport.__get_file_ext(extension_type)

        return CommitReport.__RESULT_FILE_TEMPLATE.format(
            project_name=project_name,
            binary_name=binary_name,
            project_version=project_version,
            project_uuid=project_uuid,
            ext=ext)

    @property
    def path(self) -> str:
        """
        Path to CommitReport file.
        """
        return self._path

    @property
    def head_commit(self) -> str:
        """
        The current HEAD commit under which this CommitReport was created.
        """
        return CommitReport.get_commit_hash_from_result_file(
            Path(self._path).name)

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

    def number_of_cf_interactions(self) -> int:
        """
        Total number of found control-flow interactions.
        """
        cf_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_cf_map_with_edges(cf_map)

        total_interactions = 0
        for interaction_tuple in cf_map.values():
            total_interactions += interaction_tuple[0]
        return total_interactions

    def number_of_head_cf_interactions(self) -> tp.Tuple[int, int]:
        """
        The number of control-flow interactions the HEAD commit has with other
        commits.
        """
        cf_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_cf_map_with_edges(cf_map)
        for key in cf_map:
            if key.startswith(self.head_commit):
                interaction_tuple = cf_map[key]
                return (interaction_tuple[0], interaction_tuple[1])

        return (0, 0)

    def init_df_map_with_edges(self, df_map: tp.Dict[str, tp.List[int]]):
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

    def number_of_df_interactions(self) -> int:
        """
        Total number of found data-flow interactions.
        """
        df_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_df_map_with_edges(df_map)

        total_interactions = 0
        for interaction_tuple in df_map.values():
            total_interactions += interaction_tuple[0]
        return total_interactions

    def number_of_head_df_interactions(self) -> tp.Tuple[int, int]:
        """
        The number of control-flow interactions the HEAD commit has with other
        commits.
        """
        df_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_df_map_with_edges(df_map)
        for key in df_map:
            if key.startswith(self.head_commit):
                interaction_tuple = df_map[key]
                return (interaction_tuple[0], interaction_tuple[1])

        return (0, 0)


class CommitReportMeta():

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


class CommitMap():
    """
    Provides a mapping from commit hash to additional informations.
    """

    def __init__(self, stream) -> None:
        self.__hash_to_id: tp.Dict[str, int] = dict()
        for line in stream:
            slices = line.strip().split(', ')
            self.__hash_to_id[slices[1]] = int(slices[0])

    def time_id(self, c_hash):
        """
        Convert a commit hash to a time id that allows a total order on the
        commits, based on the c_map, e.g., created from the analyzed git
        history.
        """
        return self.__hash_to_id[c_hash]

    def short_time_id(self, c_hash):
        """
        Convert a short commit hash to a time id that allows a total order on
        the commits, based on the c_map, e.g., created from the analyzed git
        history.

        The first time id is returend where the hash belonging to it starts
        with the short hash.
        """
        for key in self.__hash_to_id:
            if key.startswith(c_hash):
                return self.__hash_to_id[key]
        raise KeyError

    def c_hash(self, time_id):
        """
        Get the hash belonging to the time id.
        """
        for c_hash, t_id in self.__hash_to_id.items():
            if t_id == time_id:
                return c_hash
        raise KeyError

    def mapping_items(self):
        """
        Get an iterator over the mapping items.
        """
        return self.__hash_to_id.items()

    def write_to_file(self, target_file: tp.TextIO) -> None:
        """
        Write commit map to a file.

        Args:
            target_file: needs to be a writable stream, i.e., support .write()
        """
        for item in self.__hash_to_id.items():
            target_file.write("{}, {}\n".format(item[1], item[0]))


###############################################################################
# Connection Generators
###############################################################################


def generate_inout_cfg_cf(commit_report: CommitReport,
                          cr_meta: tp.Optional[CommitReportMeta] = None
                          ) -> pd.DataFrame:
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


def generate_interactions(commit_report: CommitReport,
                          c_map: CommitMap) -> pd.DataFrame:
    node_rows = []
    for item in commit_report.region_mappings.values():
        node_rows.append([item.hash, c_map.time_id(item.hash)])

    node_rows.sort(key=lambda row: int(row[1]), reverse=True)
    nodes = pd.DataFrame(node_rows, columns=['hash', 'id'])

    link_rows = []
    for func_g_edge in commit_report.graph_info.values():
        for cf_edge in func_g_edge.cf_edges:
            link_rows.append([
                cf_edge.edge_from, cf_edge.edge_to, 1,
                c_map.time_id(cf_edge.edge_from)
            ])

    links = pd.DataFrame(link_rows, columns=['source', 'target', 'value',
                                             'src_id'])
    return (nodes, links)


def generate_inout_cfg_df(commit_report: CommitReport,
                          cr_meta: tp.Optional[CommitReportMeta] = None
                          ) -> pd.DataFrame:
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
