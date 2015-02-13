#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  bunko.py
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

""" 青空文庫選択ダイアログ ver 2
"""

from readersub  import ReaderSetting
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
import pango

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)


class AozorabunkoIndex():
    """
        公開中　作家別作品一覧拡充版
        http://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip

        フィールド一覧
        （※はこのクラスで保持するフィールド、※※は同インデックス）

          00  ※※作品ID
          01    ※作品名
          02      作品名読み
          03  ※※ソート用読み
          04    ※副題
          05      副題読み
          06      原題
          07      初出
          08  ※※分類番号
          09    ※文字遣い種別
          10      作品著作権フラグ
          11      公開日
          12      最終更新日
          13      図書カードURL
          14    ※人物ID
          15    ※姓
          16    ※名
          17    ※姓読み
          18    ※名読み
          19  ※※姓読みソート用
          20  ※※名読みソート用
          21      姓ローマ字
          22      名ローマ字
          23      役割フラグ
          24      生年月日
          25      没年月日
          26      人物著作権フラグ
          27      底本名1
          28      底本出版社名1
          29      底本初版発行年1
          30      入力に使用した版1
          31      校正に使用した版1
          32      底本の親本名1
          33      底本の親本出版社名1
          34      底本の親本初版発行年1
          35      底本名2
          36      底本出版社名2
          37      底本初版発行年2
          38      入力に使用した版2
          39      校正に使用した版2
          40      底本の親本名2
          41      底本の親本出版社名2
          42      底本の親本初版発行年2
          43      入力者
          44      校正者
          45    ※テキストファイルURL
          46      テキストファイル最終更新日
          47      テキストファイル符号化方式
          48      テキストファイル文字集合
          49      テキストファイル修正回数
          50      XHTML/HTMLファイルURL
          51      XHTML/HTMLファイル最終更新日
          52      XHTML/HTMLファイル符号化方式
          53      XHTML/HTMLファイル文字集合
          54      XHTML/HTMLファイル修正回数


            データファイル１　作品一覧   （重複登録なし）
            作品ID|作品名|ソート用読み|副題|分類番号|文字違い種別|人物ID|テキストファイルURL
            00     01     03           04   08       09           14     45

            データファイル２　著者一覧   （重複登録なし）
            人物ID(key)|姓|名|姓読み|名読み
            14          15 16 17     18

            インデックスファイル４　著者よみがな   （重複登録なし）
            姓読みソート用+名読みソート用|人物ID|（作品一覧における初出レコード番号）
            19             20             14


            重複登録が生じうるインデックス（副キー）
                副キー
                    03 (作品名読み)ソート用読み
                    08 分類番号
                    14 人物ID

                レコード構造
                キーコード(03 or 08 or 14)|キー値|（作品一覧：レコード番号）
    """
    dbSakuhin = []
    dbAuthor = {}
    IdxAuthoryomi = []
    IdxSub = []
    IdxSubdic = {}

    Idxfilename = u''

    def __init__(self, fn=None):
        if fn != None:
            AozorabunkoIndex.Idxfilename = fn
            self.filesetup(fn)

    def remove_all(self):
        """ 読み込んだ内容を全て取り除く
        """
        try:
            while True:
                AozorabunkoIndex.dbSakuhin.pop()
        except IndexError:
            pass
        try:
            while True:
                AozorabunkoIndex.dbAuthor.popitem()
        except KeyError:
            pass
        try:
            while True:
                AozorabunkoIndex.IdxAuthoryomi.pop()
        except IndexError:
            pass
        try:
            while True:
                AozorabunkoIndex.IdxSub.pop()
        except IndexError:
            pass
        try:
            while True:
                AozorabunkoIndex.IdxSubdic.popitem()
        except KeyError:
            pass

    def reloadfile(self):
        """ インデックスファイルを再読み込みする
        """
        self.remove_all()
        self.filesetup(AozorabunkoIndex.Idxfilename)

    def filesetup(self, fn):
        """ 指定されたインデックスファイルを読み込んで格納する
        """
        with file(fn) as f0:
            fcsv = csv.reader(f0)
            rec = -2
            for fi in fcsv:
                rec += 1
                if rec == -1:
                    # ヘッダを読み飛ばす
                    continue

                AozorabunkoIndex.dbSakuhin.append(u'%s|%s|%s|%s|%s|%s|%s|%s' %
                    (fi[0], fi[1], fi[3], fi[4], fi[8], fi[9], fi[14], fi[45]))

                # 著者一覧及び著者よみがな
                if not fi[14] in AozorabunkoIndex.dbAuthor:
                    AozorabunkoIndex.dbAuthor[fi[14]] = u'%s|%s|%s|%s' % (
                                            fi[15],fi[16],fi[17],fi[18])
                    AozorabunkoIndex.IdxAuthoryomi.append(u'%s%s|%s|%d' % (
                                    fi[19], fi[20], fi[14], rec))

                # 副キー
                for i in [3, 14]:
                    self.subindex_regist(u'%02d%s' % (i, fi[i]), rec)
                for i in fi[8].split(u' '):
                    # NDCは列挙されているので切り離して各々登録する
                    if i == u'NDC' or i == u'EC' or i == u'DDC':
                        tp = i
                        continue
                    self.subindex_regist(u'08%s %s' % (tp,i), rec)

            if rec > 0:
                AozorabunkoIndex.IdxAuthoryomi.sort()
                self.subindex_restore()

    def author_find(self, idx):
        """ 人物IDから該当する著者データを得る
            未登録の場合は None を返す
        """
        return False if not idx in Aozorabunko.dbAuthor else Aozorabunko.dbAuthor[idx]

    def author_keys(self, yomi, flag=True):
        """ 著者をよみがな順でイテレータで返す
            flag
                True:
                    yomi と先頭一致するものを返す（デフォルト）
                False:
                    最初に見つかったレコードから最後まで返す。

            よみ|人物ID|初出レコード|姓|名|姓よみ|名よみ
        """
        i = bisect.bisect_left(AozorabunkoIndex.IdxAuthoryomi, yomi)
        try:
            while True:
                if yomi != AozorabunkoIndex.IdxAuthoryomi[i][:len(yomi)] and flag:
                    break
                yield u'%s|%s' % (AozorabunkoIndex.IdxAuthoryomi[i],
                    AozorabunkoIndex.dbAuthor[AozorabunkoIndex.IdxAuthoryomi[i].split(u'|')[1]])
                i += 1
        except IndexError:
            pass

    def subindex_search(self, idx):
        """ 副キー（１）
            2進探索し最寄りの要素を返す。
            見つからない場合は -1,None を返す。
        """
        curr = bisect.bisect_left(AozorabunkoIndex.IdxSub,idx)
        try:
            return (curr, AozorabunkoIndex.IdxSub[curr])
        except IndexError:
            return -1, None

    def subindex_records(self, idx):
        """ 副キー（２）
            登録されているレコード番号をイテレータで返す
        """
        if idx in AozorabunkoIndex.IdxSubdic:
           for i in AozorabunkoIndex.IdxSubdic[idx]:
               yield i

    def subindex_keys(self, idx):
        """ 副キー（３）
            登録済みキーをイテレータで返す
            事前に存在を確認すること
            例 self.subindex_keys( u'03あ' )
                03あ　で始まるキーを全て返す
            idx は unicode でなくてはならない。unicode(n,'UTF-8')
        """
        try:
            curr = bisect.bisect_left(AozorabunkoIndex.IdxSub,idx)
            while AozorabunkoIndex.IdxSub[curr][:len(idx)] == idx:
                yield AozorabunkoIndex.IdxSub[curr]
                curr += 1
        except IndexError:
            pass

    def subindex_regist(self, idx, rec):
        """ 副キーの登録
            実効速度を稼ぐためとりあえず辞書登録する
        """
        if not idx in AozorabunkoIndex.IdxSubdic:
            # 新規登録
            AozorabunkoIndex.IdxSubdic[idx] = [rec]
        else:
            # 重複登録
            AozorabunkoIndex.IdxSubdic[idx].append(rec)

    def subindex_restore(self):
        """ キーの順次検索が可能なようにリストに登録しなおす
        """
        for i in AozorabunkoIndex.IdxSubdic.iterkeys():
            AozorabunkoIndex.IdxSub.append(i)
        AozorabunkoIndex.IdxSub.sort()


