#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Test the security utilities eg CVE, CWE stuff.
"""

from datetime import datetime
import unittest
import typing as tp
from varats.utils.security_util import CVE, CWE, CWE_LIST, \
    find_cve, find_all_cve, find_cwe, find_all_cwe


class TestSecurity(unittest.TestCase):
    """
    Security tests.
    """

    def test_find_single_cve(self):
        """
        Check if the Heartbleed's CVE-2014-0160 can be properly retrieved and parsed.
        @https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-2601
        """
        cve: CVE = find_cve('CVE-2014-0160')

        reference_data: dict = {
            'cve_id': 'CVE-2014-0160',
            'score': 5.0,
            'published': datetime.strptime('2014-04-07 22:55:00', '%Y-%m-%d %H:%M:%S'),
            'vector': frozenset(['AV:N', 'AC:L', 'Au:N', 'C:P', 'I:N', 'A:N'])
        }

        self.assertTrue(cve.cve_id == reference_data['cve_id'])
        self.assertTrue(cve.score == reference_data['score'])
        self.assertTrue(cve.published == reference_data['published'])
        self.assertTrue(cve.vector == reference_data['vector'])

    def test_find_all_cve(self):
        """
        Get all OpenSSL CVE's and check if the Heartbleed CVE-2014-0160 is contained.
        @https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-2601
        """
        cve_list: tp.FrozenSet[CVE] = find_all_cve('openssl', 'openssl')
        self.assertTrue(len(cve_list) != 0)

        reference_data: dict = {
            'cve_id': 'CVE-2014-0160',
            'score': 5.0,
            'published': datetime.strptime('2014-04-07 22:55:00', '%Y-%m-%d %H:%M:%S'),
            'vector': ['AV:N', 'AC:L', 'Au:N', 'C:P', 'I:N', 'A:N']
        }

        found: bool = False
        for cve in cve_list:
            if cve.cve_id == reference_data['cve_id']:
                self.assertTrue(cve.score == reference_data['score'])
                self.assertTrue(cve.published == reference_data['published'])
                self.assertTrue(cve.vector == reference_data['vector'])
                found = True
                break
        self.assertTrue(found)

    def test_find_single_cwe(self):
        """
        Find a CWE which should be in the list
        @https://cwe.mitre.org/data/definitions/478.html
        """
        self.assertTrue(len(CWE_LIST) != 0)

        reference_data: dict = {
            'cwe_id': 'CWE-478',
            'name': 'Missing Default Case in Switch Statement',
            'description': 'The code does not have a default case in a switch statement, '
                           'which might lead to complex logical errors and resultant weaknesses.'
        }

        self.assertTrue(find_cwe(cwe_id=reference_data['cwe_id']))
        self.assertTrue(find_cwe(cwe_name=reference_data['name']))
        self.assertTrue(find_cwe(cwe_description=reference_data['description']))

    def test_find_all_cwe(self):
        """
        Find a CWE which should be in the list
        @https://cwe.mitre.org/data/definitions/478.html
        """
        cwe_list: tp.FrozenSet[CWE] = find_all_cwe()
        self.assertTrue(len(cwe_list) != 0)
        print(cwe_list)

        reference_data: dict = {
            'cwe_id': 'CWE-478',
            'name': 'Missing Default Case in Switch Statement',
            'description': 'The code does not have a default case in a switch statement, '
                           'which might lead to complex logical errors and resultant weaknesses.'
        }

        found: bool = False
        for cwe in cwe_list:
            if cwe.cwe_id == reference_data['cwe_id']:
                self.assertTrue(cwe.name == reference_data['name'])
                self.assertTrue(cwe.description == reference_data['description'])
                found = True
                break
        self.assertTrue(found)
