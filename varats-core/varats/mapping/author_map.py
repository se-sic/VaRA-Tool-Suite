"""Author map module."""

import logging
import re
import typing as tp
from collections.abc import ItemsView
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir
from plumbum import local
from pygtrie import CharTrie

from varats.project.project_util import (
    get_local_project_git_path,
    get_primary_project_source,
)
from varats.utils.git_util import (
    get_current_branch,
    FullCommitHash,
    ShortCommitHash,
)

LOG = logging.getLogger(__name__)


class AmbiguousAuthor(Exception):
    """Raised if an ambiguous author is encountered."""


name_regex = re.compile("\s*\d+\t(.*) <(.*)>")


def generate_Author_List(path):
    with local.cwd(path):
        author_list: tp.List[Author] = []
        test = git["shortlog", "-sne", "--all"]().strip().split("\n")
        for line in test:
            match = name_regex.match(line)
            if not match:
                LOG.info("Invalid author format.")
                continue
            name = match.group(1)
            email = match.group(2)
            id = name + email
            author = Author(id, name, email)
            author_list.append(author)

        return author_list


class AuthorMap():
    """Provides a mapping of an author to all combinations of author name to
    mail address."""


class Author():
    """Representation of one author."""

    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.mail = email

    def __eq__(self, other):
        if isinstance(other, Author):
            return self.id == other.id
        return False

    def merge_if_equal(self, other):
        if isinstance(other, Author):
            if self.__eq__(self, other):
                print("hi")


if __name__ == '__main__':
    a = generate_Author_List("/local/storage/hechtl/Vara/VaRA-Tool-Suite")
    print("hi")