class workslistUI(gtk.ScrolledWindow):
    """ 作品リストUI

        表示フィールド
        作品名 副題　著者名  文字遣い種別+NDC

        リストストア
        作品ID|作品名|作品名読み|副題|副題読み|文字違い種別,NDC|著者名|テキストファイルURL
        00     01     02         04   05       09+08            (14)   45


        データファイル１　作品一覧   （重複登録なし）
        作品ID|作品名|作品名読み|副題|副題読み|文字違い種別,NDC|人物ID|テキストファイルURL
        00     01     02         04   05       09+08            14     45

        データファイル２　著者一覧   （重複登録なし）
        人物ID(key)|姓|名|姓読み|名読み
        14          15 16 17     18

    """
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)

        # 作品リスト
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
                    (u'副題', 3, 175, gobject.TYPE_STRING),
                    (u'著者', 6, 70, gobject.TYPE_STRING),
                    (u'NDC分類', 4, 90, gobject.TYPE_STRING),
                    (u'仮名遣い', 5, 80, gobject.TYPE_STRING),
                    (u'DL済',8,20, gobject.TYPE_STRING)]:
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


class authorlistUI(gtk.ScrolledWindow):
    """ 著者リストUI
        氏名, よみがな, 人物ID
    """
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.tree_author = gtk.TreeView()

        self.tree_author.set_model(gtk.ListStore( gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING,
                                                    gobject.TYPE_STRING ))
        # 各項目ごとのレンダリング関数の設定
        self.rend_authorname = gtk.CellRendererText()
        self.rend_authorname.set_property('editable', False)

        self.col_authorname = gtk.TreeViewColumn(u'著者名',
                                          self.rend_authorname,
                                          text=0)
        #self.col_authorname.set_max_width(180)
        self.col_authorname.set_resizable(True)
        self.col_authorname.set_sort_column_id(0)

        self.tree_author.append_column(self.col_authorname)

        self.tree_author.set_rules_hint(True)
        self.tree_author.get_selection().set_mode(gtk.SELECTION_SINGLE)

        self.add(self.tree_author)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        #self.set_size_request(240,100)

        self.selectfile = u''

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
                self.selectfile = c.get_value(i, 2)
            f = True
        except IndexError:
            pass
        return f

    def get_value(self):
        """ 選択された人物IDを返す
        """
        return self.selectfile if self.get_selected_item() else None


