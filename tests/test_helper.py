"""Small helper classes for testing."""

import typing as tp

import attr
import plumbum as pb
from benchbuild.source import Variant, BaseSource


@attr.s
class TestSource(BaseSource):
    test_versions: tp.List[str] = attr.ib()

    @property
    def default(self) -> Variant:
        return Variant(owner=self, version=self.test_versions[0])

    def version(self, target_dir: str, version: str) -> pb.LocalPath:
        return pb.local.path('.') / f'varats-test-{version}'

    def versions(self) -> tp.Iterable[Variant]:
        return [Variant(self, v) for v in self.test_versions]
