#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  bunko3.py
#
#  Copyright 2015 sakaisatoru <endeavor2wako@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

from readersub  import ReaderSetting
import aozoradialog
import ndc

import logging
import sys
import codecs
import os.path
import os
import urllib
import zipfile
import datetime
import unicodedata
import bisect
import csv

import gtk
import gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

class aozoraDB(ReaderSetting):
    """ インデックスファイルを読み込んでデータベースを作成する

        作成するデータベース

        作品DB works[ID:record]
            作品ID, 作品名, 副題, 作品名よみ, 文字違い種別,
                                        テキストファイルURL(zipfile入手先)
        人物DB author[ID:record]
            人物ID, 姓名（連結）, 姓よみ名よみ（連結）, 役割フラグ

        インデックス
            人物 - 作品         idxAuthorWorks[人物ID:[作品ID,...], ...]
            NDC - 作品          idxNDCWorks[NDC:[作品ID,...], ...]
            作品 - 人物         idxWorksAuthor[作品ID:[人物ID,...], ...]
            作品 - NDC          idxWorksNDC[作品ID:[NDC,...], ...]
            よみがな - 人物     idxYomiAuthor[(姓名読み,人物ID), ...]
            よみがな - 作品     idxYomiWorks[(作品名読み,作品ID), ...]

    """
    (keyAUTHOR,keyNDC,keyYOMIWORKS,keyYOMIAUTHOR)=range(1,5)

    def __init__(self):
        ReaderSetting.__init__(self)
        self.defaultcsvfile = self.get_value(u'idxfile')
        self.remove_all()

    def search_yomi_itre(self, keytype, keyvalue):
        """ 指定されたキーを検索し、前方部分一致した箇所から
            イテレータを返す
        """
        if keytype == self.keyYOMIAUTHOR:   # 人物よみがな
            pos = bisect.bisect(self.idxYomiAuthor, (keyvalue,u''))
            l = len(self.idxYomiAuthor)
            while pos < l:
                if self.idxYomiAuthor[pos][0].find(keyvalue) == -1:
                    break
                yield self.idxYomiAuthor[pos]
                pos+=1
        elif keytype == self.keyYOMIWORKS:  # 作品よみがな
            pos = bisect.bisect(self.idxYomiWorks, (keyvalue,u''))
            l = len(self.idxYomiWorks)
            while pos < l:
                if self.idxYomiWorks[pos][0].find(keyvalue) == -1:
                    break
                yield self.idxYomiWorks[pos]
                pos+=1
        else:                               # キータイプエラー
            yield (u'',u'')

    def search_works_itre(self, keytype, keyvalue):
        """ 指定されたキーを検索し、結果をイテレータで返す
        """
        if keytype == self.keyAUTHOR:       # 人物IDを渡して作品IDを得る
            if keyvalue in self.idxAuthorWorks:
                for s in self.idxAuthorWorks[keyvalue]:
                    yield s
        elif keytype == self.keyNDC:        # NDCを渡して作品IDを得る
            if keyvalue in self.idxNDCWorks:
                for s in self.idxNDCWorks[keyvalue]:
                    yield s
        elif keytype == self.keyYOMIWORKS:  # よみがな
            for s in self.search_yomi_itre(keytype, keyvalue):
                yield s[1]
        else:                               # キータイプエラー
            yield u''

    def setup(self, fname=u'', ow=False):
        """ 青空インデックスファイルを読み込む
            既に実行済みなら何もしない。
            但し、ow が Trueであれば初期化して再読み込みする。
        """
        if ow:
            self.remove_all()
        if self.works or self.author:
            return

        if not fname:
            fname = self.defaultcsvfile
        indexfile = os.path.join(self.aozoradir, fname)
        with file(indexfile, 'r') as f0:
            rec = 0
            isHeader = True
            fcsv = csv.reader(f0)
            for fi in fcsv:
                if isHeader:
                    isHeader = False
                    continue
                if not fi[14] in self.author:
                # 人物新規登録
                    self.author[fi[14]] = u'%s|%s %s|%s %s|%s' % (
                            fi[14], fi[15], fi[16], fi[17], fi[18], fi[23] )
                if not fi[0] in self.works:
                # 作品新規登録
                    rec += 1
                    self.works[fi[0]] = u'%s|%s|%s|%s|%s|%s' % (
                                        fi[0],fi[1],fi[4],fi[2],fi[9],fi[45] )
                    # よみがな - 作品
                    self.idxYomiWorks.append((fi[2],fi[0]))
                    # よみがな - 人物
                    y = (u'%s %s' % (fi[17], fi[18]), fi[14])
                    if not y in self.idxYomiAuthor:
                        self.idxYomiAuthor.append(y)
                    # 作品 - 人物
                    self.idxWorksAuthor[fi[0]] = [fi[14]]
                    # 作品 - NDC
                    self.idxWorksNDC[fi[0]] = [s for s in fi[8].split()][1:]

                    # NDC - 作品登録
                    for s in fi[8].split(' '):
                        if s != u'NDC':
                            if not s in self.idxNDCWorks:
                                self.idxNDCWorks[s] = [fi[0]]
                            else:
                                self.idxNDCWorks[s].append(fi[0])
                else:
                # 既出作品、人物(著者、翻訳者等）で重複
                    # 作品 - 人物
                    self.idxWorksAuthor[fi[0]].append(fi[14])
                # 人物 - 作品登録
                if not fi[14] in self.idxAuthorWorks:
                    self.idxAuthorWorks[fi[14]] = [fi[0]]
                else:
                    self.idxAuthorWorks[fi[14]].append(fi[0])

        self.idxYomiWorks.sort()
        self.idxYomiAuthor.sort()
        return rec

    def remove_all(self):
        """ 登録内容を全てクリアする
        """
        self.works = {}
        self.author = {}
        self.idxAuthorWorks = {}
        self.idxNDCWorks = {}
        self.idxWorksAuthor = {}
        self.idxWorksNDC = {}
        self.idxYomiAuthor = []
        self.idxYomiWorks = []