class gojuonUI2(gtk.VBox):
    """ テキストエントリー付きの50音表
    """
    def __init__(self, x=2, y=1):
        gtk.VBox.__init__(self)

        self.tx = gtk.Entry()
        self.btn = gtk.ToggleButton()
        self.btn.connect('toggled', self.btn_toggled_cb)
        self.btn.set_mode(False)
        self.gojuon = gojuonUI(x,y)
        self.hbox = gtk.HBox()
        self.hbox.pack_start(self.tx)
        self.hbox.pack_start(self.btn)
        self.pack_start(self.hbox, expand=False)
        self.pack_end(self.gojuon)

        self.connect('button_press_event', self.button_press_event_cb)
        self.tx.connect('key_press_event', self.key_press_event_cb)

        self.clear()
        self.btn.toggled()

    def btn_toggled_cb(self, widget):
        """ 入力内容の適用先の切り替え
        """
        if widget.get_mode():
            self.btnbuffer_true = self.tx.get_text()
            widget.set_mode(False)
            widget.set_label(u'作品')
            self.tx.set_text(self.btnbuffer_false)
        else:
            self.btnbuffer_false = self.tx.get_text()
            widget.set_mode(True)
            widget.set_label(u'著者')
            self.tx.set_text(self.btnbuffer_true)

    def key_press_event_cb(self, widget, event):
        """ キー入力のトラップ
        """
        rv = False
        key = event.keyval
        if  key == 0xff0d:
            """ Enter
            """
            print self.tx.get_text()
            rv = True
        return rv

    def button_press_event_cb(self, widget, event):
        """
        """
        rv = False
        if event.button == 1:
            """ マウス左ボタンで1文字得る
            """
            k = self.gojuon.get_selectedletter()
            if k == u'消':
                self.tx.set_text(u'')
            elif k == u'戻':
                s = self.tx.get_text()
                self.tx.set_text(s[:-1])
            else:
                self.tx.set_text(self.tx.get_text()+k)
            # 直もイベントを上に送る
        return rv

    def clear(self):
        """ エントリーのクリア
        """
        self.btnbuffer_false = u''
        self.btnbuffer_true = u''
        self.tx.set_text(u'')

    def get_value(self):
        return (self.tx.get_text(), self.btn.get_label())


