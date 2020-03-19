"""
Main drivers for VaRA-TS
"""

import argparse
import varats.security as sec

def main_security() -> None:
    """
    Handle and simplify common security interactions with the project.
    """
    parser = argparse.ArgumentParser("Security helper")
    sub_parsers = parser.add_subparsers(help="CVE/CWE relevant information", dest="command")

    # List cve'S
    cve_parser = sub_parsers.add_parser('list-cve')
    cve_parser.add_argument('vendor',
                            type=str,
                            help='Name of the product vendor')
    cve_parser.add_argument('product',
                            type=str,
                            help='Name of the product')
    cve_parser.add_argument("--verbose",
                            help="Print verbose data",
                            action="store_true",
                            default=False)

    info_parser = sub_parsers.add_parser('info')
    info_parser.add_argument('id',
                             type=str,
                             help='ID of the CWE or CVE')
    info_parser.add_argument("--verbose",
                             help="Print verbose data",
                             action="store_true",
                             default=False)

    args = parser.parse_args()
    if args.command == 'list-cve':
        sec.list_cve_for_projects(vendor=args.vendor, product=args.product, verbose=args.verbose)
    elif args.command == 'info':
        sec.info(search=args.id, verbose=args.verbose)
    else:
        parser.print_help()
