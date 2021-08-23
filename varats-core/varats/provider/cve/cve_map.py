r"""
Map commits with resolved CVE's and CWE's based on multiple strategies.

Example Calls::

    generate_security_commit_map(
        path=Path('/home/vara/repos/vim'),
        vendor='vim',
        product='vim'
    )
    generate_security_commit_map(
        path=Path('/home/vara/repos/tensorflow'),
        vendor='google',
        product='tensorflow'
    )

Example Output::

    {
        799: {
            'commit': '76b92b2830841fd4e05006cc3cad1d8f0bc8101b',
            'cve': [CVE-2008-3432],
            'cwe': []
        },
        [..]
    }
"""
import logging
import re
import sys
import typing as tp
from collections import defaultdict
from pathlib import Path

from benchbuild.utils.cmd import git
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version
from plumbum import local

from varats.provider.cve.cve import (
    CVE,
    CWE,
    find_all_cve,
    find_all_cwe,
    find_cve,
    find_cwe,
)
from varats.utils.git_util import FullCommitHash

if sys.version_info <= (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

LOG = logging.getLogger(__name__)


def __n_grams(
    text: str,
    filter_reg: str = r'[^a-zA-Z0-9]',
    filter_len: int = 3
) -> tp.Set[str]:
    """
    Divide some text into character-level n-grams.

    Args:
        text: the text to compute the n-grams for
        filter_reg: regular expression to filter out special characters
                    (default: non-letters)

    Return:
        the set of n-grams
    """
    results: tp.Set[str] = set()
    filter_comp: tp.Pattern[str] = re.compile(filter_reg)
    for word in text.split():
        if filter_reg:
            word = filter_comp.sub('', word)
        word = word.strip()
        if filter_len <= len(word):
            results.add(word)
    return results


class CVEDictEntry(TypedDict):
    cve: tp.Set[CVE]
    cwe: tp.Set[CWE]


CVEDict = tp.Dict[FullCommitHash, CVEDictEntry]


def __create_cve_dict_entry() -> CVEDictEntry:
    return {"cve": set(), "cwe": set()}


def __collect_via_commit_mgs(
    commits: tp.List[tp.Tuple[FullCommitHash, str]]
) -> CVEDict:
    """
    Collect data about resolved CVE's/CWE's using the commit message.

    Args:
        commits: a list of commits in textual form

    Return:
        a dictionary with commit hash as key and a set of CVE's and a set of
        CWE's as values
    """
    results: CVEDict = defaultdict(__create_cve_dict_entry)

    for commit, message in commits:
        if 'CVE-' in message or 'CWE-' in message:
            # Check commit message for "CVE-XXXX-XXXXXXXX"
            # Includes old CVE format with just 4 numbers at the end,
            # as well as the new one with 8
            cve_list = re.findall(r'CVE-\d{4}-\d{4,8}', message, re.IGNORECASE)
            cve_data = []
            for cve in cve_list:
                try:
                    cve_data.append(find_cve(cve))
                except ValueError as error_msg:
                    LOG.error(error_msg)
            # Check commit message for "CWE-XXXX"
            cwe_list = re.findall(r'CWE-[\d\-]+\d', message, re.IGNORECASE)
            cwe_data = []
            for cwe in cwe_list:
                try:
                    cwe_data.append(find_cwe(cwe_id=cwe))
                except ValueError as error_msg:
                    LOG.error(error_msg)
            # Check commit message whether it contains any name or description
            # from the CWE entries
            for cwe in find_all_cwe():
                if cwe.name in message or cwe.description in message:
                    cwe_data.append(cwe)
            # Compare commit messages with CWE list using n-grams
            message_parts = __n_grams(text=message)
            for cwe in find_all_cwe():
                if not __n_grams(text=cwe.name) ^ message_parts or \
                   not __n_grams(text=cwe.description) ^ message_parts:
                    cwe_data.append(cwe)

            results[commit]['cve'].update(cve_data)
            results[commit]['cwe'].update(cwe_data)

    return results


def __collect_via_version(
    commits: tp.List[tp.Tuple[FullCommitHash, str]], cve_list: tp.FrozenSet[CVE]
) -> CVEDict:
    """
    Collect data about resolved CVE's using the tagged versions and the
    vulnerable version list in the CVE's.

    Args:
        commits: a list of commits in textual form

    Return:
        a dictionary with commit hash as key and a set of CVE's and a set of
        CWE's as values
    """
    results: CVEDict = defaultdict(__create_cve_dict_entry)

    # Collect tagged commits
    tag_list: tp.Dict[tp.Union[LegacyVersion, Version], tp.Dict[str,
                                                                tp.Any]] = {}
    for number, commit_data in enumerate(reversed(commits)):
        commit, message = commit_data
        tag = re.findall(r'\(tag:\s*.*\)', message, re.IGNORECASE)
        if tag:
            parsed_tag = parse_version(
                tag[0].split(' ')[1].replace(',', '').replace(')', '')
            )
            tag_list[parsed_tag] = {'number': number, 'commit': commit}

    # Check versions
    for cve in cve_list:
        for version in sorted(tag_list.keys()):
            if all(version > x for x in cve.vulnerable_versions):
                results[tag_list[version]['commit']]['cve'].add(cve)
                break

    return results


def __collect_via_references(
    commits: tp.List[tp.Tuple[FullCommitHash, str]],
    cve_list: tp.FrozenSet[CVE], vendor: str, product: str
) -> CVEDict:
    """
    Collect data about resolved CVE' using the reference list in each CVE's.

    Args:
        commits: a list of commits in textual form

    Return:
        a dictionary with line number as key and commit hash, a list of CVE's
        and a list of CWE's as values
    """
    results: CVEDict = defaultdict(__create_cve_dict_entry)

    for cve in cve_list:
        # Parse for github/gitlab urls which usually look like
        # {protocol}://{domain}/{vendor}/{product}/commit/{hash}
        referenced_commits = [
            x for x in cve.references if f'{vendor}/{product}/commit' in x
        ]
        if not referenced_commits:
            continue

        for referenced_commit in referenced_commits:
            for commit, _ in commits:
                if referenced_commit == commit:
                    results[commit]['cve'].add(cve)
                    break

    return results


def __merge_results(result_list: tp.List[CVEDict]) -> CVEDict:
    """
    Merge a list of results into one dictionary.

    Args:
        result_list: a list of ``commit -> cve`` maps to be merged

    Return:
        the merged dictionary with line number as key and commit hash, a list of
        unique CVE's and a list of unique CWE's as values
    """
    results: CVEDict = defaultdict(__create_cve_dict_entry)

    for unmerged in result_list:
        for entry in unmerged.keys():
            results[entry]['cve'].update(unmerged[entry]['cve'])
            results[entry]['cwe'].update(unmerged[entry]['cwe'])
    return results


def generate_cve_map(
    path: Path,
    products: tp.List[tp.Tuple[str, str]],
    end: str = "HEAD",
    start: tp.Optional[str] = None,
    only_precise: bool = True
) -> CVEDict:
    """
    Generate a commit map for a repository including the commits
    ``]start..end]`` if they contain a fix for a CVE or CWE.

    Commands to grep commit messages for CVE's/CWE's::

        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CVE-"
        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CWE-"
        git --no-pager log --all --tags --pretty="%H %d %s"

    But since this does not work in all projects, also look in the CVE/CWE
    database for matching entries.

    Args:
        path: path to the git repo of the project to get the map for
        products: a list of tuples used for querying the CVE database
        end: newest revision to consider
        start: oldest revision to consider
        only_precise: only include CVEs where an exact fixing commit can be
            identified
    Return:
        a map ``revision -> set of CVEs fixed by that revision``
    """

    def split_commit_info(commit_info: str) -> tp.Tuple[FullCommitHash, str]:
        parts = commit_info.split(' ')
        return FullCommitHash(parts[0]), ' '.join(parts[1:])

    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        commits = git(
            "--no-pager", "log", "--pretty=format:'%H %d %s'", search_range
        )
        wanted_out = list(
            map(split_commit_info, [x[1:-1] for x in commits.split('\n')])
        )

        def get_results_for_product(vendor: str, product: str) -> CVEDict:
            cve_list = find_all_cve(vendor=vendor, product=product)
            cve_maps = [
                __collect_via_commit_mgs(commits=wanted_out),
                __collect_via_references(
                    commits=wanted_out,
                    cve_list=cve_list,
                    vendor=vendor,
                    product=product
                )
            ]
            if not only_precise:
                cve_maps.append(
                    __collect_via_version(
                        commits=wanted_out, cve_list=cve_list
                    ),
                )
            return __merge_results(cve_maps)

        return __merge_results([
            get_results_for_product(vendor, product)
            for vendor, product in products
        ])
