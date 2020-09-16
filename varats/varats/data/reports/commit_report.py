"""Data wrappers for commit reports generated by VaRA."""
import logging
import typing as tp
from collections.abc import ItemsView
from pathlib import Path

import pandas as pd
import yaml
from pygtrie import CharTrie

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport, FileStatusExtension, MetaReport

LOG = logging.getLogger(__name__)


class FunctionInfo():
    """Encapsulates the information gathered for a single functions."""

    def __init__(self, raw_yaml: tp.Dict[str, tp.Any]) -> None:
        self.__name = str(raw_yaml['function-name'])
        self.__id = str(raw_yaml['id'])
        self.__region_id = str(raw_yaml['region-id'])

    @property
    def name(self) -> str:
        """Name of the function."""
        return self.__name

    @property
    def id(self) -> str:
        """Unique ID of the function info."""
        return self.__id

    @property
    def region_id(self) -> str:
        """ID of the region."""
        return self.__region_id

    def __str__(self) -> str:
        return "{} ({}): {}".format(self.name, self.id, self.region_id)


class RegionMapping():
    """Mapping from region ID to commit hash."""

    def __init__(self, raw_yaml: tp.Dict[str, tp.Any]) -> None:
        self.id = str(raw_yaml['id'])
        self.hash = str(raw_yaml['hash'])

    def __str__(self) -> str:
        return "{} = {}".format(self.id, self.hash)


class RegionToFunctionEdge():
    """Graph edge to connect regions and function data."""

    def __init__(self, from_region: str, to_function: str) -> None:
        self._from = from_region
        self._to = to_function

    @property
    def region(self) -> str:
        return self._from

    @property
    def function(self) -> str:
        return self._to

    def __str__(self) -> str:
        return "{} -> {}".format(self._from, self._to)


class RegionToRegionEdge():
    """Graph edge to interconnect regions."""

    def __init__(self, raw_yaml: tp.Dict[str, tp.Any]) -> None:
        self._from = str(raw_yaml['from'])
        self._to = str(raw_yaml['to'])

    def __str__(self) -> str:
        return "{} -> {}".format(self._from, self._to)

    @property
    def edge_from(self) -> str:
        return self._from

    @property
    def edge_to(self) -> str:
        return self._to


class FunctionGraphEdges():
    """A graph like structure that represents the connections between
    ``FunctionInfo``s."""

    def __init__(self, raw_yaml: tp.Dict[str, tp.Any]) -> None:
        self.fid = raw_yaml['function-id']
        self.cg_edges: tp.List[RegionToFunctionEdge] = []

        cg_edges = raw_yaml['call-graph-edges']
        if cg_edges is not None:
            for edge in cg_edges:
                for callee in edge['to-functions']:
                    self.cg_edges.append(
                        RegionToFunctionEdge(edge['from-region'], callee)
                    )

        self.cf_edges: tp.List[RegionToRegionEdge] = []
        cf_edges = raw_yaml['control-flow-edges']
        if cf_edges is not None:
            for edge in cf_edges:
                self.cf_edges.append(RegionToRegionEdge(edge))

        self.df_relations: tp.List[RegionToRegionEdge] = []
        df_edges = raw_yaml['data-flow-relations']
        if df_edges is not None:
            for edge in df_edges:
                self.df_relations.append(RegionToRegionEdge(edge))

    def __str__(self) -> str:
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


