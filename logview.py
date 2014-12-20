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

""" ログビューワ
"""
from __future__ import with_statement

from hypertext import HyperTextView

from readersub import ReaderSetting, AozoraDialog
import sys, codecs, os.path, datetime, unicodedata, urllib, logging
import webbrowser
import gtk, cairo, pango, pangocairo, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

class Logviewer(gtk.Window, ReaderSetting, AozoraDialog):
    """ ログファイルを表示する
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        AozoraDialog.__init__(self)

        self.logfilename = u'%s/aozora.log' % self.get_value(u'workingdir')

        # アクセラレータ
        self.accelgroup = gtk.AccelGroup()
        self.add_accel_group(self.accelgroup)

        # メニュー
        self.menuitem_file = gtk.MenuItem( u'ファイル(_F)', True )
        self.menuitem_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT, self.accelgroup)
        self.menuitem_quit.connect( 'activate', self.clicked_btnClose_cb )
        self.menu_file = gtk.Menu()
        self.menu_file.add(gtk.SeparatorMenuItem())
        self.menu_file.add(self.menuitem_quit)
        self.menuitem_file.set_submenu(self.menu_file)
        self.mainmenu = gtk.MenuBar()
        self.mainmenu.append(self.menuitem_file)

        # 表示領域とデータモデル
        self.textbuffer_logfile = gtk.TextBuffer()
        self.textview_logfile = HyperTextView(self.textbuffer_logfile)
        self.textview_logfile.link['foreground'] = 'dark blue'
        self.textview_logfile.set_wrap_mode(gtk.WRAP_CHAR)
        self.textview_logfile.set_editable(False)
        self.textview_logfile.connect('anchor-clicked', self.clicked_anchor_cb)

        self.sw3 = gtk.ScrolledWindow()
        self.sw3.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw3.add(self.textview_logfile)

        # ボタン類
        self.btnRefresh = gtk.Button(stock=gtk.STOCK_REFRESH)
        self.btnRefresh.connect("clicked", self.clicked_btnRefresh_cb )
        self.btnClear = gtk.Button(stock=gtk.STOCK_CLEAR)
        self.btnClear.connect("clicked", self.clicked_btnClear_cb )
        self.btnClose = gtk.Button(stock=gtk.STOCK_CLOSE)
        self.btnClose.connect("clicked", self.clicked_btnClose_cb )

        self.btnbox = gtk.HButtonBox()
        self.btnbox.set_layout(gtk.BUTTONBOX_SPREAD)
        self.btnbox.pack_start(self.btnRefresh, False, False, 0)
        self.btnbox.pack_start(self.btnClear, False, False, 0)
        self.btnbox.pack_end(self.btnClose, False, False, 0)

        self.vBox = gtk.VBox()
        self.vBox.set_size_request(600,400)
        self.sw3.set_size_request(600,344)
        self.vBox.pack_start(self.mainmenu, expand=False)
        self.vBox.pack_start(self.sw3, expand=False)
        self.vBox.pack_end(self.btnbox, expand=False)

        self.add(self.vBox)
        self.set_title( u'青空文庫ビューア　デバッグメッセージ' )
        self.connect("delete_event", self.delete_event_cb)
        self.connect("key-press-event", self.key_press_event_cb )

        self.ack = gtk.RESPONSE_NONE

    def clicked_anchor_cb(self, widget, text, anchor, button ):
        """ アンカー
        """
        webbrowser.open( anchor )

    def clicked_btnRefresh_cb(self, widget):
        """ 表示の更新
        """
        self.textbuffer_logfile.set_text( u'' )
        self.readlogfile()

    def clicked_btnClear_cb(self, widget):
        """ ログファイルの内容を消去する
        """
        self.msginfo( u'この機能は現在実装されていません。')

    def clicked_btnClose_cb(self, widget):
        """ ウィンドウを閉じる
        """
        self.exitall()
        self.ack = gtk.RESPONSE_CANCEL

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def key_press_event_cb(self, widget, event):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            self.exitall()
            self.ack = gtk.RESPONSE_CANCEL
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def readlogfile(self):
        """ ログファイルの内容をUIに得る
        """
        with open( self.logfilename, 'r') as f0:
            for line in f0:
                self.textview_logfile.insert( line )

    def exitall(self):
        """ 出口処理
        """
        self.hide_all()
        gtk.main_quit()

    def run(self):
        """ ウィンドウの表示
        """
        self.readlogfile()
        self.show_all()
        gtk.main()
        return self.ack



"""
if __name__=='__main__':
    a = Logviewer()
    a.run()
"""