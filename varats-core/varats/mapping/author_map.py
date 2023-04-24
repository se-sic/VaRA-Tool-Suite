"""Author map module."""

import logging
import re
import typing as tp
from functools import reduce
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir
from plumbum import local

LOG = logging.getLogger(__name__)


class AmbiguousAuthor(Exception):
    """Raised if an ambiguous author is encountered."""


name_regex = re.compile("\s*\d+\t(.*) <(.*)>")


class Author():
    """Representation of one author."""

    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.__names = [name]
        self.mail = email
        self.__mail_addresses = [email]

    def __eq__(self, other):
        if isinstance(other, Author):
            return self.id == other.id
        return False

    def __str__(self):
        return f"{self.id} {self.name} <{self.mail}>"

    def __repr__(self):
        return f"{self.id} {self.name} <{self.mail}>"

    @property
    def names(self):
        return self.__names

    @property
    def mail_addresses(self):
        return self.__mail_addresses

    def merge(self, other: ['Author']) -> ['Author']:
        if other.id < self.id:
            other.names.append(other.names)
            other.mail_addresses.append(other.mail_addresses)
            return other
        else:
            self.names.append(other.names)
            self.mail_addresses.append(other.mail_addresses)
            return self


class AuthorMap():
    """Provides a mapping of an author to all combinations of author name to
    mail address."""

    def __init__(self):
        self.current_id = 0
        self.mail_dict: tp.Dict[str, Author] = {}
        self.name_dict: tp.Dict[str, Author] = {}
        self.authors: tp.List[Author] = []

    def get_author_by_name(self, name: str):
        return self.name_dict[name]

    def get_author_by_email(self, email: str):
        return self.mail_dict[email]

    def get_authors(self):
        return self.authors

    def get_author(self, name: str, mail: str):
        if self.mail_dict[mail] == self.name_dict[name]:
            return self.name_dict[name]
        else:
            raise AmbiguousAuthor

    def new_author_id(self):
        new_id = self.current_id
        self.current_id += 1
        return new_id

    def add_entry(self, name: str, mail: str):
        ambiguos_authors = [
            author for author in self.authors
            if name in author.names or mail in author.mail_addresses
        ]
        if not ambiguos_authors:
            self.authors.append(Author(self.new_author_id(), name, mail))
        if len(ambiguos_authors) > 1:
            reduce(lambda accu, author: accu.merge(author), ambiguos_authors)

    def gen_lookup_dicts(self):
        for author in self.authors:
            for mail in author.mail_addresses:
                self.mail_dict[mail] = author
            for name in author.names:
                self.name_dict[name] = author

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
        author_map.gen_lookup_dicts()
        return author_map


if __name__ == '__main__':
    a = generate_author_map(
        "/home/simon/Documents/Vara/vara-ts/VaRA-Tool-Suite"
    )
    print(a)
