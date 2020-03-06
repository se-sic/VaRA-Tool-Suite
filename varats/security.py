#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
The security module provides different utility function for VaRA.
"""

from varats.utils.security_util import CVE


def list_cve_for_projects(vendor: str, product: str) -> None:
    """
    List all CVE's for the given vendor/product combination.
    Call via vara-sec list-cve <vendor> <product>.
    """
    print(f"Listing CVE's for {vendor}/{product}:")
    try:
        cve_list = CVE.find_all_cve(vendor=vendor, product=product)
        for cve in cve_list:
            cve_url = f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve}"
            print(f"{cve.cve_id:20} {cve_url}")
    except ValueError:
        print('No entries found.')
