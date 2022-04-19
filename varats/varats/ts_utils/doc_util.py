"""Utility module to generate sphinx documentation for varats."""
import typing as tp
from pathlib import Path

import benchbuild as bb
import pandas
import tabulate as tb

from varats.project.project_util import get_loaded_vara_projects
from varats.tools.research_tools.vara import VaRA


def _strip_python_class_decorations(raw_class_string: str) -> str:
    """
    >>> _strip_python_class_decorations( \
        "<class 'varats.projects.c_projects.file.File'>")
    'varats.projects.c_projects.file.File'

    >>> _strip_python_class_decorations( \
        "<class 'varats.projects.cpp_projects.doxygen.Doxygen'>")
    'varats.projects.cpp_projects.doxygen.Doxygen'
    """
    return raw_class_string[8:-2]


def _insert_class_reference_to_project(
    project_type: tp.Type[bb.Project]
) -> str:
    """
    >>> from varats.projects.test_projects.basic_tests import BasicTests
    >>> _insert_class_reference_to_project(str(BasicTests))
    ':class:`~varats.projects.test_projects.basic_tests.BasicTests`'
    """
    return f":class:`~{_strip_python_class_decorations(str(project_type))}`"


def generate_project_overview_table_file(output_file: Path) -> None:
    """
    Saves the projects overview table to a file.

    Args:
        output_file: to store the table in
    """

    with open(output_file, "w") as inc_file:
        inc_file.write(generate_project_overview_table())


def generate_project_overview_table() -> str:
    """
    Generates an overview table that shows all project information for vara
    projects.

    Returns: overview table
    """

    df = pandas.DataFrame(columns=["Project", "Group", "Domain", "Main Source"])

    for project_type in get_loaded_vara_projects():
        df = df.append(
            pandas.DataFrame({
                "Project": _insert_class_reference_to_project(project_type),
                "Group": project_type.GROUP,
                "Domain": project_type.DOMAIN,
                "Main Source": project_type.SOURCE[0].remote
            },
                             index=[0]),
            ignore_index=True
        )

    df.sort_values(by=['Group', 'Domain', 'Project'], inplace=True)

    return str(
        tb.tabulate(df, headers=df.keys(), tablefmt="grid", showindex=False)
    )


def generate_projects_autoclass_files(output_folder: Path) -> None:
    """Generate all project-group autoclass files."""
    for project_group in ('c_projects', 'cpp_projects', 'test_projects'):
        with open(
            output_folder / f"Autoclass_{project_group}.inc", "w"
        ) as inc_file:
            inc_file.write(
                generate_project_groups_autoclass_directives(project_group)
            )


def generate_project_groups_autoclass_directives(project_group: str) -> str:
    """
    Generates a list of autoclass directives for all projects in a project
    group.

    Args:
        project_group: group to generate the autoclass directives for

    Returns: string with all autoclass directives
    """
    autoclass_refs_for_group = ""
    for project_type in get_loaded_vara_projects():
        if project_type.GROUP != project_group:
            continue

        autoclass_refs_for_group += ".. autoclass:: " + \
            f"{_strip_python_class_decorations(str(project_type))}\n"

    return autoclass_refs_for_group


def generate_vara_install_requirements(output_folder: Path) -> None:
    """Generates dependency install commands for vara."""
    with open(output_folder / "vara_install_requirements.inc", "w") as req_file:
        vara_deps = VaRA.get_dependencies()
        for distro in vara_deps.distros:
            distro_name = str(distro)
            if distro_name == "debian":
                distro_name += "/ubuntu"

            req_file.write(
                f"""For {distro_name}:

.. code-block:: console

    sudo {vara_deps.get_install_command(distro)}

"""
            )
