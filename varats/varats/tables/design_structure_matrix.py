import json
import typing as tp
from xml.etree import ElementTree as ET

import click

from varats.project.project_util import get_project_cls_by_name
from varats.provider.architecture.architecture_model_provider import (
    ArchitectureModel,
    ArchitectureModelProvider,
)
from varats.table.table import Table
from varats.table.tables import TableConfig, TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option


class InternalDSM:
    """Internal representation of a Design Structure Matrix Used as an interface
    between reports and different DSM tools."""
    name: str
    project: str
    dependencies: tp.List["InternalDSM.Dependency"]

    class Dependency:
        source: str
        target: str
        weight: int
        name: str
        attributes: tp.Dict[str, tp.List[str]]

        def __init__(
            self, source: str, target: str, name: str, weight: int,
            attributes: tp.Optional[tp.Dict[str, tp.List[str]]]
        ) -> None:
            self.source = source
            self.target = target
            self.weight = weight
            self.name = name
            if attributes is None:
                self.attributes = {}
            else:
                self.attributes = attributes

    def __init__(self, name: str, project: str) -> None:
        self.name = name
        self.project = project
        self.dependencies: tp.List[InternalDSM.Dependency] = []

    def add_dependency(
        self,
        source: str,
        target: str,
        name: str,
        weight: int = 1,
        attributes: tp.Optional[tp.Dict[str, tp.List[str]]] = None
    ) -> None:
        dependency = InternalDSM.Dependency(
            source, target, name, weight, attributes
        )
        self.dependencies.append(dependency)

    def apply_architecture_model(self):
        project = get_project_cls_by_name(self.project)
        provider = ArchitectureModelProvider.create_provider_for_project(
            project
        )
        if provider is None:
            return
        am = provider.get_architecture_model()
        for dependency in self.dependencies:
            dependency.source = am.get_module_for_location(dependency.source)
            dependency.target = am.get_module_for_location(dependency.target)

    @classmethod
    def from_dv8_json_string(
        cls, json_string: str, project: str
    ) -> 'InternalDSM':
        json_dict = json.loads(json_string)
        if "name" in json_dict:
            name = json_dict["name"]
        else:
            name = "DV8_DSM"
        dsm = InternalDSM(name, project)
        if "variables" in json_dict and isinstance(
            json_dict["variables"], list
        ):
            variables = json_dict["variables"]
            if "cells" in json_dict and isinstance(json_dict["cells"], list):
                for cell in json_dict["cells"]:
                    if "src" in cell and "dest" in cell and "values" in cell and isinstance(
                        cell["values"], dict
                    ):
                        source_entry = variables[cell["src"]]
                        target_entry = variables[cell["dest"]]
                        for name, value in cell["values"].items():
                            dsm.add_dependency(
                                source_entry, target_entry, name, value
                            )
        return dsm


"""
Export to DSMEditor XML format
"""


