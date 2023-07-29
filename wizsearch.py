import argparse
import json

from core.index import WizIndex

def run_index(args):
    index = WizIndex(
    base_path = args.folder, wiz_path = args.wiznote_data_path)
    index.create_or_update_index()

def run_search(args):
    wiz_index = WizIndex(base_path=args.folder, wiz_path=args.wiznote_data_path)
    keyword = ' '.join(args.keywords)
    page_num = args.page_number
    total, results = wiz_index.search(keyword, page_num)
    print(json.dumps({'total': total, 'data': results}))

def main():
    shared_parser = argparse.ArgumentParser(add_help=False)
    # TODO: Create index at the data folder of that account
    shared_parser.add_argument('-O', '--folder', action='store', required=True,
                            help='The folder to place indexes.')
    # TODO: Find default WIZ_NOTE_PATH from ENV, then determin final path from account
    shared_parser.add_argument('-W', '--wiznote-data-path', action='store',
                            required=True, help='The data folder of WizNote.')

    parser = argparse.ArgumentParser('Create or Update Index of Your Notes')
    subparsers = parser.add_subparsers(dest="command", help="sub-command help")
    index_cmd = subparsers.add_parser("index", help="Create or Update Index of Your Notes",
                                      parents=[shared_parser])
    index_cmd.set_defaults(func=run_index)

    search_cmd = subparsers.add_parser("search", help="Search the database with given keywords.",
                                       parents=[shared_parser])
    search_cmd.add_argument("-p", "--page-number", type=int, default=1, help="Page number.")
    search_cmd.add_argument("keywords", nargs='*', help="Keywords to search.")
    search_cmd.set_defaults(func=run_search)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()