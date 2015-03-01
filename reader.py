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
"""

import jis3
import aozoradialog
from readersub      import ReaderSetting, History
from formater       import Aozora, CairoCanvas, AozoraCurrentTextinfo
from whatsnew       import WhatsNewUI
from logview        import Logviewer
from bunko          import BunkoUI

import tempfile
import sys
import codecs
import re
import os.path
import datetime
import unicodedata
import logging
import copy
import subprocess
import os
import zipfile

import gc
import gtk
import gobject
import pango

sys.stdout=codecs.getwriter('UTF-8')(sys.stdout)

""" UI
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
        self.shiorifile = os.path.join(self.get_value(u'workingdir'),
                                                                u'shiori.txt')
        if os.path.isfile(self.shiorifile):
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


class BookmarkUI(aozoradialog.ao_dialog):
    """ しおりの管理
        選択されたしおりの情報をタプルで返す
        選択されたしおりを削除する
        キャンセル時はNoneを返す
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        self.set_title(u'しおりの管理')

        self.bookmark_bv = BookmarkView(model=gtk.ListStore(
                                                    gobject.TYPE_STRING,
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

        self.vbox.pack_start(self.sw, True, True, 0)
        self.vbox.pack_end(gtk.HSeparator(), False, True, 0)

        self.vbox.show_all()
        self.set_size_request(512, 256)
        self.set_position(gtk.WIN_POS_CENTER)

        bi = BookMarkInfo()
        for s in bi.itre():
            sc = s.split(',')
            self.bookmark_bv.get_model().append(
                                    (sc[0],         # 書籍名
                                    sc[1],          # 著者
                                    sc[2],          # ページ番号
                                    sc[3],          # 日付
                                    sc[4],          # パス
                                    sc[5] )         # zipfile
                                    )

        self.connect('key-press-event', self.key_press_event_cb )

    def removerecord(self):
        """ しおりの削除
        """
        (c,d) = self.bookmark_bv.get_selection().get_selected_rows()  # 選択された行
        iters = [c.get_iter(p) for p in d]
        for i in iters:
            c.remove(i)
        self.savebookmark()

    def row_activated_treeview_cb(self, path, view_column, column ):
        """ しおりの上でダブルクリックした時の処理
        """
        self.response_cb(self, gtk.RESPONSE_ACCEPT)

    def get_selected_item(self):
        """ 選択されたしおりをタプルで返す
            複数個選択時は無効とし、Falseを返す
        """
        f = False
        self.rv = ('')
        (c,d) = self.bookmark_bv.get_selection().get_selected_rows()  # 選択された行
        if len(d) > 1:
            dlg = aozoradialog.msgerrinfo(
                    u'ページを開く時は、しおりを一つしか選べません。' ,self)
        else:
            try:
                iters = [c.get_iter(p) for p in d]
                for i in iters:
                    self.rv = [c.get_value(i, k) for k in xrange(6)]
                f = True
            except IndexError:
                pass
        return self.rv

    def key_press_event_cb(self, widget, event):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            pass
        elif key == 0xffff:
            # Delete
            self.removerecord()
            return True
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def savebookmark(self):
        """ UI上のしおりデータを保存する。
        """
        bi = BookMarkInfo()
        bi.remove_all()
        m = self.bookmark_bv.get_model()
        i = m.get_iter_first()
        while i:
            bi.append2(u'%s,%s,%s,%s,%s,%s\n' % m.get(i, 0, 1, 2, 3, 4, 5))
            i = m.iter_next(i)  # 次が無ければNoneでループを抜ける
        bi.update()


class ScreenSetting(aozoradialog.ao_dialog, ReaderSetting):
    """ 画面設定
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        ReaderSetting.__init__(self)
        self.set_title( u'画面設定' )

        # 1行目 -- 本文フォントセレクタ行 --
        self.fontlabel = gtk.Label( u'本文表示フォント' )
        self.fontsel = gtk.FontButton( u'%s %s' % (self.get_value(u'fontname'),
                                    self.get_value(u'fontsize')))
        self.fontsel.set_use_font(True)
        self.fontsel.set_show_size(True)
        self.fontsel.connect( "font-set", self.fontsel_cb )
        self.hbox1 = gtk.HBox()
        self.hbox1.pack_start(self.fontlabel)
        self.hbox1.pack_end(self.fontsel)

        # 2行目 -- ルビフォントセレクタ行 --
        self.rubifontlabel = gtk.Label( u'ルビ表示フォント' )
        self.rubifontsel = gtk.FontButton( u'%s %s' % (self.get_value(u'fontname'),
                                    self.get_value(u'rubifontsize')))
        self.rubifontsel.set_use_font(True)
        self.rubifontsel.set_show_size(True)
        self.rubifontsel.connect( "font-set", self.rubifontsel_cb )
        self.hbox2 = gtk.HBox()
        self.hbox2.pack_start(self.rubifontlabel)
        self.hbox2.pack_end(self.rubifontsel)

        # 2.5行目 -- colour selector --
        self.btFontcolor = gtk.ColorButton()
        self.btFontcolor.set_title(u'文字の色を選択してください')
        tmp = self.convcolor(self.get_value(u'fontcolor'))
        self.btFontcolor.set_color(gtk.gdk.Color(tmp[0],tmp[1],tmp[2]))
        self.btBackcolor = gtk.ColorButton()
        self.btBackcolor.set_title(u'背景色を選択してください')
        tmp = self.convcolor(self.get_value(u'backcolor'))
        self.btBackcolor.set_color(gtk.gdk.Color(tmp[0],tmp[1],tmp[2]))
        self.lbFontcolor = gtk.Label(u'文字色')
        self.lbBackcolor = gtk.Label(u'背景色')
        self.hbox25 = gtk.HBox()
        self.hbox25.pack_start(self.lbFontcolor)
        self.hbox25.pack_start(self.btFontcolor)
        self.hbox25.pack_start(self.lbBackcolor)
        self.hbox25.pack_end(self.btBackcolor)

        # 画面サイズ
        # group の先頭になるボタンが初期値となる
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
                            lower=1.5,upper=2.5,step_incr=0.5,page_incr=0.5)
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

        # まとめ (gtk.Dialogのデフォルトの表示域 vboxへpack)
        self.vbox.pack_start(self.hbox1)
        self.vbox.pack_start(self.hbox2)
        self.vbox.pack_start(self.hbox25)
        self.vbox.pack_start(self.hbox5)
        self.vbox.show_all()

        self.set_size_request(384, 320)

    def fontsel_cb(self, widget):
        """ 本文とルビのフォント名の同期をとる
        """
        fontsize = round(float(self.rubifontsel.get_font_name().lstrip(
                    self.rubifontsel.get_font_name().rstrip(u'.0123456789'))),
                    1 )
        fontname = widget.get_font_name().rstrip( u'.0123456789' ).lstrip(u' ')
        self.rubifontsel.set_font_name(u'%s %s' % (fontname,fontsize))

    def rubifontsel_cb(self, widget):
        """ 本文とルビのフォント名の同期をとる
        """
        fontsize = round(float(self.fontsel.get_font_name().lstrip(
                        self.fontsel.get_font_name().rstrip(u'.0123456789'))),
                        1)
        fontname = widget.get_font_name().rstrip( u'.0123456789' ).lstrip(u' ')
        self.fontsel.set_font_name(u'%s %s' % (fontname,fontsize))

    def settingupdate(self):
        """ 設定の更新
            内部のウィジェットにはアタッチしないので呼び出し側に戻ってから
            必要に応じて呼び出す。
        """
        for bt in self.radiobtn:
            # 解像度のラジオボタンの処理
            if bt.get_active():
                self.set_value(u'resolution', bt.get_label())
                break

        fontname = self.fontsel.get_font_name().rstrip('.1234567890')
        fontsize = float(self.fontsel.get_font_name()[len(fontname):])
        self.set_value(u'fontname', fontname.strip(u' '))
        self.set_value(u'fontsize','%s' % round(fontsize,1))
        fontname = self.rubifontsel.get_font_name().rstrip('.1234567890')
        fontsize = float(self.rubifontsel.get_font_name()[len(fontname):])
        self.set_value(u'rubifontsize', '%s' % round(fontsize,1))
        self.set_value(u'topmargin',    str(int(self.topmargin.get_value())))
        self.set_value(u'bottommargin', str(int(self.bottommargin.get_value())))
        self.set_value(u'leftmargin',   str(int(self.leftmargin.get_value())))
        self.set_value(u'rightmargin',  str(int(self.rightmargin.get_value())))
        self.set_value(u'linestep',     str(self.linestep.get_value()))

        self.set_value(u'fontcolor',    self.btFontcolor.get_color() )
        self.set_value(u'backcolor',    self.btBackcolor.get_color() )
        self.update()


