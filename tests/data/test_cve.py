"""
Test the security utilities eg CVE, CWE stuff.
"""

from datetime import datetime
import unittest
import typing as tp
from varats.data.provider.cve.cve_util import CVE, CWE, CWE_LIST, \
    find_cve, find_all_cve, find_cwe, find_all_cwe


class TestSecurity(unittest.TestCase):
    """
    Security tests.
    """

    REFERENCE_CVE_DATA: dict = {
        'cve_id':
            'CVE-2014-0160',
        'score':
            5.0,
        'published':
            datetime.strptime('2014-04-07 22:55:00', '%Y-%m-%d %H:%M:%S'),
        'vector':
            frozenset(['AV:N', 'AC:L', 'Au:N', 'C:P', 'I:N', 'A:N'])
    }

    REFERENCE_CWE_DATA: dict = {
        'cwe_id': 'CWE-478',
        'name': 'Missing Default Case in Switch Statement',
        'description':
            'The code does not have a default case in a switch statement, '
            'which might lead to complex logical errors and resultant '
            'weaknesses.'
    }

    def test_find_single_cve(self):
        """
        Check if the Heartbleed's CVE-2014-0160 can be properly retrieved and
        parsed.
        https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-2601
        """
        cve: CVE = find_cve('CVE-2014-0160')

        self.assertTrue(cve.cve_id == self.REFERENCE_CVE_DATA['cve_id'])
        self.assertTrue(cve.score == self.REFERENCE_CVE_DATA['score'])
        self.assertTrue(cve.published == self.REFERENCE_CVE_DATA['published'])
        self.assertTrue(cve.vector == self.REFERENCE_CVE_DATA['vector'])

    def test_find_all_cve(self):
        """
        Get all OpenSSL CVE's and check if the Heartbleed CVE-2014-0160 is 
        contained.
        @https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-2601
        """
        cve_list: tp.FrozenSet[CVE] = find_all_cve('openssl', 'openssl')
        self.assertTrue(len(cve_list) != 0)

        found: bool = False
        for cve in cve_list:
            if cve.cve_id == self.REFERENCE_CVE_DATA['cve_id']:
                self.assertTrue(cve.score == self.REFERENCE_CVE_DATA['score'])
                self.assertTrue(
                    cve.published == self.REFERENCE_CVE_DATA['published'])
                self.assertTrue(cve.vector == self.REFERENCE_CVE_DATA['vector'])
                found = True
                break
        self.assertTrue(found)

    def test_find_single_cwe(self):
        """
        Find a CWE which should be in the list
        @https://cwe.mitre.org/data/definitions/478.html
        """
        self.assertTrue(len(CWE_LIST) != 0)

        self.assertTrue(find_cwe(cwe_id=self.REFERENCE_CWE_DATA['cwe_id']))
        self.assertTrue(find_cwe(cwe_name=self.REFERENCE_CWE_DATA['name']))
        self.assertTrue(
            find_cwe(cwe_description=self.REFERENCE_CWE_DATA['description']))

    def test_find_all_cwe(self):
        """
        Find a CWE which should be in the list
        @https://cwe.mitre.org/data/definitions/478.html
        """
        cwe_list: tp.FrozenSet[CWE] = find_all_cwe()
        self.assertTrue(len(cwe_list) != 0)

        found: bool = False
        for cwe in cwe_list:
            if cwe.cwe_id == self.REFERENCE_CWE_DATA['cwe_id']:
                self.assertTrue(cwe.name == self.REFERENCE_CWE_DATA['name'])
                self.assertTrue(
                    cwe.description == self.REFERENCE_CWE_DATA['description'])
                found = True
                break
        self.assertTrue(found)
