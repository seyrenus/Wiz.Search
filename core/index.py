# -*- coding: utf-8 -*-
# created by restran on 2019/05/06
from __future__ import unicode_literals, absolute_import

import os.path
import shutil
import zipfile
import sys
from datetime import datetime
import records
import jieba
from bs4 import BeautifulSoup
from jieba.analyse import ChineseAnalyzer
from whoosh import scoring
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.filedb.filestore import FileStorage
from whoosh.index import create_in
from whoosh.qparser import QueryParser
from whoosh.query import And, Prefix, TermRange

jieba.setLogLevel(jieba.logging.ERROR)


CURRENT_INDEX_VERSION = 2

CREATE_WIZ_INDEX_TABLE_SQL = """
create table WIZ_INDEX
(
  DOCUMENT_GUID     char(36)     not null primary key,
  DOCUMENT_TITLE    varchar(768) not null,
  DOCUMENT_LOCATION varchar(768),
  DT_CREATED        char(19),
  DT_MODIFIED       char(19),
  DT_DATA_MODIFIED  char(19), -- 笔记数据修改时间
  WIZ_VERSION       int64,
  DT_INDEXED        integer(4)
);
"""

# 版本表
CREATE_WIZ_INDEX_VERSION_TABLE_SQL = """
create table WIZ_INDEX_VERSION
(
  name      char(10)     not null primary key,
  version  int64
);
"""


