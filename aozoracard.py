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

""" 青空文庫ブラウザ

    青空文庫のサイトにアクセスし、著者及び蔵書検索を行う。

    作家一覧 -> 作家 ->   (公開中の)作品 ->         図書カード
                作家名読み    作品名                 ファイルのダウンロード
                生没年        新字旧仮名 or 新仮名    テキストファイル（ルビあり）
                人物について

    サイトの構造
        作家一覧URL
            http://www.aozora.gr.jp/index_pages/person_※.html
            ※ には a, ka, sa 等が入る
                作家リスト
                    <h2><a name='sec※'>※２</h2>
                    ※には1..5, ※2はア、イ、ウ、エ、オ等
                    <ol>
                        <li><a href=''>作家名</a>(公開中:n)</li>
                    </ol>

        作品リスト
        http://www.aozora.gr.jp/index_pages/person879.html#sakuhin_list_1
        <h1>作家別作品リスト：No.※作家ID</h1>
        <table summary='作家データ'>
            <tr><td>作家名：</td><td>※作家名</td></tr>
            <tr><td>作家名読み：</td><td>※作家名読み</td></tr>
            <tr><td>ローマ字表記：</td><td>※ローマ字表記</td></tr>
            <tr><td>生年：</td><td>※yyyy-mm-dd</td></tr>
            <tr><td>没年：</td><td>※yyyy-mm-dd</td></tr>
            <tr><td>人物について：</td><td>※人物について　オプションでwikipediaへのリンク</td></tr>
        </table>
        <h2><a name="sakuhin_list_1">公開中の作品</a></h2>
        <ol>
                <li><a href='※図書カードへのリンク'>※作品名</a> ※仮名遣い、作品ID  ※オプションで翻訳物の場合、原著者へのリンク </li>
            </ol>

        図書カード
        http://www.aozora.gr.jp/cards/000879/card4872.html
            <h2><a name="download">ファイルのダウンロード</a></h2>
            <table>
                <tr>
                    <td>テキストファイル(ルビあり)</td>
                    <td>zip</td>
                    <td><a href='./files/ファイル名'>ファイル名</a></td>
                    <td><td>
                </tr>
            </table>
"""



from hypertext import HyperTextView

import jis3
from readersub import ReaderSetting, AozoraDialog, Download

import sys
import codecs
import re
import os.path
import datetime
import unicodedata
import urllib
import webbrowser
import gtk
import cairo
import pango
import pangocairo
import gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

class AuthorListData(gtk.TreeView):
    """ 著者リスト (GUI データモデル)
        氏名, 著作リストURL, 公開中の著作数
    """
    def __init__(self, *args, **kwargs):
        gtk.TreeView.__init__(self, *args, **kwargs)
        # 各項目ごとのレンダリング関数の設定
        self.rend_authorname = gtk.CellRendererText()
        self.rend_authorname.set_property('editable', False)

        self.rend_books = gtk.CellRendererText()
        self.rend_books.set_property('editable', False)

        self.rend_authorurl = gtk.CellRendererText()
        self.rend_authorurl.set_property('editable', False)

        self.col_authorname = gtk.TreeViewColumn(u'著者名',
                                          self.rend_authorname,
                                          text=0)
        #self.col_authorname.set_max_width(180)
        self.col_authorname.set_resizable(True)
        self.col_authorname.set_sort_column_id(0)

        self.append_column(self.col_authorname)


class BookListData(gtk.TreeView):
    """ 著作リスト (GUI データモデル)
        表題, URL, コメント
    """
    def __init__(self, *args, **kwargs):
        gtk.TreeView.__init__(self, *args, **kwargs)
        # 各項目ごとのレンダリング関数の設定
        self.rend_bookname = gtk.CellRendererText()
        self.rend_bookname.set_property('editable', False)

        self.rend_remarks = gtk.CellRendererText()
        self.rend_remarks.set_property('editable', False)

        self.rend_bookurl = gtk.CellRendererText()
        self.rend_bookurl.set_property('editable', False)

        self.col_bookname = gtk.TreeViewColumn(u'作品名',
                                          self.rend_bookname,
                                          text=0)
        #self.col_bookname.set_max_width(180)
        self.col_bookname.set_resizable(True)
        self.col_bookname.set_sort_column_id(0)

        self.col_remarks = gtk.TreeViewColumn(u'字体など',
                                          self.rend_remarks,
                                          text=1)
        self.col_remarks.set_resizable(False)
        self.col_remarks.set_max_width(80)
        self.col_remarks.set_sort_column_id(1)

        self.append_column(self.col_bookname)
        self.append_column(self.col_remarks)


