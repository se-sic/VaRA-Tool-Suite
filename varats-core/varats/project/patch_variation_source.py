import typing as tp

import benchbuild as bb
import plumbum as pb
from benchbuild.source import Variant, Revision

from varats.base.configuration import PatchVariationConfiguration
from varats.paper.paper_config import get_paper_config
from varats.utils.config import load_configuration_map_for_case_study


def get_current_variation_id(project: 'VProject') -> tp.Optional[int]:
    """
    Get, if available, the current variation id of project. Should the project
    be not variation specific ``None`` is returned.

    Args:
        project: to extract the variation id from


    Returns:
        variation_id if available for the given project
    """
    if project.active_revision.has_variant(PatchVariationSource.LOCAL_KEY):
        return int(
            project.active_revision.variant_by_name(
                PatchVariationSource.LOCAL_KEY
            ).version
        )

    return None


class PatchVariationSource(bb.source.FetchableSource):  # type: ignore
    """Feature source that automatically enumerates all patch variations."""

    LOCAL_KEY = "patch_variation_info"

    def __init__(self) -> None:
        super().__init__(local=self.LOCAL_KEY, remote={"fv_1": "dummy_value"})

    def version(self, target_dir: str, version: str) -> pb.LocalPath:
        return pb.LocalPath('.')

    def versions(self) -> tp.List[Variant]:
        raise NotImplementedError()

    def fetch(self) -> pb.LocalPath:
        raise NotImplementedError()

    @property
    def default(self) -> Variant:
        raise NotImplementedError()

    @property
    def is_expandable(self) -> bool:
        return True

    def is_context_free(self) -> bool:
        return False

    def versions_with_context(self, ctx: Revision) -> tp.Sequence[Variant]:
        """Computes the list of variants for given revision, multiplex with the
        config ids that should be explored.."""
        paper_config = get_paper_config()
        case_study = paper_config.get_case_studies(ctx.project_cls.NAME)[0]

        config_map = load_configuration_map_for_case_study(
            paper_config, case_study, PatchVariationConfiguration
        )

        config_ids = config_map.ids()

        return [Variant(self, str(config_id)) for config_id in config_ids]