class gojuonUI(gtk.Table):
    """ 50音表
        用途：検索の際のインデックス指定等
    """
    sIdx = {
            u'平大':u'あいうえおかきくけこさしすせそたちつてとなにぬねの' + \
                    u'はひふへほまみむめもや　ゆ　よらりるれろわ　　をん' + \
                    u'゛゜　　戻' + \
                    u'消英小　片',

            u'片大':u'アイウエオカキクケコサシスセソタチツテトナニヌネノ' + \
                    u'ハヒフヘホマミムメモヤ　ユ　ヨラリルレロワ　　ヲン' + \
                    u'゛゜　　戻' + \
                    u'消英小平　',

            u'片小':u'ァィゥェォヵ　ㇰヶ　　ㇱㇲ　　　　ッ　ㇳ　　ㇴ　　' + \
                    u'ㇵㇶㇷㇸㇹ　　ㇺ　　ャ　ュ　ョㇻㇼㇽㇾㇿヮ　　　　' + \
                    u'　　　　戻' + \
                    u'消英大平　',

            u'平小':u'ぁぃぅぇぉゕ　　ゖ　　　　　　　　っ　　　　　　　' + \
                    u'　　　　　　　　　　ゃ　ゅ　ょ　　　　　ゎ　　　　' + \
                    u'　　　　戻' + \
                    u'消英大　片',

            u'英大':u'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹ' + \
                    u'Ｚ　　　　１２３４５６７８９０−＾＼＠［；：］，．' + \
                    u'／＼　　戻' + \
                    u'消　小平片',

            u'英小':u'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙ' + \
                    u'ｚ　　　　！”＃＄％＆’（）　＝〜｜‘｛＋＊｝＜＞' + \
                    u'？＿　　戻' + \
                    u'消　大平片' }

    def __init__(self, matx=5, maty=12):
        gtk.Table.__init__(self)
        self.resize(11, 5)
        self.evbox = []
        # グリッド整形
        if matx * maty != 60:
            matx, maty = (15, 4) if matx > maty else (5, 12)

        # マトリックスへイベントボックスをセット
        for y in xrange(maty):
            for x in xrange(matx):
                self.evbox.append(gtk.EventBox())
                self.evbox[-1].add(gtk.Label())
                self.evbox[-1].connect('button_press_event',
                                        self.button_press_event_cb)
                self.attach(self.evbox[-1], x, x+1, y, y+1)

        # マトリックス初期化
        self.set_matrix()
        self.selectletter = u''

    def button_press_event_cb(self, widget, event):
        """
        """
        rv = False
        if event.button == 1:
            """ マウス左ボタンで1文字得る
            """
            k = widget.child.get_text()
            if k in u'英小大平片':
                if k in u'英平片':
                    self.currmatrix = k + self.currmatrix[-1]
                else:
                    self.currmatrix = self.currmatrix[0] + k
                # マトリックス張替え
                self.set_matrix(self.currmatrix)
                self.selectletter = u''
                # イベントマスク
                rv = True
            else:
                self.selectletter = k
        return rv

    def set_matrix(self, key=u'平大'):
        """ 指定したマトリックスをセットする
        """
        self.currmatrix = key
        pos = 0
        for s in gojuonUI.sIdx[self.currmatrix]:
            self.evbox[pos].child.set_markup(
                (u'<b>%s</b>' if pos % 5 == 0 else u'%s' ) % s)
            pos += 1

    def get_selectedletter(self):
        """ 選択された文字を返す
        """
        return self.selectletter


