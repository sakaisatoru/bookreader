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


""" reader.py
        UI、プログラム本体

    基本仕様
        概要
            青空文庫に登録されているルビ付きファイルを読み込んで表示する。

        機能
            ルビ付きファイル（shift-jis）を読み込んでフォーマットして表示。
            目次作成機能
            ページ送り、ページ指定ジャンプ
            しおり機能

    既知の問題点
    更新履歴
        同梱のファイル(rireki.txt)を参照願います。

"""

from __future__ import with_statement

from jis3       import gaiji
from readersub  import ReaderSetting, AozoraDialog, History
from aozoracard import AuthorList
from formater   import Aozora, CairoCanvas
from whatsnew   import WhatsNewUI
from logview    import Logviewer
from booklist   import BookshelfUI
#from threading  import Thread
import sys, codecs, re, os.path, datetime, unicodedata, logging
import gtk, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

"""
    UI
"""
class BookMarkInfo(ReaderSetting):
    """ しおり情報の管理

        レコードレイアウト
        作品名,著者名,ページ番号,日付,ファイルパス
    """
    def __init__(self):
        """ しおりファイルを読み込んでリストに格納する。
        """
        ReaderSetting.__init__(self)
        self.shiorifile = self.get_value(u'workingdir') + '/shiori.txt'
        if os.path.isfile(self.shiorifile) == True:
            self.rewind()
        else:
            self.remove_all()

    def append(self, s):
        """ しおりを追加する。
        """
        self.bookmarkbuff.append(s)
        self.update()

    def append2(self, s):
        self.bookmarkbuff.append(s)

    def remove(self, s):
        """ しおりを削除する。
        """
        self.bookmarkbuff.remove(s)
        self.update()

    def remove_all(self):
        """ 全て削除する。
        """
        self.bookmarkbuff = []
        self.update()

    def update(self):
        with file( self.shiorifile, 'w' ) as f0:
            for s in self.bookmarkbuff:
                f0.write(s)

    def rewind(self):
        self.bookmarkbuff = []
        with file( self.shiorifile, 'r' ) as f0:
            for s in f0:
                s.rstrip('\n')
                self.bookmarkbuff.append(s)

    def itre(self):
        """ UI 向けイテレータ
        """
        for s in self.bookmarkbuff:
            yield s.rstrip('\n')

class BookmarkView(gtk.TreeView):
    """ しおり一覧を表示・管理
        +---------------+--------+---------+--------+
        |作品名          |著者名   |ページ番号 |日付     |
        +---------------+--------+---------+--------+
    """
    def __init__(self, *args, **kwargs):
        gtk.TreeView.__init__(self, *args, **kwargs)
        # 各項目ごとのレンダリング関数の設定
        self.rend_bookname = gtk.CellRendererText()
        self.rend_bookname.set_property('editable', False)

        self.rend_author = gtk.CellRendererText()
        self.rend_author.set_property('editable', False)

        self.rend_pagenumber = gtk.CellRendererText()
        self.rend_pagenumber.set_property('editable', False)

        self.rend_bookmarkdate = gtk.CellRendererText()
        self.rend_bookmarkdate.set_property('editable', False)

        self.col_bookname = gtk.TreeViewColumn(u'本の名前',
                                          self.rend_bookname,
                                          text=0)
        self.col_bookname.set_resizable(True)
        self.col_bookname.set_sort_column_id(0)
        self.col_author = gtk.TreeViewColumn(u'著作者',
                                          self.rend_author,
                                          text=1)
        self.col_author.set_resizable(True)
        self.col_author.set_sort_column_id(1)
        self.col_pagenumber = gtk.TreeViewColumn(u'ページ',
                                          self.rend_pagenumber,
                                          text=2)
        self.col_pagenumber.set_resizable(True)
        self.col_pagenumber.set_sort_column_id(2)
        self.col_bookmarkdate = gtk.TreeViewColumn(u'しおりを挟んだ日',
                                          self.rend_bookmarkdate,
                                          text=3)
        self.col_bookmarkdate.set_resizable(True)
        self.col_bookmarkdate.set_sort_column_id(3)
        self.append_column(self.col_bookname)
        self.append_column(self.col_author)
        self.append_column(self.col_pagenumber)
        self.append_column(self.col_bookmarkdate)

