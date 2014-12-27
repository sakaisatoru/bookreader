#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright 2014 sakaisatoru <endeavor2wako@gmail.com>
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

""" booklist.py
    ダウンロードされた青空文庫を開く
"""

from __future__ import with_statement

from readersub import ReaderSetting, AozoraDialog
from aozoracard import AuthorListData, BookListData
from formater import Aozora
from logview import Logviewer
import sys, codecs, re, os.path, datetime, unicodedata, logging
import gtk, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)


class BookshelfUI(gtk.Window, ReaderSetting):
    """ 本棚のUI
        +-----------------------------+
        |   directory          button |
        +----------+------------------+
        |著作者    |作品一覧           |
        |          |                  |
        |          |                  |
        +----------+------------------+
        |   open           cancel     |
        +-----------------------------+
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        self.az = Aozora()
        currentdir = self.get_value(u'aozoradir')

        self.set_title(u'このPCにある青空文庫')

        self.lastselectfile = None
        self.ack = gtk.RESPONSE_NONE

        # ディレクトリ
        self.enDirectry = gtk.Entry()
        self.enDirectry.set_text(currentdir)
        self.enDirectry.set_size_request(522, 24)
        self.btnDirectry = gtk.Button(stock=gtk.STOCK_OPEN)
        self.btnDirectry.connect('clicked', self.clicked_btnDirectry_cb )
        self.hbox2 = gtk.HBox()
        self.hbox2.set_size_request(640, 36)
        self.hbox2.pack_start(self.enDirectry, True, True, 8)
        self.hbox2.pack_end(self.btnDirectry, False, True, 0)

        # 著者リスト
        self.al_data = AuthorListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.al_data.set_rules_hint(True)
        self.al_data.get_selection().set_mode(gtk.SELECTION_SINGLE)
        #self.al_data.connect("row-activated", self.row_activated_treeview_cb)
        self.al_data.connect("cursor_changed", self.cursor_changed_treeview_cb)
        self.al_data.set_headers_clickable(True)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.al_data)
        self.sw.set_size_request(240,400)

        # 作品リスト
        self.bl_data = BookListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.bl_data.set_rules_hint(True)
        self.bl_data.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.bl_data.connect("row-activated", self.row_activated_treeview_cb)
        #self.bl_data.connect("cursor_changed", self.cursor_changed_treeview_cb)
        self.bl_data.set_headers_clickable(True)

        self.sw2 = gtk.ScrolledWindow()
        self.sw2.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw2.add(self.bl_data)

        self.hbox = gtk.HPaned()
        self.hbox.pack1(self.sw)
        self.hbox.pack2(self.sw2)

        self.btnClear = gtk.Button(stock=gtk.STOCK_CLEAR)
        self.btnClear.connect('clicked', self.clicked_btnClear_cb )
        self.btnOk = gtk.Button(stock=gtk.STOCK_OPEN)
        self.btnOk.connect('clicked', self.clicked_btnOk_cb )
        self.btnCancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.btnCancel.connect('clicked', self.clicked_btnCancel_cb )
        self.btnBox = gtk.HButtonBox()
        self.btnBox.set_size_request(640,44)
        self.btnBox.set_layout(gtk.BUTTONBOX_SPREAD)
        self.btnBox.pack_start(self.btnClear, False, False, 0)
        self.btnBox.pack_start(self.btnOk, False, False, 0)
        self.btnBox.pack_end(self.btnCancel, False, False, 0)

        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.hbox2, False)
        self.vbox.pack_start(self.hbox)
        self.vbox.pack_end(self.btnBox, False)
        self.add(self.vbox)
        self.set_position(gtk.WIN_POS_CENTER)

        self.connect('delete_event', self.delete_event_cb)
        self.connect('key-press-event', self.key_press_event_cb )

        self.get_booklist(self.enDirectry.get_text())# ディレクトリ内の作品一覧
        self.get_authorlist()   # 著者一覧

    def clicked_btnDirectry_cb(self, widget):
        """ 青空文庫ファイルのあるディレクトリを開く
        """
        fl = gtk.FileFilter()
        fl.set_name(u'青空文庫(*.txt)')
        fl.add_pattern( '*.txt' )
        fl2 = gtk.FileFilter()
        fl2.set_name(u'全て')
        fl2.add_pattern( '*.*')

        dlg = gtk.FileChooserDialog( u'青空文庫ファイルのあるディレクトリ',
                    action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        dlg.add_filter(fl)
        dlg.add_filter(fl2)
        res = dlg.run()
        if res == gtk.RESPONSE_OK:
            fn = dlg.get_filename()
            dlg.destroy()
            self.enDirectry.set_text(fn)
            self.get_booklist(fn)
        else:
            dlg.destroy()

    def get_authorlist(self):
        """ 作品一覧より著作者一覧を得る
        """
        self.al_data.get_model().clear()
        at = {}
        dm = self.bl_data.get_model()
        for s in dm:
            if s[1] in at:
                pass
            else:
                at[s[1]] = True
                self.al_data.get_model().append((s[1], u'', u''))

    def get_booklist(self, dirname, filter=u''):
        """ 指定されたディレクトリのファイル一覧を得る
        """
        self.bl_data.get_model().clear()
        for fn in os.listdir(dirname):
            fullpath = os.path.join(dirname,fn)
            if os.path.isfile(fullpath) == True:
                if fn.split( '.' )[-1] == 'txt':
                    book, author = self.az.get_booktitle_sub(fullpath)
                    if filter != u'':
                        if filter != author:
                            continue
                    self.bl_data.get_model().append(
                                    (book,      # 作品名
                                    author,     # 著者
                                    fullpath )  # パス
                                    )

    def get_selectbook(self):
        """ 作品リスト上で選択されている作品を取得する
        """
        (c,d) = self.bl_data.get_selection().get_selected_rows()  # 選択された行
        f = False
        try:
            iters = [c.get_iter(p) for p in d]
            for i in iters:
                self.lastselectfile = c.get_value(i, 2) # full path
                f = True
        except:
            pass
        return f

    def cursor_changed_treeview_cb(self, widget):
        """ 著者リストでカーソル移動した時の処理
            作品リストを取得する
        """
        (c,d) = self.al_data.get_selection().get_selected_rows()  # 選択された行
        f = False
        try:
            iters = [c.get_iter(p) for p in d]
            for i in iters:
                self.selectauthor = c.get_value(i, 0)
            f = True
        except:
            pass
        if f:
            self.get_booklist(self.enDirectry.get_text(), self.selectauthor)
        return f

    def row_activated_treeview_cb(self, path, view_column, column ):
        """ 作品リストをダブルクリックした時の処理
        """
        self.get_selectbook()
        self.exitall()
        self.ack = gtk.RESPONSE_OK

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            self.exitall()
            self.ack = None
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def clicked_btnClear_cb(self, widget):
        """ 著者フィルタの解除
        """
        self.get_booklist(self.enDirectry.get_text())# ディレクトリ内の作品一覧
        self.get_authorlist()   # 著者一覧

    def clicked_btnOk_cb(self, widget):
        """ 開くボタンをクリックした時の処理
        """
        if self.get_selectbook() == False:
            # 作品が選択されていなければ戻る
            return False
        self.exitall()
        self.ack = gtk.RESPONSE_OK

    def clicked_btnCancel_cb(self, widget):
        self.exitall()
        self.ack = None

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def get_filename(self):
        return self.lastselectfile

    def exitall(self):
        """ 終端処理
        """
        self.hide_all()
        gtk.main_quit()

    def run(self):
        """ エントリー
        """
        self.show_all()
        self.set_modal(True)
        gtk.main()
        return self.ack

if __name__ == '__main__':
    a = BookshelfUI()
    a.run()


