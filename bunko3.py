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

from readersub_nogui  import ReaderSetting
from readersub  import DownloadUI
import aozoradialog
import ndc

import logging
import os.path
import os
import urllib
import zipfile
import bisect
import csv
import subprocess

import gtk
import gobject

class aozoraDB(ReaderSetting):
    """ インデックスファイルを読み込んでデータベースを作成する

        作成するデータベース

        作品DB works[ID:record]
            作品ID, 作品名, 副題, 作品名よみ, 文字違い種別,
                                        テキストファイルURL(zipfile入手先),
                                        XHTMLファイルURL
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
                    self.works[fi[0]] = u'%s|%s|%s|%s|%s|%s|%s' % (
                                        fi[0],fi[1],fi[4],fi[2],fi[9],fi[45],fi[50] )
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


class authorlistUI(gtk.ScrolledWindow):
    """ 著者リストUI
        ListStoreには全てのフィールドを格納する。[]は非表示
        [人物ID], 氏名, [よみがな], 役割
    """
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
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

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add(self.tree_author)
        self.set_size_request(160,300)

        self.selectfile = u''

    def set_database(self, db):
        """ データベースのアタッチ
        """
        self.currentDB = db
        self.set_list(u'') # とりあえず人物全員を表示

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

        self.tv = gtk.TreeView(model=gtk.ListStore(
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING, gobject.TYPE_STRING,
                        gobject.TYPE_STRING ))
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
        self.selectXHTML = None

    def set_list(self, key, keytype):
        """ 該当する作品リストを得る
            作品DB works[ID:record]
                作品ID, 作品名, 副題, 作品名よみ, 文字違い種別,
                                            テキストファイルURL(zipfile入手先),
                                            XHTMLファイルURL
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
                                                ndc,u''.join(author),n[5], n[6]))

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
                self.selectXHTML = c.get_value(i, 8)
            f = True
        except IndexError:
            pass
        return f

    def get_value(self):
        """ 選択された作品IDとURLを返す
        """
        if self.get_selected_item():
            return self.selectfile, self.selectURL, self.selectXHTML
        else:
            return None, None, None


class AuthorWorksUI(gtk.HPaned):
    def __init__(self, exit_cb):
        gtk.HPaned.__init__(self)

        self.authorlist = authorlistUI()
        self.authorlist.child.connect('row_activated',
                                        self.author_row_activated_treeview_cb)
        self.workslist = workslistUI()
        self.workslist.child.connect('row_activated',
                                        self.works_row_activated_treeview_cb)

        self.add1(self.authorlist)
        self.add2(self.workslist)
        self.worksID = None
        self.worksURL = None
        self.worksXHTML = None
        self.exit_cb = exit_cb  # 処理終了用出口関数

    def author_set_yomi(self, yomi):
        """
        """
        self.authorlist.set_list(yomi)

    def author_listup(self, authorIDs):
        """ 人物IDをリストで受取り、関連する作品を全てリストアップする
        """
        self.authorlist.child.get_model().clear()
        self.workslist.child.get_model().clear()
        for i in authorIDs:
            self.authorlist.set_author(i)
            self.workslist.set_list(i, aozoraDB.keyAUTHOR)

    def works_listup(self, key, keytype):
        """
        """
        self.workslist.set_list(key, keytype)

    def author_row_activated_treeview_cb(self, path, viewcol, col):
        """ 人物をクリックした時の処理
        """
        self.authorlist.get_selected_item()
        authorID = self.authorlist.get_value()
        self.workslist.set_list(authorID, aozoraDB.keyAUTHOR)

    def works_row_activated_treeview_cb(self, path, viewcol, col):
        """ 作品をクリックしたときの処理
        """
        self.worksID, self.worksURL, self.worksXHTML = self.workslist.get_value()
        self.exit_cb(self, gtk.RESPONSE_ACCEPT)

    def get_value(self):
        self.worksID, self.worksURL, self.worksXHTML = self.workslist.get_value()
        return self.worksID, self.worksURL, self.worksXHTML

    def set_database(self, db):
        self.currentDB = db
        self.authorlist.set_database(self.currentDB)
        self.workslist.set_database(self.currentDB)


