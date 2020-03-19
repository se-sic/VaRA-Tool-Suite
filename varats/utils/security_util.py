"""
Helper to search, retrieve and parse CVE's and CWE's.

Example:
    CVE.find_all_cve('vim', 'vim')
    CVE.find_cve('CVE-2019-20079')
    CWE.find_all_cwe()
"""

from datetime import datetime
import csv
import zipfile
import io
import time
import typing as tp
import requests
from packaging.version import Version, parse as version_parse, LegacyVersion
import requests_cache  # type: ignore
from tabulate import tabulate


class CVE:
    """
    CVE representation with the major fields. 

    Mainly a data object to store everything.
    Uses the API at https://cve.circl.lu/api/search/ to find entries.
    """

    def __init__(
        self, cve_id: str, score: float, published: datetime,
        vector: tp.FrozenSet[str], references: tp.FrozenSet[str], summary: str,
        vulnerable_versions: tp.FrozenSet[tp.Union[LegacyVersion, Version]]
    ) -> None:
        self.__cve_id: str = cve_id
        self.__score: float = score
        self.__published: datetime = published
        self.__vector: tp.FrozenSet[str] = vector
        self.__references: tp.FrozenSet[str] = references
        self.__summary: str = summary
        self.__vulnerable_versions: tp.FrozenSet[tp.Union[
            LegacyVersion, Version]] = vulnerable_versions

    @property
    def cve_id(self) -> str:
        """The CVE ID."""
        return self.__cve_id

    @property
    def score(self) -> float:
        """The score of this CVE."""
        return self.__score

    @property
    def published(self) -> datetime:
        """The date when this CVE was published."""
        return self.__published

    @property
    def vector(self) -> tp.FrozenSet[str]:
        """The CVE vector."""
        return self.__vector

    @property
    def references(self) -> tp.FrozenSet[str]:
        """A set of external references/urls."""
        return self.__references

    @property
    def summary(self) -> str:
        """The summary of the CVE."""
        return self.__summary

    @property
    def vulnerable_versions(
            self) -> tp.FrozenSet[tp.Union[LegacyVersion, Version]]:
        """The set of vulnerable version numbers."""
        return self.__vulnerable_versions

    @property
    def url(self) -> str:
        """The URL to the Mitre entry."""
        return f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={self.cve_id}"

    def __str__(self) -> str:
        return tabulate([
            ["ID", self.cve_id],
            ["Score", self.score],
            ["Published", self.published],
            ["Vector", '/'.join(self.vector)],
            ["URL", self.url],
            ["Summary", self.summary[:128]],
        ],
                        tablefmt="grid")

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CVE):
            return NotImplemented

        return self.cve_id == other.cve_id

    def __hash__(self) -> int:
        return hash(self.cve_id)


class CWE:
    """
    CWE representation with the major fields.

    Mainly a data object to store everything.
    """

    def __init__(self, cwe_id: str, name: str, description: str) -> None:
        self.__cwe_id: str = cwe_id
        self.__name: str = name
        self.__description: str = description

    @property
    def cwe_id(self) -> str:
        """The CWE ID."""
        return self.__cwe_id

    @property
    def name(self) -> str:
        """The name of this CWE."""
        return self.__name

    @property
    def description(self) -> str:
        """The CWE description."""
        return self.__description

    @property
    def url(self) -> str:
        """The URL to the Mitre entry."""
        id_num = self.cwe_id.split('-')[1]
        return f'https://cwe.mitre.org/data/definitions/{id_num}.html'

    def __str__(self) -> str:
        return tabulate([
            ["ID", self.cwe_id],
            ["Name", self.name[:128]],
            ["URL", self.url],
            ["Description", self.description[:128]],
        ],
                        tablefmt="grid")

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CWE):
            return NotImplemented

        return self.cwe_id == other.cwe_id

    def __hash__(self) -> int:
        return hash(self.cwe_id)


def find_all_cve(vendor: str, product: str) -> tp.FrozenSet[CVE]:
    """
    Find all CVE's for a given vendor and product combination.
    
    Args:
        vendor: vendor to search for
        product: product to search for

    Return:
        a set of :class:`CVE` objects.
    """
    if not vendor or not product:
        raise ValueError('Missing a vendor or product to search CVE\'s for!')
    response = requests.get(
        f'https://cve.circl.lu/api/search/{vendor}/{product}')
    # Sometimes the rate limit is hit so keep repeating
    while response.status_code == 429:
        time.sleep(3)
        response = requests.get(
            f'https://cve.circl.lu/api/search/{vendor}/{product}')
    if response.status_code != 200:
        raise ValueError(f'Could not retrieve CVE information '
                         f'(Code: {response.status_code})!')

    cve_list: tp.Set[CVE] = set()
    for entry in response.json()['results']:
        try:
            cve_list.add(
                CVE(cve_id=entry.get('id'),
                    score=entry.get('cvss'),
                    published=datetime.strptime(entry.get('Published'),
                                                '%Y-%m-%dT%H:%M:%S'),
                    vector=entry.get('cvss-vector', "").split('/'),
                    references=entry.get('references'),
                    summary=entry.get('summary'),
                    vulnerable_versions=frozenset([
                        version_parse(x.replace(':*', '').split(':')[-1])
                        for x in entry.get('vulnerable_configuration')
                    ])))
        except KeyError as error_msg:
            cve_id = entry.get('id')
            print(f'Error parsing {cve_id}: {error_msg}!')

    return frozenset(cve_list)


