#!/home/qfpay/python/bin/python
# -*- coding: utf-8 -*-
# Wed Oct 17 12:10:38 CST 2012


import sys
import os.path
import sqlite3


HOME = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(HOME, 'deploy.db')

conn = None

class Sqlite:
    def __init__(self):
        self.conn = sqlite3.connect(db_path)

    def execute(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        ret = cur.fetchall()
        cur.close()
        return ret

    def query(self, sql, isdict=True):
        cur = self.conn.cursor()
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()

        if res and isdict:
            ret = []
            xkeys = [ i[0] for i in cur.description ]
            for item in res:
                ret.append(dict(zip(xkeys, item)))
        else:
            ret = res 
        return ret 

    def insert(self, sql, data):
        cur = self.conn.cursor()
        cur.executemany(sql, data)
        self.conn.commit()
        cur.close()

    def update(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()
        cur.close()

def open():
    db = Sqlite()
    return db