class ndcUI(gtk.Table, ndc.NDC):
    """ 日本十進分類による検索UI
    """
    def __init__(self):
        ndc.NDC.__init__(self)
        gtk.Table.__init__(self)

        self.evbox = []

        self.restore_rui(True)
        self.restore_kou(0, True)
        self.restore_moku(0, True)

        # ヘッダ
        self.lvtmp = []
        x = 0
        y = 0
        for j in [1, 7, 1, 22, 1, 22]:
            self.lvtmp.append(gtk.Label(u'　'*j))
            self.lvtmp[-1].set_alignment(0.0, 0.5)
            self.attach(self.lvtmp[-1], x, x+1, y, y+1)
            x += 1

    def button_press_event_cb(self, widget, event):
        """
        """
        rv = False
        if event.button == 1:
            """ マウス左ボタン
            """
            lv = widget.child.get_text()
            k = lv.split(u' ')[0]
            if len(k) == 1:
                # 類が選択された
                self.restore_rui()
                widget.child.set_markup(u'<b>%s</b>' % lv)
                self.restore_kou(int(k))
                self.restore_moku(0)
                rv = True
            elif len(k) == 3:
                if widget.get_name().split(u' ')[0] == u'3':
                    # 綱が選択された
                    self.restore_kou()
                    widget.child.set_markup(u'<b>%s</b>' % lv)
                    self.restore_moku(int(k[1]))
                    rv = True
                else:
                    # 要目が選択された
                    self.restore_moku()
                    widget.child.set_markup(u'<b>%s</b>' % lv)
                    self.moku = k
        return rv

    def restore_colunm(self, x, y, pos, itre, init=False):
        for i in itre:
            if init:
                self.evbox.append(gtk.EventBox())
                self.evbox[-1].set_name( u'%s %s' % (x, y))
                self.evbox[-1].add(gtk.Label(i))
                self.evbox[-1].child.set_alignment(0.0, 0.5)
                self.evbox[-1].connect('button_press_event',
                                            self.button_press_event_cb)
                self.attach(self.evbox[-1], x, x+1, y, y+1)
            else:
                self.evbox[pos].child.set_text(i)
                pos += 1
            y += 1

    def restore_rui(self, init=False):
        """ 類をセット
        """
        self.restore_colunm(1,0,0,self.rui_itre(), init)

    def restore_kou(self, rui=-1, init=False):
        """ 綱をセット
        """
        if rui != -1:
            self.rui = rui
        self.restore_colunm(3,0,10,self.moku_itre(self.rui,-1), init)

    def restore_moku(self, kou=-1, init=False):
        """ 目をセット
        """
        if kou != -1:
            self.kou = kou
        self.restore_colunm(5,0,20,self.moku_itre(self.rui,self.kou), init)

    def get_value(self):
        """ 選択された類、綱、要目を返す
        """
        return (self.rui, self.kou, self.moku)


class selectNDCsub(aozoradialog.ao_dialog):
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        self.ndc = ndcUI()
        self.vbox.pack_start(self.ndc)
        self.connect('button_press_event',self.button_press_event_cb)
        self.vbox.show_all()
        self.set_title(u'NDCを選んでください')

    def button_press_event_cb(self, widget, event):
        self.response_cb(widget, gtk.RESPONSE_ACCEPT)

    def get_value(self):
        return self.ndc.get_value()