class authorlistUI(gtk.VBox):
    """ 著者リストUI
        ListStoreには全てのフィールドを格納する。[]は非表示
        [人物ID], 氏名, [よみがな], 役割
    """
    def __init__(self):
        gtk.VBox.__init__(self)
        self.tree_author = gtk.TreeView()
        self.tree_author.set_model(gtk.ListStore(
                                gobject.TYPE_STRING, gobject.TYPE_STRING,
                                gobject.TYPE_STRING, gobject.TYPE_STRING ))
        # 各項目ごとのレンダリング関数の設定
        self.rend = []
        self.col = []
        for t in [(u'著者名',1),(u'役割',3)]:
            self.rend.append(gtk.CellRendererText())
            self.rend[-1].set_property('editable', False)
            self.col.append(
                        gtk.TreeViewColumn(t[0],self.rend[-1],text=t[1]) )
            #self.col_authorname.set_max_width(180)
            self.col[-1].set_resizable(True)
            self.col[-1].set_sort_column_id(t[1])
            self.tree_author.append_column(self.col[-1])

        self.tree_author.set_rules_hint(True)
        self.tree_author.get_selection().set_mode(gtk.SELECTION_SINGLE)

        lv = gtk.Label()
        lv.set_text(u'よみがな')
        hv = gtk.HBox()
        self.entYomi = gtk.Entry()
        self.entYomi.connect('key_press_event',self.yomi_key_press_event_cb)
        self.entYomi.set_size_request(180,20)
        hv.pack_start(lv,expand=False)
        hv.pack_end(self.entYomi)
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.tree_author)
        self.pack_start(hv, expand=False)
        self.pack_end(self.sw)
        #self.set_size_request(240,100)

        self.selectfile = u''

    def set_database(self, db):
        """ データベースのアタッチ
        """
        self.currentDB = db
        self.set_list(u'') # とりあえず人物全員を表示

    def yomi_key_press_event_cb(self, wiget, event):
        k = event.keyval
        if k == 0xff0d: # enter
            self.set_list(wiget.get_text())
        return False

    def set_list(self, yomi):
        """ よみがなに合致する作家名をセットする
        """
        self.tree_author.get_model().clear()
        for n in self.currentDB.search_yomi_itre(aozoraDB.keyYOMIAUTHOR, yomi):
            self.set_author(n[1])

    def set_author(self, authorID):
        """ UIに一人だけ追加する
        """
        s = self.currentDB.author[authorID].split(u'|')
        self.tree_author.get_model().append((s[0],s[1],s[2],s[3]))

    def get_selected_item(self):
        """ 選択された著者のIDを返す
        """
        # この操作で返されるのは
        # c データモデルオブジェクト、ここではgtk.ListStore
        # d 選択された行
        (c,d) = self.tree_author.get_selection().get_selected_rows()  # 選択された行
        f = False
        try:
            iters = [c.get_iter(p) for p in d]
            # ここでは1行しか選択させないが複数行の選択に無改造で対応すべく
            # for で回している
            for i in iters:
                self.selectfile = c.get_value(i, 0)
            f = True
        except IndexError:
            pass
        return f

    def get_value(self):
        """ 選択された人物IDを返す
        """
        return self.selectfile if self.get_selected_item() else None


