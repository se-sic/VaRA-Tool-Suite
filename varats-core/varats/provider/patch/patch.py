import os
from pathlib import Path
import typing as tp
import xml.etree.ElementTree as ET

from benchbuild.utils.revision_ranges import _get_all_revisions_between, _get_git_for_path, RevisionRange, \
    SingleRevision

from varats.utils.git_util import CommitHash, ShortCommitHash


class Patch:
    """A class for storing a single project-specific Patch"""

    def __init__(self, project: str, shortname: str, description: str, path: Path,
                 valid_revisions: tp.Optional[tp.Set[CommitHash]] = None
                 , invalid_revisions: tp.Optional[tp.Set[CommitHash]] = None):
        self.project: str = project
        self.shortname: str = shortname
        self.description: str = description
        self.path: Path = path
        self.valid_revisions: tp.Set[CommitHash] = valid_revisions
        self.invalid_revisions: tp.Set[CommitHash] = invalid_revisions


class ProjectPatchesConfiguration:
    """A class storing a set of patches specific to a project"""

    def __init__(self, project_name: str, repository: str, patches: tp.List[Patch]):
        self.project_name: str = project_name
        self.repository: str = repository
        self.patches: tp.List[Patch] = patches

    def get_patches_for_revision(self, revision: CommitHash):
        # This could be more concise with some nested list comprehensions
        # But it would make it harder to understand
        valid_patches: tp.Set[Patch] = set()

        for patch in self.patches:
            add_patch = True
            if patch.valid_revisions and revision not in patch.valid_revisions:
                add_patch = False

            if patch.invalid_revisions and revision in patch.invalid_revisions:
                add_patch = False

            if add_patch:
                valid_patches.add(patch)

    @staticmethod
    def from_xml(xml_path: Path):
        project_name: str = Path(os.path.abspath(xml_path)).parts[-2]
        tree = ET.parse(xml_path)
        root = tree.getroot()

        if len(root.findall("repository")) != 1:
            # TODO: Proper error handling
            raise RuntimeError("Only one repository allowed")

        repository = root.findtext("repository")

        repo_git = _get_git_for_path(repository)
        patch_list: tp.List[Patch] = []

        def parse_revisions(revisions_tag: ET.Element) -> tp.Set[CommitHash]:
            res: tp.Set[CommitHash] = set()

            for revision_tag in revisions_tag.findall("single_revision"):
                res.add(ShortCommitHash(revision_tag.text))

            for revision_range_tag in revisions_tag.findall("revision_range"):
                start_tag = revision_range_tag.find("start")
                end_tag = revision_range_tag.find("end")

                res.update(
                    {ShortCommitHash(h) for h in _get_all_revisions_between(start_tag.text, end_tag.text, repo_git)})

            return res

        # We explicitly ignore further validity checking of the XML at that point
        # As for now, this is already done by a CI Job in the vara-project-patches
        # repository
        for patch in root.findall("patch"):
            shortname = patch.findtext("shortname")
            description = patch.findtext("description")
            path = Path(patch.findtext("path"))

            include_revisions: tp.Set[CommitHash] = set()

            include_revs_tag = patch.find("include_revisions")

            if include_revs_tag:
                include_revisions = parse_revisions(include_revs_tag)
            else:
                revs_list = repo_git('log', '--pretty="%H"', '--first-parent').strip().split()

            include_revisions.update([ShortCommitHash(rev) for rev in revs_list])

            exclude_revs_tag = patch.find("exclude_revisions")

            if exclude_revs_tag:
                include_revisions.difference_update(parse_revisions(exclude_revs_tag))

            patch_list.append(Patch(project_name, shortname, description, path, include_revisions))

        return ProjectPatchesConfiguration(project_name, repository, patch_list)