class BunkoUI(aozoradialog.ao_dialog, ReaderSetting):
    def __init__(self, *args, **kwargs):
        ReaderSetting.__init__(self)
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)

        self.db = aozoraDB()
        self.checkindexfile()
        self.db.setup()

        self.works = AuthorWorksUI(self.response_cb)
        self.works.set_database(self.db)

        # 検索フィルタ
        lvAuthor = gtk.Label(u'人物よみ')
        self.entAuthor = gtk.Entry()
        self.entAuthor.set_width_chars(16)
        self.entAuthor.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY,gtk.STOCK_CLEAR)
        self.entAuthor.connect('icon_press',lambda a,b,c:a.set_text(u''))
        self.entAuthor.connect('key_press_event',self.entAuthor_key_press_event_cb)
        lv = gtk.Label()
        lv.set_text(u'作品よみ')
        self.entYomi = gtk.Entry()
        self.entYomi.set_width_chars(16)
        self.entYomi.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY,gtk.STOCK_CLEAR)
        self.entYomi.connect('icon_press', lambda a,b,c:a.set_text(u''))
        self.entYomi.connect('key_press_event',self.entYomi_key_press_event_cb)

        lvNDC = gtk.Label()
        lvNDC.set_text(u'NDC')
        self.entNDC = gtk.Entry(max=3)
        self.entNDC.set_width_chars(4)
        self.entNDC.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY,gtk.STOCK_FIND)
        self.entNDC.connect('icon_press',self.NDC_icon_press_cb)
        self.entNDC.connect('key_press_event',self.entNDC_key_press_event_cb)

        self.chkDL = gtk.CheckButton(label=u'上書きダウンロード')

        hv = gtk.HBox()
        hv.pack_start(lvAuthor)
        hv.pack_start(self.entAuthor,padding=10)
        hv.pack_start(lv)
        hv.pack_start(self.entYomi, fill=True,padding=10)
        hv.pack_start(lvNDC)
        hv.pack_start(self.entNDC,padding=10)
        hv.pack_end(self.chkDL,padding=10)

        self.vbox.pack_start(hv,expand=False)
        self.vbox.pack_start(self.works)
        self.vbox.show_all()

        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title(u'インデックスによる検索')

        self.selectfile = u''
        self.selectzip = u''
        self.selectxhtml = u''
        self.selectworksid = 0

    def entAuthor_key_press_event_cb(self, wiget, event):
        """ 人物よみ検索
        """
        if event.keyval == 0xff0d: # enter
            self.works.author_set_yomi(wiget.get_text())
        return False

    def entYomi_key_press_event_cb(self, wiget, event):
        """ 作品よみ検索
        """
        if event.keyval == 0xff0d: # enter
            self.works.works_listup(wiget.get_text(), aozoraDB.keyYOMIWORKS)
        return False

    def entNDC_key_press_event_cb(self, wiget, event):
        """ NDC検索
        """
        if event.keyval == 0xff0d: # enter
            self.works.works_listup(wiget.get_text(), aozoraDB.keyNDC)
        return False

    def NDC_icon_press_cb(self, icon_pos, event, data):
        """ ダイアログを表示してNDCを選択する
        """
        dlg = selectNDCsub(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                            buttons=(gtk.STOCK_CLOSE,  gtk.RESPONSE_CLOSE))
        while dlg.run() == gtk.RESPONSE_ACCEPT:
            key = dlg.get_value()[2]
            self.entNDC.set_text(key)
            self.works.works_listup(key, aozoraDB.keyNDC)
        dlg.destroy()

    def filter_works2author(self, worksID):
        """ 作品IDを渡してその作者を得、関連作品全てをリストアップする
            インデックスに作品IDが登録されていればTrueを返す。
        """
        rv = False
        if not worksID in self.db.idxWorksAuthor:
            self.__reloadindexfile()
        if worksID in self.db.idxWorksAuthor:
            self.works.author_listup(self.db.idxWorksAuthor[worksID])
            rv = True
        return rv

    def __reloadindexfile(self):
        """ インデックスファイルを再読み込み
            読み込むように指示したなら True を返す
        """
        rv = aozoradialog.msgyesno(u'テキストを新着情報から開きましたか？登録情報がインデックス内に見当たりません。インデックスを更新しますか？',self)
        if rv == gtk.RESPONSE_YES:
            # インデックスファイルダウンロード
            self.checkindexfile(True)
            self.db.setup(ow=True)
            return True
        return False

    def checkindexfile(self, ow=False):
        """ インデックスファイルのチェック
            ow True であれば上書き
        """
        rv = False
        targetfile = os.path.join(self.aozoradir, self.get_value(u'idxfile'))
        localfile = os.path.join(self.aozoradir,
                        os.path.basename(self.get_value(u'idxfileURL')))
        if ow:
            try:
                os.remove(targetfile)
                os.remove(localfile)
            except OSError:
                pass
        if not os.path.isfile(targetfile):
            if not os.path.isfile(localfile):
                dlg = DownloadUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                            buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL))
                if dlg.set_download_url(self.get_value(u'idxfileURL'), ow):
                    rv = False if dlg.run() == gtk.RESPONSE_CANCEL else True
                localfile = dlg.get_localfilename()
                dlg.destroy()
                if not rv:
                    aozoradialog.msgerrinfo(u'ダウンロードに失敗しました。ネットワークの接続を確認してください。',self)
                    return None
            a = self.__ZipFile( localfile, u'r' )
            a.extractall(self.aozoradir)
            self.set_value(u'idxfile', a.namelist()[0])
        return os.path.join(self.aozoradir,self.get_value(u'idxfile'))

    def get_filename(self):
        """ ダウンロードしてファイル名、ZIP名、作品IDを返す
        """
        f = False
        self.selectworksid, self.selectzip, self.selectxhtml = self.works.get_value()
        if self.selectworksid == None:
            # テキストが選択されていない
            aozoradialog.msgerrinfo(u'作品を選択してください。', self)
            self.selectfile = u''
            self.selectzip = u''
            self.selectworksid = 0
            return self.selectfile, self.selectzip, self.selectworksid

        dlg = DownloadUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL))
        if dlg.set_download_url(self.selectzip if self.selectzip != u'' else self.selectxhtml,
                                    ow=self.chkDL.get_active()):
            f = False if dlg.run() == gtk.RESPONSE_CANCEL else True
        localfile = dlg.get_localfilename()
        dlg.destroy()
        if f:
            if self.selectzip != u'':
                a = self.__ZipFile(localfile, u'r' )
                a.extractall(self.aozoratextdir)
                for b in a.namelist():
                    if os.path.basename(b)[-4:].lower() == '.txt':
                        self.selectfile = os.path.join(self.aozoratextdir, b)
                        self.selectzip = a.filename
            else:
                rv = aozoradialog.msgyesno(u'このテキストはxhtml形式(ファイルは %s)です。 \n閲覧するにはブラウザが必要です。続けますか？' % localfile, self )
                if rv == gtk.RESPONSE_YES:
                    subprocess.Popen(['xdg-open', localfile])
        else:
            aozoradialog.msgerrinfo(u'ダウンロードに失敗しました。ネットワークの接続を確認してください。', self)
            self.selectfile = u''
            self.selectzip = u''
            self.selectworksid = 0

        return self.selectfile, self.selectzip, self.selectworksid

    def websearch_authors(self, worksID):
        """ 作品IDを渡して関連人物名をweb検索する
        """
        if not worksID in self.db.idxWorksAuthor:
            # インデックスファイルが旧い
            self.__reloadindexfile()
        if worksID in self.db.idxWorksAuthor:
            for i in self.db.idxWorksAuthor[worksID]:
                # 引数に空白が含まれると名前が分断されて検索されることがあるので、
                # 空白を%20に置換してから検索する。
                subprocess.Popen(['xdg-open',
                    'https://www.google.co.jp/search?q="%s"' % self.db.author[i].split('|')[1].replace(u' ', u'%20').replace(u'　', u'%20')])

    def __ZipFile(self, fn, mode):
        """ zipfile.ZipFile の差し替え
            zipfile 以外のファイルが指定された場合は間に合わせのzipfileを
            作成して返す
        """
        try:
            a = zipfile.ZipFile(fn, u'r')
        except zipfile.BadZipfile:
            # 間に合わせのzipfile を作成する
            n = os.path.basename(fn).split('.')[0]
            tmpzipname = os.path.join(self.aozoradir,
                            u'%s%X.zip' % (n, hash(n)) )
            a = zipfile.ZipFile(tmpzipname, u'a')
            a.write(fn, os.path.basename(fn))
            a.close()
            a = zipfile.ZipFile(tmpzipname, u'r')
        return a



