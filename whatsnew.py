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

from readersub_nogui import ReaderSetting
from readersub import Download, DownloadUI
import aozoradialog

import codecs
import os.path
import datetime
import urllib
import zipfile
from HTMLParser import HTMLParser

import gtk
import gobject

class ReadHTMLpage(HTMLParser, ReaderSetting, Download):
    def __init__(self):
        HTMLParser.__init__(self)
        ReaderSetting.__init__(self)

        self.nTrCount = 0
        self.nTdCount = 0
        self.flagTD = False
        self.sData = u''
        self.record=[]
        self.page=[]
        self.flagListTable = False  # リストを格納しているTableの検出用

    def handle_starttag(self, tag, attrs):
        if tag == u'table':
            for i in attrs:
                if i[0] == u'class' and i[1] == u'list':
                    self.flagListTable = True
                    break
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
            if self.flagTD:
                if self.nTdCount == 2 and self.flagListTable:
                    self.record.append(attrs[0][1])

    def handle_data(self, data):
        if self.flagListTable:
            if self.nTrCount >= 2:
                if self.nTdCount < 4:
                    if self.flagTD:
                        self.sData += data.lstrip().rstrip( u' \r\n' )

    def handle_endtag(self, tag):
        if self.flagListTable:
            if tag == u'tr':
                self.page.append(self.record)
                self.record=[]
            elif tag == u'td':
                if self.nTdCount < 4:
                    self.record.append(self.sData)
                    self.flagTD = False
            elif tag == u'table':
                self.flagListTable = False

    def setbaseurl(self, s):
        self.AOZORA_URL = s

    def gethtml(self, n):
        """ 新着情報のページをダウンロードして読み込む
        """
        url = u'%s/%s' % (self.AOZORA_URL,n)
        filename = os.path.join(self.get_value(u'workingdir'), n)
        try:
            urllib.urlretrieve(url, filename)
        except IOError:
            aozoradialog.msgerrinfo(
                u'ダウンロードに失敗しました。ネットワークへの接続状況を確認してください。',
                self )
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


class WhatsNewUI(aozoradialog.ao_dialog, ReaderSetting, Download):
    """ UI
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        ReaderSetting.__init__(self)



        # 作品リスト
        self.bl_data = BookListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.bl_data.set_rules_hint(True)
        self.bl_data.get_selection().set_mode(gtk.SELECTION_MULTIPLE) # gtk.SELECTION_SINGLE
        self.bl_data.connect("row-activated", self.row_activated_treeview_cb)

        self.sw2 = gtk.ScrolledWindow()
        self.sw2.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw2.add(self.bl_data)
        self.sw2.set_size_request(400,400)

        self.vbox.pack_start(self.sw2)
        self.vbox.show_all()

        self.set_title( u'青空文庫　新着情報' )
        self.set_position(gtk.WIN_POS_CENTER)

        a = ReadHTMLpage()
        a.setbaseurl( self.AOZORA_URL )
        a.gethtml( u'whatsnew1.html')
        for i in a.readrecord():
            try:
                self.bl_data.get_model().append((i[0],i[2],i[3],i[1]))
            except IndexError:
                pass
        self.lastselectfile = None
        self.lastselectzip = None
        self.worksid = None

    def row_activated_treeview_cb(self, path, viewcol, col):
        """ 作品リストをダブルクリックした時の処理
        """
        self.response_cb(self, gtk.RESPONSE_OK)

    def get_selected_item(self):
        """ 選択された作品をダウンロードする。
            ファイル名、ZIP名、(URLから類推した)作品ID　を返す。
        """
        (c,d) = self.bl_data.get_selection().get_selected_rows() # 選択された行
        if len(d) < 1:
            aozoradialog.msgerrinfo(u'作品が選択されていません。', self)
        f = False
        iters = [c.get_iter(p) for p in d]
        for i in iters:
            (f, sMes, z) = self.selected_book( u'%s/%s' % (
                            self.AOZORA_URL, c.get_value(i, 3)), c.get_value(i, 1) )
            worksid = c.get_value(i, 3).split(u'/')[-1].split(u'.')[0].lstrip(u'card')

            if not f:
                aozoradialog.msgerrinfo(sMes, self)
            else:
                self.lastselectfile = sMes
                self.lastselectzip = z
                self.worksid = u'%06d' % int(worksid)
        return self.lastselectfile, self.lastselectzip, self.worksid