class formaterUI(aozoradialog.ao_dialog, Aozora):
    """ プログレスバーを持ったフォーマッタUI
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        Aozora.__init__(self)
        self.set_title(u'読み込み中')
        self.pb = gtk.ProgressBar()
        self.pb.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
        self.vbox.pack_start(self.pb)
        self.vbox.show_all()
        self.set_position(gtk.WIN_POS_CENTER)

    def touchup(self, fn, zipname):
        """ 本来 formater を待ちループ内において、プログレスバーをタイマー
            駆動にして問題ないはずだが、妙な待ち時間が生じるので formaterを
            アイドルタスクへ追加している。
            このため、待ちループがない状況で実行すると失敗する。
            これを実行したらすかさず run() すること。
        """
        self.set_source(fn, zipname)
        self.maxlines = float(sum(1 for line in codecs.open(self.currentText.sourcefile)))
        self.lncounter = 0
        self.tmp = self.formater()
        gobject.timeout_add(200, self.progressbar_update) # プログレスバー
        gobject.idle_add(self.formater_itre)              # フォーマッタ

    def formater_itre(self):
        try:
            next(self.tmp)
            self.lncounter += 1
        except StopIteration:
            self.responsed = True
            self.resid = None
            return False # タスクを抜去して終わる
        return True

    def progressbar_update(self):
        """ プログレスバーを間欠的に更新する
        """
        self.pb.set_text(u'%d/%d' % (self.lncounter,self.maxlines))
        self.pb.set_fraction(self.lncounter/self.maxlines)
        return True


class ReaderUI(gtk.Window, ReaderSetting):
    """ メインウィンドウ
    """
    menutmp = '''<ui>
        <menubar name="MenuBar">
            <menu action="File">
                <menuitem action="open"/>
                <menuitem action="new"/>
                <menu action="history"/>
                <separator/>
                <menuitem action="quit"/>
            </menu>
            <menu action="Page">
                {0}
            </menu>
            <menu action="Index">
            </menu>
            <menu action="Setting">
                <menuitem action="preference"/>
            </menu>
            <menu action="Help">
                <menuitem action="view"/>
                <menuitem action="info"/>
            </menu>
        </menubar>
        <popup name="popmain">
            {0}
        </popup>
    </ui>'''

    menupagemove = '''
            <menuitem action="jump"/>
            <menuitem action="top"/>
            <menuitem action="end"/>
            <menuitem action="setbookmark"/>
            <separator/>
            <menuitem action="listbookmark"/>
    '''
    def __init__(self):
        """
        """
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)

        # フラグ類
        self.isRestart = False
        self.isBookopened = False
        self.isNowFormatting = False

        # logging 設定
        logging.basicConfig(
            filename=os.path.join(self.dicSetting[u'workingdir'],u'aozora.log'),
            filemode='w',
            format = '%(levelname)s in %(filename)s : %(message)s',
            level=logging.DEBUG )
        self.logwindow = None

        # 読書履歴を保持する
        self.bookhistory = History(os.path.join(self.dicSetting[u'settingdir'],
                                                            u'history.txt' ))
        # メニュー
        self.uimanager = gtk.UIManager()
        accelgroup = self.uimanager.get_accel_group()
        self.add_accel_group(accelgroup)

        actiongroup0 = gtk.ActionGroup('UIMergeExampleBase')
        actiongroup0.add_actions([
            ('File',    None, u'ファイル(_F)'),
                    ('open', gtk.STOCK_OPEN, u'開く(_O)',
                                '<Control>O', None, self.menu_fileopen_cb),
                    ('new',  None,           u'新着情報(_N)',
                                '<Control>N', None, self.whatsnew_cb),
                    ('history', None, u'履歴',
                                None,         None, None ),
                    ('quit', gtk.STOCK_QUIT, u'終了(_Q)',
                                '<Control>Q', None, self.menu_quit),
            ('Page',    None, u'ページ(_P)'),
                    ('jump', gtk.STOCK_JUMP_TO, u'移動(_J)',
                                '<Control>J', None, self.menu_pagejump_cb),
                    ('top', gtk.STOCK_GOTO_LAST, u'先頭(_T)',
                                '<Control>T', None, self.menu_gototop_cb),
                    ('end', gtk.STOCK_GOTO_FIRST, u'最終(_E)',
                                '<Control>E', None, self.menu_gotoend_cb),
                    ('setbookmark', None, u'しおりを挟む(_D)',
                                '<Control>D', None, self.shiori_here_cb),
                    ('listbookmark', None, u'しおりの管理(_L)',
                                '<Control>L', None, self.shiori_list_cb),
            ('Index',   None, u'目次(_I)'),
            ('Setting', None, u'設定(_S)'),
                    ('preference', gtk.STOCK_PREFERENCES, u'設定(_P)',
                                '<Control>P', None, self.menu_fontselect_cb),
            ('Help',    None, u'ヘルプ(_H)'),
                    ('view', gtk.STOCK_INFO, None,
                                '<Control>I', None, self.menu_logwindow_cb),
                    ('info', gtk.STOCK_ABOUT, None,
                                None, None, self.menu_about_cb)
            ])
        self.uimanager.insert_action_group(actiongroup0, 0)

        actiongroup = gtk.ActionGroup('UIMergeExampleBase')
        self.actiongroup = actiongroup

        merge_id = self.uimanager.add_ui_from_string(
                                    self.menutmp.format(self.menupagemove))
        self.menubar = self.uimanager.get_widget("/MenuBar")

        # 履歴用のフラグ
        self.menuhis_id = -1
        self.menu_history_update()

        #   ポップアップメニュー
        self.popupmenu_bookmark = self.uimanager.get_widget('/popmain')

        #   テキスト情報
        self.cc = AozoraCurrentTextinfo()

        #   文章表示領域
        self.imagebuf = gtk.Image()
        self.ebox = gtk.EventBox()
        self.ebox.add(self.imagebuf) # image がイベントを見ないのでeventboxを使う
        self.ebox.connect('button-press-event', self.button_press_event_cb )
        self.ebox.connect('button-release-event', self.button_release_event_cb )

        #   ビルド
        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.menubar)
        self.vbox.pack_end(self.ebox)
        self.add(self.vbox)

        self.connect('delete_event', self.delete_event_cb)
        self.connect('size-allocate', self.size_allocate_event_cb)
        self.connect('realize', self.realize_event_cb)
        self.connect('expose-event', self.expose_event_cb)
        self.connect('key-press-event', self.key_press_event_cb)
        self.set_position(gtk.WIN_POS_CENTER)

        #   下請けサブプロセス用スクリプトの書き出し
        self.drawingsubprocess = os.path.join(sys.path[0],u'draw.py')
        with open(self.drawingsubprocess,'w') as f0:
            f0.write(   u'#!/usr/bin/python\n'+
                        u'# -*- coding: utf-8 -*-\n'+
                        u'#  draw.py\n'+
                        u'import sys\n'+
                        u'from formater import CairoCanvas\n'+
                        u'if __name__ == "__main__":\n'+
                        u'    cTmp = CairoCanvas()\n'+
                        u'    cTmp.writepage(long(sys.argv[1]))' )

        self.dlgSetting = None

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        #if event.state & gtk.gdk.CONTROL_MASK:
        #    key = event.hardware_keycode #event.keyval
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
            self.page_common(0)
        elif key == 0xff57:
            # End
            self.page_common(self.cc.pagecounter)
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def whatsnew_cb(self, widget):
        """ 青空文庫新着情報
        """
        dlg = WhatsNewUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN,     gtk.RESPONSE_OK))
        res = dlg.run()
        if res == gtk.RESPONSE_OK:
            fn, z = dlg.get_selected_item()
            dlg.destroy()
            self.bookopen(fn, zipname=z)
        else:
            dlg.destroy()

    def mokuji_jump(self, widget, s):
        """ 目次ジャンプの下請け
            ページ番号の指定が手抜き
        """
        self.page_common(int(s.split()[1])-1)

    def shiori_here_cb(self, widget):
        """ テキスト上でのポップアップ（１）
            しおりを挟む
        """
        n = self.cc.get_booktitle()
        s = u'%s,%s,%d,%s,%s,%s\n' % ( n[0], n[1], self.currentpage+1,
                datetime.date.today(), self.cc.sourcefile, self.cc.zipfilename)
        bm = BookMarkInfo()
        bm.append(s)

    def shiori_list_cb(self, widget):
        """ テキスト上でのポップアップ（２）
            しおり一覧
        """
        bi = BookmarkUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_DELETE,   gtk.RESPONSE_REJECT,
                                gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OK,       gtk.RESPONSE_ACCEPT))
        while True:
            s = bi.run()
            if s == gtk.RESPONSE_ACCEPT:
                s = bi.get_selected_item()
                bi.destroy()
                break
            elif s == gtk.RESPONSE_REJECT:
                bi.removerecord()
            else:
                bi.destroy()
                s = None
                break
        if s:
            self.bookopen(s[4], zipname=s[5], pagenum=int(s[2])-1)


    def menu_fontselect_cb(self, widget):
        """ 画面設定
        """
        if self.dlgSetting:
            # 多重起動抑止
            return
        self.dlgSetting = ScreenSetting(parent=self,
                        flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK,       gtk.RESPONSE_ACCEPT))
        if self.dlgSetting.run() == gtk.RESPONSE_ACCEPT:
            self.dlgSetting.settingupdate()
            if aozoradialog.msgyesno( u'設定を反映するには再起動が必要です。' + \
                            u'今すぐ再起動しますか？',self ) == gtk.RESPONSE_YES:
                self.isRestart = True
        self.dlgSetting.destroy()
        self.dlgSetting = None
        if self.isRestart:
            self.exitall()

    def menu_pagejump_cb(self, widget):
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

    def menu_gototop_cb(self, widget):
        """ 先頭ページへ
        """
        self.page_common(0)

    def menu_gotoend_cb(self, widget):
        """ 最終ページへ
        """
        self.page_common(self.cc.pagecounter)

    def menu_logwindow_cb(self, widget):
        """ ログファイルの表示
        """
        if self.logwindow != None:
            return # 多重起動を抑止
        self.logwindow = Logviewer(parent=self,
                                    flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                buttons=(gtk.STOCK_CLOSE,   gtk.RESPONSE_OK))
        self.logwindow.run()
        self.logwindow.destroy()
        self.logwindow = None

    def menu_about_cb(self, widget):
        """ プログラムバージョン
        """
        dlg = gtk.AboutDialog()
        dlg.set_program_name(u'青空文庫リーダー')
        dlg.set_version(u'unstable version')
        dlg.set_copyright(u'by sakai satoru 2015')
        dlg.run()
        dlg.destroy()

    def menu_quit(self,widget,data=None):
        self.exitall()

    def menu_fileopen_cb( self, widget ):
        self.menu_fileopen()

    def menu_historyopen_cb(self, widget):
        """ 読書履歴
        """
        i = int(widget.get_label().split(u':')[0][1:]) - 1
        (nm, pg, fn, z) = self.bookhistory.get_item(i).split(u',')
        self.bookopen(fn, zipname=z, pagenum=int(pg))
        self.menu_history_update() # メニューバーのアイテム書き換え

    def menu_fileopen(self):
        """ 青空文庫ファイルを開く
        """
        dlg = BunkoUI()
        dlg.run()
        fn, z = dlg.get_filename()
        if fn != u'':
            self.bookopen(fn, zipname=z)

    def bookopen(self, fn, zipname=u'', pagenum=0):
        """ テキストを開く
        """
        if self.isNowFormatting:
            return
        if self.cc.sourcefile != fn:
            self.savecurrenttexthistory() # 履歴に保存,UIも書き換えないと齟齬を生じる
            self.isNowFormatting = True
            pb = formaterUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL))
            # 新規読み込み
            a = zipfile.ZipFile(zipname, u'r' )
            a.extractall(self.aozoratextdir)
            pb.touchup(fn, zipname)
            c = pb.run()
            if c == gtk.RESPONSE_CANCEL:
                # 途中終了
                pass
            else:
                # 目次の作成

                # ページ情報の複写
                self.cc = copy.copy(pb.currentText)
            pb.destroy()
            self.isNowFormatting = False
        self.page_common(pagenum)

    def menu_history_update(self):
        """ 読書履歴をメニューへ登録する
        """
        if self.menuhis_id != -1:
            self.uimanager.remove_ui(self.menuhis_id )
            self.uimanager.remove_action_group(self.historyaction)
            self.uimanager.ensure_update()
            del self.historyaction

        count = 1
        menu = []
        action = []
        for item in self.bookhistory.iter():
            a_name = 'history%d' % count
            action.append((a_name, None,
                u'_%d:%s' % (count,item.split(',')[0]),
                None, None, self.menu_historyopen_cb))
            menu.append('<menuitem action="%s"/>' % a_name)
            count += 1
        self.historyaction = gtk.ActionGroup('historymenuaction')
        self.historyaction.add_actions(action)
        menustr = '''<ui>
                <menubar name="MenuBar">
                    <menu action="File">
                        <menu action="history">
                            {0}
                        </menu>
                    </menu>
                </menubar>
        </ui>'''
        self.uimanager.insert_action_group(self.historyaction, -1)
        self.menuhis_id = self.uimanager.add_ui_from_string(
                                    menustr.format(''.join(menu)))
        self.uimanager.ensure_update()

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

    def page_common(self, n=-1):
        """ 指定されたページをUIへ表示する
            テキストが開かれていなければ何もしない
        """
        if self.cc.sourcefile != u'':
            if n > self.cc.pagecounter:
                # 存在しないページが指定されている
                n = 0
            if n >= 0:
                self.currentpage = n
            #cTmp = CairoCanvas()
            #cTmp.writepage(self.cc.currentpage[self.currentpage])
            #del cTmp
            # pango のメモリリークに対応するためサブプロセスへ移行
            subprocess.call(['python',self.drawingsubprocess,
                            u'%ld' % self.cc.currentpage[self.currentpage]])
            self.imagebuf.set_from_file(os.path.join(
                            self.get_value(u'workingdir'), 'thisistest.png'))
            bookname,author = self.cc.get_booktitle()
            self.set_title(u'【%s】 %s - %s / %s - 青空文庫リーダー' %
                (bookname, author, self.currentpage+1,self.cc.pagecounter+1))

    def size_allocate_event_cb(self, widget, event, data=None):
        pass

    def realize_event_cb(self, widget):
        pass

    def expose_event_cb(self, widget, event, data=None):
        return False

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def savecurrenttexthistory(self):
        """ 現在開いているテキストがあれば履歴へ保存する
        """
        bookname,author = self.cc.get_booktitle()
        if bookname and self.cc.zipfilename:
            self.bookhistory.update( u'%s,%d,%s,%s' %
                (bookname, self.currentpage,self.cc.sourcefile,self.cc.zipfilename))
            self.isBookopened = True # テキストを開いていた、というフラグ
        self.bookhistory.save()

    def exitall(self, data=None ):
        logging.shutdown()
        self.savecurrenttexthistory()
        #   展開したテキストを全て削除する
        try:
            for s in os.listdir(self.aozoratextdir):
                os.remove(os.path.join(self.aozoratextdir,s))
        except:
            print u'一時ファイルの削除中にエラーが発生しました。'

        self.hide_all()
        gtk.main_quit()

    def run(self, opened=False):
        """ エントリー
            再起動フラグ及びテキストを開いていたかどうかを返す
        """
        self.currentpage = 0
        self.dummytitle = u'　　　青空文庫リーダー'
        self.set_title( u'青空文庫リーダー' )

        s = os.path.join(self.get_value(u'workingdir'), 'titlepage.txt' )
        with codecs.open(s,'w', 'shift_jis') as f0:
            f0.write(
                self.dummytitle+'\n'+
                u'\n'+
                u'［＃本文終わり］\n'+
                u'バージョン［＃「バージョン」は中見出し］\n'+
                u'［＃１字下げ］非安定版　2015［＃「2015」は縦中横］年2［＃「2」は縦中横］月21［＃「21」は縦中横］日\n'+
                u'\n'+
                u'このプログラムについて［＃「このプログラムについて」は中見出し］\n'+
                u'［＃ここから１字下げ］'+
                u'青空文庫 http://www.aozora.gr.jp/ のテキストファイルを Pango と GTK+2 と Python2 を使って縦書きで読もう、というものです。\n'+
                u'［＃字下げ終わり］\n'+
                u'\n'+
                u'既知の問題点［＃「既知の問題点」は中見出し］\n'+
                u'［＃ここから１字下げ、折り返して２字下げ］'+
                u'・プログラム内で使用する作業領域［＃「作業領域」は横組み］の解放を'+
                u' Python まかせにしており、このためメモリを相当使い'+
                u'ます。メモリの少ない環境で動かす場合は念のため注意願'+
                u'います。\n'+
                u'・Pango の仕様により、文字の向きが正しく表示されない場合があります。\n'+
                u'・傍線における波線を実装していません。\n'+
                u'・注記が重複すると正しく表示されない場合があります。\n'+
                u'・傍点の本文トレースは厳密なものではありません。\n'+
                u'・連続して出現するルビが重なった場合、後続が下にずれます。どこにかかっているのか分かりにくくなった場合は'+
                u'フォントサイズを小さくしてみてください。\n'+
                u'・画像の直後で改ページされるとキャプションが表示されません。\n'+
                u'・割り注の途中で改行したり、１行からはみ出したりした場合は正しく表示されません。\n'+
                u'・閲覧履歴はプログラム終了時に開いていたテキストのみ記録されます。これは仕様です。'+
                u'複数のテキストを行き来する場合はしおりをご利用ください。\n'+
                u'［＃字下げ終わり］\n'+
                u'［＃改ページ］\n'+
                u'\nライセンス［＃「ライセンス」は大見出し］\n'+
                u'［＃ここから１字下げ］\n' +
                u'Copyright 2015 sakaisatoru  endeavor2wako@gmail.com\n'+
                u'\n'+
                u'This program is free software; you can redistribute it and/or modify'+
                u'it under the terms of the GNU General Public License as published by'+
                u'the Free Software Foundation; either version 2 of the License, or'+
                u'(at your option) any later version.'+
                u'\n'+
                u'This program is distributed in the hope that it will be useful,'+
                u'but WITHOUT ANY WARRANTY; without even the implied warranty of'+
                u'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the'+
                u'GNU General Public License for more details.'+
                u'\n'+
                u'You should have received a copy of the GNU General Public License'+
                u'along with this program; if not, write to the Free Software'+
                u'Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,'+
                u'MA 02110-1301, USA.\n'+
                u'［＃字下げ終わり］\n')

        aoTmp = Aozora()
        aoTmp.set_source(s)
        for tmp in aoTmp.formater():
            pass
        self.cc = copy.copy(aoTmp.currentText)
        #cTmp = CairoCanvas()
        #cTmp.writepage(0)
        #del cTmp
        subprocess.call(['python',self.drawingsubprocess, '0'])
        del aoTmp
        self.imagebuf.clear()
        self.imagebuf.set_from_file(
            os.path.join(self.get_value(u'workingdir'), 'thisistest.png'))

        self.show_all()

        """ テキスト読み込み指示があった
            メインループ開始前でこのままだとformaterUIがすべってしまうので
            アイドル待ちループに登録してメインループ後に動かす
        """
        if opened and len(self.menuitem_history):
            gobject.idle_add(self.restart_sub)

        gtk.main()
        return self.isRestart, self.isBookopened

    def restart_sub(self):
        """ gobject.idle_add 用のサブ
            1回だけ実行すれば良いのでFalse で戻る
        """
        rv = self.bookhistory.get_item(0)
        if rv:
            (nm, pg, fn, z) = rv.split(u',')
            self.bookopen(fn, zipname=z, pagenum=int(pg))
        return False

if __name__ == '__main__':
    gc.enable()
    restart = True
    bookopened = False
    while restart:
        ui = ReaderUI()
        restart, bookopened = ui.run(bookopened)
        ui.destroy()
        del ui

