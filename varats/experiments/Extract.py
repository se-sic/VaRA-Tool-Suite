import attr
from plumbum import local

import benchbuild.utils.actions as actions
from benchbuild.utils.cmd import extract_bc


@attr.s
class Extract(actions.Step):
    NAME = "EXTRACT"
    DESCRIPTION = "Extract bitcode out of the execution file."

    action_fn = attr.ib(default=__evaluate_extraction, repr=False)


    def __evaluate_extraction(self):
        """
        This step extracts the bitcode of the executable of the project
        into one file.
        """
        project = self.obj
        project_src = local.path(project.builddir) / project.src_dir
        with local.cwd(project_src):
            extract_bc(project.name)