def find_cve(cve_id: str) -> CVE:
    """
    Find a CVE by its ID (CVE-YYYY-XXXXX).
    :param cve_id: CVE id to search for.
    :return: CVE object.
    """
    if not cve_id:
        raise ValueError('Missing a CVE ID!')
    response = requests.get(f'https://cve.circl.lu/api/cve/{cve_id}')
    # Sometimes the rate limit is hit so keep repeating
    while response.status_code == 429:
        time.sleep(3)
        response = requests.get(f'https://cve.circl.lu/api/cve/{cve_id}')
    if response.status_code != 200:
        raise ValueError(f'Could not retrieve CVE information '
                         f'(Code: {response.status_code})!')

    cve_data: tp.Dict[str, tp.Any] = response.json()
    if not cve_data:
        raise ValueError(f'Could not find CVE information for {cve_id}, '
                         f'maybe it is a wrong number?')
    return CVE(cve_id=cve_data.get('id', None),
               score=cve_data.get('cvss', None),
               published=datetime.strptime(cve_data.get('Published', None),
                                           '%Y-%m-%dT%H:%M:%S'),
               vector=frozenset(cve_data.get('cvss-vector', None).split('/')),
               references=cve_data.get('references', None),
               summary=cve_data.get('summary', None),
               vulnerable_versions=frozenset([
                   version_parse(x['title'].replace(':*', '').split(':')[-1])
                   for x in cve_data.get('vulnerable_configuration', None)
               ]))


def find_all_cwe() -> tp.FrozenSet[CWE]:
    """
    Create a set of all CWE's. The set with CWE numbers is downloaded from
    @https://cwe.mitre.org/data/downloads.html.
    :return: Set of CWE objects.
    """
    source_urls: tp.FrozenSet[str] = frozenset([
        'https://cwe.mitre.org/data/csv/699.csv.zip',
        'https://cwe.mitre.org/data/csv/1194.csv.zip',
        'https://cwe.mitre.org/data/csv/1000.csv.zip'
    ])

    cwe_list: tp.Set[CWE] = set()

    # Download each zip file, extract it and parse its entries
    for source_url in source_urls:
        response = requests.get(source_url)
        # Sometimes the rate limit is hit so keep repeating
        while response.status_code == 429:
            time.sleep(3)
            response = requests.get(source_url)
        if response.status_code != 200:
            raise ValueError(f'Could not retrieve CVE information '
                             f'(Code: {response.status_code})!')

        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        with zip_file.open(zip_file.namelist()[0], 'r') as csv_file:
            reader = csv.DictReader(io.TextIOWrapper(csv_file),
                                    delimiter=',',
                                    quotechar='"')
            for entry in reader:
                cwe_id = entry.get('CWE-ID')
                cwe_list.add(
                    CWE(cwe_id=f'CWE-{cwe_id}',
                        name=entry.get('Name', ''),
                        description=entry.get('Description', '')))

    return frozenset(cwe_list)


def find_cwe(cwe_id: str = '',
             cwe_name: str = '',
             cwe_description: str = '') -> CWE:
    """
    Find a CWE by its attributes (ID (CWE-XXX), name, description).
    :param cwe_id: ID of the CWE to search for.
    :param cwe_name: Name of the CWE to search for.
    :param cwe_description: Description of the CWE to search for.
    :return: CWE if one is found, otherwise raise a ValueError.
    """
    for cwe in CWE_LIST:
        if (cwe_id and cwe.cwe_id == cwe_id) or \
           (cwe_name and cwe.name == cwe_name) or \
           (cwe_description and cwe.description == cwe_description):
            return cwe
    raise ValueError(
        f'Could not find CWE ({cwe_id}, {cwe_name}, {cwe_description})!')


# Cache all requests to limit external requests for a week
requests_cache.install_cache('requests_cache', expire_after=604800)

# Since this list is static it might as well be declared here so it is
# ready to use
CWE_LIST: tp.FrozenSet[CWE] = find_all_cwe()
