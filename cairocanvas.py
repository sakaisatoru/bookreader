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

from readersub_nogui import ReaderSetting, AozoraScale

import codecs
import os.path
import unicodedata
import math
from contextlib import contextmanager
from HTMLParser import HTMLParser
import re

import gtk
import cairo
import pango
import pangocairo

import gc

@contextmanager
def cairocontext(surface):
    try:
        context = cairo.Context(surface)
        # ~ context = surface.cairo_create()
        yield context
    finally:
        del context

@contextmanager
def pangocairocontext(cairoctx):
    try:
        pangoctx = pangocairo.CairoContext(cairoctx)
        yield pangoctx
    finally:
        del pangoctx

_LEFT,_RIGHT = (0,1)

"""
    行の構成
    縦書表示する文字の、右上の角がホームポジション (translate(x,y)の引数)
    cairocanvasは左上角が(0,0)

                    (self.xpos)
                        (self.xpos+self.__honbunxpos)
            +-----------+-----------+
     ル 傍 傍            本　　　　　　　 傍 傍 ル
     ビ 点 線            文            線 点 ビ
"""

class expango(HTMLParser, AozoraScale, ReaderSetting):
    def __init__(self, canvas, ypos):
        HTMLParser.__init__(self)
        AozoraScale.__init__(self)
        ReaderSetting.__init__(self)
        self.sf             = canvas
        self.oldwidth       = 0
        self.figstack       = []    # キャプション表示位置を保持する
        self.captionwidth   = 0
        self.captiondata    = u''
        self.tatenakadata   = u''   # 縦中横データ
        self.xpos_sideofset = 0     # sub, sup 時の相対位置
        self.__honbunxpos   = 0
        self.ypos2          = ypos
        self.rubilastYpos   = [0,0] # 直前に出現したルビの末端 left, right
        self.boutenofset    = [0,0] # 傍点出現位置の補正値 left, right
        self.tatenakayoko_rubi_ofset = 0 # 縦中横時のルビ位置の補正値

        self.forecolor = gtk.gdk.color_parse(self.get_value(u'fontcolor'))
        self.backcolor = gtk.gdk.color_parse(self.get_value(u'backcolor'))
        self.setfont(self.canvas_fontname, self.canvas_fontsize,
                                                    self.canvas_rubifontsize )

    def destroy(self):
        del self.tagstack
        del self.attrstack

    def settext(self, data, xpos):
        self.xpos           = xpos
        self.ypos           = self.ypos2
        self.rubilastYpos   = [0,0]  # 直前のルビの最末端
        self.tagstack       = []
        self.attrstack      = []
        self.inKeikakomigyou = False # 罫囲み（行中）のフラグ
        self.keisenxpos     = 0

        """ Pangoのバグに対する対策
            オリジナルのPangoがタグによる重力制御を振り切るケースが多々あるため、ここで
            文字種を判定し英文には横組タグ(aozora yokogumi)を付す。
        """
        sTmp                = []
        end                 = len(data)
        localtagstack       = []
        pos_start           = 0
        pos_end             = 0
        while pos_start < end:
            if data[pos_start:pos_start+2] == u'</':
                # 既存の閉じタグを検出
                if localtagstack and localtagstack[-1] == u'<aozora yokogumi2':
                    # このルーチンで挿入したタグがあれば先に閉じる
                    localtagstack.pop()
                    sTmp.append( u'</aozora>' )

                pos_end = data.find( u'>', pos_start)
                if pos_end != -1:
                    if localtagstack:
                        localtagstack.pop()
                    sTmp.append(data[pos_start:pos_end+1])
                    pos_start = pos_end + 1
                    continue

            elif data[pos_start] == u'<':
                # 既存のタグを検出
                pos_end = data.find( u'>', pos_start)
                if pos_end != -1:
                    if localtagstack and localtagstack[-1] == u'<aozora yokogumi2':
                        # このルーチンで挿入したタグがあれば先に閉じる
                        localtagstack.pop()
                        sTmp.append( u'</aozora>' )
                    pos_end += 1
                    localtagstack.append(data[pos_start:pos_end])
                    sTmp.append(data[pos_start:pos_end])
                    pos_start = pos_end
                    continue

            elif self.isYokoChar(data[pos_start]):
                # 横書き文字ならタグを挿入する
                # 但し
                #   既にyokogumiタグがある あるいは 縦中横のなかである
                #   caption の中である 割り注の中である
                #   なら見送る
                for s in localtagstack:
                    if s.find(u'yokogumi')      != -1 or \
                       s.find(u'tatenakayoko')  != -1 or \
                       s.find(u'caption')       != -1 or \
                       s.find(u'warichu')       != -1:
                        break
                else:
                    localtagstack.append( u'<aozora yokogumi2' )
                    sTmp.append( u'<aozora yokogumi="dmy">' )

            elif localtagstack and u'<aozora yokogumi2' in localtagstack:
                # 縦書き文字検出
                # このルーチンでの横組みが指定されていれば閉じる
                localtagstack.pop()
                sTmp.append( u'</aozora>' )

            sTmp.append(data[pos_start])
            pos_start += 1

        self.feed(u''.join(sTmp))
        self.close()

    def setfont(self, font, size, rubisize):
        """ フォント
        """
        self.font           = pango.FontDescription(u'%s %f' % (font,size))
        self.font_rubi      = pango.FontDescription(u'%s %f' % (font,rubisize))
        self.update_charwidth(self.font)

    def getforegroundcolour(self):
        return self.forecolor

    def getbackgroundcolour(self):
        return self.backcolor

    def isYokoChar(self, c):
        """ 横組みがデフォルトなキャラクタであれば True を返す
            ※手抜きしているので後日書き直し予定。
        """
        if c in self.charwidth_serif:
           # いわゆるASCII文字
           f = True
        elif c in u'”“’‘':
            # ワイドな引用符
            f = True
        elif c >= u'Ａ' and c <= u'Ｚ':
            f = False
        elif c >= u'ａ' and c <= u'ｚ':
            f = False
        else:
            f = False
            n = unicodedata.category(c)
            if n[0] == 'L':
                if n != 'Lo' and n != 'Lm':
                    f = True # リガチャ狙い
        return f

    def handle_entityref(self, name):
        """ &amp; 等があるとトラップされる。そのままだと & < > は表示できないので
            ここで改めて送出する。
        """
        self.handle_data(u'&%s;' % name)

    def handle_starttag(self, tag, attr):
        if tag == u'aozora':
            if attr[0][0].find(u'bousen') != -1 or attr[0][0].find(u'rubi') != -1:
                # 傍線及びルビの表示開始位置を保存
                attr.append((u'start',self.ypos))
        self.tagstack.append(tag)
        self.attrstack.append(attr)

    def handle_endtag(self, tag):
        if tag == "sup" or tag == "sub":
            # 左右小文字の表示位置を解除
            self.xpos_sideofset = 0

        # 実行時間を稼ぐためifを先行させる。andで連結しているので式の評価順序に注意
        if self.tagstack != [] and self.tagstack[-1] == tag:
            with cairocontext(self.sf) as ctx:
                ctx.set_source_rgb(self.forecolor.red_float,
                                    self.forecolor.green_float,
                                    self.forecolor.blue_float) # 描画色
                try:
                    if self.attrstack[-1][0][0].find(u'rubi') != -1:
                        """ ルビ・左ルビ
                        """
                        sideband = _RIGHT if self.attrstack[-1][0][0] == u'rubi' else _LEFT
                        # ママ表示　ルビにママをつける場合は２行表示とする
                        rubipos = self.attrstack[-1][0][1].rfind(u'〔ルビママ〕')
                        if rubipos == -1:
                            rubipos = self.attrstack[-1][0][1].rfind(u'〔ママ〕')
                        if rubipos > 0:
                            if rubipos <= len(self.attrstack[-1][0][1])/2.:
                                # ルビが短い
                                rubitmp = u'%s\n%s' % (self.attrstack[-1][0][1][rubipos:],
                                    self.attrstack[-1][0][1][:rubipos].center(len(self.attrstack[-1][0][1][rubipos:])*2))
                            else:
                                rubitmp = u'%s\n%s' % (self.attrstack[-1][0][1][rubipos:].center(len(self.attrstack[-1][0][1][:rubipos])*2),
                                    self.attrstack[-1][0][1][:rubipos])
                            rubitmp = rubitmp.strip(u'\n') # １行しかない場合は改行を外す
                        else:
                            rubitmp = self.attrstack[-1][0][1]

                        with pangocairocontext(ctx) as pangoctx:
                            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                            layout = pangoctx.create_layout()
                            pc = layout.get_context()       # Pango を得る
                            pc.set_base_gravity('east')     # markup 前に実行
                            pc.set_gravity_hint('natural')   # markup 前に実行
                            layout.set_font_description(self.font_rubi)

                            layout.set_markup(rubitmp)
                            rubilength,rubispan = layout.get_pixel_size()
                            length = self.ypos - self.attrstack[-1][2][1]
                            # 表示位置 垂直方向のセンタリング
                            # 縦中横の時(length==0)はフォント１文字分の高さを仮定
                            y = self.attrstack[-1][2][1] + int(((self.fontheight if length<1. else length)-rubilength) // 2.)
                            if y < 0:
                                y = 0
                            if y < self.rubilastYpos[sideband]:
                                # ルビが連なる場合、直前のルビとの干渉を回避する
                                y = self.rubilastYpos[sideband]

                            pangoctx.translate(self.xpos + [-1,rubispan][sideband] + \
                                [-1,1][sideband] * (self.__honbunxpos * self.canvas_rubioffset + self.tatenakayoko_rubi_ofset) + \
                                                self.boutenofset[sideband], y)
                            pangoctx.rotate(1.57075)
                            pangoctx.update_layout(layout)
                            pangoctx.show_layout(layout)
                            self.rubilastYpos[sideband] = y + rubilength  # ルビの最末端を保存
                            del pc
                            del layout
                            # 補正値は使い捨て
                            self.boutenofset[sideband] = 0
                            self.tatenakayoko_rubi_ofset = 0

                    elif self.attrstack[-1][0][0] == u'keikakomigyou':
                        """ 罫囲み（行中）の閉じ罫線（下側罫線）
                        """
                        if self.attrstack[-1][0][1] in [u'3', u'0']:
                            ctx.set_antialias(cairo.ANTIALIAS_NONE)
                            ctx.set_line_width(1)
                            # 下
                            ctx.move_to(self.xpos - self.keisenxpos, self.ypos)
                            ctx.rel_line_to(self.keisenxpos*2, 0)
                            ctx.stroke()
                            self.inKeikakomigyou = False

                    elif self.attrstack[-1][0][0] == u'caption':
                        """ 画像が表示されていればキャプションを横書きで表示する。
                        """
                        if self.figstack:
                            (self.xpos, self.ypos, self.captionwidth) = self.figstack.pop()
                            with pangocairocontext(ctx) as pangoctx:
                                ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                                layout = pangoctx.create_layout()
                                layout.set_font_description(self.font)
                                pc = layout.get_context() # Pango を得る
                                pc.set_base_gravity('south')
                                pc.set_gravity_hint('natural')
                                layout.set_markup(self.captiondata.replace('\a','\n'))
                                span, length = layout.get_pixel_size()
                                pangoctx.translate(
                                    self.xpos + max(0, (self.captionwidth-span)/2),
                                    self.ypos )
                                pangoctx.rotate(0)
                                pangoctx.update_layout(layout)
                                pangoctx.show_layout(layout)
                                del pc
                            self.captiondata = u''

                    elif self.attrstack[-1][0][0] == u'tatenakayoko':
                        """ 縦中横
                        """
                        with pangocairocontext(ctx) as pangoctx:
                            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                            layout = pangoctx.create_layout()
                            layout.set_font_description(self.font)
                            # 縦中横 直前の表示位置を元にセンタリングする
                            pc = layout.get_context() # Pango を得る
                            # 横組文字の高さが幅より大きいとレイアウトが崩れるので、
                            # 高さ（１文字の送り）を予め求める。
                            pc.set_base_gravity('east')
                            pc.set_gravity_hint('strong')
                            layout.set_markup(u'国')
                            length,y0 = layout.get_pixel_size()
                            #length += 1
                            pc.set_base_gravity('south')
                            pc.set_gravity_hint('natural')
                            layout.set_markup(self.tatenakadata)
                            y, length0 = layout.get_pixel_size() #x,yを入れ替えることに注意
                            # ルビ表示位置の補正量を求める
                            # 但し、現状ではルビの表示処理が先行するので意味がない。
                            #self.tatenakayoko_rubi_ofset = int(math.ceil(y/2.)) - self.__honbunxpos
                            #if self.tatenakayoko_rubi_ofset < 0:
                            #    self.tatenakayoko_rubi_ofset = 0
                            pangoctx.translate(self.xpos - int(math.ceil(y/2.)) + self.xpos_sideofset,
                                        self.ypos - int(round((length0-length)/2.-0.5)))
                            pangoctx.update_layout(layout)
                            pangoctx.show_layout(layout)
                            del pc
                            self.tatenakadata = u''
                            self.ypos += length

                    elif self.attrstack[-1][0][0].find(u'bousen') != -1:
                        """ 傍線各種
                        """
                        ltmp = self.ypos - self.attrstack[-1][1][1]
                        xofset = self.__honbunxpos * ( 1 if self.attrstack[-1][0][0] == u'bousen' else -1 )
                        ctx.set_antialias(cairo.ANTIALIAS_NONE)
                        ctx.new_path()
                        ctx.set_line_width(1)
                        if self.attrstack[-1][0][1] == u'破線':
                            ctx.set_dash((3.5,3.5,3.5,3.5))
                        elif self.attrstack[-1][0][1] == u'鎖線':
                            ctx.set_dash((1.5,1.5,1.5,1.5))
                        elif self.attrstack[-1][0][1] == u'二重傍線':
                            ctx.move_to(self.xpos + xofset +2, self.attrstack[-1][1][1]) # １本目
                            ctx.rel_line_to(0, ltmp)
                            ctx.stroke()

                        if self.attrstack[-1][0][1] == u'波線':
                            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                            spn = 5 # 周期
                            vx = 3 # 振幅
                            tmpx = self.xpos + xofset
                            for y in xrange(0, int(ltmp), spn):
                                tmpy = self.attrstack[-1][1][1] + y
                                ctx.move_to(tmpx, tmpy)
                                ctx.curve_to(tmpx,tmpy, tmpx+vx,tmpy+spn/2, tmpx,tmpy+spn)
                                vx *= -1
                        else:
                            # 波線以外を描画
                            ctx.move_to(self.xpos + xofset, self.attrstack[-1][1][1])
                            ctx.rel_line_to(0, ltmp)
                        ctx.stroke()

                except IndexError:
                    pass
            self.tagstack.pop()
            self.attrstack.pop()

    def handle_data(self, data):
        """ 挟まれたテキスト部分が得られる
        """

        def __removetag_warichu(sTmp):
            """ 割り注下請（暫定）
                フォーマッタがごみを混ぜるのでそれを取り除くフィルタ
                <sub></sub><sup></sup>以外のタグを抜去する。
            """

            def ___searchtag(_s, _pos=0):
                """ タグを見つけてその最初と終わりを返す
                    見つからない場合は -1, -1
                    タグが閉じていない場合は start, -1
                    ネスティングに対応する
                """
                _end = -1
                _start = _s.find(u'<',_pos)
                while _start != -1:
                    _pos = _s.find(u'<',_start+1)
                    if _pos == -1:
                        _end = _s.find(u'>',_start+1)
                        if _end != -1:
                            _end += 1
                        break
                    else:
                        _start = _pos
                return _start, _end


            __s = []
            __c = 0
            __f = False
            # <>
            __s0, __e0 = ___searchtag(sTmp)
            while __s0 != -1:
                __s.append(sTmp[:__s0])
                if sTmp[__s0:__e0] in [u'<sup>',u'</sup>',u'<sub>',u'</sub>']:
                    #__s.append(sTmp[:__s0])
                    __s.append(sTmp[__s0:__e0])
                    __c += len(sTmp[__s0:__e0])
                sTmp = sTmp[__e0:]
                __s0, __e0 = ___searchtag(sTmp)
            __s.append(sTmp)
            sTmp = u''.join(__s)

            """
            if sTmp.find(u'［＃改行］') != -1:
                # 改行されているので、長い方の文字数を返す
                __l = 0
                for __s0 in sTmp.split(u'［＃改行］'):
                    if len(__s0) > __l:
                        __l = len(self.__removetag(__s0))
            else:
                __l = int(math.ceil((len(sTmp) - __c)/2.))
            """
            return sTmp#, __l






        def __bouten_common(key, sideband):
            """ 傍点表示
            """
            def ___cairo_bouten():
                # 傍点・白ゴマ傍点
                ctx00.move_to(tmpx, tmpy)
                ctx00.curve_to(tmpx+d, tmpy,  tmpx+d, tmpy+d,  tmpx+d, tmpy+d)
                ctx00.curve_to(tmpx+d, tmpy+d,
                                tmpx+r+r/2, tmpy+d+r/2,  tmpx+r, tmpy+d)
                ctx00.curve_to(tmpx+r, tmpy+r, tmpx, tmpy, tmpx, tmpy)

            def ___cairo_batsu():
                # ばつ傍点
                ctx00.move_to(tmpx, tmpy)
                ctx00.rel_line_to(d, d)
                ctx00.move_to(tmpx+d, tmpy)
                ctx00.rel_line_to(-d, d)

            def ___cairo_maru():
                # 白丸・黒丸（輪郭）・二重丸（外円）・蛇の目（外円）傍点
                ctx00.new_sub_path()
                ctx00.arc(tmpx+r,tmpy+r,r, 0, 2*3.1415)

            def ___cairo_maru2():
                # 二重丸（内円）・蛇の目（内円）傍点
                ___cairo_maru()
                ctx00.stroke() # ここで外円を描く
                ctx00.arc(tmpx+r,tmpy+r,r/2., 0, 2*3.1415)
                if dicArg[key] == u'蛇の目傍点':
                    ctx00.fill()
                else:
                    ctx00.stroke()

            def ___cairo_sankaku():
                # 白三角・黒三角傍点
                xx = r * 0.9226 # 底辺 外接円の面積=3辺の積/(4*半径)より
                yy = r * 0.7989 # 高さ
                ctx00.move_to(tmpx+r, tmpy+r - yy)
                ctx00.rel_line_to(xx,2*yy)
                ctx00.rel_line_to(-2*xx,0)
                ctx00.rel_line_to(xx,-2*yy)

            dicfunc = {
                u'ばつ傍点':___cairo_batsu,
                u'白ゴマ傍点':___cairo_bouten,  u'傍点':___cairo_bouten,
                u'白丸傍点':___cairo_maru,      u'丸傍点':___cairo_maru,
                u'二重丸傍点':___cairo_maru2,   u'蛇の目傍点':___cairo_maru2,
                u'白三角傍点':___cairo_sankaku, u'黒三角傍点':___cairo_sankaku
                }

            with cairocontext(self.sf) as ctx00:
                step = round(length / float(len(data))) # 送り量
                d = self.fontwidth /4.          # 表示幅、例えば白丸の直径
                r = d / 2.                      # 表示幅の半分、例えば白丸の半径
                # 表示領域左上座標
                tmpx = self.xpos + \
                        self.__honbunxpos * self.canvas_rubioffset * (-1 if sideband == _LEFT else 1 )+ \
                        r * (-2 if sideband == _LEFT else 1)
                tmpy = self.ypos + d + r
                ctx00.new_path()
                ctx00.set_antialias(cairo.ANTIALIAS_DEFAULT) # cairo.ANTIALIAS_NONE
                ctx00.set_source_rgb(self.forecolor.red_float,
                                            self.forecolor.green_float,
                                            self.forecolor.blue_float)
                ctx00.set_line_width(d/5.7)     # フォントサイズに連動する
                # 傍点を描く。修飾対象文字が縦中横で修飾される場合は１文字扱い。
                for s in data if not u'tatenakayoko' in dicArg else u' ':
                    dicfunc[dicArg[key]]()      # 引数は大域渡し
                    tmpy += step
                if dicArg[key] in [u'傍点', u'丸傍点', u'蛇の目傍点', u'黒三角傍点']:
                    ctx00.fill()
                else:
                    ctx00.stroke()
            self.boutenofset[sideband] = -d if sideband == _LEFT else (d+r)


        """------------------------------------------------------------------
        """
        # 初期化
        self.boutenofset    = [0, 0]    # 傍点描画後のルビ位置補正値
        rubispan            = 0
        dicArg              = {}
        sTmp                = data
        fontsizename        = u''
        length              = 0.

        try:
            # タグスタックに積まれている書式指定を全て付す
            # TOS（即ちdataの直前に出現したタグ)から見ていくことに注意。
            # Pangoでうまく処理できないタグはここで代替処理する
            pos = -1
            while True:
                s = self.tagstack[pos]
                if s == u'aozora':
                    # 拡張したタグは必ず属性をとる
                    for i in self.attrstack[pos]:
                        dicArg[i[0]] = i[1]
                    pos -= 1
                    if u'tatenakayoko' in dicArg:
                        # 縦中横の中に含まれるsub/supで指定された補正値を解除
                        self.xpos_sideofset = 0
                    continue
                elif s == u'sup':
                    self.xpos_sideofset = int(math.ceil(self.fontwidth / 3.))
                    sTest = (u'<sup>', sTmp, u'</sup>')
                elif s == u'sub':
                    self.xpos_sideofset = -int(math.ceil(self.fontwidth / 3.))
                    sTest = (u'<sub>', sTmp, u'</sub>')
                else:
                    # 引数復元
                    sTest = []
                    sTest.append(u'<%s' % s)
                    if self.attrstack[pos] != []:
                        for i in self.attrstack[pos]:
                            sTest.append(u' %s="%s"' % (i[0],i[1]))
                            # 変更されたフォントサイズを得る
                            if s == u'span':
                                if i[0] == u'size':
                                    fontsizename = i[1]

                        sTest.append(u'>')
                        sTest.append(sTmp)
                        sTest.append(u'</%s>' % self.tagstack[pos])
                sTmp = u''.join(sTest)
                pos -= 1
        except IndexError:
            pass

        # 表示
        with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
            ctx.set_source_rgb(self.forecolor.red_float,
                                            self.forecolor.green_float,
                                            self.forecolor.blue_float) # 描画色
            layout = pangoctx.create_layout()
            layout.set_font_description(self.font)

            if not dicArg:
                # 本文表示本体
                sTmp = sTmp.replace('\a','\n') # 改行コードの復元
                pc = layout.get_context() # Pango を得る
                # 正しいlengthを得るため、予め文字の向きを決める
                pc.set_base_gravity('east')
                pc.set_gravity_hint('strong')
                layout.set_markup(sTmp)
                length, span = layout.get_pixel_size()
                self.__honbunxpos = int(math.ceil(span/2.))
                # 描画位置　左右小文字はタグで分断されているので手動で表示位置を補正する。
                pangoctx.translate(self.xpos + self.xpos_sideofset + self.__honbunxpos,
                                                    self.ypos)
                pangoctx.rotate(1.57075) # 90度右回転、即ち左->右を上->下へ
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc
                del sTmp
                del layout
            else:
                if u'img' in dicArg:
                    # 段落埋め込みの画像
                    sTmp = sTmp.replace(u'＃',u'　')
                    layout.set_markup(sTmp)
                    # 描画位置の調整
                    length, y = layout.get_pixel_size() #幅と高さを返す(実際のピクセルサイズ)
                    imgtmpx = int(math.ceil(float(dicArg[u'width'])/2.))
                    imgtmpy = int(math.ceil((length - float(dicArg[u'height']))/2.))
                    pangoctx.translate(self.xpos - imgtmpx, self.ypos+imgtmpy)
                    pangoctx.rotate(0)
                    img = cairo.ImageSurface.create_from_png(
                            os.path.join(self.aozoratextdir,dicArg[u'img']) )
                    ctx.set_source_surface(img,0,0) # 直前のtranslateが有効
                    ctx.paint()
                    del img

                elif u'img2' in dicArg:
                    # 画像
                    pangoctx.translate(
                        self.xpos,
                        self.ypos + self.fontheight/2)
                    pangoctx.rotate(0)
                    img = cairo.ImageSurface.create_from_png(
                                os.path.join(self.aozoratextdir,dicArg[u'img2']))

                    ctx.scale(float(dicArg[u'rasio']),float(dicArg[u'rasio']))
                    # scaleで画像を縮小すると座標系全てが影響を受ける為、translate で指定したものを活かす
                    sp = cairo.SurfacePattern(self.sf)
                    sp.set_filter(cairo.FILTER_BEST) #FILTER_GAUSSIAN )#FILTER_NEAREST)
                    ctx.set_source_surface(img,0,0)
                    ctx.paint()
                    length = int(dicArg[u'height'])
                    # キャプション描画位置を退避
                    self.figstack.append((self.xpos,
                        self.ypos + self.fontheight + length,
                        int(dicArg[u'width'])) )
                    del img

                elif u'img3' in dicArg:
                    # 回りこみを伴う画像
                    xposadj = math.ceil(int(dicArg[u'width'])/float(self.canvas_linewidth))
                    xposadj = (xposadj*self.canvas_linewidth - int(dicArg[u'width']))/2
                    xposadj = self.xpos + self.canvas_linewidth/2 - int(dicArg[u'width']) - xposadj
                    pangoctx.translate(
                        xposadj,
                        self.ypos + self.fontheight/2)
                    pangoctx.rotate(0)
                    img = cairo.ImageSurface.create_from_png(
                                os.path.join(self.aozoratextdir,dicArg[u'img3']))

                    ctx.scale(float(dicArg[u'rasio']),float(dicArg[u'rasio']))
                    # scaleで画像を縮小すると座標系全てが影響を受ける為、translate で指定したものを活かす
                    sp = cairo.SurfacePattern(self.sf)
                    sp.set_filter(cairo.FILTER_BEST) #FILTER_GAUSSIAN )#FILTER_NEAREST)
                    ctx.set_source_surface(img,0,0)
                    ctx.paint()
                    length = int(dicArg[u'height'])
                    # キャプション描画位置を退避 ただし、キャプションが続かない場合、スタックに取り残される。
                    self.figstack.append( (
                        xposadj,
                        self.ypos + self.fontheight + length,
                        int(dicArg[u'width']) ) )
                    del img

                elif u'caption' in dicArg:
                    # 画像が表示されていればキャプションを連結する。
                    if self.figstack:
                        self.captiondata += sTmp

                elif u'warichu' in dicArg:
                    # 割り注
                    layout.set_markup(data)
                    length,y = layout.get_pixel_size()
                    #sTmp = dicArg[u'warichu'].split(u'［＃改行］')
                    sTmp = __removetag_warichu(dicArg[u'warichu']).split(u'［＃改行］')
                    if len(sTmp) < 2:
                        try:
                            l = int(dicArg[u'height'])
                            sTmp = [ dicArg[u'warichu'][:l],dicArg[u'warichu'][l:] ]
                        except KeyError:
                            print "割り注デバッグ ",sTmp[0]
                    sTmp.insert(1,u'\n')
                    pc = layout.get_context()
                    pc.set_base_gravity('east')
                    pc.set_gravity_hint('natural')
                    layout.set_markup(u'<span size="x-small">%s</span>' % ''.join(sTmp))
                    x0,y = layout.get_pixel_size()
                    pangoctx.translate(self.xpos + y//2,
                                    self.ypos + int(round((length-x0)/2.)))
                    pangoctx.rotate(1.57075)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc

                elif u'tatenakayoko' in dicArg:
                    # 縦中横はタグが閉じた時点で描画する
                    self.tatenakadata += sTmp
                    length = 0.

                else:
                    # 本文表示本体 送り量や書き出し位置の調整タグの処理を含む。
                    # ※少しでも処理速度を稼ぐため上にも似たルーチンがあります
                    sTmp = sTmp.replace('\a','\n') # 改行コードの復元
                    if u'mado' in dicArg:
                        # 窓見出し
                        sTmp = u'<span font_desc="%s" size="small">%s</span>' % (
                                    dicArg[u'font_desc'], sTmp )
                    pc = layout.get_context() # Pango を得る
                    # 正しいlengthを得るため、予め文字の向きを決める
                    if u'yokogumi' in dicArg or u'yokogumi2' in dicArg:
                        pc.set_base_gravity('south')
                        pc.set_gravity_hint('natural')
                    else:
                        pc.set_base_gravity('east')
                        pc.set_gravity_hint('strong')
                    layout.set_markup(sTmp)
                    length, span = layout.get_pixel_size()
                    self.__honbunxpos = int(math.ceil(span/2.))
                    if u'half' in dicArg:
                        # 連続して出現すする括弧等の送り量を調整する
                        honbunokuri = float(dicArg['half'])
                        if honbunokuri > 0:
                            length *= honbunokuri
                        else:
                            self.ypos += length * honbunokuri
                    if u'ofset' in dicArg:
                        # 文字の書き出し位置をずらす
                        self.ypos += float(dicArg['ofset'])
                    if u'adj' in dicArg:
                        # 文字の送り量を増減する
                        length += float(dicArg['adj'])

                    if u'dash' in dicArg:
                        # ダッシュ
                        # フォントを使わずcairoで描画する
                        ctx.new_path()
                        ctx.set_line_width(1)
                        ctx.move_to(self.xpos, self.ypos)
                        ctx.rel_line_to(0, length)
                        ctx.close_path()
                        ctx.stroke()

                    else:
                        if u'mado' in dicArg:
                            # 窓見出しの描画位置の調整(３行か２行取りになることが前提）
                            pangoctx.translate(
                                self.xpos - self.canvas_linewidth // (4-int(dicArg['lines'])) + span//2,
                                self.ypos + self.fontheight//2)  # 描画位置
                        else:
                            # 描画位置　左右小文字はタグで分断されているので手動で表示位置を補正する。
                            pangoctx.translate(self.xpos + self.xpos_sideofset + self.__honbunxpos,
                                                    self.ypos )
                        pangoctx.rotate(1.57075) # 90度右回転、即ち左->右を上->下へ
                        pangoctx.update_layout(layout)
                        pangoctx.show_layout(layout)
                    del pc

                del sTmp
                del layout

                if u'keikakomigyou' in dicArg:
                    # 罫囲み（行中における）
                    # １行中に他のタグが出現すると、その都度上側罫線を描いて
                    # しまうのでフラグで回避する
                    # 下側罫線はタグの終端検出時に描画する
                    with cairocontext(self.sf) as ctx00:
                        ctx00.set_antialias(cairo.ANTIALIAS_NONE)
                        ctx00.set_source_rgb(self.forecolor.red_float,
                                            self.forecolor.green_float,
                                            self.forecolor.blue_float)
                        ctx00.set_line_width(1)
                        self.keisenxpos = self.__honbunxpos
                        # 右
                        ctx00.move_to(self.xpos + self.__honbunxpos, self.ypos)
                        ctx00.rel_line_to(0, length)
                        # 左
                        ctx00.move_to(self.xpos - self.__honbunxpos, self.ypos)
                        ctx00.rel_line_to(0, length)
                        if not self.inKeikakomigyou and dicArg[u'keikakomigyou'] in [u'1', u'0']:
                            # 上
                            ctx00.move_to(self.xpos - self.keisenxpos, self.ypos)
                            ctx00.rel_line_to(self.keisenxpos * 2, 0)
                            self.inKeikakomigyou = True
                        ctx00.stroke()

                if u'bouten' in dicArg:
                    # 傍点
                    __bouten_common(u'bouten', _RIGHT)
                if u'leftbouten' in dicArg:
                    # 左傍点
                    __bouten_common(u'leftbouten', _LEFT)

        # 次の呼び出しでの表示位置
        self.ypos += length


class CairoCanvas(ReaderSetting):
    """ cairo / pangocairo を使って文面を縦書きする
    """
    reKeikakomi = re.compile(ur'<aozora keikakomi="(?P<name>.+?)" ofset="(?P<ofset>\d+?)" length="(?P<length>\d+?)"></aozora>')
    def __init__(self, gdkwin=None):
        ReaderSetting.__init__(self)
        self.gdkwin = gdkwin

    def writepage(self, pageposition, buffname=u'', currentpage=0, maxpage=0, title=u''):
        """ 指定したページを描画する
            pageposition : 表示ページのフォーマット済ファイル上での絶対位置
        """

        def __kakomi_sub(mx, oy, wt, mode=0):
            """ 囲み罫線下請け
                mode 罫線の描画位置を指定
                    bit 0  : 右辺
                    bit 1  : 上下辺
                    bit 2  : 左辺
                mode 0..無し  1..右辺       2..上下辺      3..右辺+上下辺
                　　　4..左辺  5..左辺+右辺   6..左辺+上下辺  7..全部
                使うのは2,3,6,7のみ
            """
            if not mode:
                return
            oy = oy * self.canvas_fontheight
            mx -= oy
            mx += self.canvas_fontheight + min(self.canvas_fontheight,self.canvas_topmargin//2)
            oy += self.canvas_topmargin - min(self.canvas_fontheight,self.canvas_topmargin//2)
            with cairocontext(self.sf) as ctx:
                ctx.set_antialias(cairo.ANTIALIAS_NONE)
                ctx.set_source_rgb(self.forecolor.red_float,
                                    self.forecolor.green_float,
                                    self.forecolor.blue_float) # 描画色
                ctx.new_path()
                ctx.set_line_width(1)

                if mode & 1:
                    # 右辺
                    ctx.move_to( xpos + wt, oy )
                    ctx.rel_line_to(0, mx)
                    ctx.stroke()
                if mode & 2:
                    # 上下辺
                    ctx.move_to( xpos, oy )
                    ctx.rel_line_to(wt, 0)
                    ctx.stroke()
                    ctx.move_to( xpos, oy + mx )
                    ctx.rel_line_to(wt, 0)
                    ctx.stroke()
                if mode & 4:
                    # 左辺
                    ctx.move_to( xpos, oy )
                    ctx.rel_line_to(0, mx)
                    ctx.stroke()

        if not buffname:
            buffname = self.destfile

        keimode = 0             # 罫囲みモード
        keiheight = 0           # 囲み内に出現する文字列の最大長
        offset_y = 0            # 文字列の書き出し位置
        tmpwidth = 0
        tmpheight = 0

        xpos = self.canvas_width - self.canvas_rightmargin - int(math.ceil(self.canvas_linewidth/2.))
        KeikakomiXendpos = xpos

        # キャンバスの確保
        # ~ if self.gdkwin != None:
            # ~ self.sf = self.gdkwin
        # ~ else:
        self.sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        self.canvas_width, self.canvas_height)

        #self.sf = cairo.PDFSurface('tmp.pdf',
        #                self.canvas_width*1.0, self.canvas_height*1.0)

        # 文字列表示クラス
        self.drawstring = expango(self.sf, self.canvas_topmargin)

        # 描画色の準備
        self.forecolor = self.drawstring.getforegroundcolour()
        # 画面クリア
        with cairocontext(self.sf) as ctx:
            ctx.rectangle(0, 0, self.canvas_width, self.canvas_height)
            self.backcolor = self.drawstring.getbackgroundcolour()
            ctx.set_source_rgb(self.backcolor.red_float,
                                self.backcolor.green_float,
                                self.backcolor.blue_float)
            ctx.fill()

        # 行末揃え確認用
        """
        with cairocontext(self.sf) as ctx:
            ctx.set_antialias(cairo.ANTIALIAS_NONE)
            ctx.set_source_rgb(self.forecolor.red_float,
                                self.forecolor.green_float,
                                self.forecolor.blue_float) # 描画色
            ctx.new_path()
            ctx.set_line_width(1)
            ctx.move_to(0,self.canvas_topmargin)
            ctx.rel_line_to(self.canvas_width,0)
            ctx.stroke()
            ctx.move_to(0,self.canvas_height - self.canvas_bottommargin)
            ctx.rel_line_to(self.canvas_width,0)
            ctx.stroke()


            ctx.move_to(0,
                    self.canvas_topmargin + self.chars * self.canvas_fontheight)
            ctx.rel_line_to(self.canvas_width,0)
            ctx.rel_line_to(0,-self.canvas_fontheight)
            ctx.rel_line_to(-self.canvas_width,0)
            ctx.close_path()
            ctx.stroke()
        #"""

        with codecs.open(buffname, 'r', 'UTF-8') as f0:
            f0.seek(pageposition)
            i = self.pagelines #+ 1
            while i:
                s0 = f0.readline().rstrip('\n')

                reTmp = self.reKeikakomi.search(s0)
                if reTmp and reTmp.group(u'name') == u'start':
                    s0 = s0[:reTmp.start()] + s0[reTmp.end():]
                    KeikakomiXendpos = xpos
                    keimode = 1 # 右辺

                if s0:
                    self.drawstring.settext(s0, xpos)

                reTmp = self.reKeikakomi.search(s0)
                if reTmp and reTmp.group(u'name') == u'cont':
                    # 罫囲み中
                    s0 = s0[:reTmp.start()] + s0[reTmp.end():]
                    __kakomi_sub(int(reTmp.group(u'length')),
                                    int(reTmp.group(u'ofset')),
                                        KeikakomiXendpos - xpos, keimode|2)
                    KeikakomiXendpos = xpos

                reTmp = self.reKeikakomi.search(s0)
                if reTmp and reTmp.group(u'name') == u'end':
                    # 罫囲み終わり
                    s0 = s0[:reTmp.start()] + s0[reTmp.end():]
                    __kakomi_sub(int(reTmp.group(u'length')),
                                    int(reTmp.group(u'ofset')),
                                        KeikakomiXendpos - xpos, keimode|6)

                if s0.find( u'<aozora newpage="dmy">' ) != -1:
                    break

                if s0:
                    # 行末が CR の場合は改行しないで終わる
                    if s0[-1] != '\r':
                        xpos -= self.canvas_linewidth
                        i -= 1
                else:
                    # 文字列が空なら改行のみで終わる
                    xpos -= self.canvas_linewidth
                    i -= 1



        # ノンブル(ページ番号)
        if currentpage:
            with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                ctx.set_source_rgb(self.forecolor.red_float,
                                    self.forecolor.green_float,
                                    self.forecolor.blue_float)
                layout = pangoctx.create_layout()
                layout.set_font_description(self.drawstring.font)
                layout.set_markup( u'<span size="x-small">%d (全%d頁)</span>' % (currentpage, maxpage))
                wx,wy = layout.get_pixel_size() # 左下時必要
                pangoctx.translate(int(self.get_value('leftmargin')),
                                    self.canvas_height - wy -4) # 左下時のY位置
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del layout

            # 柱（テキスト名）
            if title:
                with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                    ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                    ctx.set_source_rgb(self.forecolor.red_float,
                                        self.forecolor.green_float,
                                        self.forecolor.blue_float)
                    layout = pangoctx.create_layout()
                    layout.set_font_description(self.drawstring.font)
                    layout.set_markup( u'<span size="x-small">%s</span>' % title.strip(u' ').strip(u'　'))
                    pangoctx.translate(int(self.get_value('leftmargin')), 4) # 表示位置 (左上)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del layout

        self.sf.write_to_png(os.path.join(self.get_value(u'workingdir'),
                                    'thisistest.png'))
        # ~ self.sf.show()
        self.sf.finish()
        del self.drawstring
        del self.sf




