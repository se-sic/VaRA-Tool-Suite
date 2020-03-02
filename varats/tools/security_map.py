#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Map commits with CVE's and CVE's.
Example:
    generate_security_commit_map(path=Path('/home/vara/qemu'), vendor='qemu', product='qemu')
"""

import typing as tp
from pathlib import Path
import re
from packaging.version import parse as parse_version
from plumbum import local
from plumbum.cmd import git
from varats.utils.security_util import CVE, find_cwe, CWE_LIST


def generate_security_commit_map(path: Path,
                                 vendor: str,
                                 product: str,
                                 end: str = "HEAD",
                                 start: tp.Optional[str] = None) -> set:
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
        full_out = git("--no-pager", "log", "--pretty=format:'%H %d %s'")
        wanted_out = git("--no-pager", "log", "--pretty=format:'%H %d %s'", search_range)
        full_out = [x[1:-1] for x in full_out.split('\n')]
        wanted_out = [x[1:-1] for x in wanted_out.split('\n')]

        entries, tag_list = set(), {}
        for number, line in enumerate(reversed(full_out)):
            if line in wanted_out:
                line_parts = line.split(' ')
                commit, message = line_parts[0], ' '.join(line_parts[1:])
                # For each commit check if the message contains a "CVE-*" or "CWE-*" or CWE message
                if 'CVE-' in message or 'CWE-' in message:
                    cve_list, cve_data = re.findall(r'CVE-[\d\-]+\d', message, re.IGNORECASE), []
                    for cve in cve_list:
                        try:
                            cve_data.append(CVE.find_cve(cve))
                        except ValueError as error_msg:
                            print(error_msg)
                    cwe_list, cwe_data = re.findall(r'CWE-[\d\-]+\d', message, re.IGNORECASE), []
                    for cwe in cwe_list:
                        try:
                            cwe_data.append(find_cwe(cwe))
                        except ValueError as error_msg:
                            print(error_msg)
                    for cwe in CWE_LIST:
                        if cwe.name in message or cwe.description in message:
                            cwe_data.append(cwe)

                    entries.add((number, commit, frozenset(cve_data), frozenset(cwe_list)))
                else:  # Collect version -> commit
                    tag = re.findall(r'\(tag:\s*.*\)', message, re.IGNORECASE)
                    if tag:
                        tag = parse_version(tag[0].split(' ')[1].replace(',', '').replace(')', ''))
                        tag_list[tag] = {'number': number, 'commit': commit}

        # For each CVE for this specific project get the first version that is not vulnerable to it
        for cve in CVE.find_all_cve(vendor, product):
            # Find by version
            for version in sorted(tag_list.keys()):
                if all([version > x for x in cve.vulnerable_versions]):
                    entries.add((
                        tag_list[version]['number'],
                        tag_list[version]['commit'],
                        frozenset([cve]),
                        frozenset()
                    ))
                    break
            patch_commit = [x for x in cve.references if f'{vendor}/{product}/commit' in x]
            if patch_commit:
                patch_commit = patch_commit[0]
                for number, line in enumerate(reversed(wanted_out)):
                    line_parts = line.split(' ')
                    commit = line_parts[0]
                    if patch_commit == commit:
                        entries.add((
                            number,
                            commit,
                            frozenset([cve]),
                            frozenset()
                        ))
                        break

        # Filter everything
        entries_filtered, entries_tmp = set(), {}
        for number, commit, cve_list, cwe_list in entries:
            if number not in entries_tmp.keys():
                entries_tmp[number] = {
                    'commit': commit,
                    'cve_list': list(cve_list),
                    'cwe_list': list(cwe_list)
                }
            else:
                entries_tmp[number]['cve_list'] += list(cve_list)
                entries_tmp[number]['cwe_list'] += list(cwe_list)
        for key, value in entries_tmp.items():
            entries_filtered.add((
                key,
                value['commit'],
                frozenset(value['cve_list']),
                frozenset(value['cwe_list'])
            ))

        # TODO: Return CommitMap or something similar and refactor this stuff...
        return entries_filtered