class workslistUI(gtk.ScrolledWindow):
    """ 作品リストUI

        表示フィールド
        作品名 副題　著者名  文字遣い種別 NDC

        リストストア
        作品ID|作品名|副題|作品名読み|文字違い種別|NDC|著者名|テキストファイルURL
    """
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        # 作品リスト
        self.tv = gtk.TreeView(model=gtk.ListStore(
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING ))
        self.tv.set_rules_hint(True)
        self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)#(gtk.SELECTION_SINGLE)
        self.tv.set_headers_clickable(True)

        # 各項目ごとのレンダリング関数の設定
        # 見出し、連結フィールド位置、幅初期値
        self.col = []
        for i in [  (u'作品名', 1, 200, gobject.TYPE_STRING),
                    (u'副題', 2, 175, gobject.TYPE_STRING),
                    (u'著者', 6, 70, gobject.TYPE_STRING),
                    (u'NDC分類', 5, 90, gobject.TYPE_STRING),
                    (u'仮名遣い', 4, 80, gobject.TYPE_STRING)]:
            self.col.append(gtk.TreeViewColumn(i[0],
                                gtk.CellRendererText(), text=i[1] ))
            self.col[-1].set_sort_column_id(i[1])
            self.col[-1].set_resizable(True)
            self.col[-1].set_clickable(True)
            self.col[-1].set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.col[-1].set_fixed_width(i[2])
            self.tv.append_column(self.col[-1])

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add(self.tv)
        self.set_size_request(640,300)

        self.selectfile = None
        self.selectURL = None

    def set_list(self, key, keytype):
        """ 該当する作品リストを得る
            作品DB works[ID:record]
                作品ID, 作品名, 副題, 作品名よみ, 文字違い種別,
                                            テキストファイルURL(zipfile入手先)
            人物DB author[ID:record]
                人物ID, 姓名（連結）, 姓よみ名よみ（連結）, 役割フラグ
        """
        self.tv.get_model().clear()
        for i in self.currentDB.search_works_itre(keytype, key):
            n = self.currentDB.works[i].split('|')
            ndc = u''
            author = []
            if n[0] in self.currentDB.idxWorksNDC:
                for i in self.currentDB.idxWorksNDC[n[0]]:
                    ndc += i+u' '
            if n[0] in self.currentDB.idxWorksAuthor:
                for i in self.currentDB.idxWorksAuthor[n[0]]:
                    if author != []:
                        author.append(u'\n')
                    author.append(self.currentDB.author[i].split('|')[1])
                    if self.currentDB.author[i].split('|')[3] != u'著者':
                        author.append(
                            u'(%s)' % self.currentDB.author[i].split('|')[3])
            self.tv.get_model().append((n[0],n[1],n[2],n[3],n[4],
                                                ndc,u''.join(author),n[5]))

    def set_database(self, db):
        """ データベースのアタッチ
        """
        self.currentDB = db
        self.set_list(u'', aozoraDB.keyYOMIWORKS)

    def get_selected_item(self):
        """ 選択された著者のIDを返す
        """
        # この操作で返されるのは
        # c データモデルオブジェクト、ここではgtk.ListStore
        # d 選択された行
        (c,d) = self.tv.get_selection().get_selected_rows()  # 選択された行
        f = False
        try:
            iters = [c.get_iter(p) for p in d]
            # ここでは1行しか選択させないが複数行の選択に無改造で対応すべく
            # for で回している
            for i in iters:
                self.selectfile = c.get_value(i, 0)
                self.selectURL = c.get_value(i, 7)
            f = True
        except IndexError:
            pass
        return f

    def get_value(self):
        """ 選択された作品IDとURLを返す
        """
        if self.get_selected_item():
            return self.selectfile, self.selectURL
        else:
            return None, None

