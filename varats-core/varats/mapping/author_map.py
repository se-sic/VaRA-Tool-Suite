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


class Author():
    """Representation of one author."""

    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.mail = email

    def __eq__(self, other):
        if isinstance(other, Author):
            return self.id == other.id
        return False

    def __str__(self):
        return f"{self.id} {self.name} <{self.mail}>"

    def __repr__(self):
        return f"{self.id} {self.name} <{self.mail}>"

    def merge_if_equal(self, other):
        if isinstance(other, Author):
            if self.__eq__(self, other):
                print("hi")


class AuthorMap():
    """Provides a mapping of an author to all combinations of author name to
    mail address."""

    def __init__(self):
        self.current_id = 0
        self.mail_dict: tp.Dict[str, Author] = {}
        self.name_dict: tp.Dict[str, Author] = {}

    def get_author_by_name(self, name: str):
        return self.name_dict[name]

    def get_auhtor_by_email(self, email: str):
        return self.mail_dict[email]

    def get_author(self, name: str, mail: str):
        if self.mail_dict[mail] == self.name_dict[name]:
            return self.name_dict[name]
        else:
            raise AmbiguousAuthor

    def add_entry(self, name: str, mail: str):
        author_by_name = self.name_dict.get(name, None)
        author_by_mail = self.mail_dict.get(mail, None)
        if author_by_name:
            if author_by_mail:
                if author_by_name != author_by_mail:
                    self.name_dict[name] = author_by_mail
                    self.mail_dict[author_by_name.mail] = author_by_mail
                else:
                    return
            else:
                self.mail_dict[mail] = author_by_name
        elif author_by_mail:
            self.name_dict[name] = author_by_mail
        else:
            new_author = Author(self.current_id, name, mail)
            self.current_id += 1
            self.name_dict[name] = new_author
            self.mail_dict[mail] = new_author

    def __repr__(self):
        return f"{self.name_dict} \n {self.mail_dict}"


def generate_author_map(path: Path) -> AuthorMap:
    """Generate an AuthorMap for the repository at the given path."""
    with local.cwd(path):
        author_map = AuthorMap()
        test = git["shortlog", "-sne", "--all"]().strip().split("\n")
        for line in test:
            match = name_regex.match(line)
            if not match:
                LOG.info("Invalid author format.")
                continue
            name = match.group(1)
            email = match.group(2)
            author_map.add_entry(name, email)

        return author_map


if __name__ == '__main__':
    a = generate_author_map(
        "/home/simon/Documents/Vara/vara-ts/VaRA-Tool-Suite"
    )
    print(a)
