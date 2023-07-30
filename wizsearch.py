import argparse
import json

from core.index import WizIndex
from flask import Flask, request, jsonify

def run_index(args):
    index = WizIndex(base_path = args.folder,
                     wiz_path = args.wiznote_data_path,
                     verbose=True)
    index.create_or_update_index()
    print("Full-text indexing is done.")

def run_search(args):
    wiz_index = WizIndex(base_path=args.folder, wiz_path=args.wiznote_data_path)
    keyword = ' '.join(args.keywords)
    page_num = args.page_number
    total, results = wiz_index.search(keyword, page_num)
    print(json.dumps({'total': total, 'data': results}))

app = Flask("WizSearch")

@app.route('/')
def test_page():
    return "Hello World"

@app.route('/api/search', methods=['POST'])
def page_search():
    wiz_index = app.wiz_index
    keyword = request.json.get('keyword')
    page_num = request.json.get('page_num', 1)
    total, results = wiz_index.search(keyword, page_num)
    return jsonify({'code': 200, 'data': results, 'total': total, 'msg': 'ok'})

def run_server(args):
    app.wiz_index = WizIndex(base_path=args.folder, wiz_path=args.wiznote_data_path)
    app.run(host="127.0.0.1", port=args.port)

def main():
    shared_parser = argparse.ArgumentParser(add_help=False)
    # TODO: Create index at the data folder of that account
    shared_parser.add_argument('-O', '--folder', action='store', required=True,
                            help='The folder to place indexes.')
    # TODO: Find default WIZ_NOTE_PATH from ENV, then determin final path from account
    # Example: '/Users/your_name/.wiznote/your_account/data'
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

    server_cmd = subparsers.add_parser("server", help="Run a search service on local machine.",
                                       parents=[shared_parser])
    server_cmd.add_argument('-p', '--port', default=5000, type=int,
                           help='Run server on which port.')
    server_cmd.set_defaults(func=run_server)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()