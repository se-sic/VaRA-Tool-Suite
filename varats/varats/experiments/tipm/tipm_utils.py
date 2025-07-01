from varats.project.varats_project import VProject


def select_binaries(project: VProject):
    if project.name == "FastDownward":
        return [bi for bi in project.binaries if bi.name == "downward"][0]

    return project.binaries[0]
