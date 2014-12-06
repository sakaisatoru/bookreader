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

""" 新着情報の取得

        新着情報の全てのページを参照し、著者名、作品名（副題）、公開日、
        URLのリストを得る。
"""

from __future__ import with_statement

from readersub import ReaderSetting, AozoraDialog, Download
from aozoracard import AuthorList
import sys, codecs, re, os.path, datetime, unicodedata, urllib
from HTMLParser import HTMLParser
import gtk, cairo, pango, pangocairo, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)


class ReadHTMLpage(HTMLParser, ReaderSetting, Download):
    def __init__(self):
        HTMLParser.__init__(self)
        ReaderSetting.__init__(self)

        self.nTableCount = 0
        self.nTrCount = 0
        self.nTdCount = 0
        self.flagTD = False
        self.sData = u''
        self.record=[]
        self.page=[]

    def handle_starttag(self, tag, attrs):
        if tag == u'table':
            self.nTableCount += 1
            self.nTrCount = 0
            self.nTdCount = 0
        elif tag == u'tr':
            self.nTrCount += 1
            self.nTdCount = 0
        elif tag == u'td':
            self.nTdCount += 1
            self.flagTD = True
            self.sData = u''
        elif tag == u'a':
            if self.flagTD == True:
                if self.nTdCount == 2 and self.nTableCount == 2:
                    self.record.append(attrs[0][1])

    def handle_data(self, data):
        if self.nTableCount == 2:
            if self.nTrCount >= 2:
                if self.nTdCount < 4:
                    if self.flagTD == True:
                        self.sData += data.lstrip().rstrip( u' \r\n' )

    def handle_endtag(self, tag):
        if self.nTableCount == 2:
            if tag == u'tr':
                self.page.append(self.record)
                self.record=[]
                print u'\r\n'
            elif tag == u'td':
                if self.nTdCount < 4:
                    self.record.append(self.sData)
                    self.flagTD = False

    def setbaseurl(self, s):
        self.AOZORA_URL = s

    def gethtml(self, n):
        """ 新着情報のページをダウンロードして読み込む
        """
        url = u'%s/%s' % (self.AOZORA_URL,n)
        filename = u'%s/%s' % (self.get_value(u'workingdir'), n)
        try:
            urllib.urlretrieve(url, filename)
        except IOError:
            self.msgerrinfo( u'ダウンロードに失敗しました。ネットワークへの接続状況を確認してください。' )
            return

        with codecs.open( filename, 'r', u'UTF-8' ) as f0:
            self.feed(f0.read())
            self.close()

    def readrecord(self):
        for s in self.page:
            yield s


class BookListData(gtk.TreeView):
    """ 新着リスト
    """
    def __init__(self, *args, **kwargs):
        gtk.TreeView.__init__(self, *args, **kwargs)
        # 公開日
        self.rend_releasedate = gtk.CellRendererText()
        self.rend_releasedate.set_property('editable', False)
        # 作品名
        self.rend_bookname = gtk.CellRendererText()
        self.rend_bookname.set_property('editable', False)
        # URL
        self.rend_bookurl = gtk.CellRendererText()
        self.rend_bookurl.set_property('editable', False)
        # 作家名
        self.rend_authorname = gtk.CellRendererText()
        self.rend_authorname.set_property('editable', False)

        self.col_releasedate = gtk.TreeViewColumn(u'公開日',
                                          self.rend_releasedate,
                                          text=0)
        self.col_releasedate.set_resizable(True)
        self.col_releasedate.set_sort_column_id(0)

        self.col_bookname = gtk.TreeViewColumn(u'作品名等',
                                          self.rend_bookname,
                                          text=1)
        self.col_bookname.set_resizable(True)
        self.col_bookname.set_sort_column_id(1)
        self.col_authorname = gtk.TreeViewColumn(u'作家名等',
                                          self.rend_authorname,
                                          text=2)
        self.col_authorname.set_resizable(True)
        self.col_authorname.set_sort_column_id(2)


        self.append_column(self.col_releasedate)
        self.append_column(self.col_bookname)
        self.append_column(self.col_authorname)

class WhatsNewUI(gtk.Window, ReaderSetting, AozoraDialog, Download):
    """ UI
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        AozoraDialog.__init__(self)

        self.AOZORA_URL = u'http://www.aozora.gr.jp/index_pages' # whatsnew1.html'

        # 作品リスト
        self.bl_data = BookListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.bl_data.set_rules_hint(True)
        self.bl_data.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.bl_data.connect("row-activated", self.row_activated_treeview_cb)

        self.sw2 = gtk.ScrolledWindow()
        self.sw2.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw2.add(self.bl_data)
        self.sw2.set_size_request(400,400)

        # 開く・キャンセルボタン
        self.btnOk = gtk.Button(stock=gtk.STOCK_OPEN)
        self.btnOk.connect("clicked", self.clicked_btnOk_cb )
        self.btnCancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.btnCancel.connect("clicked", self.clicked_btnCancel_cb )
        self.bb = gtk.HButtonBox()
        self.bb.set_size_request(640,44)
        self.bb.set_layout(gtk.BUTTONBOX_SPREAD)
        self.bb.pack_start(self.btnOk)
        self.bb.pack_end(self.btnCancel)

        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.sw2)
        self.vbox.pack_end(self.bb)

        self.add(self.vbox)
        self.set_title( u'青空文庫　新着情報' )
        self.set_position(gtk.WIN_POS_CENTER)

        self.connect("delete_event", self.delete_event_cb)

        a = ReadHTMLpage()
        a.setbaseurl( self.AOZORA_URL )
        a.gethtml( u'whatsnew1.html')
        for i in a.readrecord():
            try:
                self.bl_data.get_model().append(
                                (i[0],i[2],i[3],i[1]))
            except:
                pass

        self.lastselectfile = None
        self.ack = gtk.RESPONSE_NONE


    def row_activated_treeview_cb(self, path, viewcol, col):
        """ 作品リストをダブルクリックした時の処理
            ダイアログを開いたまま、青空文庫のダウンロードを行う
        """
        if self.get_selected_book() == True:
            self.msginfo( u'ダウンロードしました' )
            self.ack = gtk.RESPONSE_OK
        else:
            pass

    def clicked_btnOk_cb(self, widget):
        """ 開くボタンをクリックした時の処理
            ダウンロードして終わる
        """
        if self.get_selected_book() == True:
            self.exitall()
            self.ack = gtk.RESPONSE_OK
        else:
            pass

    def clicked_btnCancel_cb(self, widget):
        self.exitall()
        self.ack = None

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def get_selected_book(self):
        """ 選択された作品をダウンロードする
                この操作で返されるのは
                c データモデルオブジェクト、ここではgtk.ListStore
                d 選択された行
        """
        (c,d) = self.bl_data.get_selection().get_selected_rows()  # 選択された行
        f = False
        iters = [c.get_iter(p) for p in d]
        for i in iters:
            (f, sMes) = self.selected_book( u'%s/%s' % (
                                self.AOZORA_URL, c.get_value(i, 3)) )
            if f == False:
                self.msgerrinfo( sMes )
            else:
                self.lastselectfile = sMes

        return f

    def exitall(self):
        self.hide_all()
        gtk.main_quit()
        #self.destroy()

    def run(self):
        self.show_all()
        self.set_modal(True)
        gtk.main()
        return (self.ack, self.lastselectfile)