"""
    UI
"""

class AuthorList(gtk.Window, ReaderSetting, AozoraDialog, Download):
    """ インターネット上の青空文庫へのアクセスUI

        １）50音順に著者を表示し、
        ２）選択された著者の作品リストを表示
        ３）選択された作品をダウンロード、複数選択可能
                ダウンロードしたZIPファイルを展開してルビつきテキストファイルを
                ローカルに保存する
        ダイアログ戻り値
            (gtk.RESPONSE_OK | gtk.RESPONSE_CANCEL,
                最後に落とした作品のテキストファイル名 | None)
    """
    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)
        AozoraDialog.__init__(self)

        self.AOZORA_URL= u'http://www.aozora.gr.jp/index_pages'

        #
        self.set_title( u'著者別索引' )
        # 著者リスト
        self.al_data = AuthorListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.al_data.set_rules_hint(True)
        self.al_data.get_selection().set_mode(gtk.SELECTION_SINGLE)
        #self.al_data.connect("row-activated", self.row_activated_treeview_cb)
        self.al_data.connect("cursor_changed", self.cursor_changed_treeview_cb)
        #self.al_data.set_headers_clickable(True)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.al_data)
        self.sw.set_size_request(240,-1)

        # 作品リスト
        self.bl_data = BookListData(model=gtk.ListStore(
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING,
                                                        gobject.TYPE_STRING ))
        self.bl_data.set_rules_hint(True)
        self.bl_data.get_selection().set_mode(gtk.SELECTION_MULTIPLE)#(gtk.SELECTION_SINGLE)
        self.bl_data.connect("row-activated", self.row_activated_treeview_cb)
        #self.bl_data.connect("cursor_changed", self.cursor_changed_treeview_cb)
        #self.al_data.set_headers_clickable(True)

        self.sw2 = gtk.ScrolledWindow()
        self.sw2.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw2.add(self.bl_data)

        # 著者コメント
        self.textbuffer_authorinfo = gtk.TextBuffer()
        self.textbuffer_authorinfo.set_text( u'' )

        self.textview_authorinfo = HyperTextView(self.textbuffer_authorinfo)
        self.textview_authorinfo.link['foreground'] = 'dark blue'
        self.textview_authorinfo.set_wrap_mode(gtk.WRAP_CHAR)
        self.textview_authorinfo.set_editable(False)
        self.textview_authorinfo.connect('anchor-clicked', self.clicked_anchor_cb)

        self.sw3 = gtk.ScrolledWindow()
        self.sw3.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw3.add(self.textview_authorinfo)

        self.btn_A = gtk.Button(label=u'あ')
        self.btn_KA = gtk.Button(label=u'か')
        self.btn_SA = gtk.Button(label=u'さ')
        self.btn_TA = gtk.Button(label=u'た')
        self.btn_NA = gtk.Button(label=u'な')
        self.btn_HA = gtk.Button(label=u'は')
        self.btn_MA = gtk.Button(label=u'ま')
        self.btn_YA = gtk.Button(label=u'や')
        self.btn_RA = gtk.Button(label=u'ら')
        self.btn_WA = gtk.Button(label=u'わ')
        self.btn_ZZ = gtk.Button(label=u'他')

        self.btn_A.connect("clicked", self.clicked_btnSet_cb, u'a')
        self.btn_KA.connect("clicked", self.clicked_btnSet_cb, u'ka')
        self.btn_SA.connect("clicked", self.clicked_btnSet_cb, u'sa')
        self.btn_TA.connect("clicked", self.clicked_btnSet_cb, u'ta')
        self.btn_NA.connect("clicked", self.clicked_btnSet_cb, u'na')
        self.btn_HA.connect("clicked", self.clicked_btnSet_cb, u'ha')
        self.btn_MA.connect("clicked", self.clicked_btnSet_cb, u'ma')
        self.btn_YA.connect("clicked", self.clicked_btnSet_cb, u'ya')
        self.btn_RA.connect("clicked", self.clicked_btnSet_cb, u'ra')
        self.btn_WA.connect("clicked", self.clicked_btnSet_cb, u'wa')
        self.btn_ZZ.connect("clicked", self.clicked_btnSet_cb, u'zz')

        self.btnbox = gtk.HButtonBox()
        #self.btnbox.set_size_request(-1,32)
        self.btnbox.pack_start(self.btn_A, False, False, 0)
        self.btnbox.pack_start(self.btn_KA, False, False, 0)
        self.btnbox.pack_start(self.btn_SA, False, False, 0)
        self.btnbox.pack_start(self.btn_TA, False, False, 0)
        self.btnbox.pack_start(self.btn_NA, False, False, 0)
        self.btnbox.pack_start(self.btn_HA, False, False, 0)
        self.btnbox.pack_start(self.btn_MA, False, False, 0)
        self.btnbox.pack_start(self.btn_YA, False, False, 0)
        self.btnbox.pack_start(self.btn_RA, False, False, 0)
        self.btnbox.pack_start(self.btn_WA, False, False, 0)
        self.btnbox.pack_end(self.btn_ZZ, False, False, 0)

        self.vbox2 = gtk.VPaned()
        self.vbox2.pack1(self.sw3)
        self.vbox2.pack2(self.sw2)
        #self.vbox2.set_size_request(400,300)

        self.btnCancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        self.btnCancel.connect("clicked", self.clicked_btnCancel_cb )
        self.btnOpen = gtk.Button(stock=gtk.STOCK_OPEN)
        self.btnOpen.connect("clicked", self.clicked_btnOpen_cb )
        self.btnboxcmd = gtk.HButtonBox()
        self.btnboxcmd.set_layout(gtk.BUTTONBOX_END )
        self.btnboxcmd.pack_start(self.btnOpen)
        self.btnboxcmd.pack_end(self.btnCancel)

        self.hbox1 = gtk.HPaned()
        self.hbox1.pack1(self.sw)
        self.hbox1.pack2(self.vbox2)

        self.sbStatus = gtk.Statusbar()
        self.sbStatus.set_has_resize_grip(True)

        self.vbox = gtk.VBox()
        self.vbox.set_size_request(600,400)
        self.vbox.pack_start(self.btnbox, expand=False)
        self.vbox.pack_start(gtk.HSeparator(), expand=False)
        self.vbox.pack_start(self.hbox1, True, True, 0)
        self.vbox.pack_start(gtk.HSeparator(), expand=False)
        self.vbox.pack_start(self.btnboxcmd, expand=False )
        self.vbox.pack_end(self.sbStatus, expand=False)
        self.add(self.vbox)
        self.connect("delete_event", self.delete_event_cb)
        self.connect("key-press-event", self.key_press_event_cb )
        self.set_position(gtk.WIN_POS_CENTER)

        # 戻り値初期化
        self.selectfile = u''
        self.selectbook = u''
        self.lastselectfile = None
        self.ack = gtk.RESPONSE_NONE
        #self.get_authorlist(u'a')

    def clicked_anchor_cb(self, widget, text, anchor, button ):
        webbrowser.open( anchor )

    def clicked_btnSet_cb(self, widget, v):
        self.get_authorlist(v)
        self.bl_data.get_model().clear()

    def get_authorlist(self, a):
        """ 指定された50音行の著者一覧を得る
        """
        readcodecs = 'UTF-8'
        reAuthorList = re.compile( ur'.*?<li><a href=\"(?P<URL>.+?)\">.*?(?P<AUTHOR>.+?)</a>.*?公開中：(?P<BOOKS>\d+).*?</li>' )

        url = u'%s/person_%s.html' % ( self.AOZORA_URL,  a )
        filename = os.path.join(self.get_value(u'workingdir'), u'person_%s.html' % a)
        if not os.path.exists(filename):
            try:
                urllib.urlretrieve(url, filename)
            except IOError:
                self.msgerrinfo( u'ダウンロードに失敗しました。ネットワークへの接続状況を確認してください。' )
                return

        self.al_data.get_model().clear()
        with codecs.open( filename, 'r', readcodecs ) as f0:
            for line in f0:
                mTmp = reAuthorList.search(line)
                if mTmp:
                    self.al_data.get_model().append(
                            (mTmp.group(u'AUTHOR') , mTmp.group(u'BOOKS'),
                                mTmp.group(u'URL'))
                        )
        self.textbuffer_authorinfo.set_text( u'' )

    def get_booklist(self, a):
        """ 著作一覧及び著者コメントを得る
            著者コメント及び著作コメント欄のアンカーは取り除く
        """
        readcodecs = 'UTF-8'
        reBookList = re.compile( ur'.*?<li><a href=\"(?P<URL>.+?)\">(?P<BOOKTITLE>.+?)</a>(?P<REMARKS>.+?)</li>' )
        reAuthorComment = re.compile( ur'<tr><td class="header">(?P<HEADER>.*?)</td><td>(?P<INFO>.*?)</td></tr>' )
        reSub = re.compile( ur'<.+?>' )
        reWikipediaTag = re.compile( ur'「<a href="(?P<LINK>http://ja.wikipedia.org/wiki/.*?)".*?>(?P<AUTHOR>.*?)</a>」')

        filename = a.split(u'#')[0]
        url = u'%s/%s' % (self.AOZORA_URL,filename)
        filename = os.path.join(self.get_value(u'workingdir'), filename)
        if not os.path.exists(filename):
            try:
                urllib.urlretrieve(url, filename)
            except IOError:
                self.msgerrinfo( u'ダウンロードに失敗しました。ネットワークへの接続状況を確認してください。' )
                return

        with codecs.open( filename, 'r', readcodecs ) as f0:
            self.bl_data.get_model().clear()
            self.textbuffer_authorinfo.set_text(u'')
            flag = False
            sAuthorComment = u''
            for line in f0:
                if line == u'<table summary="作家データ">\n':
                    flag = True
                if flag:
                    if line == u'</table>\n':
                        flag = False
                    else:
                        # 著者コメントを得る
                        mTmp = reAuthorComment.search(line)
                        if mTmp:
                            sTmpInfo = u'%s:%s\n' % (
                                mTmp.group(u'HEADER').lstrip().rstrip(u' :：'),
                                reSub.sub(u'',mTmp.group(u'INFO')).lstrip().rstrip())
                            mWikitag = reWikipediaTag.search(mTmp.group(u'INFO'))
                            if mWikitag:
                                # jp.wikipediaへのリンクがあればタグを生成する
                                self.textview_authorinfo.insert(
                                    sTmpInfo.rstrip(u'「%s」\n' % mWikitag.group(u'AUTHOR')))
                                self.textview_authorinfo.insert_with_anchor(
                                    u'Wikipedia %s' % mWikitag.group(u'AUTHOR'),
                                    mWikitag.group(u'LINK') )
                            else:
                                self.textview_authorinfo.insert( sTmpInfo )

                else:
                    # 著作であれば一覧へ追加する
                    mTmp = reBookList.search(line)
                    if mTmp:
                        self.bl_data.get_model().append(
                                (mTmp.group(u'BOOKTITLE'),
                                    reSub.sub(u'',mTmp.group(u'REMARKS').lstrip().rstrip()),
                                        mTmp.group(u'URL'))
                            )
        #self.textbuffer_authorinfo.set_text( sAuthorComment )

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
            (f, sMes) = self.selected_book(u'%s/%s' %
                                        (self.AOZORA_URL, c.get_value(i, 2)) )
            if not f:
                self.msgerrinfo( sMes )
            else:
                self.lastselectfile = sMes

        return f

    def row_activated_treeview_cb(self, path, view_column, column ):
        """ 作品リストをダブルクリックした時の処理
            ダイアログを開いたまま、青空文庫のダウンロードを行う
        """
        if self.get_selected_book():
            self.msginfo( u'ダウンロードしました' )
            self.ack = gtk.RESPONSE_OK
        else:
            pass

    def clicked_btnOpen_cb(self, widget):
        """ 開くボタンをクリックした時の処理
            ダウンロードして終わる
        """
        if self.get_selected_book():
            self.ack = gtk.RESPONSE_OK
            self.exitall()
        else:
            pass

    def get_selected_item(self):
        """ 選択された著者のURLを返す
        """
        # この操作で返されるのは
        # c データモデルオブジェクト、ここではgtk.ListStore
        # d 選択された行
        (c,d) = self.al_data.get_selection().get_selected_rows()  # 選択された行
        f = False
        try:
            iters = [c.get_iter(p) for p in d]
            # ここでは1行しか選択させないが複数行の選択に無改造で対応すべく for で回している
            for i in iters:
                self.selectfile = c.get_value(i, 2)
                # ステータスバーへの表示
                ctx = self.sbStatus.get_context_id(u'')
                self.sbStatus.push(ctx, u'%s   公開中の作品数:%s' % (c.get_value(i, 0), c.get_value(i, 1)))
            f = True
        except IndexError:
            pass
        return f

    def cursor_changed_treeview_cb(self, widget):
        """ 著者リストでカーソル移動した時の処理
            作品リストを取得する
        """
        if self.get_selected_item():
            self.get_booklist( self.selectfile )
        else:
            pass

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def clicked_btnCancel_cb(self, widget):
        self.exitall()
        self.ack = gtk.RESPONSE_CANCEL
        self.selectfile = u''

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            self.exitall()
            self.ack = gtk.RESPONSE_CANCEL
            self.selectfile = ''
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def exitall(self):
        self.hide_all()
        gtk.main_quit()

    def run(self):
        self.show_all()
        self.set_modal(True)
        gtk.main()
        return (self.ack, self.lastselectfile)


if __name__ == '__main__':
    a = AuthorList()
    a.run()