class CommitReport(BaseReport):
    """Data class that gives access to a loaded commit report."""

    SHORTHAND = "CR"
    FILE_TYPE = "yaml"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        with open(path, "r") as stream:
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

            for raw_fg_edge in gedges:
                f_edge = FunctionGraphEdges(raw_fg_edge)
                self.graph_info[f_edge.fid] = f_edge

    @property
    def head_commit(self) -> str:
        """The current HEAD commit under which this CommitReport was created."""
        return CommitReport.get_commit_hash_from_result_file(
            Path(self.path).name
        )

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = "yaml"
    ) -> str:
        """
        Generates a filename for a commit report with 'yaml' as file extension.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return MetaReport.get_file_name(
            CommitReport.SHORTHAND, project_name, binary_name, project_version,
            project_uuid, extension_type, file_ext
        )

    @staticmethod
    def get_supplementary_file_name(
        project_name: str, binary_name: str, project_version: str,
        project_uuid: str, info_type: str, file_ext: str
    ) -> str:
        """
        Generates a filename for a commit report supplementary file.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            info_type: specifies the kind of supplementary file
            file_ext: file extension of the report file

        Returns:
            name for the supplementary report file that can later be uniquly
            identified
        """
        return BaseReport.get_supplementary_file_name(
            CommitReport.SHORTHAND, project_name, binary_name, project_version,
            project_uuid, info_type, file_ext
        )

    def calc_max_cf_edges(self) -> int:
        """Calculate the highest amount of control-flow interactions of a single
        commit region."""
        cf_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_cf_map_with_edges(cf_map)

        total = 0
        for from_to_pair in cf_map.values():
            total = max(max(from_to_pair[0], from_to_pair[1]), total)

        return total

    def calc_max_df_edges(self) -> int:
        """Calculate the highest amount of data-flow interactions of a single
        commit region."""
        df_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_df_map_with_edges(df_map)

        total = 0
        for from_to_pair in df_map.values():
            total = max(max(from_to_pair[0], from_to_pair[1]), total)

        return total

    def __str__(self) -> str:
        return "FInfo:\n\t{}\nRegionMappings:\n\t{}\n" \
            .format(self.finfos.keys(), self.region_mappings.keys())

    def __repr__(self) -> str:
        return "CR: " + self.path.name

    def __lt__(self, other: 'CommitReport') -> bool:
        return self.path < other.path

    def init_cf_map_with_edges(
        self, cf_map: tp.Dict[str, tp.List[int]]
    ) -> None:
        """
        Initialize control-flow map with edges and from/to counters.

        Args:
            cf_map: control-flow
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
        """Total number of found control-flow interactions."""
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

        Returns:
            tuple (incoming_head_interactions, outgoing_head_interactions)
        """
        cf_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_cf_map_with_edges(cf_map)
        for key in cf_map:
            if key.startswith(self.head_commit):
                interaction_tuple = cf_map[key]
                return (interaction_tuple[0], interaction_tuple[1])

        return (0, 0)

    def init_df_map_with_edges(
        self, df_map: tp.Dict[str, tp.List[int]]
    ) -> None:
        """
        Initialize data-flow map with edges and from/to counters.

        Returns:
            tuple (incoming_head_interactions, outgoing_head_interactions)
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
        """Total number of found data-flow interactions."""
        df_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_df_map_with_edges(df_map)

        total_interactions = 0
        for interaction_tuple in df_map.values():
            total_interactions += interaction_tuple[0]
        return total_interactions

    def number_of_head_df_interactions(self) -> tp.Tuple[int, int]:
        """The number of control-flow interactions the HEAD commit has with
        other commits."""
        df_map: tp.Dict[str, tp.List[int]] = dict()
        self.init_df_map_with_edges(df_map)
        for key in df_map:
            if key.startswith(self.head_commit):
                interaction_tuple = df_map[key]
                return (interaction_tuple[0], interaction_tuple[1])

        return (0, 0)


class CommitReportMeta():
    """Meta report class that combines the data of multiple reports, comming
    from different revisions, into one."""

    def __init__(self) -> None:
        self.finfos: tp.Dict[str, FunctionInfo] = dict()
        self.region_mappings: tp.Dict[str, RegionMapping] = dict()
        self.__cf_ylimit = 0
        self.__df_ylimit = 0

    def merge(self, commit_report: CommitReport) -> None:
        """
        Merge data from commit report into CommitReportMeta.

        Args:
            commit_report: new report that will be added to the meta report
        """
        self.finfos.update(commit_report.finfos)
        self.region_mappings.update(commit_report.region_mappings)
        self.__cf_ylimit = max(
            self.__cf_ylimit, commit_report.calc_max_cf_edges()
        )
        self.__df_ylimit = max(
            self.__df_ylimit, commit_report.calc_max_df_edges()
        )

    @property
    def cf_ylimit(self) -> int:
        return self.__cf_ylimit

    @property
    def df_ylimit(self) -> int:
        return self.__df_ylimit

    def __str__(self) -> str:
        return "FInfo:\n\t{}\nRegionMappings:\n\t{}\n" \
            .format(self.finfos.keys(), self.region_mappings.keys())


