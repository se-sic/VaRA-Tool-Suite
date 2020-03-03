#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
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
from packaging.version import Version, parse as version_parse
import requests_cache


class CVE:
    """
    CVE representation with the major fields. Mainly a data object to store everything.
    """

    def __init__(self,
                 cve_id: str,
                 score: float,
                 published: datetime,
                 vector: tp.FrozenSet[str],
                 references: tp.FrozenSet[str],
                 summary: str,
                 vulnerable_versions: tp.FrozenSet[Version]) -> None:
        self.__cve_id = cve_id
        self.__score = score
        self.__published = published
        self.__vector = vector
        self.__references = references
        self.__summary = summary
        self.__vulnerable_versions = vulnerable_versions

    @property
    def cve_id(self) -> str:
        """ Return CVE ID. """
        return self.__cve_id

    @property
    def score(self) -> float:
        """ Return the score of this CVE. """
        return self.__score

    @property
    def published(self) -> datetime:
        """ Return the date when this CVE was published. """
        return self.__published

    @property
    def vector(self) -> tp.FrozenSet[str]:
        """ Return the CVE vector. """
        return self.__vector

    @property
    def references(self) -> tp.FrozenSet[str]:
        """ Return a set of external references/urls. """
        return self.__references

    @property
    def summary(self) -> str:
        """ Return the summary. """
        return self.__summary

    @property
    def vulnerable_versions(self) -> tp.FrozenSet[Version]:
        """ Return set of vulnerable version numbers. """
        return self.__vulnerable_versions

    def __str__(self) -> str:
        return self.__cve_id

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def find_all_cve(vendor: str, product: str) -> tp.FrozenSet:
        """
        Find all CVE's for a given vendor and product combination.
        :param vendor: Vendor to search for.
        :param product: Product to search for.
        :return: Set of @CVE objects.
        """
        if not vendor or not product:
            raise ValueError('Missing a vendor or product to search CVE\'s for!')
        response = requests.get(f'https://cve.circl.lu/api/search/{vendor}/{product}')
        while response.status_code == 429:
            time.sleep(3)
            response = requests.get(f'https://cve.circl.lu/api/search/{vendor}/{product}')
        if response.status_code != 200:
            raise ValueError(f'Could not retrieve CVE information (Code: {response.status_code})!')

        cve_list = set()
        for entry in response.json()['results']:
            try:
                cve_list.add(CVE(
                    cve_id=entry.get('id'),
                    score=entry.get('cvss'),
                    published=datetime.strptime(entry.get('Published'), '%Y-%m-%dT%H:%M:%S'),
                    vector=entry.get('cvss-vector', "").split('/'),
                    references=entry.get('references'),
                    summary=entry.get('summary'),
                    vulnerable_versions=frozenset([
                        version_parse(x.replace(':*', '').split(':')[-1])
                        for x in entry.get('vulnerable_configuration')
                    ])
                ))
            except KeyError as error_msg:
                cve_id = entry.get('id')
                print(f'Error parsing {cve_id}: {error_msg}!')

        return frozenset(cve_list)

    @staticmethod
    def find_cve(cve_id: str):
        """
        Find a CVE by its ID (CVE-YYYY-XXXXX).
        :param cve_id: CVE id to search for.
        :return: CVE object.
        """
        if not cve_id:
            raise ValueError('Missing a CVE ID!')
        response = requests.get(f'https://cve.circl.lu/api/cve/{cve_id}')
        while response.status_code == 429:
            time.sleep(3)
            response = requests.get(f'https://cve.circl.lu/api/cve/{cve_id}')
        if response.status_code != 200:
            raise ValueError(f'Could not retrieve CVE information (Code: {response.status_code})!')

        cve_data = response.json()
        if not cve_data:
            raise ValueError(
                f'Could not find CVE information for {cve_id}, maybe it is a wrong number?'
            )
        return CVE(
            cve_id=cve_data.get('id'),
            score=cve_data.get('cvss'),
            published=datetime.strptime(cve_data.get('Published'), '%Y-%m-%dT%H:%M:%S'),
            vector=cve_data.get('cvss-vector', "").split('/'),
            references=cve_data.get('references'),
            summary=cve_data.get('summary'),
            vulnerable_versions=frozenset([
                x['title'].replace(':*', '').split(':')[-1]
                for x in cve_data.get('vulnerable_configuration')
            ])
        )


class CWE:
    """
    CWE representation with the major fields. Mainly a data object to store everything.
    """

    def __init__(self,
                 cwe_id: str,
                 name: str,
                 description: str) -> None:
        self.__cwe_id = cwe_id
        self.__name = name
        self.__description = description

    @property
    def cwe_id(self) -> str:
        """ Return CWE ID. """
        return self.__cwe_id

    @property
    def name(self) -> str:
        """ Return the name of this CWE. """
        return self.__name

    @property
    def description(self) -> str:
        """ Return the description. """
        return self.__description

    def __str__(self) -> str:
        return self.__cwe_id

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def find_all_cwe() -> tp.FrozenSet:
        """
        Create a set of all CWE's.
        :return: Set of CWE objects.
        """
        response = requests.get('https://cwe.mitre.org/data/csv/699.csv.zip')
        while response.status_code == 429:
            time.sleep(3)
            response = requests.get('https://cwe.mitre.org/data/csv/699.csv.zip')
        if response.status_code != 200:
            raise ValueError(f'Could not retrieve CVE information (Code: {response.status_code})!')

        cwe_list = set()

        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        with zip_file.open(zip_file.namelist()[0], 'r') as csv_file:
            reader = csv.DictReader(io.TextIOWrapper(csv_file), delimiter=',', quotechar='"')
            for entry in reader:
                cwe_id = entry.get('CWE-ID')
                cwe_list.add(CWE(
                    cwe_id=f'CWE-{cwe_id}',
                    name=entry.get('Name'),
                    description=entry.get('Description')
                ))

        return frozenset(cwe_list)

    @staticmethod
    def find_cwe(cwe_id: str = None, cwe_name: str = None, cwe_description: str = None):
        """
        Find a CWE by its attributes (ID (CWE-XXX), name, description).
        :param cwe_id: CWE to search for.
        :return: CWE if one is found, otherwise raise a ValueError.
        """
        for cwe in CWE_LIST:
            if cwe.cwe_id == cwe_id or \
               cwe.cwe_name == cwe_name or \
               cwe.cwe_description == cwe_description:
                return cwe

        raise ValueError(f'Could not find this CWE: {cwe_id}!')


# Cache all requests to limit external requests for a month
requests_cache.install_cache('security_cache', expire_after=2629800)

# Since this list is static it might as well be declared here so it is ready to use
CWE_LIST = CWE.find_all_cwe()
