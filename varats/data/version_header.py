"""
This module provides a reusable version header for all yaml reports generated
by VaRA. The version header specifies the type of the following yaml file and
the version.
"""


class WrongYamlFileType(Exception):
    """
    Exception raised for miss matches of the file type.
    """

    def __init__(self, expected_type, actual_type):
        super().__init__("Expected FileType: '{}' but got '{}'".format(
            expected_type, actual_type))


class WrongYamlFileVersion(Exception):
    """
    Exception raised for miss matches of the file version.
    """

    def __init__(self, expected_version, actual_version):
        super().__init__("Expected minimal version: '{}' but got version '{}'".
                         format(expected_version, actual_version))


class NoVersionHeader(Exception):
    """
    Exception raised for wrong yaml documents.
    """

    def __init__(self):
        super().__init__("No VersionHeader found, got wrong yaml document.")


class VersionHeader(object):
    """
    VersionHeader describing the type and version of the following yaml file.
    """

    def __init__(self, yaml_doc):
        if 'DocType' not in yaml_doc or 'Version' not in yaml_doc:
            raise NoVersionHeader()

        self.__doc_type = yaml_doc['DocType']
        self.__version = int(yaml_doc['Version'])

    @property
    def doc_type(self) -> str:
        """Type of the following yaml file."""
        return self.__doc_type

    def is_type(self, type_name) -> bool:
        """Checks if the type of the following yaml file is type_name."""
        return type_name == self.doc_type

    def raise_if_not_type(self, type_name):
        """
        Checks if the type of the following yaml file is type_name,
        otherwise, raises an exception.
        """
        if not self.is_type(type_name):
            raise WrongYamlFileType(type_name, self.doc_type)

    @property
    def version(self) -> int:
        """Document version number."""
        return self.__version

    def raise_if_version_is_less_than(self, version_bound):
        """
        Checks if the current version is equal or bigger that version_bound,
        otherwise, raises an exception.
        """
        if self.version < version_bound:
            raise WrongYamlFileVersion(version_bound, self.version)
