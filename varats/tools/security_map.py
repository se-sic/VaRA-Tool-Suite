"""
Map commits with resolved CVE's and CWE's based on multiple strategies.

Example Calls:
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
Example Output:
    {
        799: {
            'commit': '76b92b2830841fd4e05006cc3cad1d8f0bc8101b',
            'cve': [CVE-2008-3432],
            'cwe': []
        },
        [..]
    }
"""

import typing as tp
from pathlib import Path
import re
from packaging.version import parse as parse_version, Version, LegacyVersion
from plumbum import local
from plumbum.cmd import git
from varats.utils.security_util import (CVE, CWE_LIST, find_cve, find_cwe,
                                        find_all_cve)


def __n_grams(text: str,
              filter_reg: str = r'[^a-zA-Z0-9]',
              filter_len: int = 3) -> tp.Set[str]:
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


def __collect_via_commit_mgs(
        commits: tp.List[str]) -> tp.Dict[int, tp.Dict[str, tp.Any]]:
    """
    Collect data about resolved CVE's/CWE's using the commit message.
    
    Args:
        commits: a list of commits
    
    Return: 
        a dictionary with line number as key and commit hash, a list of CVE's
        and a list of CWE's as values
    """
    results: tp.Dict[int, tp.Dict[str, tp.Any]] = {}

    for number, line in enumerate(reversed(commits)):
        line_parts = line.split(' ')
        commit, message = line_parts[0], ' '.join(line_parts[1:])
        if 'CVE-' in message or 'CWE-' in message:
            # Check commit message for "CVE-XXXX-XXXXXXXX"
            # Includes old CVE format with just 4 numbers at the end,
            # as well as the new one with 8
            cve_list, cve_data = re.findall(r'CVE-\d{4}-\d{4,8}', message,
                                            re.IGNORECASE), []
            for cve in cve_list:
                try:
                    cve_data.append(find_cve(cve))
                except ValueError as error_msg:
                    print(error_msg)
            # Check commit message for "CWE-XXXX"
            cwe_list, cwe_data = re.findall(r'CWE-[\d\-]+\d', message,
                                            re.IGNORECASE), []
            for cwe in cwe_list:
                try:
                    cwe_data.append(find_cwe(cwe_id=cwe))
                except ValueError as error_msg:
                    print(error_msg)
            # Check commit message whether it contains any name or description
            # from the CWE entries
            for cwe in CWE_LIST:
                if cwe.name in message or cwe.description in message:
                    cwe_data.append(cwe)
            # Compare commit messages with CWE list using n-grams
            message_parts = __n_grams(text=message)
            for cwe in CWE_LIST:
                if not __n_grams(text=cwe.name) ^ message_parts or \
                   not __n_grams(text=cwe.description) ^ message_parts:
                    cwe_data.append(cwe)

            results[number] = {
                'commit': commit,
                'cve': cve_data,
                'cwe': cwe_data
            }

    return results


def __collect_via_version(
        commits: tp.List[str],
        cve_list: tp.FrozenSet[CVE]) -> tp.Dict[int, tp.Dict[str, tp.Any]]:
    """
    Collect data about resolved CVE's using the tagged versions
    and the vulnerable version list in the CVE's.

    Args:
        commits: a list of commits

    Return:
        a dictionary with line number as key and commit hash, a list of CVE's
        and a list of CWE's as values
    """
    results: tp.Dict[int, tp.Dict[str, tp.Any]] = {}

    # Collect tagged commits
    tag_list: tp.Dict[tp.Union[LegacyVersion, Version], tp.Dict[str,
                                                                tp.Any]] = {}
    for number, line in enumerate(reversed(commits)):
        line_parts = line.split(' ')
        commit, message = line_parts[0], ' '.join(line_parts[1:])
        tag = re.findall(r'\(tag:\s*.*\)', message, re.IGNORECASE)
        if tag:
            parsed_tag = parse_version(tag[0].split(' ')[1].replace(
                ',', '').replace(')', ''))
            tag_list[parsed_tag] = {'number': number, 'commit': commit}

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


def __collect_via_references(
        commits: tp.List[str], cve_list: tp.FrozenSet[CVE], vendor: str,
        product: str) -> tp.Dict[int, tp.Dict[str, tp.Any]]:
    """
    Collect data about resolved CVE' using the reference list in each CVE's.

    Args:
        commits: a list of commits

    Return:
        a dictionary with line number as key and commit hash, a list of CVE's
        and a list of CWE's as values
    """
    results: tp.Dict[int, tp.Dict[str, tp.Any]] = {}

    for cve in cve_list:
        # Parse for github/gitlab urls which usually look like
        # {protocol}://{domain}/{vendor}/{product}/commit/{hash}
        referenced_commits = [
            x for x in cve.references if f'{vendor}/{product}/commit' in x
        ]
        if not referenced_commits:
            continue

        for referenced_commit in referenced_commits:
            for number, line in enumerate(reversed(commits)):
                commit = line.split(' ')[0]
                if referenced_commit == commit:
                    if number in results.keys():
                        results[number]['cve'] += [cve]
                    else:
                        results[number] = {
                            'commit': commit,
                            'cve': [cve],
                            'cwe': []
                        }
                    break

    return results


def __merge_results(
    result_list: tp.List[tp.Dict[int, tp.Dict[str, tp.Any]]]
) -> tp.Dict[int, tp.Dict[str, tp.Any]]:
    """
    Merge a list of results into one dictionary.
    
    Return:
        the merged dictionary with line number as key and commit hash, a list of
        unique CVE's and a list of unique CWE's as values
    """
    results: tp.Dict[int, tp.Dict[str, tp.Any]] = {}

    for unmerged in result_list:
        for entry in unmerged.keys():
            if entry in results.keys():
                results[entry]['cve'] = list(
                    set(results[entry]['cve'] + unmerged[entry]['cve']))
                results[entry]['cwe'] = list(
                    set(results[entry]['cwe'] + unmerged[entry]['cwe']))
            else:
                results[entry] = unmerged[entry]

    return results


def generate_security_commit_map(
        path: Path,
        vendor: str,
        product: str,
        end: str = "HEAD",
        start: tp.Optional[str] = None) -> tp.Dict[int, tp.Dict[str, tp.Any]]:
    """
    Generate a commit map for a repository including the commits
    ``]start..end]`` if they contain a fix for a CVE or CWE.

    Commands to grep commit messages for CVE's/CWE's:
        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CVE-"
        git --no-pager log --all --pretty=format:'%H %d %s' --grep="CWE-"
        git --no-pager log --all --tags --pretty="%H %d %s"

    But since this does not work in all projects, also look in the CVE/CWE
    database for matching entries.
    """
    search_range = ""
    if start is not None:
        search_range += start + ".."
    search_range += end

    with local.cwd(path):
        commits = git("--no-pager", "log", "--pretty=format:'%H %d %s'",
                      search_range)
        wanted_out = [x[1:-1] for x in commits.split('\n')]

        cve_list = find_all_cve(vendor=vendor, product=product)
        results = __merge_results([
            __collect_via_commit_mgs(commits=wanted_out),
            __collect_via_version(commits=wanted_out, cve_list=cve_list),
            __collect_via_references(commits=wanted_out,
                                     cve_list=cve_list,
                                     vendor=vendor,
                                     product=product)
        ])

        return results
