import textwrap

import attr
import benchbuild.utils.actions as actions
from benchbuild.settings import CFG
from benchbuild.utils.cmd import extract_bc, cp
from plumbum import local


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
        project_src = local.path(
            project.builddir) / project.src_dir / project.name

        with local.cwd(CFG["vara"]["result"].value()):
            extract_bc(project_src)
            cp(local.path(project_src) + ".bc", local.path(
                str(CFG["vara"]["result"].value())) / project.name + ".bc")
