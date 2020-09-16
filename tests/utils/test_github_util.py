"""Test github utilities."""
import typing as tp
import unittest

from github import Github, PaginatedList
from github.GithubObject import GithubObject, NonCompletableGithubObject
from github.PaginatedList import PaginatedListBase

from tests.test_utils import replace_config
from varats.utils.github_util import (
    get_cached_github_object,
    _get_cached_pygithub_object,
    _get_cached_pygithub_object_list,
    get_cached_github_object_list,
)


class MockGithubObject(NonCompletableGithubObject):

    def __init__(
        self,
        requester=None,
        headers=None,
        attributes=None,
        completed=True
    ) -> None:
        super().__init__(requester, headers, attributes, completed)

    def _initAttributes(self) -> None:
        pass

    def _useAttributes(self, attributes: tp.Any) -> None:
        pass


class MockPaginatedList(PaginatedListBase):

    def __init__(self, items: tp.List[GithubObject]) -> None:
        super().__init__()
        self.__items = items
        super()._grow()

    def _couldGrow(self):
        return False

    def _fetchNextPage(self):
        return self.__items


class TestGithubObjectCache(unittest.TestCase):
    """Test the GithubObjectCache."""

    def test_cache_single_object(self):
        """Test caching a single GithubObject."""
        demo_github_object: GithubObject = MockGithubObject()

        def load_github_object(github: Github):
            return demo_github_object

        # with tempfile.TemporaryDirectory() as tmpdir:
        with replace_config() as config:
            github_object = get_cached_github_object(
                "demo_github_object", load_github_object
            )
            self.assertEqual(demo_github_object, github_object)
            # check if object is cached
            self.assertIsNotNone(
                _get_cached_pygithub_object("demo_github_object")
            )

    def test_cache_paginated_list(self):
        """Test caching a PaginatedList of GithubObjects."""
        demo_github_object1: GithubObject = MockGithubObject()
        demo_github_object2: GithubObject = MockGithubObject()
        demo_github_object3: GithubObject = MockGithubObject()
        demo_python_list = [
            demo_github_object1, demo_github_object2, demo_github_object3
        ]
        demo_paginated_list = MockPaginatedList(demo_python_list)

        def load_github_list(github: Github) -> PaginatedList:
            return demo_paginated_list

        # with tempfile.TemporaryDirectory() as tmpdir:
        with replace_config() as config:
            github_object_list = get_cached_github_object_list(
                "demo_github_list", load_github_list
            )
            self.assertEqual(demo_python_list, github_object_list)
            # check if object is cached
            cached_list = _get_cached_pygithub_object_list("demo_github_list")
            self.assertIsNotNone(cached_list)
            self.assertEqual(3, len(cached_list))