class CommitMap():
    """Provides a mapping from commit hash to additional information."""

    def __init__(self, stream: tp.Iterable[str]) -> None:
        self.__hash_to_id: CharTrie = CharTrie()
        for line in stream:
            slices = line.strip().split(', ')
            self.__hash_to_id[slices[1]] = int(slices[0])

    def time_id(self, c_hash: str) -> int:
        """
        Convert a commit hash to a time id that allows a total order on the
        commits, based on the c_map, e.g., created from the analyzed git
        history.

        Args:
            c_hash: commit hash

        Returns:
            unique time-ordered id
        """
        return tp.cast(int, self.__hash_to_id[c_hash])

    def short_time_id(self, c_hash: str) -> int:
        """
        Convert a short commit hash to a time id that allows a total order on
        the commits, based on the c_map, e.g., created from the analyzed git
        history.

        The first time id is returend where the hash belonging to it starts
        with the short hash.

        Args:
            c_hash: commit hash

        Returns:
            unique time-ordered id
        """
        subtrie = self.__hash_to_id.items(prefix=c_hash)
        if subtrie:
            if len(subtrie) > 1:
                LOG.warning(f"Short commit hash is ambiguous: {c_hash}.")
            return tp.cast(int, subtrie[0][1])
        raise KeyError

    def c_hash(self, time_id: int) -> str:
        """
        Get the hash belonging to the time id.

        Args:
            time_id: unique time-ordered id

        Returns:
            commit hash
        """
        for c_hash, t_id in self.__hash_to_id.items():
            if t_id == time_id:
                return tp.cast(str, c_hash)
        raise KeyError

    def mapping_items(self) -> tp.ItemsView[str, int]:
        """Get an iterator over the mapping items."""
        return ItemsView(self.__hash_to_id)

    def write_to_file(self, target_file: tp.TextIO) -> None:
        """
        Write commit map to a file.

        Args:
            target_file: needs to be a writable stream, i.e., support .write()
        """
        for item in self.__hash_to_id.items():
            target_file.write("{}, {}\n".format(item[1], item[0]))

    def __str__(self) -> str:
        return str(self.__hash_to_id)


###############################################################################
# Connection Generators
###############################################################################


def generate_inout_cfg_cf(
    commit_report: CommitReport,
    cr_meta: tp.Optional[CommitReportMeta] = None
) -> pd.DataFrame:
    """
    Generates a pandas dataframe that contains the commit region control-flow
    interaction information.

    Args:
        commit_report: report containing the commit data
        cr_meta: the meta commit report, if available
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

    rows.sort(
        key=lambda row:
        (row[0], -tp.cast(int, row[3]), -tp.cast(int, row[1]), row[2])
    )

    return pd.DataFrame(
        rows, columns=['Region', 'Amount', 'Direction', 'TSort']
    )


def generate_interactions(
    commit_report: CommitReport, c_map: CommitMap
) -> pd.DataFrame:
    """
    Converts the commit analysis interaction data from a ``CommitReport`` into a
    pandas data frame for plotting.

    Args:
        commit_report: the report
        c_map: commit map for mapping commits to unique IDs
    """
    node_rows = []
    for item in commit_report.region_mappings.values():
        node_rows.append([item.hash, c_map.time_id(item.hash)])

    node_rows.sort(key=lambda row: int(tp.cast(int, row[1])), reverse=True)
    nodes = pd.DataFrame(node_rows, columns=['hash', 'id'])

    link_rows = []
    for func_g_edge in commit_report.graph_info.values():
        for cf_edge in func_g_edge.cf_edges:
            link_rows.append([
                cf_edge.edge_from, cf_edge.edge_to, 1,
                c_map.time_id(cf_edge.edge_from)
            ])

    links = pd.DataFrame(
        link_rows, columns=['source', 'target', 'value', 'src_id']
    )
    return (nodes, links)


def generate_inout_cfg_df(
    commit_report: CommitReport,
    cr_meta: tp.Optional[CommitReportMeta] = None
) -> pd.DataFrame:
    """
    Generates a pandas dataframe that contains the commit region data-flow
    interaction information.

    Args:
        commit_report: report containing the commit data
        cr_meta: the meta commit report, if available
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

    rows.sort(
        key=lambda row:
        (row[0], -tp.cast(int, row[3]), -tp.cast(int, row[1]), row[2])
    )

    return pd.DataFrame(
        rows, columns=['Region', 'Amount', 'Direction', 'TSort']
    )