class WizIndex(object):
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'  # 时间格式

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
                # 检查 WIZ_INDEX_VERSION 表是否存在
                result = conn.query("SELECT name FROM sqlite_master WHERE type='table' AND name='WIZ_INDEX_VERSION'").first()
                if not result:
                    # 如果表不存在，则创建表
                    conn.query(CREATE_WIZ_INDEX_TABLE_SQL)
                    conn.query("INSERT INTO WIZ_INDEX_VERSION (name, version) VALUES ('version', 0)")
                # 查询版本号，如果版本号小于2，需要重建索引
                result = conn.query("SELECT version FROM WIZ_INDEX_VERSION WHERE name = 'version'").first()
                if not result or result['version'] < 2:
                    conn.query('DROP TABLE IF EXISTS WIZ_INDEX')
                    conn.query(CREATE_WIZ_INDEX_TABLE_SQL)
                    conn.query('PRAGMA auto_vacuum = FULL;')
                    conn.query("UPDATE WIZ_INDEX_VERSION SET version=" + str(CURRENT_INDEX_VERSION) + " where name = 'version'")

                    if os.path.exists(self.index_path):
                        shutil.rmtree(self.index_path)

        except:
            pass

        # 如果目录不存在。创建索引目录
        if not os.path.exists(self.index_path):
            os.mkdir(self.index_path)

        analyzer = ChineseAnalyzer()
        self.schema = Schema(
            title=TEXT(stored=True, analyzer=analyzer),
            path=ID(stored=True),
            content=TEXT(stored=True, analyzer=analyzer),
            location=ID(stored=True),
            create_time=DATETIME(stored=True),
            modify_time=DATETIME(stored=True)
        )

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
                                content=r['DOCUMENT_TITLE'] + '\n' + html_content.body.text,
                                location=r['DOCUMENT_LOCATION'],
                                create_time=datetime.strptime(r['DT_CREATED'], self.DATE_FORMAT),
                                modify_time=datetime.strptime(r['DT_DATA_MODIFIED'], self.DATE_FORMAT)
                            )
                            sql = """insert into WIZ_INDEX (DOCUMENT_GUID, DOCUMENT_TITLE, DOCUMENT_LOCATION, DT_CREATED, DT_MODIFIED,DT_DATA_MODIFIED, WIZ_VERSION) 
                            values (:DOCUMENT_GUID, :DOCUMENT_TITLE, :DOCUMENT_LOCATION, :DT_CREATED, :DT_MODIFIED, :DT_DATA_MODIFIED, :WIZ_VERSION)"""
                        elif action == 'update':
                            writer.delete_by_term('path', r['DOCUMENT_GUID'])
                            writer.update_document(
                                path=r['DOCUMENT_GUID'],
                                title=r['DOCUMENT_TITLE'],
                                content=r['DOCUMENT_TITLE'] + '\n' + html_content.body.text,
                                location=r['DOCUMENT_LOCATION'],
                                create_time=datetime.strptime(r['DT_CREATED'], self.DATE_FORMAT),
                                modify_time=datetime.strptime(r['DT_DATA_MODIFIED'], self.DATE_FORMAT)
                            )

                            sql = """update WIZ_INDEX set DOCUMENT_TITLE=:DOCUMENT_TITLE, 
                            DOCUMENT_LOCATION=:DOCUMENT_LOCATION, DT_CREATED=:DT_CREATED, 
                            DT_MODIFIED=:DT_MODIFIED, DT_DATA_MODIFIED=:DT_DATA_MODIFIED, WIZ_VERSION=:WIZ_VERSION where DOCUMENT_GUID=:DOCUMENT_GUID"""

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
                            'DT_DATA_MODIFIED': r['DT_DATA_MODIFIED'],
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
                create_start_date=None, create_end_date=None, 
                modify_start_date=None, modify_end_date=None):
        """
        搜索笔记
        :param keyword: 关键词
        :param page_num: 页码
        :param search_in: 搜索范围（title 或 content）
        :param folder_path: 文件夹路径
        :param create_start_date: 创建开始日期
        :param create_end_date: 创建结束日期
        :param modify_start_date: 修改开始日期
        :param modify_end_date: 修改结束日期
        """
        try:
            idx = self.get_idx()
            searcher = idx.searcher(weighting=scoring.TF_IDF())
            parser = QueryParser(search_in if search_in else 'content', schema=idx.schema)
            page_size = 20

            # whoosh: DATETIME fields do not currently support open-ended ranges.
            # You can simulate an open ended range by using an endpoint far in the past or future.
            if create_start_date and not create_end_date:
                create_end_date = '2099-12-31'
            if create_end_date and not create_start_date:
                create_start_date = '1970-01-01'
            if modify_start_date and not modify_end_date:
                modify_end_date = '2099-12-31'
            if modify_end_date and not modify_start_date:
                modify_start_date = '1970-01-01'

            # 将字符串日期转换为 datetime 对象
            if create_start_date and isinstance(create_start_date, str):
                create_start_date = datetime.strptime(create_start_date + " 00:00:00", self.DATE_FORMAT)
            if create_end_date and isinstance(create_end_date, str):
                create_end_date = datetime.strptime(create_end_date + " 23:59:59", self.DATE_FORMAT)
            if modify_start_date and isinstance(modify_start_date, str):
                modify_start_date = datetime.strptime(modify_start_date + " 00:00:00", self.DATE_FORMAT)
            if modify_end_date and isinstance(modify_end_date, str):
                modify_end_date = datetime.strptime(modify_end_date + " 23:59:59", self.DATE_FORMAT)

            # 如果 folder_path 不以 '/' 结尾，则添加一个 '/'
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            # 构建查询条件
            query_conditions = []
            if keyword:
                query_conditions.append(parser.parse(keyword))
            if folder_path:
                query_conditions.append(Prefix("location", folder_path))
            if create_start_date or create_end_date:
                query_conditions.append(TermRange("create_time", create_start_date, create_end_date))
            if modify_start_date or modify_end_date:
                query_conditions.append(TermRange("modify_time", modify_start_date, modify_end_date))

            # 合并所有查询条件
            final_query = And(query_conditions)

            # 执行查询并分页
            results = searcher.search_page(final_query, page_num, pagelen=page_size)
            total = len(results)

            # 构建返回数据
            data = []
            for hit in results:
                dt_created = hit.get('create_time')
                dt_modified = hit.get('modify_time')

                # 格式化为字符串
                dt_created_str = dt_created.strftime(self.DATE_FORMAT) if dt_created else None
                dt_modified_str = dt_modified.strftime(self.DATE_FORMAT) if dt_modified else None

                data.append({
                    'highlights': hit.highlights("content"),
                    'document_guid': hit.get('path'),
                    'title': hit.get('title'),
                    'document_location': hit.get('location'),
                    'dt_created': dt_created_str,
                    'dt_modified': dt_modified_str,
                })

            return total, data

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