class DSMEditorXML:
    title: str
    project: str
    entries: tp.Dict[str, "DSMEditorXML.DSMEntry"]
    groups: tp.List["DSMGroup"]
    connections: tp.List["DSMConnection"]
    interfaces: tp.Dict[str, tp.Dict[str, "DMSInterface"]]
    entryUid: int = 0
    groupUid: int = 0
    interfaceUid: int = 0

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

        # genertae xml element for group
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
                ET.SubElement(interfaces,
                              "interface").set("uid", str(interface))
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
            ET.SubElement(col, "alias"
                         ).text = str(self.alias if is_col else self.uid)
            return col

    def __init__(self, DSM: InternalDSM) -> None:
        self.title = DSM.name
        self.project = DSM.project
        self.entries = {}
        self.groups = []
        self.connections = []
        self.interfaces = {}
        for dependency in DSM.dependencies:
            target_entry = self.get_or_create_entry(dependency.target)
            source_entry = self.get_or_create_entry(dependency.source)
            dep_interfaces = []
            for group, attributes in dependency.attributes.items():
                for item in attributes:
                    dep_interfaces.append(
                        self.get_or_create_interface(group, item, item[:2])
                    )
            self.add_connection(
                source_entry.uid, target_entry.alias, dependency.name,
                dependency.weight, [i.uid for i in dep_interfaces]
            )

    def get_or_create_entry(self, name: str) -> DSMEntry:
        if name in self.entries:
            return self.entries[name]
        entry = DSMEditorXML.DSMEntry(
            self.entryUid, name,
            len(self.entries) + 1, 2147483647, self.entryUid + 1
        )
        self.entries[name] = entry
        self.entryUid += 2
        return entry

    def add_group(self, name: str, priority: int) -> None:
        group = DSMEditorXML.DSMGroup(self.groupUid, name, priority)
        self.groups.append(group)
        self.groupUid += 1

    def get_or_create_interface(
        self, interface_group: str, name: str, abbreviation: str
    ) -> DMSInterface:
        if self.interfaces.get(interface_group) is None:
            self.interfaces[interface_group] = {}
        elif name in self.interfaces[interface_group]:
            return self.interfaces[interface_group][name]
        interface = DSMEditorXML.DMSInterface(
            self.interfaceUid, name, abbreviation
        )
        self.interfaces[interface_group][name] = interface
        self.interfaceUid += 1
        return interface

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
        connection = DSMEditorXML.DSMConnection(
            row_uid, col_uid, name, weight, interfaces
        )
        self.connections.append(connection)

    def crate_info(self, info: ET.Element) -> ET.Element:
        ET.SubElement(info, "title").text = self.title
        ET.SubElement(info, "project").text = self.project
        ET.SubElement(info, "customer")
        ET.SubElement(info, "type").text = "feature"
        ET.SubElement(info, "version").text = "v2.1.0"
        return info

    def to_xml(self) -> ET.Element:
        dsm = ET.Element("dsm")
        self.crate_info(ET.SubElement(dsm, "info"))
        columns = ET.SubElement(dsm, "columns")
        for _, entry in self.entries.items():
            entry.to_xml(columns, is_col=True)
        rows = ET.SubElement(dsm, "rows")
        for _, entry in self.entries.items():
            entry.to_xml(rows, is_col=False)
        connections = ET.SubElement(dsm, "connections")
        for connection in self.connections:
            connection.to_xml(connections)
        groups = ET.SubElement(dsm, "groupings")
        for group in self.groups:
            group.to_xml(groups)
        interfaces = ET.SubElement(dsm, "interfaces")
        for grouping_name, group_interfaces in self.interfaces.items():
            grouping = ET.SubElement(interfaces, "grouping")
            grouping.set("name", grouping_name)
            for _, interface in group_interfaces.items():
                interface.to_xml(grouping)
        return dsm

    def to_xml_string(self) -> str:
        return ET.tostring(self.to_xml(), encoding="unicode")


"""
Export to DV8 DSM format
"""


class DV8DSM:

    variables: tp.Dict[str, int]
    cells: tp.Dict[tp.Tuple[int, int], tp.Dict[str, int]]
    name: str

    def __init__(self, DSM: InternalDSM) -> None:
        self.name = f"{DSM.project}_{DSM.name}"
        self.variables = {
            item: index for index, item in enumerate(
                list({dep.source for dep in DSM.dependencies
                     }.union({dep.target for dep in DSM.dependencies}))
            )
        }
        self.cells = {}
        for dependency in DSM.dependencies:
            source_index = self.variables[dependency.source]
            target_index = self.variables[dependency.target]
            if source_index == target_index:
                continue
            if (source_index, target_index) not in self.cells:
                self.cells[(source_index, target_index)] = {}
            if dependency.name not in self.cells[(source_index, target_index)]:
                self.cells[(source_index, target_index)][dependency.name] = 0
            self.cells[(source_index, target_index)][dependency.name
                                                    ] += dependency.weight
            if dependency.attributes is not None:
                for group, attribute in dependency.attributes.items():
                    for atr in attribute:
                        attribute_name = f"{group} ({atr})"
                        if attribute_name not in self.cells[
                            (source_index, target_index)]:
                            self.cells[(source_index,
                                        target_index)][attribute_name] = 0
                        self.cells[(source_index, target_index
                                   )][attribute_name] += dependency.weight

    def to_dv8_string(self) -> str:
        out_dict = {
            "@schemaVersion":
                "1.0",
            "name":
                self.name,
            "variables":
                list(self.variables.keys()),
            "cells": [{
                "src": key[0],
                "dest": key[1],
                "values": {
                    name: val for name, val in value.items()
                }
            } for key, value in self.cells.items()]
        }

        return json.dumps(out_dict)


