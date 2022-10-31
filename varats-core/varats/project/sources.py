"""Implements additional sources for projects."""

import typing as tp

import benchbuild as bb
import plumbum as pb
from benchbuild.source import Variant
from benchbuild.source.base import Revision

from varats.paper_mgmt.paper_config import get_paper_config
from varats.utils.git_util import ShortCommitHash


class FeatureSource(bb.source.FetchableSource):
    """Base for context aware test sources."""

    def version(self, target_dir: str, version: str) -> pb.LocalPath:
        print(f"{target_dir=} - {version=}")
        # raise NotImplementedError()
        return None

    def versions(self) -> tp.List[Variant]:
        raise NotImplementedError()

    def fetch(self) -> pb.LocalPath:
        return NotImplementedError()

    @property
    def default(self) -> Variant:
        raise NotImplementedError()

    @property
    def is_expandable(self) -> bool:
        return True

    def is_context_free(self) -> bool:
        return False

    def versions_with_context(self, ctx: Revision) -> tp.Sequence[Variant]:

        print(f"{ctx=}")
        print(f"{ctx.primary=}")

        cs = get_paper_config().get_case_studies(ctx.project_cls.NAME)[0]
        print(f"{cs=}")
        config_ids = cs.get_config_ids_for_revision(
            ShortCommitHash(ctx.primary.version)
        )
        print(f"{config_ids=}")

        return [Variant(self, str(config_id)) for config_id in config_ids]