class BunkoUI(gtk.Window, ReaderSetting):
    indexfileurl = u'http://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip'

    def __init__(self):
        gtk.Window.__init__(self)
        ReaderSetting.__init__(self)

        # インデックスファイル読み込み
        self.checkindexfile()
        self.db = AozorabunkoIndex( self.checkindexfile() )

        # 作品一覧
        self.sakuhin = workslistUI()
        self.sakuhin.child.connect('row_activated',
                                self.sakuhin_row_activated_treeview_cb)
        # NDC
        self.ndc = ndcUI()
        vhNDCsakuhin = gtk.VBox()
        vhNDCsakuhin.pack_start(self.ndc)
        vhNDCsakuhin.connect('button_press_event',
                                self.vhNDCsakuhin_button_press_event_cb)

        # 50音及び作者一覧
        self.tbl = gojuonUI2(2,1)
        self.author = authorlistUI()
        self.author.child.connect('row_activated',
                                self.author_row_activated_treeview_cb)
        vbGojuonauthor = gtk.HBox()
        vbGojuonauthor.pack_start(self.tbl)
        vbGojuonauthor.pack_start(self.author)
        vbGojuonauthor.connect('button_press_event',
                                self.vbGojuonauthor_button_press_event_cb)

        # 全体
        ntb = gtk.Notebook()
        ntb.append_page(vbGojuonauthor, gtk.Label(u'五十音別'))
        ntb.append_page(vhNDCsakuhin, gtk.Label(u'NDC'))

        btnIdxDL = gtk.Button(u'インデックスを新規ダウンロード')
        btnIdxDL.connect('clicked', self.btnIdxDL_clicked_cb)
        btnDL = gtk.Button(u'一括ダウンロード')
        btnDL.connect('clicked', self.btnDL_clicked_cb)
        btnClose = gtk.Button(stock=gtk.STOCK_CLOSE)
        btnClose.connect('clicked', self.btnClose_clicked_cb)
        btnOpen = gtk.Button(stock=gtk.STOCK_OPEN)
        btnOpen.connect('clicked', self.btnOpen_clicked_cb)

        btnbox = gtk.HButtonBox()
        btnbox.set_size_request(740,24)
        btnbox.set_layout(gtk.BUTTONBOX_EDGE)
        btnbox.pack_start(btnIdxDL)
        btnbox.pack_start(btnDL)
        btnbox.pack_start(btnOpen)
        btnbox.pack_end(btnClose)

        vh = gtk.VBox()
        vh.pack_start(self.sakuhin)
        vh.pack_start(ntb)
        vh.pack_end(btnbox, expand=False)

        self.add(vh)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title(u'インデックスによる検索')

        self.connect('delete_event', self.delete_event_cb )
        self.connect("key-press-event", self.key_press_event_cb )
        # 検索キー値
        self.curr_ndc = u''
        self.curr_yomi = u''
        self.curr_authorid = u''

        #選択されたテキスト
        self.selectfile = u''

    def btnDL_clicked_cb(self, widget):
        """ 一括ダウンロード
        """
        self.selected_value()

    def btnIdxDL_clicked_cb(self, widget):
        """ インデックスファイルの再ロード
        """
        self.checkindexfile(True)
        self.db.reloadfile()
        self.sakuhin.child.get_model().clear()
        self.tbl.clear()

    def btnOpen_clicked_cb(self, widget):
        self.selected_value()
        self.exitall()

    def btnClose_clicked_cb(self, widget):
        self.exitall()

    def sakuhin_row_activated_treeview_cb(self, path, view_column, column):
        self.selected_value()
        print self.get_filename()
        self.exitall()

    def set_sakuhinlist(self, k):
        """ 検索下請け
            インデックスに該当するレコードをUIに登録する
            ディレクトリにダウンロード済みファイルがあるかのチェックも
            ここで行う。
        """
        for i in self.db.subindex_records(k):
            n = self.db.dbSakuhin[i].split(u'|')
            s = self.db.dbAuthor[n[6]].split(u'|')
            if k[:2] == u'14' and self.curr_yomi != u'':
                """ 人物IDによる検索なので、作品よみがなをチェック
                """
                if self.curr_yomi != n[2][:len(self.curr_yomi)]:
                    continue
            elif k[:2] == u'03' and self.curr_authorid != u'':
                """ 作品よみがなによる検索なので、人物IDをチェック
                """
                if n[6] != self.curr_authorid[2:]:
                    continue
            self.sakuhin.child.get_model().append(
                    (n[0], n[1], n[2], n[3], n[4], n[5], s[0]+u' '+s[1], n[7],
                    u'●' if os.path.isfile(os.path.join(
                        self.get_value(u'aozoradir'),
                            os.path.basename(n[7])) ) else u''  ))

    def author_row_activated_treeview_cb(self, path, view_column, column):
        """ 著者一覧用コールバック（１）
            検索
        """
        self.author.get_selected_item()
        k = self.author.get_value()
        if k:
            k = u'14' + unicode(k, 'UTF-8')
            self.curr_authorid = k
            self.sakuhin.child.get_model().clear()
            self.set_sakuhinlist(k)

    def vbGojuonauthor_button_press_event_cb(self, widget, event):
        """ 50音表用コールバック（１）
            検索
        """
        rv = False
        if event.button == 1:
            v = self.tbl.get_value()
            k = unicode(v[0], 'UTF-8')
            if v[1] == u'著者':
                self.author.child.get_model().clear()
                if k == u'':
                    self.curr_authorid = k
                for i in self.db.author_keys(k):
                    n = i.split(u'|')
                    self.author.child.get_model().append((
                            n[3]+u' '+n[4], n[0], n[1] ))
            else:
                # 作品名よみがな先頭部分一致検索
                self.sakuhin.child.get_model().clear()
                self.curr_yomi = k
                for i in self.db.subindex_keys( u'03' + k ):
                    self.set_sakuhinlist(i)
            rv = True

        return rv

    def vhNDCsakuhin_button_press_event_cb(self, widget, event):
        """ NDC用コールバック（１）
            検索
        """
        rv = False
        if event.button == 1:
            self.sakuhin.child.get_model().clear()
            k = u'08NDC %s' % self.ndc.get_value()[2]
            self.set_sakuhinlist(k)
            # 児童書
            k = u'08NDC K%s' % self.ndc.get_value()[2]
            self.set_sakuhinlist(k)
            rv = True

        return rv

    def checkindexfile(self, ow=False):
        """ インデックスファイルのチェック
            存在しなければ新規ダウンロード
        """
        localfile = os.path.join(self.get_value(u'aozoradir'),
                                        os.path.basename(BunkoUI.indexfileurl))
        if ow:
            os.remove(localfile)
        if not os.path.isfile(localfile):
            if not self.download(BunkoUI.indexfileurl,localfile):
                return None

        a = zipfile.ZipFile( localfile, u'r' )
        a.extractall( self.get_value(u'aozoradir'))
        return os.path.join(self.get_value(u'aozoradir'),a.namelist()[0])

    def download(self, url, localfile=u'', ow=True):
        """ ダウンロード下請け
            ow : True で上書きダウンロード
        """
        rv = True
        if localfile == u'':
            localfile = os.path.join(self.get_value(u'aozoradir'),
                                                os.path.basename(url))
        if not ow and os.path.isfile(localfile):
            """ ファイルがあればダウンロードしない
            """
            pass
        else:
            try:
                urllib.urlretrieve(url, localfile)
            except IOError:
                # ダウンロードに失敗
                #logging.error( u'Download error : ' % url )
                rv = False
        return (rv, localfile)

    def selected_value(self):
        """ 選択されたテキストをダウンロードする
        """
        # この操作で返されるのは
        # c データモデルオブジェクト、ここではgtk.ListStore
        # d 選択された行
        (c,d) = self.sakuhin.child.get_selection().get_selected_rows()
        try:
            iters = [c.get_iter(p) for p in d]
            for i in iters:
                r = self.download(c.get_value(i, 7), ow=False)
                if r[0]:
                    a = zipfile.ZipFile(r[1], u'r' )
                    a.extractall(self.get_value(u'aozoradir'))
                    for b in a.namelist():
                        if os.path.basename(b)[-4:] == '.txt':
                            self.selectfile = os.path.join(
                                self.get_value(u'aozoradir'), b )
                            break
        except IndexError:
            pass

    def get_filename(self):
        return self.selectfile

    def key_press_event_cb( self, widget, event ):
        """ キー入力のトラップ
        """
        key = event.keyval
        if key == 0xff1b:
            # ESC
            self.exitall()
            self.selectfile = ''
        # デフォルトルーチンに繋ぐため False を返すこと
        return False

    def delete_event_cb(self, widget, event, data=None):
        self.exitall()

    def exitall(self):
        self.hide_all()
        gtk.main_quit()

    def run(self):
        self.show_all()
        gtk.main()


if __name__ == '__main__':
    a = BunkoUI()
    a.run()
