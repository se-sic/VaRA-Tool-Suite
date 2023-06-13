"""Author map module."""

import logging
import re
import typing as tp
from functools import reduce
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir

from varats.utils.git_util import __get_git_path_arg

LOG = logging.getLogger(__name__)

NAME_REGEX = re.compile("\s*\d+\t(.*) <(.*)>")


class Author():
    """Representation of one author."""

    def __init__(self, id: int, name: str, email: str) -> None:
        self.id = id
        self.name = name
        self.__names = {name}
        self.mail = email
        self.__mail_addresses = {email}

    def __eq__(self, other) -> bool:
        if isinstance(other, Author):
            return self.id == other.id
        return False

    def __str__(self) -> str:
        return f"{self.id} {self.name} <{self.mail}>"

    def __repr__(self) -> str:
        return f"{self.id} {self.name} <{self.mail}>; {self.names},{self.mail_addresses}"

    @property
    def names(self) -> tp.Set[str]:
        return self.__names

    @property
    def mail_addresses(self) -> tp.Set[str]:
        return self.__mail_addresses

    def add_data(self, name: str, mail: str) -> None:
        if not name in self.names:
            self.names.add(name)
        if not mail in self.mail:
            self.mail_addresses.add(mail)

    def merge(self, other: 'Author') -> 'Author':
        if other.id < self.id:
            other.names.union(self.names)
            other.mail_addresses.union(self.mail_addresses)
            return other

        self.names.union(other.names)
        self.mail_addresses.union(other.mail_addresses)
        return self


class AuthorMap():
    """Provides a mapping of an author to all combinations of author name to
    mail address."""

    def __init__(self) -> None:
        self._look_up_invalid = True
        self.current_id = 0
        self.mail_dict: tp.Dict[str, Author] = {}
        self.name_dict: tp.Dict[str, Author] = {}
        self.__authors: tp.List[Author] = []

    def get_author_by_name(self, name: str) -> tp.Optional[Author]:
        if self._look_up_invalid:
            self._gen_lookup_dicts()
        return self.name_dict.get(name, None)

    def get_author_by_email(self, email: str) -> tp.Optional[Author]:
        if self._look_up_invalid:
            self._gen_lookup_dicts()
        return self.mail_dict.get(email, None)

    @property
    def authors(self) -> tp.List[Author]:
        return self.__authors

    def get_author(self, name: str, mail: str) -> tp.Optional[Author]:
        """
        Get an author by name and mail.

        Returns None if no author or multiple authors were found matching the
        combination of name and mail-address.
        """
        if self._look_up_invalid:
            self._gen_lookup_dicts()

        mail_author = self.mail_dict.get(mail, None)
        if mail_author == (name_author := self.name_dict.get(name, None)):
            return name_author

        return None

    def new_author_id(self) -> int:
        """Get a unique id for an author."""
        new_id = self.current_id
        self.current_id += 1
        return new_id

    def add_entry(self, name: str, mail: str) -> None:
        """Add authors to the map and invalidate look up dicts."""
        ambiguos_authors = [
            author for author in self.__authors
            if name in author.names or mail in author.mail_addresses
        ]

        if not ambiguos_authors:
            self.__authors.append(Author(self.new_author_id(), name, mail))
            self.look_up_invalid = True
            return

        if len(ambiguos_authors) > 1:
            existing_author = reduce(
                lambda accu, author: accu.merge(author), ambiguos_authors
            )
        else:
            existing_author = ambiguos_authors[0]

        existing_author.add_data(name, mail)
        self._look_up_invalid = True

    def _gen_lookup_dicts(self) -> None:
        """Generate the dicts for name and mail lookups."""
        for author in self.__authors:
            for mail in author.mail_addresses:
                self.mail_dict[mail] = author
            for name in author.names:
                self.name_dict[name] = author

        self._look_up_invalid = False

    def __repr__(self) -> str:
        return f"{self.name_dict} \n {self.mail_dict}"


def generate_author_map(path: Path) -> AuthorMap:
    """Generate an AuthorMap for the repository at the given path."""
    author_map = AuthorMap()
    test = git[__get_git_path_arg(path), "shortlog", "-sne",
               "--all"]().strip().split("\n")
    for line in test:
        match = NAME_REGEX.match(line)
        if not match:
            LOG.warning(f"Invalid author format. {line}")
            continue
        name = match.group(1)
        email = match.group(2)
        author_map.add_entry(name, email)

    return author_map
