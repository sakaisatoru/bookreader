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
                caption
                rubi
                bousen
                leftrubi
                yokogumi

        拡張されたタグ
        pango   sup
                sub

    """
     # 右側傍点及び傍線
    dicBouten = {
        u'白ゴマ傍点':u'﹆',
        u'丸傍点':u'●',      u'白丸傍点':u'○',    u'黒三角傍点':u'▲',
        u'白三角傍点':u'△',  u'二重丸傍点':u'◎',  u'蛇の目傍点':u'◉',
        u'ばつ傍点':u'×',    u'傍点':u'﹅',
        u'波線':u'〜〜' }

    # 送り調整を要する文字
    kakko = u',)]｝、）］｝〕〉》」』】〙〗〟’”｠»・。、．，([{（［｛〔〈《「『【〘〖〝‘“｟«'

    def __init__(self, canvas):
        HTMLParser.__init__(self)
        AozoraScale.__init__(self)
        ReaderSetting.__init__(self)
        self.sf = canvas
        self.xposoffsetold = 0
        self.oldlength = 0. # self.oldlength = 0
        self.oldwidth = 0
        self.rubilastYpos = 0       # 直前のルビの最末端
        self.leftrubilastYpos = 0   # 直前の左ルビの最末端

    def destroy(self):
        del self.tagstack
        del self.attrstack

    def settext(self, data, xpos, ypos):
        self.xpos = xpos
        self.ypos = ypos
        self.rubilastYpos = 0       # 直前のルビの最末端
        self.leftrubilastYpos = 0   # 直前の左ルビの最末端
        self.tagstack = []
        self.attrstack = []

        """ Pangoのバグに対する対策
            オリジナルのPangoがタグによる重力制御を振り切るケースが多々ある
            ため、ここで文字種を判定し英文には横組タグ(aozora yokogumi)を
            付す。
        """
        sTmp = []
        end = len(data)
        tagstack = []
        pos_start = 0
        pos_end = 0
        while pos_start < end:
            if data[pos_start:pos_start+2] == u'</':
                # 既存の閉じタグ
                if tagstack and tagstack[-1] == u'<aozora yokogumi':
                    # このルーチンで挿入したタグがあれば先に閉じる
                    tagstack.pop()
                    sTmp.append( u'</aozora>' )

                pos_end = data.find( u'>', pos_start)
                if pos_end != -1:
                    if tagstack:
                        tagstack.pop()
                    sTmp.append(data[pos_start:pos_end+1])
                    pos_start = pos_end + 1
                    continue

            elif data[pos_start] == u'<':
                # タグ
                pos_end = data.find( u'>', pos_start)
                if pos_end != -1:
                    pos_end += 1
                    tagstack.append(data[pos_start:pos_end])
                    sTmp.append(data[pos_start:pos_end])
                    pos_start = pos_end
                    continue

            elif self.isYokoChar(data[pos_start]):
                # 横書き文字ならタグを挿入する
                # 但し
                #   既にyokogumiタグがある あるいは 縦中横のなかである
                #   なら見送る
                for s in tagstack:
                    if s.find(u'<aozora yokogumi') != -1 or s.find(u'tatenakayoko') != -1:
                        break
                else:
                    tagstack.append( u'<aozora yokogumi' )
                    sTmp.append( u'<aozora yokogumi="dmy">' )

            elif tagstack and tagstack[-1] == u'<aozora yokogumi':
                # 縦書き文字検出
                # このルーチンでの横組みが指定されていれば閉じる
                tagstack.pop()
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
                self.tagstack.pop()
                self.attrstack.pop()

    def handle_data(self, data):
        """ 挟まれたテキスト部分が得られる
        """
        vector = 0
        fontspan = 1
        xposoffset = 0
        boutenoffset = 0
        rubispan = 0
        dicArg = {}
        sTmp = data
        try:
            # タグスタックに積まれている書式指定を全て付す
            # Pangoでうまく処理できないタグはここで代替処理する
            pos = -1
            while True:
                s = self.tagstack[pos]
                if s == u'aozora':
                    # 拡張したタグは必ず引数をとる
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
                    fontspan = self.fontmagnification(u'<%s>' % s)
                    #sTest = [u'<sup>', sTmp, u'</sup>']
                    sTest = [u'<span size="small">', sTmp, u'</span>']
                elif s == u'sub':
                    #<sub>単独ではベースラインがリセットされる為、外部で指定する
                    #また文字高(行高)がnormalのままとなるので size を使う
                    xposoffset = -int(math.ceil(self.fontwidth / 3.))
                    fontspan = self.fontmagnification(u'<%s>' % s)
                    #sTest = [u'<sub>', sTmp, u'</sub>']
                    sTest = [u'<span size="small">', sTmp, u'</span>']
                else:
                    # 引数復元
                    sTest = []
                    sTest.append(u'<%s' % s)
                    if self.attrstack[pos] != []:
                        for i in self.attrstack[pos]:
                            sTest.append(u' %s="%s"' % (i[0],i[1]))
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
                                os.path.join(self.aozoratextdir,dicArg[u'img2']) )

                    ctx.scale(float(dicArg[u'rasio']),float(dicArg[u'rasio']))
                    # scaleで画像を縮小すると座標系全てが影響を受ける為、
                    # translate で指定したものを活かす
                    sp = cairo.SurfacePattern(self.sf)
                    sp.set_filter(cairo.FILTER_BEST) #FILTER_GAUSSIAN )#FILTER_NEAREST)
                    ctx.set_source_surface(img,0,0)
                    ctx.paint()
                    #length = int(float(self.get_value(u'fontheight'))*1 +
                    #    math.ceil(float(dicArg[u'height'])*float(dicArg[u'rasio'])))
                    length = float(self.get_value(u'fontheight'))*1 + \
                        math.ceil(float(dicArg[u'height'])*float(dicArg[u'rasio']))
                    # 後続のキャプション用に退避
                    self.oldlength = length
                    self.oldwidth = int(round(float(dicArg[u'width']) *
                                                        float(dicArg[u'rasio'])))
                    del img

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
                    layout.set_markup(u'<span size="smaller">%s</span>' % ''.join(sTmp))
                    x0,y = layout.get_pixel_size()
                    pangoctx.translate(self.xpos + y//2,
                                    self.ypos + int(round(float(length-x0)/2.)))
                    pangoctx.rotate(1.57075)
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc

                elif u'caption' in dicArg:
                    # キャプション
                    # 直前に画像がなかったり改ページされている場合は失敗するので、
                    # 処理そのものをキャンセルする
                    #
                    # set_widthが思うようにいかないので手動で改行位置を求める
                    # ch : １行あたりの文字数
                    if self.oldwidth > 0:
                        ch = int(round(self.oldwidth / (float(self.get_value(u'fontheight')) *
                                self.fontmagnification( u'size="smaller"' )) ))
                        sTmp = u''
                        for s0 in dicArg[u'caption'].split(u'\\n'):
                            while len(s0) > ch:
                                sTmp += s0[:ch] + u'\n'
                                s0 = s0[ch:]
                            sTmp += s0[:ch] + u'\n'
                        sTmp = u'<span size="smaller">%s</span>' % sTmp.rstrip(u'\n')
                        pc = layout.get_context() # Pango を得る
                        pc.set_base_gravity('south')
                        pc.set_gravity_hint('natural')
                        layout.set_markup(sTmp)
                        length, y = layout.get_pixel_size()
                        pangoctx.translate(
                            self.xpos + int(self.get_value(u'linewidth')) + (self.oldwidth - length)//2,
                                                    self.ypos + 5 + self.oldlength)
                        pangoctx.rotate(0)
                        pangoctx.update_layout(layout)
                        pangoctx.show_layout(layout)
                        del pc
                        length = y
                    else:
                        length = 0. #length = 0

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

                else:
                    # 本文表示本体
                    # ※少しでも処理速度を稼ぐため上にも似たルーチンがあります
                    pc = layout.get_context() # Pango を得る
                    # 正しいlengthを得るため、予め文字の向きを決める
                    if u'yokogumi' in dicArg:
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
                            #dashctx.set_antialias(cairo.ANTIALIAS_GRAY)
                            dashctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                            #dashctx.set_antialias(cairo.ANTIALIAS_NONE)
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

                if u'bousen' in dicArg:
                    # 傍線 但し波線を実装していません
                    with cairocontext(self.sf) as ctx00:
                        ctx00.set_antialias(cairo.ANTIALIAS_NONE)
                        if dicArg[u'bousen'][-1] == u'線':
                            ctx00.new_path()
                            ctx00.set_line_width(1)
                            if dicArg[u'bousen'] == u'破線':
                                ctx00.set_dash((3.5,3.5,3.5,3.5))
                            elif dicArg[u'bousen'] == u'鎖線':
                                ctx00.set_dash((1.5,1.5,1.5,1.5))
                            elif dicArg[u'bousen'] == u'二重傍線':
                                ctx00.move_to(self.xpos + honbunxpos +2, self.ypos)
                                ctx00.rel_line_to(0, length)
                                ctx00.stroke()
                            elif dicArg[u'bousen'] == u'波線':
                                pass
                            ctx00.move_to(self.xpos + honbunxpos, self.ypos)
                            ctx00.rel_line_to(0, length)
                            ctx00.stroke()
                        else:
                            # 傍点
                            # 本文表示長さ(ピクセル長)を文字数で割ったステップに
                            # 1文字づつ描画する。このためかなりメモリを費消する。
                            sB = u''
                            step = int(round(length / float(len(data))))
                            boutenoffset = int(round(honbunxpos*1.3))
                            tmpypos = self.ypos
                            if dicArg[u'bousen'] in [u'白ゴマ傍点', u'ばつ傍点', u'傍点']:
                                boutenfont = self.font
                            else:
                                boutenfont = self.font_rubi # 使う文字が大きいのでサイズを下げる
                                tmpypos += int(round((self.fontheight - self.rubifontheight)/2.))
                            for s in data:
                                with cairocontext(self.sf) as ctx002, pangocairocontext(ctx002) as panctx00:
                                    layout = panctx00.create_layout()
                                    layout.set_font_description(boutenfont)
                                    pc = layout.get_context()
                                    pc.set_base_gravity('east')
                                    pc.set_gravity_hint('natural')
                                    layout.set_text(self.dicBouten[dicArg[u'bousen']])
                                    panctx00.translate( self.xpos + honbunxpos + boutenoffset,
                                                                    tmpypos)
                                    tmpypos += step
                                    panctx00.rotate(1.57075)
                                    panctx00.update_layout(layout)
                                    panctx00.show_layout(layout)
                                del pc
                                del layout

                if u'rubi' in dicArg:
                    with cairocontext(self.sf) as ctx00, pangocairocontext(ctx00) as pangoctx00:
                        # ルビ
                        layout = pangoctx00.create_layout()
                        pc = layout.get_context()       # Pango を得る
                        pc.set_base_gravity('east')     # markup 前に実行
                        pc.set_gravity_hint('natural')   # markup 前に実行
                        layout.set_font_description(self.font_rubi)

                        # ルビにママをつける場合の処理
                        # ２行表示とする
                        rubipos = dicArg[u'rubi'].rfind(u'〔ルビママ〕') # if dicArg[u'rubi'] else -1
                        if rubipos != -1:
                            rubitmp = u'%s\n%s' % (
                                    dicArg[u'rubi'][rubipos:],
                                    dicArg[u'rubi'][:rubipos])
                            rubioffset = rubispan # 開始位置X座標のオフセット
                        else:
                            rubitmp = dicArg[u'rubi'] #if dicArg[u'rubi'] else u''
                            rubioffset = 0
                        layout.set_markup(rubitmp)
                        rubilength,rubispan = layout.get_pixel_size()
                        # 表示位置 垂直方向のセンタリング
                        y = self.ypos + int((length-rubilength) // 2.)
                        if y < 0:
                            y = 0
                        if y < self.rubilastYpos:
                            y = self.rubilastYpos # 直前のルビとの干渉をとりあえず回避する
                        if boutenoffset:
                            rubispan *= 2 # 傍点がある場合は重ね書きを回避する
                        pangoctx00.translate(self.xpos + honbunxpos + rubispan + rubioffset, y)
                        pangoctx00.rotate(1.57075)
                        pangoctx00.update_layout(layout)
                        pangoctx00.show_layout(layout)
                        self.rubilastYpos = y + rubilength #ルビの最末端を保存
                        del pc
                        del layout

                if u'leftrubi' in dicArg:
                    with cairocontext(self.sf) as ctx00, pangocairocontext(ctx00) as pangoctx00:
                        # 左ルビ
                        layout = pangoctx00.create_layout()
                        pc = layout.get_context()       # Pango を得る
                        pc.set_base_gravity('east')     # markup 前に実行
                        pc.set_gravity_hint('natural')   # markup 前に実行
                        layout.set_font_description(self.font_rubi)
                        layout.set_markup(dicArg[u'leftrubi'])
                        rubilength,rubispan = layout.get_pixel_size()
                        # 表示位置センタリング
                        y = self.ypos + int((length-rubilength) // 2.)
                        if y < 0:
                            y = 0
                        if y < self.leftrubilastYpos:
                            y = self.leftrubilastYpos # 直前のルビとの干渉をとりあえず回避する
                        pangoctx00.translate(self.xpos - honbunxpos ,y)
                        pangoctx00.rotate(1.57075)
                        pangoctx00.update_layout(layout)
                        pangoctx00.show_layout(layout)
                        self.leftrubilastYpos = y + rubilength #左ルビの最末端を保存
                        del pc
                        del layout

        # ypos 更新
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





