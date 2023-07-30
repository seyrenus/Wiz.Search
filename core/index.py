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
            #FIXME: create table using another way
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
        self.schema = Schema(title=TEXT(stored=True), path=ID(stored=True),
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

    def search(self, keyword, page_num):
        idx = self.get_idx()
        searcher = idx.searcher(weighting=scoring.TF_IDF())
        parser = QueryParser("content", schema=idx.schema)
        page_size = 20
        q = parser.parse(keyword)
        results = searcher.search_page(q, page_num, pagelen=page_size)
        total = len(results)
        data = []
        for hit in results:
            item = {
                'highlights': hit.highlights("content"),
                'document_guid': hit.get('path'),
                'title': hit.get('title')
            }
            data.append(item)

        document_guid_list = [t['document_guid'] for t in data]
        if len(document_guid_list) > 0:
            sql = """select * from WIZ_INDEX where DOCUMENT_GUID in ('%s')""" % "','".join(document_guid_list)
            with self.index_db.get_connection() as conn:
                rows = conn.query(sql).as_dict()
            guid_dict = {t['DOCUMENT_GUID']: t for t in rows}
            for t in data:
                item = guid_dict.get(t['document_guid'])
                if item is not None:
                    t['document_location'] = item['DOCUMENT_LOCATION']
                    t['dt_created'] = item['DT_CREATED']
                    t['dt_modified'] = item['DT_MODIFIED']
                    t['wiz_version'] = item['WIZ_VERSION']
                else:
                    t['document_location'] = ''
                    t['dt_created'] = ''
                    t['dt_modified'] = ''
                    t['wiz_version'] = ''

        return total, data
