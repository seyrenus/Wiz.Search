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
    search_in = request.json.get('search_in')
    page_num = request.json.get('page_num', 1)
    folder_path = request.json.get('folder_path')
    start_date = request.json.get('start_date')
    end_date = request.json.get('end_date')
    modify_start_date = request.json.get('modify_start_date')
    modify_end_date = request.json.get('modify_end_date')
    
    total, results = wiz_index.search(
        keyword=keyword,
        page_num=page_num,
        search_in=search_in,
        folder_path=folder_path,
        start_date=start_date,
        end_date=end_date,
        modify_start_date=modify_start_date,
        modify_end_date=modify_end_date
    )
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

@app.route('/api/folders', methods=['GET'])
def get_folders():
    try:
        wiz_index = app.wiz_index
        folders = wiz_index.get_folders()
        return jsonify({
            "success": True,
            "data": folders
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })

if __name__ == '__main__':
    main()