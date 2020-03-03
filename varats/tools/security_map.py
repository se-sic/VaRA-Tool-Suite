#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Map commits with resolved CVE's and CWE's based on multiple strategies.
Example Call:
    generate_security_commit_map(path=Path('/home/vara/vim'), vendor='vim', product='vim')
    {
        799: {
            'commit': '76b92b2830841fd4e05006cc3cad1d8f0bc8101b',
            'cve': [CVE-2008-3432],
            'cwe': []
        },
        7859: {
            'commit': '5a73e0ca54c77e067c3b12ea6f35e3e8681e8cf8',
            'cve': [CVE-2017-17087],
            'cwe': []
        },
        [..]
    }
"""

import typing as tp
from pathlib import Path
import re
from packaging.version import parse as parse_version
from plumbum import local
from plumbum.cmd import git
from varats.utils.security_util import CVE, find_cwe, CWE_LIST


def __collect_via_commit_mgs(commits: tp.List[str]) -> dict:
    """
    Collect data about resolved CVE's/CWE's using the commit message.
    :param commits: List of commits.
    :return: Dictionary with line number as key and commit hash, a list of CVE's
             and a list of CWE's as values.
    """
    results = {}

    for number, line in enumerate(reversed(commits)):
        line_parts = line.split(' ')
        commit, message = line_parts[0], ' '.join(line_parts[1:])
        if 'CVE-' in message or 'CWE-' in message:
            # Check commit message for "CVE-XXX"
            cve_list, cve_data = re.findall(r'CVE-[\d\-]+\d', message, re.IGNORECASE), []
            for cve in cve_list:
                try:
                    cve_data.append(CVE.find_cve(cve))
                except ValueError as error_msg:
                    print(error_msg)
            # Check commit message for "CWE-XXX"
            cwe_list, cwe_data = re.findall(r'CWE-[\d\-]+\d', message, re.IGNORECASE), []
            for cwe in cwe_list:
                try:
                    cwe_data.append(find_cwe(cwe))
                except ValueError as error_msg:
                    print(error_msg)
            # Check commit message if it contains any name or description from the CWE entries
            for cwe in CWE_LIST:
                if cwe.name in message or cwe.description in message:
                    cwe_data.append(cwe)

            results[number] = {'commit': commit, 'cve': cve_data, 'cwe': cwe_data}

    return results


def __collect_via_version(commits: tp.List[str],
                          cve_list: tp.List[CVE]) -> dict:
    """
    Collect data about resolved CVE's using the tagged versions
    and the vulnerable version list in the CVE's.
    :param commits: List of commits.
    :return: Dictionary with line number as key and commit hash, a list of CVE's
             and a list of CWE's as values.
    """
    results = {}

    # Collect tagged commits
    tag_list = {}
    for number, line in enumerate(reversed(commits)):
        line_parts = line.split(' ')
        commit, message = line_parts[0], ' '.join(line_parts[1:])
        tag = re.findall(r'\(tag:\s*.*\)', message, re.IGNORECASE)
        if tag:
            tag = parse_version(tag[0].split(' ')[1].replace(',', '').replace(')', ''))
            tag_list[tag] = {'number': number, 'commit': commit}

    # Check versions
    for cve in cve_list:
        for version in sorted(tag_list.keys()):
            if all([version > x for x in cve.vulnerable_versions]):
                if tag_list[version]['number'] in results.keys():
                    results[tag_list[version]['number']]['cve'] += [cve]
                else:
                    results[tag_list[version]['number']] = {
                        'commit': tag_list[version]['commit'],
                        'cve': [cve],
                        'cwe': [],
                    }
                break

    return results


def __collect_via_references(commits: tp.List[str],
                             cve_list: tp.List[CVE],
                             vendor: str,
                             product: str) -> dict:
    """
    Collect data about resolved CVE' using the reference list in each CVE's.
    :param commits: List of commits.
    :return: Dictionary with line number as key and commit hash, a list of CVE's
             and a list of CWE's as values.
    """
    results = {}

    for cve in cve_list:
        # Parse for github/gitlab urls which usually look like
        # {protocol}://{domain}/{vendor}/{product}/commit/{hash}
        referenced_commits = [x for x in cve.references if f'{vendor}/{product}/commit' in x]
        if not referenced_commits:
            continue

        for referenced_commit in referenced_commits:
            for number, line in enumerate(reversed(commits)):
                commit = line.split(' ')[0]
                if referenced_commit == commit:
                    if number in results.keys():
                        results[number]['cve'] += [cve]
                    else:
                        results[number] = {'commit': commit, 'cve': [cve], 'cwe': []}
                    break

    return results


def __merge_results(result_list: tp.List[dict]) -> dict:
    """
    Merge a list of results into one dictionary.
    :param commits: List of result dictionaries.
    :return: Dictionary with line number as key and commit hash, a list of CVE's
             and a list of CWE's as values.
    """
    results = {}

    for unmerged in result_list:
        for entry in unmerged.keys():
            if entry in results.keys():
                results[entry]['cve'] = list(set(results[entry]['cve'] + unmerged[entry]['cve']))
                results[entry]['cwe'] = list(set(results[entry]['cwe'] + unmerged[entry]['cwe']))
            else:
                results[entry] = unmerged[entry]

    return results


def generate_security_commit_map(path: Path,
                                 vendor: str,
                                 product: str,
                                 end: str = "HEAD",
                                 start: tp.Optional[str] = None) -> dict:
    """
    Generate a commit map for a repository including the commits ]start..end]
    if they contain a fix for a CVE or CWE.
    Commands to grep commit messages for CVE's/CWE's:
        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CVE-"
        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CWE-"
        git --no-pager log --all --tags --pretty="%H %d %s"
    But since this does not work in all projects also look in the CVE/CWE
    database for matching entries.
    """
    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        commits = git("--no-pager", "log", "--pretty=format:'%H %d %s'", search_range)
        wanted_out = [x[1:-1] for x in commits.split('\n')]

        cve_list = CVE.find_all_cve(vendor, product)
        results = __merge_results([
            __collect_via_commit_mgs(wanted_out),
            __collect_via_version(wanted_out, cve_list),
            __collect_via_references(wanted_out, cve_list, vendor, product)
        ])

        return results
