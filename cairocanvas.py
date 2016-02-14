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

import cairo
import pango
import pangocairo


@contextmanager
def cairocontext(surface):
    try:
        context = cairo.Context(surface)
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

class expango(HTMLParser, AozoraScale, ReaderSetting):
    """ 追加されたタグ
        aozora  tatenakayoko
                img
                img2
                warichu
                caption     # 廃止
                rubi
                bousen
                leftrubi
                yokogumi

        拡張されたタグ
        pango   sup
                sub

    """
    # 送り調整を要する文字
    kakko = u',)]｝、）］｝〕〉》」』】〙〗〟’”｠»・。、．，([{（［｛〔〈《「『【〘〖〝‘“｟«'

    def __init__(self, canvas):
        HTMLParser.__init__(self)
        AozoraScale.__init__(self)
        ReaderSetting.__init__(self)
        self.sf = canvas
        self.oldwidth = 0
        self.rubilastYpos = 0       # 直前のルビの最末端
        self.rubilastXofset = 0     # 直前のルビが左右いずれかを保持
        self.figstack = []          # キャプション表示位置を保持する

    def destroy(self):
        del self.tagstack
        del self.attrstack

    def settext(self, data, xpos, ypos):
        self.xpos = xpos
        self.ypos = ypos
        self.rubilastYpos = 0       # 直前のルビの最末端
        self.tagstack = []
        self.attrstack = []
        self.inKeikakomigyou = False # 罫囲み（行中）のフラグ
        self.keisenxpos = 0

        """ Pangoのバグに対する対策
            オリジナルのPangoがタグによる重力制御を振り切るケースが多々ある
            ため、ここで文字種を判定し英文には横組タグ(aozora yokogumi)を
            付す。
        """
        sTmp = []
        end = len(data)
        localtagstack = []
        pos_start = 0
        pos_end = 0
        while pos_start < end:
            if data[pos_start:pos_start+2] == u'</':
                # 既存の閉じタグ
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
                # タグ
                pos_end = data.find( u'>', pos_start)
                if pos_end != -1:
                    pos_end += 1
                    localtagstack.append(data[pos_start:pos_end])
                    sTmp.append(data[pos_start:pos_end])
                    pos_start = pos_end
                    continue

            elif self.isYokoChar(data[pos_start]):
                # 横書き文字ならタグを挿入する
                # 但し
                #   既にyokogumiタグがある あるいは 縦中横のなかである
                #   caption の中である
                #   なら見送る
                for s in localtagstack:
                    if s.find(u'<aozora yokogumi') != -1 or s.find(u'tatenakayoko') != -1:
                        break
                    if s.find(u'<aozora caption') != -1:
                        break
                else:
                    localtagstack.append( u'<aozora yokogumi2' )
                    sTmp.append( u'<aozora yokogumi="dmy">' )

            elif localtagstack and u'<aozora yokogumi2' in localtagstack:
                # 縦書き文字検出
                # このルーチンでの横組みが指定されていれば閉じる
                localtagstack.pop()
                postmp = -1
                try:
                    while sTmp[postmp][0:2] != u'</' and sTmp[postmp][0] == u'<':
                        # この文字にタグが掛かっている場合、遡って閉じる
                        postmp -= 1
                    postmp += 1
                    if postmp == 0:
                        sTmp.append( u'</aozora>' )
                    else:
                        sTmp.insert(postmp,u'</aozora>' )
                except IndexError:
                    sTmp.append( u'</aozora>' )

            sTmp.append(data[pos_start])
            pos_start += 1

        self.feed(u''.join(sTmp))
        self.close()

    def setcolour(self, fore, back):
        """ 描画色・背景色を得る
        """
        (self.foreR,self.foreG,self.foreB) = self.convcolor(fore)
        (self.backR,self.backG,self.backB) = self.convcolor(back)

    def setfont(self, font, size, rubisize):
        """ フォント
        """
        self.fontname = font
        self.fontsize = size
        self.fontrubisize = rubisize
        self.fontheight = int(round(float(size)*(16./12.)))
        self.fontwidth = self.fontheight # 暫定
        self.rubifontheight = int(round(float(rubisize)*(16./12.)))
        self.font = pango.FontDescription(u'%s %f' % (font,size))
        self.font_rubi = pango.FontDescription(u'%s %f' % (font,rubisize))

    def getforegroundcolour(self):
        return (self.foreR,self.foreG,self.foreB)

    def getbackgroundcolour(self):
        return (self.backR,self.backG,self.backB)

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

    def handle_starttag(self, tag, attr):
        self.tagstack.append(tag)
        self.attrstack.append(attr)

    def handle_endtag(self, tag):
        if self.tagstack != []:
            if self.tagstack[-1] == tag:
                try:
                    if self.attrstack[-1][0][0] == u'keikakomigyou':
                        if self.attrstack[-1][0][1] in [u'3', u'0']:
                            # 罫囲み（行中）の閉じ罫線（下側罫線）
                            # handle_data では都度引かれてしまうのでここで処理する
                            with cairocontext(self.sf) as ctx00:
                                ctx00.set_antialias(cairo.ANTIALIAS_NONE)
                                ctx00.set_line_width(1)
                                # 下
                                ctx00.move_to(self.xpos - self.keisenxpos, self.ypos)
                                ctx00.rel_line_to(self.keisenxpos*2, 0)
                                ctx00.stroke()
                                self.inKeikakomigyou = False
                except IndexError:
                    pass
                self.tagstack.pop()
                self.attrstack.pop()

    def handle_data(self, data):
        """ 挟まれたテキスト部分が得られる
        """

        def __bousen_common(key, xofset):
            """ 傍線表示
            """
            with cairocontext(self.sf) as ctx00:
                ctx00.set_antialias(cairo.ANTIALIAS_NONE)
                ctx00.new_path()
                ctx00.set_line_width(1)
                if dicArg[key] == u'破線':
                    ctx00.set_dash((3.5,3.5,3.5,3.5))
                elif dicArg[key] == u'鎖線':
                    ctx00.set_dash((1.5,1.5,1.5,1.5))
                elif dicArg[key] == u'二重傍線':
                    ctx00.move_to(self.xpos + xofset +2, self.ypos)
                    ctx00.rel_line_to(0, length)
                    ctx00.stroke()

                if dicArg[key] == u'波線':
                    ctx00.set_antialias(cairo.ANTIALIAS_DEFAULT)
                    spn = 5 # 周期
                    vx = 3 # 振幅
                    tmpx = self.xpos + xofset
                    for y in xrange(0, length, spn):
                        tmpy = self.ypos + y
                        ctx00.move_to(tmpx, tmpy)
                        ctx00.curve_to(tmpx,tmpy, tmpx+vx,tmpy+spn/2, tmpx,tmpy+spn)
                        vx *= -1
                else:
                    # 波線以外を描画
                    ctx00.move_to(self.xpos + xofset, self.ypos)
                    ctx00.rel_line_to(0, length)
                ctx00.stroke()

        def __bouten_common(key, xofset):
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
                # stroke                      fill
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
                tmpx = self.xpos + xofset + r * (-2 if xofset < 0 else 1)
                tmpy = self.ypos + d + r
                ctx00.new_path()
                ctx00.set_antialias(cairo.ANTIALIAS_DEFAULT) # cairo.ANTIALIAS_NONE
                ctx00.set_line_width(d/5.7)     # フォントサイズに連動する
                # 傍点を描く。修飾対象文字が縦中横で修飾される場合は１文字扱い。
                for s in data if not u'tatenakayoko' in dicArg else u' ':
                    dicfunc[dicArg[key]]()      # 引数は大域渡し
                    tmpy += step
                if dicArg[key] in [u'傍点', u'丸傍点', u'蛇の目傍点', u'黒三角傍点']:
                    ctx00.fill()
                else:
                    ctx00.stroke()
            self.boutenofset = -d if xofset < 0 else (d+r)

        def __rubi_common(key, xofset):
            """ ルビ表示
            """
            with cairocontext(self.sf) as ctx00, pangocairocontext(ctx00) as pangoctx00:
                layout = pangoctx00.create_layout()
                pc = layout.get_context()       # Pango を得る
                pc.set_base_gravity('east')     # markup 前に実行
                pc.set_gravity_hint('natural')   # markup 前に実行
                layout.set_font_description(self.font_rubi)

                # ルビにママをつける場合の処理
                # ２行表示とする
                rubipos = dicArg[key].rfind(u'〔ルビママ〕')
                if rubipos == -1:
                    rubipos = dicArg[key].rfind(u'〔ママ〕')
                if rubipos != -1:
                    if rubipos <= len(dicArg[key])/2.:
                        # ルビが短い
                        rubitmp = u'%s\n%s' % (dicArg[key][rubipos:],
                            dicArg[key][:rubipos].center(len(dicArg[key][rubipos:])*2))
                    else:
                        rubitmp = u'%s\n%s' % (dicArg[key][rubipos:].center(len(dicArg[key][:rubipos])*2),
                            dicArg[key][:rubipos])
                    rubitmp = rubitmp.strip(u'\n') # １行しかない場合は改行を外す
                else:
                    rubitmp = dicArg[key]
                layout.set_markup(rubitmp)
                rubilength,rubispan = layout.get_pixel_size()

                # 表示位置 垂直方向のセンタリング
                y = self.ypos + int((length-rubilength) // 2.)
                if y < 0:
                    y = 0
                if y < self.rubilastYpos and self.rubilastXofset * xofset > 0:
                    # ルビが連なる場合、直前のルビとの干渉を回避する
                    y = self.rubilastYpos

                if key == u'leftrubi':
                    rubispan = 0
                #"""
                pangoctx00.translate(self.xpos + xofset + rubispan + \
                                            self.boutenofset, y)

                pangoctx00.rotate(1.57075)
                pangoctx00.update_layout(layout)
                pangoctx00.show_layout(layout)
                self.rubilastYpos = y + rubilength  # ルビの最末端を保存
                self.rubilastXofset = xofset # ルビが左右いずれかであるかを保持
                del pc
                del layout

        def __fontsizechange(parentsize, default):
            """ 一段階大きい（あるいは小さい）フォントサイズを得る
            """
            if not parentsize:
                size = default
            else:
                tmp = parentsize.split(u'-')
                size = u''
                if len(tmp) == 1:
                    size = u'x-%s' % tmp[0]
                else:
                    size = u'x%s' % parentsize
                if u'xxx' in size:
                    size = parentsize #
            return size

        """------------------------------------------------------------------
        """
        # 初期化
        self.boutenofset = 0    # 傍点描画後のルビ位置補正値

        xposoffset = 0
        rubispan = 0
        dicArg = {}
        sTmp = data
        fontsizename = u''

        try:
            # タグスタックに積まれている書式指定を全て付す
            # Pangoでうまく処理できないタグはここで代替処理する
            pos = -1
            while True:
                s = self.tagstack[pos]
                if s == u'aozora':
                    # 拡張したタグは必ず属性をとる
                    for i in self.attrstack[pos]:
                        dicArg[i[0]] = i[1]
                    # 一部のタグは本文を引数で置換する
                    if u'tatenakayoko' in dicArg:
                        sTmp = dicArg[u'tatenakayoko']
                    pos -= 1
                    continue
                elif s == u'sup':
                    #<sup>単独ではベースラインがリセットされる為、外部で指定する
                    #また文字高(行高)がnormalのままとなるので size を使う
                    xposoffset = int(math.ceil(self.fontwidth / 3.))
                    sTest = [u'<span size="small">', sTmp, u'</span>']
                    # 本文サイズとの相対値としたいが、タグを内側からチェックしているので
                    # 本文側のサイズを知ることができない！
                    # 例：<span size=><sup>hoge</sup></span>
                    # 　　<sup>が先にチェックされている
                    #sTest = [u'<span size="%s">' % __fontsizechange(fontsizename, u'small'), sTmp, u'</span>']
                elif s == u'sub':
                    #<sub>単独ではベースラインがリセットされる為、外部で指定する
                    #また文字高(行高)がnormalのままとなるので size を使う
                    xposoffset = -int(math.ceil(self.fontwidth / 3.))
                    sTest = [u'<span size="small">', sTmp, u'</span>']
                    #sTest = [u'<span size="%s">' % __fontsizechange(fontsizename, u'small'), sTmp, u'</span>']
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
            ctx.set_source_rgb(self.foreR,self.foreG,self.foreB) # 描画色
            layout = pangoctx.create_layout()
            layout.set_font_description(self.font)
            honbunxpos = 0
            if not dicArg:
                # 本文表示本体
                pc = layout.get_context() # Pango を得る
                # 正しいlengthを得るため、予め文字の向きを決める
                pc.set_base_gravity('east')
                pc.set_gravity_hint('strong')
                layout.set_markup(sTmp)
                length, span = layout.get_pixel_size()

                honbunxpos = int(math.ceil(span/2.))
                pangoctx.translate(self.xpos + xposoffset + honbunxpos,
                                                    self.ypos)  # 描画位置
                pangoctx.rotate(1.57075) # 90度右回転、即ち左->右を上->下へ
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc
                del sTmp
                del layout
            else:
                if u'img' in dicArg:
                    sTmp = sTmp.replace(u'＃',u'　')
                    layout.set_markup(sTmp)
                    # 段落埋め込みの画像
                    # 描画位置の調整
                    length, y = layout.get_pixel_size() #幅と高さを返す(実際のピクセルサイズ)
                    imgtmpx = int(math.ceil(float(dicArg[u'width'])/2.))
                    imgtmpy = int(math.ceil((length - float(dicArg[u'height']))/2.))
                    #length = int(dicArg[u'height'])
                    #print length
                    pangoctx.translate(self.xpos + xposoffset - imgtmpx,
                                            #self.ypos)
                                            self.ypos+imgtmpy)
                    pangoctx.rotate(0)
                    img = cairo.ImageSurface.create_from_png(
                            os.path.join(self.aozoratextdir,dicArg[u'img']) )
                    ctx.set_source_surface(img,0,0) # 直前のtranslateが有効
                    ctx.paint()
                    del img

                elif u'img2' in dicArg:
                    # 画像
                    pangoctx.translate(self.xpos + xposoffset,
                        self.ypos + int(self.get_value(u'fontheight'))*1)
                    pangoctx.rotate(0)
                    img = cairo.ImageSurface.create_from_png(
                                os.path.join(self.aozoratextdir,dicArg[u'img2']))

                    ctx.scale(float(dicArg[u'rasio']),float(dicArg[u'rasio']))
                    # scaleで画像を縮小すると座標系全てが影響を受ける為、
                    # translate で指定したものを活かす
                    sp = cairo.SurfacePattern(self.sf)
                    sp.set_filter(cairo.FILTER_BEST) #FILTER_GAUSSIAN )#FILTER_NEAREST)
                    ctx.set_source_surface(img,0,0)
                    ctx.paint()
                    length = float(self.get_value(u'fontheight'))*1 + \
                        math.ceil(float(dicArg[u'height'])*float(dicArg[u'rasio']))
                    # キャプション用に退避
                    self.figstack.append((self.xpos,
                        self.ypos + int(self.get_value(u'fontheight'))*1 + length,
                        round(float(dicArg[u'width']) * float(dicArg[u'rasio'])) ))
                    del img

                elif u'caption' in dicArg:
                    # 画像が表示されていればキャプションを横書きで表示する。
                    #if self.oldwidth > 0:
                    if self.figstack:
                        (self.xpos, self.ypos, tmpwidth) = self.figstack.pop()
                        ch = int(round(tmpwidth / (float(self.get_value(u'fontheight')) *
                                self.fontmagnification( u'size="smaller"' )) ))
                        s0 = sTmp[:ch-1]
                        for i in range(ch-1, len(sTmp), ch):
                            s0 = u'%s\n%s' % (s0, sTmp[i:i+ch])

                        sTmp = u'<span size="smaller">%s</span>' % s0 #.rstrip(u'\n')
                        pc = layout.get_context() # Pango を得る
                        pc.set_base_gravity('south')
                        pc.set_gravity_hint('natural')
                        layout.set_markup(sTmp)
                        span, length = layout.get_pixel_size()
                        pangoctx.translate(
                            self.xpos + xposoffset,
                            self.ypos )
                        pangoctx.rotate(0)
                        pangoctx.update_layout(layout)
                        pangoctx.show_layout(layout)
                        del pc
                    else:
                        length = 0.

                elif u'warichu' in dicArg:
                    # 割り注
                    layout.set_markup(data)
                    length,y = layout.get_pixel_size()
                    sTmp = dicArg[u'warichu'].split(u'［＃改行］')
                    if len(sTmp) < 2:
                        l = int(dicArg[u'height'])
                        sTmp = [ dicArg[u'warichu'][:l],dicArg[u'warichu'][l:] ]
                    sTmp.insert(1,u'\n')
                    pc = layout.get_context()
                    pc.set_base_gravity('east')
                    pc.set_gravity_hint('natural')
                    layout.set_markup(u'<span size="x-small">%s</span>' % ''.join(sTmp))
                    x0,y = layout.get_pixel_size()
                    pangoctx.translate(self.xpos + y//2,
                                    self.ypos + int(round(float(length-x0)/2.)))
                    pangoctx.rotate(1.57075)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc

                elif u'tatenakayoko' in dicArg:
                    # 縦中横 直前の表示位置を元にセンタリングする
                    pc = layout.get_context() # Pango を得る
                    pc.set_base_gravity('south')
                    pc.set_gravity_hint('natural')
                    layout.set_markup(sTmp)
                    y, length = layout.get_pixel_size() #x,yを入れ替えることに注意
                    pangoctx.translate(self.xpos + xposoffset - int(math.ceil(y/2.)),
                                                        self.ypos)
                    pangoctx.rotate(0)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc
                    # ルビ、傍点、傍線類の表示位置を設定
                    honbunxpos = xposoffset + int(math.ceil(y/2.))

                else:
                    # 本文表示本体
                    # ※少しでも処理速度を稼ぐため上にも似たルーチンがあります
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
                        with cairocontext(self.sf) as dashctx:
                            # cairo.ANTIALIAS_GRAY, cairo.ANTIALIAS_NONE
                            dashctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                            dashctx.new_path()
                            dashctx.set_line_width(1)
                            dashctx.move_to(self.xpos + xposoffset + honbunxpos,
                                                    self.ypos+1)
                            dashctx.rel_line_to(0, length-3)
                            dashctx.close_path()
                            dashctx.stroke()
                    else:
                        honbunxpos = int(math.ceil(span/2.))
                        pangoctx.translate(self.xpos + xposoffset + honbunxpos,
                                                    self.ypos )  # 描画位置
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
                        ctx00.set_line_width(1)
                        self.keisenxpos = honbunxpos
                        # 右
                        ctx00.move_to(self.xpos + honbunxpos, self.ypos)
                        ctx00.rel_line_to(0, length)
                        # 左
                        ctx00.move_to(self.xpos - honbunxpos, self.ypos)
                        ctx00.rel_line_to(0, length)
                        if not self.inKeikakomigyou and dicArg[u'keikakomigyou'] in [u'1', u'0']:
                            # 上
                            ctx00.move_to(self.xpos - self.keisenxpos, self.ypos)
                            ctx00.rel_line_to(self.keisenxpos * 2, 0)
                            self.inKeikakomigyou = True
                        ctx00.stroke()

                if u'bousen' in dicArg:
                    # 傍線
                    __bousen_common(u'bousen', honbunxpos)
                if u'bouten' in dicArg:
                    # 傍点
                    __bouten_common(u'bouten', honbunxpos)

                # 大域変数で傍点との重なりを回避するのでbouten/bousen処理の直後に置くこと
                # 親文字に送り量調整された括弧類や句読点類が含まれると、ルビを繰り返し
                # 表示してしまう。
                if u'rubi' in dicArg and not data in self.kakko:
                    # ルビ
                    __rubi_common(u'rubi', honbunxpos)

                if u'leftbousen' in dicArg:
                    # 左傍線
                    __bousen_common(u'leftbousen', -honbunxpos)

                if u'leftbouten' in dicArg:
                    # 左傍点
                    __bouten_common(u'leftbouten', -honbunxpos)

                # 大域変数で傍点との重なりを回避するのでleft bouten/bousen処理の直後に置くこと
                # 親文字に送り量調整された括弧類や句読点類が含まれると、ルビを繰り返し
                # 表示してしまう。
                if u'leftrubi' in dicArg and not data in self.kakko:
                    # 左ルビ
                    __rubi_common(u'leftrubi', -honbunxpos)
                    # 多重表示を回避するため、一度表示したタグを抜去する
                    for pos, s in enumerate(self.tagstack):
                        if self.tagstack[pos] == u'aozora':
                            for i in self.attrstack[pos]:
                                if i[0] == u'leftrubi' and i[1] == dicArg[u'leftrubi']:
                                    #self.tagstack.pop(pos)
                                    self.attrstack.pop(pos)
                                    self.attrstack.insert(pos, [(u'dmy',u'dmy')])
                                    break
                            else:
                                continue
                            break

        # 次の呼び出しでの表示位置
        self.ypos += length


class CairoCanvas(ReaderSetting, AozoraScale):
    """ cairo / pangocairo を使って文面を縦書きする
    """
    def __init__(self):
        ReaderSetting.__init__(self)

    def writepage(self, pageposition, buffname=u'', currentpage=0, maxpage=0, title=u''):
        """ 指定したページを描画する
            pageposition : 表示ページのフォーマット済ファイル上での絶対位置
        """
        if not buffname:
            buffname = self.destfile

        inKeikakomi = False # 罫囲み
        maxchars = 0            # 囲み内に出現する文字列の最大長
        offset_y = 0            # 文字列の書き出し位置
        tmpwidth = 0
        tmpheight = 0
        fontheight = int(self.get_value(u'fontheight'))
        fontwidth = fontheight # 暫定

        xpos = self.canvas_width - self.canvas_rightmargin - int(math.ceil(self.canvas_linewidth/2.))
        KeikakomiXendpos = xpos
        KeikakomiYendpos = self.canvas_height - self.canvas_topmargin - int(self.get_value(u'bottommargin'))

        # キャンバスの確保
        self.sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        self.canvas_width, self.canvas_height)
        #self.sf = cairo.PDFSurface('tmp.pdf',
        #                self.canvas_width*1.0, self.canvas_height*1.0)

        # 文字列表示クラス
        self.drawstring = expango(self.sf)
        self.drawstring.setcolour(self.get_value(u'fontcolor'),
                                                self.get_value(u'backcolor'))
        self.drawstring.setfont(self.canvas_fontname, self.canvas_fontsize,
                                                    self.canvas_rubifontsize )
        # 画面クリア
        with cairocontext(self.sf) as ctx:
            ctx.rectangle(0, 0, self.canvas_width, self.canvas_height)
            r,g,b = self.drawstring.getbackgroundcolour()
            ctx.set_source_rgb(r, g, b)
            ctx.fill()

        # 行末揃え確認用
        """
        with cairocontext(self.sf) as ctx:
            ctx.set_antialias(cairo.ANTIALIAS_NONE)
            ctx.new_path()
            ctx.set_line_width(1)
            ctx.move_to(0,
                    self.canvas_topmargin + self.chars * fontheight)
            ctx.rel_line_to(self.canvas_width,0)
            ctx.rel_line_to(0,-fontheight)
            ctx.rel_line_to(-self.canvas_width,0)
            ctx.close_path()
            ctx.stroke()
        #"""

        with codecs.open(buffname, 'r', 'UTF-8') as f0:
            f0.seek(pageposition)
            for i in xrange(self.pagelines):
                s0 = f0.readline().rstrip('\n')

                tmpxpos = s0.find(u'<aozora keikakomi="start"></aozora>')
                if tmpxpos != -1:
                    # 罫囲み開始
                    inKeikakomi = True
                    offset_y = self.chars
                    maxchars = 0
                    s0 = s0[:tmpxpos] + s0[tmpxpos+35:]
                    KeikakomiXendpos = xpos# + int(round(self.canvas_linewidth/2.))

                tmpxpos = s0.find(u'<aozora keikakomi="end"></aozora>')
                if tmpxpos != -1:
                    # 罫囲み終わり
                    inKeikakomi = False
                    s0 = s0[:tmpxpos] + s0[tmpxpos+33:]
                    if offset_y > 0:
                        offset_y -= 1
                    maxchars -= offset_y
                    if maxchars < self.chars:
                        maxchars += 1
                    tmpwidth = KeikakomiXendpos - xpos
                    with cairocontext(self.sf) as ctx:
                        ctx.set_antialias(cairo.ANTIALIAS_NONE)
                        ctx.new_path()
                        ctx.set_line_width(1)
                        ctx.move_to(xpos,
                                self.canvas_topmargin + offset_y * fontheight)
                        ctx.rel_line_to(tmpwidth,0)
                        ctx.rel_line_to(0, maxchars * fontheight)
                        ctx.rel_line_to(-tmpwidth,0)
                        ctx.close_path()
                        ctx.stroke()

                if inKeikakomi:
                    # 罫囲み時の最大高さを得る
                    tmpheight = self.linelengthcount(s0)
                    if  tmpheight > maxchars:
                        maxchars = tmpheight
                    # 文字列の最低書き出し位置を求める
                    sTmp = s0.strip()
                    if sTmp:
                        tmpheight = s0.find(sTmp)
                        if tmpheight < offset_y:
                            offset_y = tmpheight

                self.drawstring.settext(s0, xpos, self.canvas_topmargin)
                #self.drawstring.destroy()
                xpos -= self.canvas_linewidth

        # ノンブル(ページ番号)
        if currentpage:
            with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                layout = pangoctx.create_layout()
                layout.set_markup( u'<span size="x-small">%d (全%d頁)</span>' % (currentpage, maxpage))
                wx,wy = layout.get_pixel_size() # 左下時必要
                pangoctx.translate(int(self.get_value('leftmargin')), self.canvas_height - wy -4) # 左下時のY位置
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del layout

            # 柱（テキスト名）
            if title:
                with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                    layout = pangoctx.create_layout()
                    layout.set_markup( u'<span size="x-small">%s</span>' % title.strip(u' ').strip(u'　'))
                    pangoctx.translate(int(self.get_value('leftmargin')), 4) # 表示位置 (左上)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del layout

        self.sf.write_to_png(os.path.join(self.get_value(u'workingdir'),
                                                            'thisistest.png'))
        self.sf.finish()
        del self.drawstring
        del self.sf





