#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
<menu action="View">
            <menuitem action="x00"/>
            <menuitem action="x10"/>
            <menuitem action="x20"/>
            <menuitem action="x30"/>
            <menuitem action="x05"/>
            <menuitem action="x15"/>
            <menuitem action="x25"/>
            <menuitem action="xs1"/>
            <menuitem action="xs2"/>
            <menuitem action="xs3"/>
        </menu>
        <popup>
        <menuitem action="x00"/>
        <menuitem action="x10"/>
        <menuitem action="x20"/>
        <menuitem action="x30"/>
        <menuitem action="x05"/>
        <menuitem action="x15"/>
        <menuitem action="x25"/>
        <menuitem action="xs1"/>
        <menuitem action="xs2"/>
        <menuitem action="xs3"/>
        <separator/>
        <menuitem action="quit"/>
    </popup>
"""
ui_str = """<ui>
    <menubar name="MenuBar">
        <menu action="File">
            <menuitem action="quit"/>
        </menu>

    </menubar>

</ui>"""

import gtk
#import common

class TestWindow(gtk.Window):
    def __init__(self):
        # 継承のお約束
        gtk.Window.__init__(self)
        #
        # メニューを作る
        #
        # まず GtkUIManager 作成
        uimanager = gtk.UIManager()
        # GtkAccelGroup を得る
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        # GtkActionGroup 作成
        actiongroup = gtk.ActionGroup("sasakimamenu")
        # GtkActionEntry を作成して突っ込む
        # name, stock_id, label, accelerator, tooltip, callback
        actions0 = [("quit", gtk.STOCK_QUIT, "終了(_Q)", "<Control>Q", "さいなら", self.on_quit),
                    ("File", None, "ファイル(_F)"),
                    ("View", None, "表示(_V)")]
                    #("Popup", None, "")]
        actiongroup.add_actions(actions0)
        # GtkRadioActionEntry の List を作成
        # name, stock_id, label, accelerator, tooltip, value
        actions1 = [("x00", None, "ウインドサイズ", "0", "ウインドサイズ", 0),
                    ("x10", None, "x1.0", "1", "x1.0", 1),
                    ("x20", None, "x2.0", "2", "x2.0", 2),
                    ("x30", None, "x3.0", "3", "x3.0", 3),
                    ("x05", None, "x0.5", "4", "x0.5", 4),
                    ("x15", None, "x1.5", "5", "x1.5", 5),
                    ("x25", None, "x2.5", "6", "x2.5", 6),
                    ("xs1", None, "set1", "7", "set1", 7),
                    ("xs2", None, "set2", "8", "set1", 8),
                    ("xs3", None, "set3", "9", "set1", 9) ]
        # GtkRadioAction を突っ込む
        # entries, value=0, on_change=None, user_data=None
        #actiongroup.add_radio_actions(actions1, 0, self.on_size_change)
        #
        uimanager.insert_action_group(actiongroup, 0)
        uimanager.add_ui_from_string(ui_str)
        # Popup Menu を得る
        self.popup_menu = uimanager.get_widget('/popup')
        # セレクタの List を作っておく
        self.size_str = ["win","x1.0","x2.0","x3.0","x0.5","x1.5","x2.5","set1","set2","set3"]
        # おしまい
        #
        # ステータスバーを作る
        #self.sb = common.CStatusBar(2, self)
        #self.sb.label[0].set_text("こんどは")
        #self.sb.label[1].set_text("menu を作ったよ")
        vb = gtk.VBox()
        # 最初にメニューを突っ込もうね
        menubar = uimanager.get_widget("/MenuBar")
        vb.pack_start(menubar, False)
        da = gtk.DrawingArea()
        vb.pack_start(da)
        #vb.pack_start(self.sb, False, False, 0)
        self.add(vb)
        self.connect("delete-event", self.on_quit)
        # GDK イベントの有効化を行っておく
        da.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        da.connect("button_press_event", self.on_button_down)
        self.resize(320, 240)
        self.show_all()

    def on_size_change(self, action, current):
        # ステータスバーにサイズの表示
        self.sb.label[1].set_text(self.size_str[action.get_current_value()])

    def on_quit(self, widget, event=None):
        # bye
        gtk.main_quit()
        return True

    def on_button_down(self, widget, event):
        # 右クリで PopupMenu
        if event.button == 3:
            self.popup_menu.popup(None, None, None, event.button, event.time)

if __name__ == "__main__":
    w = TestWindow()
    gtk.main()