class BookmarkUI(gtk.Window):
    """ しおりの管理
        選択されたしおりの情報をタプルで返す
        選択されたしおりを削除する
        キャンセル時はNoneを返す
    """
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_title(u'しおりの管理')

        self.bookmark_bv = BookmarkView(model=gtk.ListStore(
                                                    gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING ))
        self.bookmark_bv.set_rules_hint(True)
        self.bookmark_bv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.bookmark_bv.connect("row-activated", self.row_activated_treeview_cb)
        self.bookmark_bv.set_headers_clickable(True)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.bookmark_bv)
        self.sw.set_size_request(512,200)

        self.btnDelete = gtk.Button(stock=gtk.STOCK_DELETE)
        self.btnDelete.connect("clicked", self.clicked_btnDelete_cb )
        self.btnOk = gtk.Button(stock=gtk.STOCK_OPEN)
        self.btnOk.connect("clicked", self.clicked_btnOk_cb )
        self.btnCancel = gtk.Button(stock=gtk.STOCK_QUIT)
        self.btnCancel.connect("clicked", self.clicked_btnCancel_cb )
        self.bb = gtk.HButtonBox()
        self.bb.set_size_request(512,44)
        self.bb.set_layout(gtk.BUTTONBOX_SPREAD)
        self.bb.pack_start(self.btnDelete)
        self.bb.pack_start(self.btnOk)
        self.bb.pack_end(self.btnCancel)

        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.sw, True, True, 0)
        self.vbox.pack_start(gtk.HSeparator(), False, True, 0)
        self.vbox.pack_end(self.bb, False, True, 0 )

        self.add(self.vbox)
        self.set_size_request(512, 256)
        self.set_position(gtk.WIN_POS_CENTER)

        self.connect("delete_event", self.delete_event_cb)
        self.connect( 'key-press-event', self.key_press_event_cb )
        bi = BookMarkInfo()
        for s in bi.itre():
            sc = s.split(',')
            self.bookmark_bv.get_model().append(
                                    (sc[0],         # 書籍名
                                    sc[1],          # 著者
                                    sc[2],          # ページ番号
                                    sc[3],          # 日付
                                    sc[4] )         # パス
                                    )
        self.rv = None

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def clicked_btnDelete_cb(self, widget):
        """ しおりの削除
        """
        (c,d) = self.bookmark_bv.get_selection().get_selected_rows()  # 選択された行
        iters = [c.get_iter(p) for p in d]
        for i in iters:
            c.remove(i)

    def row_activated_treeview_cb(self, path, view_column, column ):
        """ しおりの上でダブルクリックした時の処理
        """
        if self.get_selected_item() == True:
            self.exitall()

    def get_selected_item(self):
        """ 選択されたしおりをタプルで返す
            複数個選択時は無効とし、Falseを返す
        """
        f = False
        self.rv = ('')
        (c,d) = self.bookmark_bv.get_selection().get_selected_rows()  # 選択された行
        if len(d) > 1:
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                                        gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                        u'ページを開く時は、しおりを一つしか選べません。' )
            dlg.run()
            dlg.destroy()
        else:
            try:
                iters = [c.get_iter(p) for p in d]
                for i in iters:
                    self.rv = ( c.get_value(i, 0), c.get_value(i, 1),
                            c.get_value(i, 2), c.get_value(i, 3), c.get_value(i, 4) )
                f = True
            except:
                pass
        return f

    def clicked_btnOk_cb(self, widget):
        if self.get_selected_item() == True:
            self.exitall()

    def clicked_btnCancel_cb(self, widget):
        self.exitall()
        self.rv = None

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            self.exitall()
            self.rv = None
        elif key == 0xffff:
            # Delete
            self.clicked_btnDelete_cb(widget)
            return True
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def exitall(self):
        """ UI上のしおりデータを保存して終了する。
        """
        bi = BookMarkInfo()
        bi.remove_all()
        m = self.bookmark_bv.get_model()
        i = m.get_iter_first()
        while i:
            bi.append2(u'%s,%s,%s,%s,%s\n' % m.get(i, 0, 1, 2, 3, 4))
            i = m.iter_next(i)  # 次が無ければNoneでループを抜ける
        bi.update()

        self.hide_all()
        gtk.main_quit()

    def run(self):
        self.show_all()
        self.set_modal(True)
        gtk.main()
        return self.rv