def architecture_model_to_DV8_clustering(
    project: str, architecture_model: ArchitectureModel
) -> str:
    out_dict: dict[str, tp.Any] = {
        "@schemaVersion": "1.0",
        "name": f"{project}_ArchitectureModel_Clustering",
    }
    groups: tp.Dict[str, dict[str, tp.Any]] = {}
    for module, locations in architecture_model.modules.items():
        group = {
            "@type":
                "group",
            "name":
                module,
            "nested": [{
                "@type": "item",
                "name": str.join("/",
                                 loc.file.split('/')[1:])
            } for loc in locations]
        }
        groups[module] = group
    for package, modules in architecture_model.packages.items():
        group = {
            "@type": "group",
            "name": package,
            "nested": [
                groups[module] for module in modules if module in groups
            ]
        }
        for module in modules:
            if module in groups:
                del groups[module]
        groups[package] = group
    out_dict["structure"] = [group for _, group in groups.items()]
    return json.dumps(out_dict, indent=4)


class DesignStructureMatrix(Table, table_name=None):

    dsm: InternalDSM

    def __init__(self, table_config: TableConfig, **kwargs: tp.Any):
        super().__init__(table_config, **kwargs)

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        return DSMEditorXML(
            self.dsm
        ).to_xml_string() if table_format == TableFormat.DSM else DV8DSM(
            self.dsm
        ).to_dv8_string()  #TODO integrate with table formats


class ArchitectureModelDSMTable(DesignStructureMatrix, table_name="DV8_DSM"):

    def __init__(
        self, table_config: tp.Any, dv8_matrix: tp.TextIO, project_name: str,
        **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)
        json_string = dv8_matrix.read()
        self.dsm = InternalDSM.from_dv8_json_string(json_string, project_name)
        self.dsm.apply_architecture_model()


class ArchitectureModelDV8Clustering(Table, table_name="DV8_Clust"):

    def __init__(
        self, table_config: tp.Any, project_name: str, **table_kwargs: tp.Any
    ) -> None:
        super().__init__(table_config, **table_kwargs)

        self.project_name = project_name

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        project = get_project_cls_by_name(self.project_name)
        provider = ArchitectureModelProvider.create_provider_for_project(
            project
        )
        if provider is None:
            raise ValueError(
                f"No architecture model found for project {self.project_name}"
            )
        return architecture_model_to_DV8_clustering(
            self.project_name, provider.get_architecture_model()
        )


class ArchitectureModelDSMTableGenerator(
    TableGenerator,
    generator_name="DV8_DSM",
    options=[
        make_cli_option(
            "-dv8",
            "--dv8-matrix",
            type=click.File("r"),
            required=True,
            metavar="dv8_matrix",
            help="The dv8 Matrix to convert."
        ),
        make_cli_option(
            "-p",
            "--project-name",
            type=str,
            required=True,
            metavar="project_name",
            help="The project name the dv8 matrix is for."
        )
    ]
):
    """Table generator for generating a Design Structure Matrix from a dv8
    matrix file."""

    def generate(self) -> tp.List[Table]:
        return [
            ArchitectureModelDSMTable(
                self.table_config, self.table_kwargs["dv8_matrix"],
                self.table_kwargs["project_name"]
            )
        ]


class ArchitectureModelDV8ClusterGenerator(
    TableGenerator,
    generator_name="DV8_Clx",
    options=[
        make_cli_option(
            "-p",
            "--project-name",
            type=str,
            required=True,
            metavar="project_name",
            help="The project name the dv8 matrix is for."
        )
    ]
):
    """Table generator for generating a Design Structure Matrix from a dv8
    matrix file."""

    def generate(self) -> tp.List[Table]:
        return [
            ArchitectureModelDV8Clustering(
                self.table_config, self.table_kwargs["project_name"]
            )
        ]
