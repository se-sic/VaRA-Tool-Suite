"""
The security module provides different utility functions for VaRA.
"""

from varats.utils.security_util import find_all_cve, find_cve, find_cwe


def list_cve_for_projects(vendor: str,
                          product: str,
                          verbose: bool = False) -> None:
    """
    List all CVE's for the given vendor/product combination.
    Call via vara-sec list-cve <vendor> <product>.
    """
    print(f"Listing CVE's for {vendor}/{product}:")
    try:
        for cve in find_all_cve(vendor=vendor, product=product):
            if verbose:
                print(cve, end='\n\n')
            else:
                print(f'{cve.cve_id:20} [{cve.url}]')
    except ValueError:
        print('No entries found.')


def info(search: str, verbose: bool = False) -> None:
    """
    Search for matching CVE/CWE and print its data.
    """
    print(f"Fetching information for {search}:")

    if search.lower().startswith('cve-'):
        cve = find_cve(cve_id=search)
        if verbose:
            print(cve)
        else:
            print(f'{cve.cve_id:20} [{cve.url}]')
    elif search.lower().startswith('cwe-'):
        cwe = find_cwe(cwe_id=search)
        if verbose:
            print(cwe)
        else:
            print(f'{cwe.cwe_id:20} [{cwe.url}]')
    else:
        print(
            f'Could not parse input. Did you mean CVE-{search} or CWE-{search}?'
        )