class ScreenSetting(gtk.Window, ReaderSetting):
    """ 画面設定
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        self.set_title( u'画面設定' )

        # 1行目 -- 本文フォントセレクタ行 --
        self.fontlabel = gtk.Label( u'本文表示フォント' )
        self.fontsel = gtk.FontButton( u'%s %s' % (self.get_value( u'fontname' ),
                                    self.get_value( u'fontsize' )))
        self.fontsel.set_use_font(True)
        self.fontsel.set_show_size(True)
        self.fontsel.connect( "font-set", self.fontsel_cb )
        self.hbox1 = gtk.HBox()
        self.hbox1.pack_start(self.fontlabel)
        self.hbox1.pack_end(self.fontsel)

        # 2行目 -- ルビフォントセレクタ行 --
        self.rubifontlabel = gtk.Label( u'ルビ表示フォント' )
        self.rubifontsel = gtk.FontButton( u'%s %s' % (self.get_value( u'fontname' ),
                                    self.get_value( u'rubifontsize' )))
        self.rubifontsel.set_use_font(True)
        self.rubifontsel.set_show_size(True)
        self.rubifontsel.connect( "font-set", self.rubifontsel_cb )
        self.hbox2 = gtk.HBox()
        self.hbox2.pack_start(self.rubifontlabel)
        self.hbox2.pack_end(self.rubifontsel)

        # 2.5行目 -- colour selector --
        self.btFontcolor = gtk.ColorButton()
        self.btFontcolor.set_title(u'文字の色を選択してください')
        sC = self.get_value(u'fontcolor')
        nC = (len(sC)-1)/3
        tmpC = gtk.gdk.Color(eval(u'0x'+sC[1:1+nC])/65535.0,
                                eval(u'0x'+sC[1+nC:1+nC+nC])/65535.0,
                                    eval(u'0x'+sC[1+nC+nC:1+nC+nC+nC])/65535.0,0)
        self.btFontcolor.set_color(tmpC)
        self.btBackcolor = gtk.ColorButton()
        self.btBackcolor.set_title(u'背景色を選択してください')
        sC = self.get_value(u'backcolor')
        nC = (len(sC)-1)/3
        tmpC = gtk.gdk.Color(eval(u'0x'+sC[1:1+nC])/65535.0,
                                eval(u'0x'+sC[1+nC:1+nC+nC])/65535.0,
                                    eval(u'0x'+sC[1+nC+nC:1+nC+nC+nC])/65535.0,0)
        self.btBackcolor.set_color(tmpC)
        self.lbFontcolor = gtk.Label(u'文字色')
        self.lbBackcolor = gtk.Label(u'背景色')
        self.hbox25 = gtk.HBox()
        self.hbox25.pack_start(self.lbFontcolor)
        self.hbox25.pack_start(self.btFontcolor)
        self.hbox25.pack_start(self.lbBackcolor)
        self.hbox25.pack_end(self.btBackcolor)

        # 画面サイズ
        # group の先頭になるボタンが初期値となる
        #
        a = self.get_value(u'resolution')
        self.sizelabel = gtk.Label( u'画面サイズ' )
        self.vbuttonbox = gtk.VButtonBox()
        self.radiobtn = []
        for s in [u'SVGA', u'WSVGA', u'XGA', u'WXGA']:
            self.radiobtn.append( gtk.RadioButton(label=s) )
        for t in self.radiobtn:
            if t.get_label() == a:
                gp = t
                break
        for t in self.radiobtn:
            if t.get_label() != a:
                t.set_group(gp)
            self.vbuttonbox.add(t)

        # マージン
        self.marginlabel = gtk.Label( u'マージン' )
        self.tbMargin   = gtk.Table( rows = 4, columns = 2 )
        topadj      = gtk.Adjustment(value=int(self.get_value(u'topmargin')),
                                    lower=0,upper=50,step_incr=1,page_incr=10)
        bottomadj   = gtk.Adjustment(value=int(self.get_value(u'bottommargin')),
                                    lower=0,upper=50,step_incr=1,page_incr=10)
        leftadj     = gtk.Adjustment(value=int(self.get_value(u'leftmargin')),
                                    lower=0,upper=50,step_incr=1,page_incr=10)
        rightadj    = gtk.Adjustment(value=int(self.get_value(u'rightmargin')),
                                    lower=0,upper=50,step_incr=1,page_incr=10)
        self.topmargin      = gtk.SpinButton( adjustment = topadj,
                                                    climb_rate = 1, digits = 0)
        self.bottommargin   = gtk.SpinButton( adjustment = bottomadj,
                                                    climb_rate = 1, digits = 0)
        self.leftmargin     = gtk.SpinButton( adjustment = leftadj,
                                                    climb_rate = 1, digits = 0)
        self.rightmargin    = gtk.SpinButton( adjustment = rightadj,
                                                    climb_rate = 1, digits = 0)
        self.tbMargin.attach( gtk.Label( u'上' ), 0, 1, 0, 1)
        self.tbMargin.attach( gtk.Label( u'下' ), 0, 1, 1, 2)
        self.tbMargin.attach( gtk.Label( u'左' ), 0, 1, 2, 3)
        self.tbMargin.attach( gtk.Label( u'右' ), 0, 1, 3, 4)
        self.tbMargin.attach( self.topmargin, 1, 2, 0, 1)
        self.tbMargin.attach( self.bottommargin ,1, 2, 1, 2)
        self.tbMargin.attach( self.leftmargin ,1, 2, 2, 3)
        self.tbMargin.attach( self.rightmargin ,1, 2, 3, 4)
        self.hbox3 = gtk.HBox()
        self.hbox3.pack_start(self.marginlabel)
        self.hbox3.pack_end(self.tbMargin)

        # 行間
        self.linesteplabel = gtk.Label( u'行間' )
        linestepadj = gtk.Adjustment(
                        value=float(self.get_value(u'linestep')),
                            lower=0,upper=2.5,step_incr=0.5,page_incr=0.5)
        self.linestep = gtk.SpinButton(adjustment  = linestepadj,
                                        climb_rate = 0.5, digits = 1)
        self.hbox4 = gtk.HBox()
        self.hbox4.pack_start(self.linesteplabel)
        self.hbox4.pack_end(self.linestep)

        # 3行目
        self.vbox2 = gtk.VBox()
        self.vbox2.pack_start(self.hbox3)
        self.vbox2.pack_end(self.hbox4)
        self.hbox5 = gtk.HBox()
        self.hbox5.pack_start(self.sizelabel)
        self.hbox5.pack_start(self.vbuttonbox)
        self.hbox5.pack_end(self.vbox2)

        # 4行目 -- ボタン行 --
        self.btnOk = gtk.Button(stock=gtk.STOCK_OK)
        self.btnOk.connect("clicked", self.clicked_btnOk_cb )
        self.btnCancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.btnCancel.connect("clicked", self.clicked_btnCancel_cb )
        self.bb = gtk.HButtonBox()
        self.bb.set_layout(gtk.BUTTONBOX_END )
        self.bb.pack_start(self.btnOk)
        self.bb.pack_end(self.btnCancel)

        # まとめ
        self.vbox5 = gtk.VBox(spacing=10)
        self.vbox5.pack_start(self.hbox1)
        self.vbox5.pack_start(self.hbox2)
        self.vbox5.pack_start(self.hbox25)
        self.vbox5.pack_start(self.hbox5)
        self.vbox5.pack_end(self.bb)

        self.add(self.vbox5)
        self.set_size_request(384, 320)

        self.connect('delete_event', self.delete_event_cb)

        self.rv = False


    def fontsel_cb(self, widget):
        """ 本文とルビのフォント名の同期をとる
        """
        s = widget.get_font_name().rstrip( u' 0123456789' )
        s = s + u' ' + self.rubifontsel.get_font_name().split(u' ')[-1]
        self.rubifontsel.set_font_name(s)

    def rubifontsel_cb(self, widget):
        """ 本文とルビのフォント名の同期をとる
        """
        s = widget.get_font_name().rstrip( u' 0123456789' )
        s = s + u' ' + self.fontsel.get_font_name().split(u' ')[-1]
        self.fontsel.set_font_name(s)

    def exitall(self):
        self.hide_all()
        gtk.main_quit()

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def clicked_btnOk_cb(self, widget):
        for bt in self.radiobtn:
            """ 解像度のラジオボタンの処理
            """
            if bt.get_active() == True:
                self.set_value(u'resolution', bt.get_label())
                break
        self.set_value(u'fontname',     self.fontsel.get_font_name().rstrip(' 1234567890') )
        self.set_value(u'fontsize',     str(self.fontsel.get_font_name().split(' ')[-1]))
        self.set_value(u'rubifontsize', str(self.rubifontsel.get_font_name().split(' ')[-1]))
        self.set_value(u'topmargin',    str(int(self.topmargin.get_value())))
        self.set_value(u'bottommargin', str(int(self.bottommargin.get_value())))
        self.set_value(u'leftmargin',   str(int(self.leftmargin.get_value())))
        self.set_value(u'rightmargin',  str(int(self.rightmargin.get_value())))
        self.set_value(u'linestep',     str(self.linestep.get_value()))

        self.set_value(u'fontcolor',    self.btFontcolor.get_color() )
        self.set_value(u'backcolor',    self.btBackcolor.get_color() )
        self.update()
        self.rv = True
        self.exitall()

    def clicked_btnCancel_cb(self, widget):
        self.rv = False
        self.exitall()

    def run(self):
        self.show_all()
        self.set_modal(True)
        gtk.main()
        return self.rv


class ReaderUI(gtk.Window, ReaderSetting, AozoraDialog):
    """ メインウィンドウ
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        AozoraDialog.__init__(self)

        # logging 設定
        logging.basicConfig(
            filename=u'%s/aozora.log' % self.dicSetting[u'workingdir'],
            filemode='w',
            format = '%(levelname)s in %(filename)s : %(message)s',
            level=logging.DEBUG )
        self.logwindow = Logviewer()

        """ 読書履歴
        """
        self.bookhistory = History(u'%s/history.txt' % self.dicSetting[u'settingdir'])
        self.menuitem_history = []
        count = 1
        for item in self.bookhistory.iter():
            self.menuitem_history.append(
                        gtk.MenuItem('_%d: %s' % (count,item.split(',')[0]),True) )
            count += 1
        for item in self.menuitem_history:
            item.connect('activate', self.menu_historyopen_cb)

        """ アクセラレータ
        """
        self.accelgroup = gtk.AccelGroup()
        self.add_accel_group(self.accelgroup)

        """ メインメニュー - ファイル
        """
        self.menuitem_file = gtk.MenuItem(u'ファイル(_F)', True )
        self.menuitem_open = gtk.ImageMenuItem(gtk.STOCK_OPEN, self.accelgroup)
        self.menuitem_open.connect('activate', self.menu_fileopen_cb )
        self.menuitem_download = gtk.MenuItem(u'青空文庫へアクセス(_D)', True )
        self.menuitem_download.connect('activate', self.online_access_cb )
        self.menuitem_whatsnew = gtk.MenuItem(u'青空文庫新着情報(_N)', True )
        self.menuitem_whatsnew.connect('activate', self.whatsnew_cb )
        self.menuitem_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT, self.accelgroup)
        self.menuitem_quit.connect('activate', self.exitall )
        self.menu_file = gtk.Menu()
        self.menu_file.add(self.menuitem_open)
        self.menu_file.add(self.menuitem_download)
        self.menu_file.add(self.menuitem_whatsnew)
        self.menu_file.add(gtk.SeparatorMenuItem())
        for item in self.menuitem_history:
            self.menu_file.add(item)
        self.menu_file.add(gtk.SeparatorMenuItem())
        self.menu_file.add(self.menuitem_quit)
        self.menuitem_file.set_submenu(self.menu_file)

        """ メインメニュー - ツール
        """
        self.menuitem_tool = gtk.MenuItem( u'ツール(_T)', True )
        self.menuitem_pagejump = gtk.ImageMenuItem(gtk.STOCK_JUMP_TO, self.accelgroup)
        self.menuitem_pagejump.connect( 'activate', self.menu_pagejump_cb )
        self.menuitem_bookmark = gtk.MenuItem( u'しおりの管理(_L)', True)
        self.menuitem_bookmark.connect( 'activate', self.shiori_list_cb )
        self.menu_tool = gtk.Menu()
        self.menu_tool.add(self.menuitem_pagejump)
        self.menu_tool.add(self.menuitem_bookmark)
        self.menuitem_tool.set_submenu(self.menu_tool)

        """ メインメニュー - 目次
        """
        self.menuitem_mokuji = gtk.MenuItem( u'目次(_I)', True )
        self.menu_mokuji = gtk.Menu()

        """ メインメニュー - 設定
        """
        self.menuitem_fontselect = gtk.MenuItem( u'フォント(_F)', True )
        self.menuitem_fontselect = gtk.ImageMenuItem( gtk.STOCK_SELECT_FONT, self.accelgroup )
        self.menuitem_fontselect.connect( 'activate', self.menu_fontselect_cb )

        self.menuitem_setting = gtk.MenuItem( u'設定(_S)', True )

        self.menu_setting = gtk.Menu()
        self.menu_setting.add(self.menuitem_fontselect)
        self.menuitem_setting.set_submenu(self.menu_setting)

        """ メインメニュー - ヘルプ
        """
        self.menuitem_help = gtk.MenuItem( u'ヘルプ(_H)', True )
        self.menuitem_logwindow = gtk.ImageMenuItem(gtk.STOCK_INFO, self.accelgroup)
        self.menuitem_logwindow.connect( 'activate', self.menu_logwindow_cb )
        self.menuitem_info = gtk.ImageMenuItem(gtk.STOCK_ABOUT, self.accelgroup)
        self.menuitem_info.connect( 'activate', self.menu_about_cb )
        self.menu_help = gtk.Menu()
        self.menu_help.add(self.menuitem_logwindow)
        self.menu_help.add(self.menuitem_info)
        self.menuitem_help.set_submenu(self.menu_help)

        self.mainmenu = gtk.MenuBar()
        self.mainmenu.append(self.menuitem_file)
        self.mainmenu.append(self.menuitem_tool)
        self.mainmenu.append(self.menuitem_mokuji)
        self.mainmenu.append(self.menuitem_setting)
        self.mainmenu.append(self.menuitem_help)

        """ ポップアップメニュー
        """
        self.pmenu_book_do = gtk.MenuItem( u'このページにしおりを挟む(_S)', True)
        self.pmenu_book_do.connect( 'activate', self.shiori_here_cb )
        self.pmenu_book_list = gtk.MenuItem( u'しおりの管理(_L)', True)
        self.pmenu_book_list.connect( 'activate', self.shiori_list_cb )
        self.popupmenu_bookmark = gtk.Menu()
        self.popupmenu_bookmark.append(self.pmenu_book_do)
        self.popupmenu_bookmark.append(self.pmenu_book_list)
        self.popupmenu_bookmark.show_all()


        #   文章表示領域
        self.cc = CairoCanvas()
        self.imagebuf = gtk.Image()
        self.ebox = gtk.EventBox()
        self.ebox.add(self.imagebuf)    # image がイベントを見ないのでeventboxを使う
        self.ebox.connect('button-press-event', self.button_press_event_cb )
        self.ebox.connect('button-release-event', self.button_release_event_cb )

        #   ビルド
        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.mainmenu, expand=False)
        self.vbox.pack_end(self.ebox)
        self.add(self.vbox)

        self.scount = 0
        self.ecount = 0
        self.mousecount = 0
        self.connect('delete_event', self.delete_event_cb)
        self.connect('size-allocate', self.size_allocate_event_cb)
        self.connect('realize', self.realize_event_cb)
        self.connect('expose-event', self.expose_event_cb)
        self.connect('key-press-event', self.key_press_event_cb)
        self.set_position(gtk.WIN_POS_CENTER)

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        if event.state & gtk.gdk.CONTROL_MASK:
            key = event.hardware_keycode #event.keyval
            if key == 57:
                # CTRL_N
                self.whatsnew_cb( widget )
            elif key == 41:
                # CTRL_F
                self.online_access_cb( widget )
            elif key == 46:
                # CTRL_L
                self.shiori_list_cb( widget )
        else:
            key = event.keyval
            if key == 32:
                 # space
                if event.state & gtk.gdk.SHIFT_MASK:
                    self.prior_page()
                else:
                    self.next_page()
            elif key == 65361 or key == 0xff56:
                # left arrow cursor or PgUp
                self.next_page()
            elif key == 65363 or key == 0xff55:
                # right arrow cursor or PgDn
                self.prior_page()
            elif key == 0xff50:
                # Home
                self.page_common( 0 )
            elif key == 0xff57:
                # End
                self.page_common( self.cc.pagecounter )
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def online_access_cb(self, widget):
        """ インターネット上の青空文庫にアクセス
        """
        dlg = AuthorList()
        res,fn = dlg.run()
        dlg.destroy()
        if res == gtk.RESPONSE_OK:
            self.bookopen(fn)

    def whatsnew_cb(self, widget):
        """ 青空文庫新着情報
        """
        dlg = WhatsNewUI()
        res,fn = dlg.run()
        dlg.destroy()
        if res == gtk.RESPONSE_OK:
            self.bookopen(fn)

    def mokuji_create(self):
        """ フォーマッタが作成した目次を読み込んで
            メニューに追加する
        """
        if self.cc.sourcefile != u'':
            menu = gtk.Menu()
            for s in self.cc.mokuji_itre():
                menuitem = gtk.MenuItem(s, False)
                menuitem.connect( 'activate', self.mokuji_jump, s )
                menu.add(menuitem)
                menuitem.show()
            self.menuitem_mokuji.set_submenu(menu)

    def mokuji_jump(self, widget, s):
        """ 目次ジャンプの下請け
            ページ番号の指定が手抜き
        """
        self.page_common(int(s.split()[1])-1)

    def shiori_here_cb( self, widget ):
        """ テキスト上でのポップアップ（１）
            しおりを挟む
        """
        n = self.cc.get_booktitle()
        s = u'%s,%s,%d,%s,%s\n' % (n[0], n[1],
                            self.currentpage+1,
                            datetime.date.today(), self.cc.get_source() )
        bm = BookMarkInfo()
        bm.append(s)

    def shiori_list_cb( self, widget ):
        """ テキスト上でのポップアップ（２）
            しおり一覧
        """
        bi = BookmarkUI()
        s = bi.run()
        bi.destroy()
        if s != None:
            self.bookopen(s[4], int(s[2])-1)

    def menu_fontselect_cb( self, widget ):
        """ 表示フォントを選択する
        """
        dlg = ScreenSetting()
        if dlg.run() == True:
            self.msginfo( u'変更した設定は再起動後に反映されます。' )
            #self.cc.resize()
        dlg.destroy()


    def menu_pagejump_cb( self, widget ):
        """ ページ指定ジャンプ
        """
        label = gtk.Label( u'ページ番号' )
        adj = gtk.Adjustment(value=1,lower=1,upper=self.cc.pagecounter+1,
                                step_incr=1,page_incr=10)
        spin = gtk.SpinButton(adjustment=adj, climb_rate=1,digits=0)
        hb = gtk.HBox()
        hb.pack_start(label,True,False,0)
        hb.pack_start(spin,True,False,0)
        dlg = gtk.Dialog(title=u'ページジャンプ')
        dlg.vbox.pack_start(hb,True,True,0)
        dlg.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK,
                            gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.show_all()
        if dlg.run() == gtk.RESPONSE_OK:
            a = adj.get_value()
            self.page_common(int(a)-1)
        dlg.destroy()

    def menu_logwindow_cb( self, widget ):
        """ ログファイルの表示
        """
        self.logwindow.run()

    def menu_about_cb( self, widget ):
        """ プログラムバージョン
        """
        dlg = gtk.AboutDialog()
        dlg.set_program_name( u'青空文庫リーダー' )
        dlg.set_version( u'unstable version' )
        dlg.set_copyright( u'by sakai satoru 2015' )
        dlg.run()
        dlg.destroy()

    def menu_historyopen_cb(self, widget):
        """ 読書履歴
        """
        i = int(widget.get_label().split(u':')[0][1:]) - 1
        (nm, pg, fn) = self.bookhistory.get_item(i).split(u',')
        self.bookopen(fn, int(pg))

    def menu_fileopen_cb( self, widget ):
        self.menu_fileopen()

    def menu_fileopen(self):
        """ ローカルにある青空文庫ファイルを開く
        """
        dlg = BookshelfUI()
        res = dlg.run()
        if res == gtk.RESPONSE_OK:
            fn = dlg.get_filename()
            dlg.destroy()
            self.bookopen(fn)
        else:
            dlg.destroy()

    def bookopen(self, fn, pagenum=0):
        if self.cc.get_source() == fn:
            #   既にフォーマット済みのテキストを表示する場合
            self.page_common( pagenum )
        else:
            self.cc.do_format(fn)
            self.page_common( pagenum )
            self.mokuji_create()

    def button_release_event_cb( self, widget, event ):
        return False

    def button_press_event_cb( self, widget, event ):
        """ マウスクリック
            左ボタン    ページ送り・戻し
                        何も開かれていなければファイル選択ダイアログ
            右ボタン    カレントメニュー
        """
        if event.button == 1:               # 左ボタン
            if self.cc.sourcefile == u'':
                self.menu_fileopen()
            else:
                (x,y) = widget.get_pointer()
                if x < self.cc.canvas_width / 2:
                    self.next_page()
                else:
                    self.prior_page()
        elif event.button == 3:             # 右ボタン
            if self.cc.sourcefile != u'':
                self.popupmenu_bookmark.popup(
                                None, None, None, event.button, event.time)
        return False

    def prior_page(self):
        if self.currentpage > 0:
            self.currentpage -= 1
            self.page_common()

    def next_page(self):
        if self.currentpage < self.cc.pagecounter:
            self.currentpage += 1
            self.page_common()

    def page_common(self, n=None):
        """ 指定されたページをUIへ表示する
        """
        if n != None:
            if n <= self.cc.pagecounter and n >= 0:
                self.currentpage = n

        self.cc.writepage(self.currentpage)
        self.imagebuf.set_from_file(self.get_value(u'workingdir') + '/thisistest.png')
        bookname,author = self.cc.get_booktitle()
        self.set_title(u'【%s】 %s - %s / %s - 青空文庫リーダー' %
            (bookname, author, self.currentpage+1,self.cc.pagecounter+1) )

    def size_allocate_event_cb(self, widget, event, data=None):
        pass

    def realize_event_cb(self, widget):
        pass

    def expose_event_cb(self, widget, event, data=None):
        return False

    def delete_event_cb(self, widget, event, data=None):
        self.exitall(widget, None )

    def exitall(self, widget, data=None ):
        logging.shutdown()
        #   現在読んでいる本を履歴に保存する
        bookname,author = self.cc.get_booktitle()
        if bookname != u'':
            self.bookhistory.update( u'%s,%d,%s' %
                (bookname, self.currentpage,self.cc.sourcefile) )
        self.bookhistory.save()
        self.hide_all()
        gtk.main_quit()

    def run(self):
        """ エントリー
        """
        self.currentpage = 0
        self.cc.write_a_line(u'<span font_desc="Sans bold 6">あおぞらぶんこ</span>\n' +
                                u'<span font_desc="Sans bold 12"><span underline="low">青空文庫リーダー</span></span>')
        self.imagebuf.set_from_file(
                        '%s/.cache/aozora/thisistest.png' % self.get_homedir())
        self.set_title(u'青空文庫リーダー')
        self.show_all()
        gtk.main()

if __name__ == '__main__':
    ui = ReaderUI()
    ui.run()
