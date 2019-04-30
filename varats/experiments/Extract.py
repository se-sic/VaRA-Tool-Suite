import attr
import benchbuild.utils.actions as actions

from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp, mkdir
from plumbum import local

CFG["vara"] = {
    "outfile": {
        "default": "",
        "desc": "Path to store results of VaRA CFR analysis."
    },
    "result": {
        "default": "",
        "desc": "Path to store already annotated projects."
    },
}


@attr.s
class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    BC_CACHE_FOLDER_TEMPLATE = "{cache_dir}/{project_name}/"
    BC_FILE_TEMPLATE = "{project_name}-{project_version}.bc"

    def __call__(self):
        """
        This step extracts the bitcode of the executable of the project
        into one file.
        """
        if not self.obj:
            return
        project = self.obj
        project_src = local.path(project.builddir) / project.SRC_FILE /\
            project.name

        bc_cache_folder = self.BC_CACHE_FOLDER_TEMPLATE.format(
            cache_dir=str(CFG["vara"]["result"]),
            project_name=str(project.name))
        mkdir("-p", local.path() / bc_cache_folder)

        bc_cache_file = bc_cache_folder + self.BC_FILE_TEMPLATE.format(
            project_name=str(project.name),
            project_version=str(project.version))

        extract_bc(project_src)
        cp(local.path(project_src) + ".bc", local.path() / bc_cache_file)
