import attr
import benchbuild.utils.actions as actions

from benchbuild.settings import CFG
from benchbuild.utils.cmd import cp
from benchbuild.utils.path import path_to_list, list_to_path
from plumbum import local
from os import getenv

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
            project.BIN_NAME

        with local.cwd(local.path(str(CFG["vara"]["result"]))):
            env = CFG["env"].value
            path = path_to_list(getenv("PATH", ""))
            path.extend(env.get("PATH", []))

            extract_bc = local["extract-bc"]
            extract_bc = extract_bc.with_env(PATH=list_to_path(path))
            extract_bc(project_src)

            cp(local.path(project_src) + ".bc", local.path() /
               project.name + ".bc")
