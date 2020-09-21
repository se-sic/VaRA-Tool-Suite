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


class DummyGithubObject(NonCompletableGithubObject):
    """Dummy GithubObject class."""

    # pylint: disable=invalid-name
    def _initAttributes(self) -> None:
        pass

    # pylint: disable=invalid-name
    def _useAttributes(self, attributes: tp.Any) -> None:
        pass


def create_dummy_github_object() -> GithubObject:
    return DummyGithubObject(None, {}, None, True)


class DummyPaginatedList(PaginatedListBase):
    """Dummy PaginatedList class."""

    def __init__(self, items: tp.List[GithubObject]) -> None:
        super().__init__()
        self.__items = items
        super()._grow()

    # pylint: disable=invalid-name,no-self-use
    def _couldGrow(self):
        return False

    # pylint: disable=invalid-name
    def _fetchNextPage(self):
        return self.__items


class TestGithubObjectCache(unittest.TestCase):
    """Test the GithubObjectCache."""

    def test_cache_single_object(self):
        """Test caching a single GithubObject."""
        demo_github_object: GithubObject = create_dummy_github_object()

        # pylint: disable=unused-argument
        def load_github_object(github: Github):
            return demo_github_object

        with replace_config():
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
        demo_github_object1: GithubObject = create_dummy_github_object()
        demo_github_object2: GithubObject = create_dummy_github_object()
        demo_github_object3: GithubObject = create_dummy_github_object()
        demo_python_list = [
            demo_github_object1, demo_github_object2, demo_github_object3
        ]
        demo_paginated_list = DummyPaginatedList(demo_python_list)

        # pylint: disable=unused-argument
        def load_github_list(github: Github) -> PaginatedList:
            return demo_paginated_list

        with replace_config():
            github_object_list = get_cached_github_object_list(
                "demo_github_list", load_github_list
            )
            self.assertEqual(demo_python_list, github_object_list)
            # check if object is cached
            cached_list = _get_cached_pygithub_object_list("demo_github_list")
            self.assertIsNotNone(cached_list)
            self.assertEqual(3, len(cached_list))
