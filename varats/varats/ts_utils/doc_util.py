"""Utility module to generate sphinx documentation for varats."""
import typing as tp
from pathlib import Path

import benchbuild as bb
import pandas
import tabulate as tb

from varats.project.project_util import get_loaded_vara_projects
from varats.provider.feature.feature_model_provider import FeatureModelProvider
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


def construct_feature_model_link(project_type: tp.Type[bb.Project]) -> str:
    """
    Construct a link to the feature-model folder of our online feature model
    collection.

    Args:
        project_type: type of the project to link the feature model for
    """
    fm_provider = FeatureModelProvider.get_provider_for_project(project_type)
    fm_doc_link = ""

    if (
        feature_model :=
        fm_provider.get_feature_model_path("currently_not_needed")
    ):
        sanitized_repo = FeatureModelProvider.fm_repository.replace('.git', '')
        fm_sub_path = feature_model.parent.name
        fm_doc_link = f"`Model <{sanitized_repo}/tree/master/{fm_sub_path}>`__"

    return fm_doc_link


def generate_project_overview_table() -> str:
    """
    Generates an overview table that shows all project information for vara
    projects.

    Returns: overview table
    """

    dfs = [
        pandas.DataFrame(
            columns=[
                "Project", "Group", "Domain", "FeatureModel", "Main Source"
            ]
        )
    ]

    for project_type in get_loaded_vara_projects():
        dfs.append(
            pandas.DataFrame({
                "Project":
                    _insert_class_reference_to_project(project_type),
                "Group":
                    project_type.GROUP,
                "Domain":
                    project_type.DOMAIN,
                "FeatureModel":
                    construct_feature_model_link(project_type),
                "Main Source":
                    project_type.SOURCE[0].remote
                    if project_type.SOURCE else None
            },
                             index=[0]),
        )

    df = pandas.concat(dfs, ignore_index=True)
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
