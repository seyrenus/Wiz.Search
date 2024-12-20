# -*- coding: utf-8 -*-
# created by restran on 2019/05/06
from __future__ import unicode_literals, absolute_import

import os.path
import shutil
import zipfile
import sys

import records
import jieba
from bs4 import BeautifulSoup
from jieba.analyse import ChineseAnalyzer
from whoosh import scoring
from whoosh.fields import Schema, TEXT, ID
from whoosh.filedb.filestore import FileStorage
from whoosh.index import create_in
from whoosh.qparser import QueryParser

jieba.setLogLevel(jieba.logging.ERROR)

CREATE_TABLE_SQL = """
create table WIZ_INDEX
(
  DOCUMENT_GUID     char(36)     not null primary key,
  DOCUMENT_TITLE    varchar(768) not null,
  DOCUMENT_LOCATION varchar(768),
  DT_CREATED        char(19),
  DT_MODIFIED       char(19),
  WIZ_VERSION       int64,
  DT_INDEXED        integer(4)
);
"""


class WizIndex(object):
    def __init__(self, base_path, wiz_path, verbose=False):
        if not os.path.exists(base_path):
            os.mkdir(base_path)

        self.verbose = verbose
        self.base_path = base_path
        self.index_path = os.path.join(base_path, "data")
        self.wiz_path = wiz_path
        self.index_db = records.Database('sqlite:///' + os.path.join(self.base_path, 'database.db'))

        try:
            with self.index_db.get_connection() as conn:
                conn.query('select * from WIZ_INDEX')
        except:
            # FIXME: create table using another way
            if self.verbose:
                print('create table WIZ_INDEX', file=sys.stderr)
            with self.index_db.get_connection() as conn:
                conn.query(CREATE_TABLE_SQL)
                conn.query('PRAGMA auto_vacuum = FULL;')

            if os.path.exists(self.index_path):
                shutil.rmtree(self.index_path)

            if not os.path.exists(self.index_path):
                os.mkdir(self.index_path)

        analyzer = ChineseAnalyzer()
        self.schema = Schema(title=TEXT(stored=True, analyzer=analyzer),
                             path=ID(stored=True),
                             content=TEXT(stored=True, analyzer=analyzer))

    def get_idx(self):
        try:
            storage = FileStorage(self.index_path)  # idx_path 为索引路径
            idx = storage.open_index(indexname='wiz_index', schema=self.schema)
        except:
            idx = create_in(self.index_path, self.schema, indexname='wiz_index')

        return idx

    def get_should_index_data(self):
        wiz_db = records.Database('sqlite:///{}'.format(os.path.join(self.wiz_path, 'index.db')))
        sql = """select * from WIZ_DOCUMENT"""
        with wiz_db.get_connection() as conn:
            wiz_rows = conn.query(sql).as_dict()
        sql = """select * from WIZ_INDEX"""
        with self.index_db.get_connection() as conn:
            index_rows = conn.query(sql).as_dict()
        wiz_dict = {t['DOCUMENT_GUID']: t for t in wiz_rows}
        index_dict = {t['DOCUMENT_GUID']: {'data': t, 'action': 'delete'} for t in index_rows}
        for k, v in wiz_dict.items():
            if k not in index_dict:
                index_dict[k] = {
                    'data': v,
                    'action': 'insert'
                }
            else:
                if v['WIZ_VERSION'] > index_dict[k]['data']['WIZ_VERSION']:
                    index_dict[k] = {
                        'data': v,
                        'action': 'update'
                    }
                else:
                    index_dict[k] = {
                        'data': v,
                        'action': None
                    }

        index_data = [t for t in index_dict.values() if t['action'] not in (None,)]
        wiz_db.close()
        return index_data

    def create_or_update_index(self):
        index_data = self.get_should_index_data()
        idx = self.get_idx()
        writer = idx.writer()
        count = len(index_data)
        if self.verbose:
            print('total: %s' % count, file=sys.stderr)
        for i, v in enumerate(index_data):
            r = v['data']
            action = v['action']
            document_guid = r['DOCUMENT_GUID']

            zipfilename = os.path.join(self.wiz_path, 'notes/{%s}' % document_guid)
            if not os.path.exists(zipfilename):
                continue

            try:
                zf = zipfile.ZipFile(zipfilename)
            except zipfile.BadZipFile as e:
                if self.verbose:
                    print("Skip encrypted document", file=sys.stderr)
                continue

            for filename in zf.namelist():
                if filename == 'index.html':
                    try:
                        data = zf.read(filename)
                        html_content = BeautifulSoup(data, 'html5lib')
                        if self.verbose:
                            print('%s %s, %s' % (i, action, r['DOCUMENT_TITLE']), file=sys.stderr)
                        if action == 'insert':
                            writer.add_document(
                                path=r['DOCUMENT_GUID'],
                                title=r['DOCUMENT_TITLE'],
                                content=r['DOCUMENT_TITLE'] + '\n' + html_content.body.text
                            )
                            sql = """insert into WIZ_INDEX (DOCUMENT_GUID, DOCUMENT_TITLE, DOCUMENT_LOCATION, DT_CREATED, DT_MODIFIED, WIZ_VERSION) 
                            values (:DOCUMENT_GUID, :DOCUMENT_TITLE, :DOCUMENT_LOCATION, :DT_CREATED, :DT_MODIFIED, :WIZ_VERSION)"""
                        elif action == 'update':
                            writer.delete_by_term('path', r['DOCUMENT_GUID'])
                            writer.update_document(
                                path=r['DOCUMENT_GUID'],
                                title=r['DOCUMENT_TITLE'],
                                content=r['DOCUMENT_TITLE'] + '\n' + html_content.body.text
                            )

                            sql = """update WIZ_INDEX set DOCUMENT_TITLE=:DOCUMENT_TITLE, 
                            DOCUMENT_LOCATION=:DOCUMENT_LOCATION, DT_CREATED=:DT_CREATED, 
                            DT_MODIFIED=:DT_MODIFIED, WIZ_VERSION=:WIZ_VERSION where DOCUMENT_GUID=:DOCUMENT_GUID"""

                        elif action == 'delete':
                            writer.delete_by_term('path', r['DOCUMENT_GUID'])
                            sql = """delete from WIZ_INDEX where DOCUMENT_GUID=:DOCUMENT_GUID"""
                        else:
                            continue

                        params = {
                            'DOCUMENT_GUID': r['DOCUMENT_GUID'],
                            'DOCUMENT_TITLE': r['DOCUMENT_TITLE'],
                            'DOCUMENT_LOCATION': r['DOCUMENT_LOCATION'],
                            'DT_CREATED': r['DT_CREATED'],
                            'DT_MODIFIED': r['DT_MODIFIED'],
                            'WIZ_VERSION': r['WIZ_VERSION']
                        }
                        with self.index_db.get_connection() as conn:
                            conn.query(sql, **params)

                    except Exception as e:
                        if self.verbose:
                            print(e, file=sys.stderr)
            else:
                zf.close()
        writer.commit()

    def search(self, keyword, page_num=1, search_in=None, folder_path=None,
                start_date=None, end_date=None, 
                modify_start_date=None, modify_end_date=None):
        """
        搜索笔记
        :param keyword: 关键词
        :param page_num: 页码
        :param search_in: 搜索范围（title 或 content）
        :param folder_path: 文件夹路径
        :param start_date: 创建开始日期
        :param end_date: 创建结束日期
        :param modify_start_date: 修改开始日期
        :param modify_end_date: 修改结束日期
        """
        try:
            idx = self.get_idx()
            searcher = idx.searcher(weighting=scoring.TF_IDF())
            parser = QueryParser(search_in if search_in else 'content', schema=idx.schema)
            page_size = 20
            q = parser.parse(keyword)
            
            # 先获取所有匹配的结果
            results = searcher.search(q, limit=None)  # 不限制结果数量
            total = len(results)
            
            # 收集所有匹配文档的 GUID
            all_guids = [hit.get('path') for hit in results]
            if not all_guids:
                return 0, []

            # 构建基础查询条件
            conditions = []
            guid_list = "','".join(all_guids)
            conditions.append(f"DOCUMENT_GUID in ('{guid_list}')")
            
            # 添加其他过滤条件
            if folder_path:
                conditions.append(f"DOCUMENT_LOCATION LIKE '{folder_path}%'")
            if start_date:
                conditions.append(f"DT_CREATED >= '{start_date} 00:00:00'")
            if end_date:
                conditions.append(f"DT_CREATED <= '{end_date} 23:59:59'")
            if modify_start_date:
                conditions.append(f"DT_MODIFIED >= '{modify_start_date} 00:00:00'")
            if modify_end_date:
                conditions.append(f"DT_MODIFIED <= '{modify_end_date} 23:59:59'")

            # 构建完整的 SQL 查询，包含分页
            offset = (page_num - 1) * page_size
            sql = f"""
                SELECT * FROM WIZ_INDEX 
                WHERE {' AND '.join(conditions)}
                ORDER BY DT_MODIFIED DESC
                LIMIT {page_size} OFFSET {offset}
            """
            
            # 获取总数的查询
            count_sql = f"""
                SELECT COUNT(*) as total FROM WIZ_INDEX 
                WHERE {' AND '.join(conditions)}
            """

            with self.index_db.get_connection() as conn:
                # 获取分页数据
                rows = conn.query(sql).as_dict()
                # 获取总数
                total_count = conn.query(count_sql).first()['total']

            # 构建返回数据
            data = []
            guid_dict = {t['DOCUMENT_GUID']: t for t in rows}
            
            # 获取当前页的搜索结果
            current_page_results = searcher.search(q, limit=None)
            for hit in current_page_results:
                guid = hit.get('path')
                if guid in guid_dict:
                    item = {
                        'highlights': hit.highlights("content"),
                        'document_guid': guid,
                        'title': hit.get('title'),
                        'document_location': guid_dict[guid]['DOCUMENT_LOCATION'],
                        'dt_created': guid_dict[guid]['DT_CREATED'],
                        'dt_modified': guid_dict[guid]['DT_MODIFIED'],
                        'wiz_version': guid_dict[guid]['WIZ_VERSION']
                    }
                    data.append(item)

            return total_count, data

        except Exception as e:
            print(f"Search error: {str(e)}")
            return 0, []

    def get_folders(self):
        """获取文件夹结构"""
        try:
            # 使用 SQL 查询获取所有文件夹
            sql = """
                SELECT DISTINCT DOCUMENT_LOCATION 
                FROM WIZ_INDEX 
                WHERE DOCUMENT_LOCATION != '/' 
                ORDER BY DOCUMENT_LOCATION
            """
            with self.index_db.get_connection() as conn:
                rows = conn.query(sql).as_dict()
            
            # 构建文件夹树结构
            folder_tree = []
            for row in rows:
                location = row['DOCUMENT_LOCATION']
                if not location:
                    continue
                    
                parts = location.strip('/').split('/')
                current = folder_tree
                
                path_parts = []
                for part in parts:
                    if not part:
                        continue
                    path_parts.append(part)
                    current_path = '/' + '/'.join(path_parts)
                    
                    # 查找当前层级是否已存在该文件夹
                    found = False
                    for item in current:
                        if item['path'] == current_path:
                            current = item['children']
                            found = True
                            break
                    
                    if not found:
                        new_folder = {
                            'name': part,
                            'path': current_path,
                            'children': []
                        }
                        current.append(new_folder)
                        current = new_folder['children']
            
            return folder_tree
            
        except Exception as e:
            print(f"Error getting folders: {str(e)}")
            return []


        return total, data
