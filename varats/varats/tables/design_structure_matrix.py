import typing as tp
from xml.etree import ElementTree as ET

import pandas as pd
from numpy.core.defchararray import title

from varats.table.table import Table
from varats.table.tables import TableConfig, TableFormat


def crate_matrix(df: pd.DataFrame) -> str:
    df.columns = df.columns.map('{0[0]}/{0[1]}'.format)
    df = df.droplevel(level=1)
    df = df.rename_axis(["<group>"], axis=0)
    df = df.rename_axis(None, axis=1)
    return df.to_csv()


class DMSInterface:
    uid: int
    name: str
    abbreviation: str

    def __init__(self, uid: int, name: str, abbreviation: str) -> None:
        self.uid = uid
        self.name = name
        self.abbreviation = abbreviation

    def to_xml(self, parent: ET.Element) -> ET.Element:
        interface = ET.SubElement(parent, "interface")
        ET.SubElement(interface, "uid").text = str(self.uid)
        ET.SubElement(interface, "name").text = self.name
        ET.SubElement(interface, "abbrev").text = self.abbreviation
        return interface


class DSMGroup:
    name: str
    priority: int
    uid: int
    background_color: tp.Tuple[float, float, float]
    foreground_color: tp.Tuple[float, float, float]

    def __init__(
        self,
        uid: int,
        name: str,
        priority: int,
        background_color: tp.Tuple[float, float, float] = (1.0, 1.0, 1.0),
        foreground_color: tp.Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> None:
        self.uid = uid
        self.name = name
        self.priority = priority
        self.background_color = background_color
        self.foreground_color = foreground_color

    #genertae xml element for group
    def to_xml(self, parent: ET.Element) -> ET.Element:
        group = ET.SubElement(parent, "group")
        ET.SubElement(group, "uid").text = str(self.uid)
        ET.SubElement(group, "priority").text = str(self.priority)
        ET.SubElement(group, "name").text = self.name
        ET.SubElement(group, "gr").text = str(self.background_color[0])
        ET.SubElement(group, "gg").text = str(self.background_color[1])
        ET.SubElement(group, "gb").text = str(self.background_color[2])
        ET.SubElement(group, "fr").text = str(self.foreground_color[0])
        ET.SubElement(group, "fg").text = str(self.foreground_color[1])
        ET.SubElement(group, "fb").text = str(self.foreground_color[2])
        return group


class DSMConnection:
    row_uid: int
    col_uid: int
    name: str
    weight: float
    interfaces: tp.List[int]

    def __init__(
        self,
        row_uid: int,
        col_uid: int,
        name: str,
        weight: float = 1.0,
        interfaces=None
    ) -> None:
        if interfaces is None:
            interfaces = []
        self.row_uid = row_uid
        self.col_uid = col_uid
        self.name = name
        self.weight = weight
        self.interfaces = interfaces

    def to_xml(self, parent: ET.Element) -> ET.Element:
        connection = ET.SubElement(parent, "connection")
        ET.SubElement(connection, "row_uid").text = str(self.row_uid)
        ET.SubElement(connection, "col_uid").text = str(self.col_uid)
        ET.SubElement(connection, "name").text = self.name
        ET.SubElement(connection, "weight").text = str(self.weight)
        interfaces = ET.SubElement(connection, "interfaces")
        for interface in self.interfaces:
            ET.SubElement(interfaces, "interface").set("uid", str(interface))
        return connection


class DSMEntry:
    name: str
    index: int
    group: int
    alias: int
    uid: int

    def __init__(
        self, uid: int, name: str, index: int, group: int, alias: int
    ) -> None:
        self.uid = uid
        self.name = name
        self.index = index
        self.group = group
        self.alias = alias

    def to_xml(self, parent: ET.Element, is_col: bool = True) -> ET.Element:
        col = ET.SubElement(parent, "col" if is_col else "row")
        col.set("uid", str(self.uid if is_col else self.alias))
        ET.SubElement(col, "name").text = self.name
        ET.SubElement(col, "sort_index").text = str(self.index)
        ET.SubElement(col, "group1").text = str(self.group)
        ET.SubElement(col,
                      "alias").text = str(self.alias if is_col else self.uid)
        return col


class DSM:
    title: str
    project: str
    entries: tp.List[DSMEntry]
    groups: tp.List[DSMGroup]
    connections: tp.List[DSMConnection]
    interfaces: tp.List[DMSInterface]
    entryUid: int = 0
    groupUid: int = 0
    interfaceUid: int = 0

    def __init__(
        self,
        title: str,
        project: str,
        entries=None,
        groups=None,
        connections=None,
        interfaces=None
    ) -> None:
        if entries is None:
            entries = []
        if groups is None:
            groups = []
        groups.append(DSMGroup(2147483647, "(none)", -1))
        if connections is None:
            connections = []
        if interfaces is None:
            interfaces = []
        self.title = title
        self.project = project
        self.entries = entries
        self.groups = groups
        self.connections = connections
        self.interfaces = interfaces

    def add_entry(self, name: str) -> tuple[int, int]:
        entry = DSMEntry(
            self.entryUid, name,
            len(self.entries) + 1, 2147483647, self.entryUid + 1
        )
        self.entries.append(entry)
        self.entryUid += 2
        return entry.uid, entry.alias

    def add_group(self, name: str, priority: int) -> None:
        group = DSMGroup(self.groupUid, name, priority)
        self.groups.append(group)
        self.groupUid += 1

    def add_interface(self, name: str, abbreviation: str) -> int:
        interface = DMSInterface(self.interfaceUid, name, abbreviation)
        self.interfaces.append(interface)
        self.interfaceUid += 1
        return interface.uid

    def add_connection(
        self,
        row_uid: int,
        col_uid: int,
        name: str = "x",
        weight: float = 1.0,
        interfaces=None
    ) -> None:
        if interfaces is None:
            interfaces = []
        connection = DSMConnection(row_uid, col_uid, name, weight, interfaces)
        self.connections.append(connection)

    def crate_info(self, info: ET.Element) -> ET.Element:
        ET.SubElement(info, "title").text = self.title
        ET.SubElement(info, "project").text = self.project
        ET.SubElement(info, "customer")
        ET.SubElement(info, "type").text = "symmetric"
        ET.SubElement(info, "version").text = "v2.1.0"
        return info

    def to_xml(self) -> ET.Element:
        dsm = ET.Element("dsm")
        self.crate_info(ET.SubElement(dsm, "info"))
        columns = ET.SubElement(dsm, "columns")
        for entry in self.entries:
            entry.to_xml(columns, is_col=True)
        rows = ET.SubElement(dsm, "rows")
        for entry in self.entries:
            entry.to_xml(rows, is_col=False)
        connections = ET.SubElement(dsm, "connections")
        for connection in self.connections:
            connection.to_xml(connections)
        groups = ET.SubElement(dsm, "groupings")
        for group in self.groups:
            group.to_xml(groups)
        interfaces = ET.SubElement(ET.SubElement(dsm, "interfaces"), "grouping")
        interfaces.set("name", "features")
        for interface in self.interfaces:
            interface.to_xml(interfaces)
        return dsm

    def to_xml_string(self) -> str:
        return ET.tostring(self.to_xml(), encoding="unicode")


class DesignStructureMatrix(Table, table_name=None):

    data: pd.DataFrame = None
    dsm: DSM = None

    def __init__(self, table_config: TableConfig, **kwargs: tp.Any):
        super().__init__(table_config, **kwargs)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        output = "symmetric\n"
        output += crate_matrix(self.data)
        ET.dump(self.dsm.to_xml())
        return self.dsm.to_xml_string()
