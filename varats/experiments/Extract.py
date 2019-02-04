import attr
import benchbuild.utils.actions as actions

from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp
from plumbum import local

CFG["vara"] = {
    "outfile": {
        "default": "",
        "desc": "Path to store results of VaRA CFR analysis."
    },
    "result": {
        "default": "",
        "desc": "Path to store already annotated projects."
    }
}


@attr.s
class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

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

        with local.cwd(local.path(str(CFG["vara"]["result"]))):
            extract_bc(project_src)
            cp(local.path(project_src) + ".bc", local.path() /
               project.name + "-" + project.version + ".bc")
