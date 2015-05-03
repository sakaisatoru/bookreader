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

import aozoradialog
from readersub_nogui import ReaderSetting, History
from formater       import Aozora, AozoraCurrentTextinfo
#from cairocanvas    import CairoCanvas
from whatsnew       import WhatsNewUI
from logview        import Logviewer
from bunko3         import BunkoUI

import tempfile
import sys
import codecs
import os.path
import datetime
import logging
import copy
import subprocess
import os
import zipfile
import inspect

import gc
import gtk
import gobject

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
        +-------------+--------+----------+--------+
        |作品名       |著者名  |ページ番号|日付    |
        +-------------+--------+----------+--------+
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
            gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING,
            gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING,
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
                                    sc[5],          # zipfile
                                    sc[6]))         # 作品ID

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
            複数個選択時は無効とし、('')を返す
        """
        rv = ('')
        (c,d) = self.bookmark_bv.get_selection().get_selected_rows()  # 選択された行
        if len(d) > 1:
            dlg = aozoradialog.msgerrinfo(
                    u'ページを開く時は、しおりを一つしか選べません。' ,self)
        else:
            try:
                iters = [c.get_iter(p) for p in d]
                for i in iters:
                    rv = [c.get_value(i, k) for k in xrange(7)]
            except IndexError:
                pass
        return rv

    def key_press_event_cb(self, widget, event):
        """ キー入力のトラップ
        """
        if event.keyval == 0xffff:  # Delete
            self.removerecord()
            return True
        return False                # False を返してデフォルトルーチンに繋ぐ

    def savebookmark(self):
        """ UI上のしおりデータを保存する。
        """
        bi = BookMarkInfo()
        bi.remove_all()
        m = self.bookmark_bv.get_model()
        i = m.get_iter_first()
        while i:
            bi.append2(u'%s,%s,%s,%s,%s,%s,%s\n' % m.get(i, 0, 1, 2, 3, 4, 5, 6))
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

    def touchup(self, fn, zipname, works):
        """ 本来 formater を待ちループ内において、プログレスバーをタイマー
            駆動にして問題ないはずだが、妙な待ち時間が生じるので formaterを
            アイドルタスクへ追加している。
            このため、待ちループがない状況で実行すると失敗する。
            これを実行したらすかさず run() すること。
        """
        self.set_source(fn, zipname, works)
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


class MenuItemUI(object):
    """ メニュー項目を更新する
    """
    def __init__(self, uimanager, menustr, namestr, labelfunc, func_cb):
        """
            uimanager   UIマネージャ
            menustr     メニュー生成用文字列
            namestr     アクション名生成用文字列
            labelfunc   メニューラベル生成用関数
            func_cb     コールバック関数
        """
        self.uimanager = uimanager
        self.merge_id = -1  # マージ番号
        self.menustr = menustr
        self.namestr = namestr
        self.labelfunc = labelfunc
        self.func_cb = func_cb

    def remove(self):
        """ 既存のメニュー項目を抜去する
        """
        if self.merge_id != -1:
            self.uimanager.remove_ui(self.merge_id)
            self.uimanager.remove_action_group(self.action)
            self.uimanager.ensure_update()
            del self.action

    def update(self, itr):
        """ イテレータを受け取ってアップデートする
        """
        self.remove() # 最初に既存部分を抜去する
        count = 1
        menu = []
        action = []
        while True:
            try:
                item = itr.next()
                a_name = '%s%d' % (self.namestr,count)   # アクション名
                a_label = self.labelfunc(count, item)
                # name, stockitem,label, shortcut, tooltip, callback
                action.append((a_name, None, a_label, None, None, self.func_cb))
                menu.append('<menuitem action="%s"/>' % a_name )
                count += 1
            except StopIteration:
                break
        self.action = gtk.ActionGroup('ag_%s' % self.namestr)
        self.action.add_actions(action)
        self.uimanager.insert_action_group(self.action, -1)
        self.merge_id = self.uimanager.add_ui_from_string(
                            self.menustr.format(''.join(menu)))
        self.uimanager.ensure_update()


class ReaderUI(gtk.Window, ReaderSetting):
    """ メインウィンドウ
    """
    menutmp = '''<ui>
        <menubar name="MenuBar">
            <menu action="File">
                <menuitem action="open"/>
                <menuitem action="new"/>
                <menu action="history"/>
                <menuitem action="author"/>
                <menuitem action="websearch"/>
                <separator/>
                <menuitem action="quit"/>
            </menu>
            <menu action="Page">
                {0}
            </menu>
            <menu action="Index">
            </menu>
            <menu action="View">
                <menuitem action="fullscreen"/>
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
            <menuitem action="setbookmark"/>
            <separator/>
            <menuitem action="listbookmark"/>
            <separator/>
            <menuitem action="jump"/>
            <menuitem action="top"/>
            <menuitem action="back"/>
            <menuitem action="forward"/>
            <menuitem action="end"/>
    '''

    sHistoryMenu = '''<ui>
                <menubar name="MenuBar">
                    <menu action="File">
                        <menu action="history">
                            {0}
                        </menu>
                    </menu>
                </menubar>
        </ui>
    '''

    sIndexMenu = '''<ui>
                <menubar name="MenuBar">
                    <menu action="Index">
                            {0}
                    </menu>
                </menubar>
        </ui>
    '''

    def __init__(self):
        """
        """
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)

        # タイトルバーに表示されるアイコン
        # チャイルドウィンドウにも引き継がれるが、ダイアログには反映されない
        #self.set_icon(gtk.gdk.pixbuf_new_from_file(u'aozorareader32.png'))

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
                        '<Control>O', None, lambda a:self.menu_fileopen()),
                ('new',  None,           u'新着情報(_N)',
                        '<Control>N', None, self.whatsnew_cb),
                ('author',gtk.STOCK_INDEX, u'この作者の他の作品(_A)',
                        '<Control>A', None, lambda a:self.menu_fileopen(mode=u'A')),
                ('websearch',gtk.STOCK_NETWORK, u'この作者を調べる(_F)',
                        '<Control>F', None, self.menu_websearch_cb),
                ('history', None, u'履歴(_H)',
                            None,         None, None ),
                ('quit', gtk.STOCK_QUIT, u'終了(_Q)',
                        '<Control>Q', None, lambda a:self.exitall()),
            ('Page',    None, u'ページ(_P)'),
                ('jump', gtk.STOCK_JUMP_TO, u'移動(_J)',
                        '<Control>J', None, self.menu_pagejump_cb),
                ('top', gtk.STOCK_GOTO_LAST, u'先頭(_T)',
                        'Home', None, lambda a:self.page_common(0)),
                ('back', gtk.STOCK_GO_FORWARD, u'前頁',
                        'Next', None, lambda a:self.prior_page()),
                ('forward', gtk.STOCK_GO_BACK, u'次頁',
                        'Prior', None, lambda a:self.next_page()),
                ('end', gtk.STOCK_GOTO_FIRST, u'最終(_E)',
                        'End', None, lambda a:self.page_common(self.cc.pagecounter)),
                ('setbookmark', None, u'しおりを挟む(_D)',
                        '<Control>D', None, self.shiori_here_cb),
                ('listbookmark', None, u'しおりの管理(_L)',
                        '<Control>L', None, self.shiori_list_cb),
            ('Index',   None, u'目次(_I)'),
            ('View', None, u'表示(_V)'),
                ('fullscreen', gtk.STOCK_FULLSCREEN, u'全画面表示',
                            'F11', None, lambda a:self.toggle_fullscreen()),
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

        # 履歴項目UI
        self.miHistory = MenuItemUI(self.uimanager, self.sHistoryMenu,
                    'history', self.history_label, self.menu_historyopen_cb)
        self.miHistory.update(self.bookhistory.iter())

        # 目次UI
        self.miIndex = MenuItemUI(self.uimanager, self.sIndexMenu,
                    'index', self.index_label, self.mokuji_jump_cb)

        #   ポップアップメニュー
        self.popupmenu_bookmark = self.uimanager.get_widget('/popmain')

        #   テキスト情報
        self.cc = AozoraCurrentTextinfo()

        #   文章表示領域
        self.imagebuf = gtk.Image()
        self.ebox = gtk.EventBox()
        self.ebox.add(self.imagebuf) # image がイベントを見ないのでeventboxを使う
        self.ebox.connect('button-press-event', self.button_press_event_cb)

        #   ビルド
        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.menubar, expand=False)
        self.vbox.pack_end(self.ebox)
        self.add(self.vbox)

        self.connect('delete_event', self.delete_event_cb)
        self.connect('size-allocate', self.size_allocate_event_cb)
        self.connect('realize', self.realize_event_cb)
        self.connect('expose-event', self.expose_event_cb)
        self.connect('key-press-event', self.key_press_event_cb)
        self.connect('window_state_event', self.window_state_event_cb)
        self.set_position(gtk.WIN_POS_CENTER)

        #   下請けサブプロセス用スクリプトの書き出し
        self.drawingsubprocess = os.path.join(sys.path[0],u'draw.py')
        with open(self.drawingsubprocess,'w') as f0:
            f0.write(   u'#!/usr/bin/python\n'+
                        u'# -*- coding: utf-8 -*-\n'+
                        u'#  draw.py\n'+
                        u'import sys\n'+
                        u'from cairocanvas import CairoCanvas\n'+
                        u'if __name__ == "__main__":\n'+
                        u'    n = sys.argv[1].split()\n'+
                        u'    t = u"" if len(n) < 4 else n[3]\n'+
                        u'    cTmp = CairoCanvas()\n'+
                        u'    cTmp.writepage(long(n[0]), currentpage=int(n[1]), maxpage=int(n[2]), title=t)' )

        self.dlgSetting = None  # 設定ダイアログ
        self.dlgBookopen = None # テキストオープンダイアログ
        self.window_current_state = None # ウィンドウ状態を保持

    def key_press_event_cb(self, widget, event):
        """ キー入力のトラップ
        """
        #if event.state & gtk.gdk.CONTROL_MASK:
        #    key = event.hardware_keycode #event.keyval
        key = event.keyval
        if key == 32:                           # space
            if event.state & gtk.gdk.SHIFT_MASK:
                self.prior_page()
            else:
                self.next_page()
        elif key == 0xff53:                     # right
            self.prior_page()
        elif key == 0xff51:                     # left
            self.next_page()
        else:
            return False    # Falseを返してデフォルトルーチンに繋ぐ
        return True

    def toggle_fullscreen(self):
        """ 全画面表示の切り替え
        """
        if self.window_current_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.unfullscreen()
        else:
            self.fullscreen()

    def window_state_event_cb(self, widget, event, data=None):
        """ ウィンドウ状態の追跡
        """
        self.window_current_state = event.new_window_state

    def whatsnew_cb(self, widget):
        """ 青空文庫新着情報
        """
        dlg = WhatsNewUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN,     gtk.RESPONSE_OK))
        res = dlg.run()
        if res == gtk.RESPONSE_OK:
            fn, z, worksid = dlg.get_selected_item() # 選択行がないのに呼ぶとエラー
            dlg.destroy()
            self.bookopen(fn, zipname=z, works=worksid) # destory後に呼ぶ
        else:
            dlg.destroy()

    def mokuji_jump_cb(self, widget):
        """ 目次ジャンプ
        """
        self.page_common(int(widget.get_label().split()[1]))

    def shiori_here_cb(self, widget):
        """ テキスト上でのポップアップ（１）
            しおりを挟む
        """
        n = self.cc.get_booktitle()
        s = u'%s,%s,%d,%s,%s,%s,%s\n' % (n[0], n[1], self.currentpage,
                datetime.date.today(), self.cc.sourcefile,
                self.cc.zipfilename, self.cc.worksid)
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
            self.bookopen(s[4], zipname=s[5], works=s[-1], pagenum=int(s[2]))

    def menu_fontselect_cb(self, widget):
        """ 画面設定
        """
        if self.dlgSetting:
            return # 多重起動抑止
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
        adj = gtk.Adjustment(value=1,lower=1,upper=self.cc.pagecounter,
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
            self.page_common(int(a))
        dlg.destroy()

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

    def menu_historyopen_cb(self, widget):
        """ 読書履歴
        """
        i = int(widget.get_label().split(u':')[0][1:]) - 1
        (nm, pg, fn, z, w) = self.bookhistory.get_item(i).split(u',')
        self.bookopen(fn, zipname=z, works=w, pagenum=int(pg))
        self.miHistory.update(self.bookhistory.iter())

    def menu_websearch_cb(self, widget):
        """ ブラウザを呼び出して関連人物の検索を行う
        """
        if self.dlgBookopen == None:
            self.dlgBookopen = BunkoUI(parent=self,
                                        flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=(gtk.STOCK_CANCEL,  gtk.RESPONSE_CANCEL,
                                 gtk.STOCK_OPEN,    gtk.RESPONSE_ACCEPT))
        self.dlgBookopen.websearch_authors(self.cc.worksid)

    def menu_fileopen(self, mode=u''):
        """ 青空文庫ファイルを開く
            ダイアログは一度開いたら、呼び出し側が終了するまで破壊されない。
            mode = 'A' 関連付けモード（カレントテキストの作者関連を見る）
        """
        fn = u''
        if self.dlgBookopen == None:
            self.dlgBookopen = BunkoUI(parent=self,
                                        flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                            buttons=(gtk.STOCK_CANCEL,  gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_OPEN,    gtk.RESPONSE_ACCEPT))
        if mode == u'A':
            self.dlgBookopen.filter_works2author(self.cc.worksid)
        a = self.dlgBookopen.run()
        if a == gtk.RESPONSE_ACCEPT:
            fn, z, w = self.dlgBookopen.get_filename()

            self.dlgBookopen.hide_all()
        elif a == gtk.RESPONSE_DELETE_EVENT:
            # ダイアログが閉じられた
            self.dlgBookopen.destroy()
            self.dlgBookopen = None
        else:
            self.dlgBookopen.hide_all()
        if fn != u'':
            self.bookopen(fn, zipname=z, works=w)

    def bookopen(self, fn, zipname=u'', works=0, pagenum=0):
        """ テキストを開く
            fn ファイル名, zipname ZIP名, works 作品ID, pagenum ページ番号
        """
        self.currentpage = 0
        if self.isNowFormatting:
            return # フォーマット中の読み込みを抑止
        if self.cc.sourcefile != fn:
            self.savecurrenttexthistory() # 履歴に保存
            self.miHistory.update(self.bookhistory.iter())
            self.isNowFormatting = True
            pb = formaterUI(parent=self, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=(   gtk.STOCK_CANCEL,   gtk.RESPONSE_CANCEL))
            # 新規読み込み
            a = zipfile.ZipFile(zipname, u'r' )
            a.extractall(self.aozoratextdir)
            zipname = a.filename
            pb.touchup(fn, zipname, works)
            c = pb.run()
            if c != gtk.RESPONSE_CANCEL:
                self.miIndex.update(pb.mokuji_itre())   # 目次UI
                self.cc = copy.copy(pb.currentText)     # ページ情報の複写
            pb.destroy()
            self.isNowFormatting = False
        if self.currentpage != 0:
            # フォーマット中に閲覧を始めていたらそのページを維持する
            pagenum = self.currentpage
        self.page_common(pagenum)

    def index_label(self, count, item):
        """ 目次UIのラベルを返す この関数は消さない
        """
        return item

    def history_label(self, count, item):
        """ 読書履歴UI のラベルを返す
        """
        return u'_%d:%s' % (count, item.split(',')[0])

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
                        u'%ld %d %d %s' % (self.cc.currentpage[self.currentpage],
                                            self.currentpage,
                                            self.cc.pagecounter,
                                            self.cc.booktitle)])
            self.imagebuf.set_from_file(os.path.join(
                            self.get_value(u'workingdir'), 'thisistest.png'))
            bookname,author = self.cc.get_booktitle()
            self.set_title(u'【%s】 %s - 青空文庫リーダー' % (bookname, author))

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
            self.bookhistory.update( u'%s,%d,%s,%s,%s' %
                        (bookname, self.currentpage, self.cc.sourcefile,
                         self.cc.zipfilename, self.cc.worksid))
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
                u'｜バージョン《ばーじょん》［＃「バージョン」は中見出し］\n'+
                u'［＃１字下げ］非安定版　2015［＃「2015」は縦中横］年5［＃「5」は縦中横］月3［＃「3」は縦中横］日\n'+
                u'\n'+
                u'このプログラムについて［＃「このプログラムについて」は中見出し］\n'+
                u'［＃ここから１字下げ］'+
                u'青空文庫《あおぞらぶんこ》 http://www.aozora.gr.jp/ のテキストファイルを Pango と GTK+2 と Python2 を使って縦書きで読もう、というものです。\n'+
                u'［＃字下げ終わり］\n'+
                u'\n'+
                u'実装されていない機能［＃「実装されていない機能」は中見出し］（……以下に代替）\n'+
                u'［＃ここから１字下げ、折り返して２字下げ］'+
                u'・窓見出し……同行見出し\n'+
                u'・波線（波形傍線）……傍線\n'+
                u'・囲み罫線（一行にかかるもの）……無し\n'+
                u'［＃字下げ終わり］\n'+
                u'\n'+
                u'既知の問題点［＃「既知の問題点」は中見出し］\n'+
                u'［＃ここから１字下げ、折り返して２字下げ］'+
                u'・プログラム内で使用する作業領域の解放を Python まかせにしており、このためメモリを相当使います。\n'+
                u'・全体的に動作が遅いです。\n'+
                u'・行末揃えが不完全です。\n'+
                u'・ダッシュの表示にフォントを使っており、途切れて表示されます。\n'+
                u'・フォントによっては縦書き用の字形を持たないため、正しく表示されないことがあります。\n'+
                u'・注記が重複すると正しく表示されない場合があります。\n'+
                u'・傍点の本文トレースは厳密なものではありません。\n'+
                u'・連続して出現するルビが重なった場合、後続が下にずれます。どこにかかっているのか分かりにくくなった場合は'+
                u'フォントサイズを小さくしてみてください。\n'+
                u'・画像の直後で改ページされるとキャプションを表示しません。\n'+
                u'［＃字下げ終わり］\n'+
                u'［＃改ページ］\n'+
                u'\nライセンス［＃「ライセンス」は大見出し］\n'+
                u'［＃ここから１字下げ］\n' +
                u'Copyright 2015 sakaisatoru  endeavor2wako@gmail.com\n'+
                u'\n'+
                u'This program is free software; you can redistribute it and/or modify '+
                u'it under the terms of the GNU General Public License as published by '+
                u'the Free Software Foundation; either version 2 of the License, or '+
                u'(at your option) any later version.'+
                u'\n'+
                u'This program is distributed in the hope that it will be useful,'+
                u'but WITHOUT ANY WARRANTY; without even the implied warranty of '+
                u'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the '+
                u'GNU General Public License for more details.'+
                u'\n'+
                u'You should have received a copy of the GNU General Public License '+
                u'along with this program; if not, write to the Free Software '+
                u'Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, '+
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
        subprocess.call(['python',self.drawingsubprocess, '0 0 0 '])
        del aoTmp
        self.imagebuf.clear()
        self.imagebuf.set_from_file(
            os.path.join(self.get_value(u'workingdir'), 'thisistest.png'))

        self.show_all()

        """ テキスト読み込み指示があった
            メインループ開始前でこのままだとformaterUIがすべってしまうので
            アイドル待ちループに登録してメインループ後に動かす
        """
        if opened:
            gobject.idle_add(self.restart_sub)

        gtk.main()
        return self.isRestart, self.isBookopened

    def restart_sub(self):
        """ gobject.idle_add 用のサブ
            1回だけ実行すれば良いのでFalse で戻る
        """
        rv = self.bookhistory.get_item(0)
        if rv:
            (nm, pg, fn, z, worksid) = rv.split(u',')
            self.bookopen(fn, zipname=z, works=worksid, pagenum=int(pg))
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