class AuthorWorksUI(gtk.HPaned):
    def __init__(self, exit_cb):
        gtk.HPaned.__init__(self)

        self.authorlist = authorlistUI()
        self.authorlist.sw.child.connect('row_activated',
                                        self.author_row_activated_treeview_cb)
        self.workslist = workslistUI()
        self.workslist.child.connect('row_activated',
                                        self.works_row_activated_treeview_cb)
        self.add1(self.authorlist)
        self.add2(self.workslist)
        self.worksID = None
        self.worksURL = None
        self.exit_cb = exit_cb  # 処理終了用出口関数

    def author_listup(self, authorIDs):
        """ 人物IDをリストで受取り、関連する作品を全てリストアップする
        """
        self.authorlist.sw.child.get_model().clear()
        self.workslist.child.get_model().clear()
        for i in authorIDs:
            self.authorlist.set_author(i)
            self.workslist.set_list(i, aozoraDB.keyAUTHOR)

    def author_row_activated_treeview_cb(self, path, viewcol, col):
        """ 人物をクリックした時の処理
        """
        self.authorlist.get_selected_item()
        authorID = self.authorlist.get_value()
        self.workslist.set_list(authorID, aozoraDB.keyAUTHOR)

    def works_row_activated_treeview_cb(self, path, viewcol, col):
        """ 作品をクリックしたときの処理
        """
        self.worksID, self.worksURL = self.workslist.get_value()
        self.exit_cb(self, gtk.RESPONSE_ACCEPT)

    def get_value(self):
        self.worksID, self.worksURL = self.workslist.get_value()
        return self.worksID, self.worksURL

    def set_database(self, db):
        self.currentDB = db
        self.authorlist.set_database(self.currentDB)
        self.workslist.set_database(self.currentDB)



class BunkoUI(aozoradialog.ao_dialog, ReaderSetting):
    def __init__(self, *args, **kwargs):
        ReaderSetting.__init__(self)
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)

        self.db = aozoraDB()
        self.checkindexfile()
        self.db.setup()

        self.works = AuthorWorksUI(self.response_cb)
        self.works.set_database(self.db)

        self.vbox.pack_start(self.works)
        self.vbox.show_all()

        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title(u'インデックスによる検索')

        self.selectfile = u''
        self.selectzip = u''
        self.selectworksid = 0

    def filter_works2author(self, worksID):
        """ 作品IDを渡してその作者を得、関連作品全てをリストアップする
        """
        try:
            self.works.author_listup(self.db.idxWorksAuthor[worksID])
        except KeyError:
            pass

    def checkindexfile(self, ow=False):
        """ インデックスファイルのチェック
            ow True であれば上書き
        """
        indexfileurl = ''
        localfile = os.path.join(self.aozoradir,
                            os.path.basename(self.get_value(u'idxfileURL')))
        if ow:
            os.remove(localfile)
        if not os.path.isfile(localfile):
            rv = self.download(self.get_value(u'idxfileURL'), localfile)
            if not rv:
                aozoradialog.msgerrinfo(u'ダウンロードに失敗しました。',self)
                return None

            a = zipfile.ZipFile( localfile, u'r' )
            a.extractall(self.aozoradir)
            self.set_value(u'idxfile', a.namelist()[0])
        return os.path.join(self.aozoradir,self.get_value(u'idxfile'))

    def download(self, url, localfile=u'', ow=True):
        """ ダウンロード下請け
            ow : True で上書きダウンロード
        """
        rv = True
        if localfile == u'':
            localfile = os.path.join(self.aozoradir, os.path.basename(url))
        if not ow and os.path.isfile(localfile):
            # ファイルがあればダウンロードしない
            rv = aozoradialog.msgyesno(u'既にダウンロードされています。上書きしますか？',self)
            if rv != gtk.RESPONSE_YES:
                return (True, localfile)
        try:
            urllib.urlretrieve(url, localfile)
        except IOError:
            # ダウンロードに失敗
            #logging.error( u'Download error : ' % url )
            rv = False
        return (rv, localfile)

    def get_filename(self):
        """ ダウンロードしてファイル名、ZIP名、作品IDを返す
        """
        self.selectworksid, self.selectzip = self.works.get_value()
        f, sMes = self.download(self.selectzip, ow=False)
        if not f:
            aozoradialog.msgerrinfo(u'ダウンロードに失敗しました。', self)
            self.selectfile = u''
            self.selectzip = u''
            self.selectworksid = 0
        else:
            a = zipfile.ZipFile(sMes, u'r' )
            a.extractall(self.aozoratextdir)
            for b in a.namelist():
                if os.path.basename(b)[-4:] == '.txt':
                    self.selectfile = os.path.join(self.aozoratextdir, b)
                    self.selectzip = sMes

        return self.selectfile, self.selectzip, self.selectworksid



