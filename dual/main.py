# -*- coding: iso-8859-1 -*-
# Copyright (C) 2013-2014 Marcus Priesch, All rights reserved
# In Prandnern 31, A--2122 Riedenthal, Austria. office@priesch.co.at
#
#++
# Name
#    osd-led-app/main
#
# Purpose
#    main app to control the osd rgbw led strip
#
# Revision Dates
#    28-Apr-2013 (MPR) Creation
#    12-Mar-2014 (SPO) added multi led support
#    ««revision-date»»···
#--:
import kivy
import coapy
import coapput
import socket
import time

from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.config import Config
from kivy.uix.gridlayout import GridLayout
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.screenmanager import ScreenManager, Screen

PORT = 5683
HOST = "aaaa::221:2eff:ff00:355b"
PATH = "a/dual_rgbw_led"

class RGBW_Led_Widget (BoxLayout) :
    red             = ObjectProperty (None)
    green           = ObjectProperty (None)
    blue            = ObjectProperty (None)
    white           = ObjectProperty (None)
    brightness      = ObjectProperty (None)
    switch          = ObjectProperty (None)
    ## ipv6_address    = ObjectProperty (None)
    status          = ObjectProperty (None)
    buttoncontainer = ObjectProperty (None)
    send_coap       = True
    Colors          = 0
    def __init__(self, idx, config, **kwargs):
        super(RGBW_Led_Widget, self).__init__(**kwargs)
        self.idx = idx
        self.send_coap = True
        self.config = config

    def build(self, colors) :
        print "widget idx:",self.idx
        print colors
        self.turned_off = False
        self.Colors = colors
        for btn in self.buttoncontainer.children :
            idx = btn.idx
            val = colors.get (idx)
            if val :
                # set button background
                red, green, blue, white, bri = val
                bri   = bri / 255.0
                red   = int (red   * bri)
                green = int (green * bri)
                blue  = int (blue  * bri)
#                white = int (white * bri)
                btn.color_set = True
                with btn.canvas.before :
                    Color \
                        ( red / 255.0
                        , green / 255.0
                        , blue / 255.0
                        , 1
                        )
            else :
                with btn.canvas.before :
                    Color \
                        ( 32
                        , 32
                        , 32
                        , 1
                        )
        self.switch.bind (active = self.color_changed)
        return self

    def set_leds(self, red, green, blue, white):
        print "turned off:", self.turned_off
        App.get_running_app().do_color_change \
            ( self.send_coap
            , self.idx
            , red, green, blue, white, self.status
            )
    # end def set_leds

    def color_changed (self, *args, **kws) :
        red   = self.red.value
        green = self.green.value
        blue  = self.blue.value
        white = self.white.value
        bri   = self.brightness.value_normalized

        red   = int (red   * bri)
        green = int (green * bri)
        blue  = int (blue  * bri)
        white = int (white * bri)

        with self.color.canvas.before :
            Color (red / 255.0, green / 255.0, blue / 255.0)
#            Rectangle ( pos  = self.root.color.pos
#                      , size = self.root.color.size
#                      )

        if not self.switch.active :
            red = green = blue = 0
        else :
            self.turned_off = False
        if not self.turned_off :
            #App.get_running_app().do_color_change(self.send_coap, self.idx, red, green, blue, white, self.status)
            self.set_leds (red, green, blue, white)

        if not self.switch.active :
            self.turned_off = True
    # end def color_changed

    def btn_touch_down (self, args) :
        btn, event = args
        if btn.collide_point (*event.pos) :
            btn.touch_down_ts = time.time ()
            print "btn_touch_down", btn, btn.idx
            print "btn_touch_down", event.is_double_tap, event.pos
            return True
        return False

    # end def btn_touch_down

    def btn_touch_up (self, args) :
        btn, event = args
        if not btn.collide_point (*event.pos) :
            return False

        print "btn pressed", btn, btn.idx, btn.color_set
        number = btn.idx

        if hasattr (btn, "touch_down_ts") :
            if time.time () - btn.touch_down_ts > 1 :
                print "long click"
                btn.color_set = False

        if btn.color_set == True :
            # set new color on the leds
            print self.Colors,type (self.Colors)
            [r,g,b,w,bri]         = self.Colors [number]
            self.send_coap        = False
            self.red.value   = r
            self.green.value = g
            self.blue.value  = b
            self.white.value = w
            self.brightness.value = bri
            self.send_coap        = True
            r = int (r * bri / 255.0)
            g = int (g * bri / 255.0)
            b = int (b * bri / 255.0)
            w = int (w * bri / 255.0)
            self.set_leds (r, g, b, w)

        else :
            # store currently selected color
            color = \
                [ self.red.value
                , self.green.value
                , self.blue.value
                , self.white.value
                , self.brightness.value
                ]
            self.Colors [number] = color
            self.config.set \
                ("OSD_RGBW_Led_App", "COLORS_%d" % self.idx, self.Colors)
            self.config.write ()
            self._set_btn_color (btn, *color)
            btn.color_set = True

        return True
    # end def btn_pressed

    def _set_btn_color (self, btn, r, g, b, w, bri):
        with btn.canvas.before :
            Color \
                ( r / 255.0 * bri / 255.0
                , g / 255.0 * bri / 255.0
                , b / 255.0 * bri / 255.0
                , 1
                )
    # end def _set_btn_color
#end class RGBW_Led_Widget

class RGBW_Layout_Container (GridLayout) :
  rgbw1 = ObjectProperty(RGBW_Led_Widget)
  rgbw2 = ObjectProperty(RGBW_Led_Widget)
  clr_picker = ColorPicker()
  def __init__(self, colors, config):
    super(RGBW_Layout_Container, self).__init__()
    self.rgbw1 = RGBW_Led_Widget(1, config)
    self.rgbw2 = RGBW_Led_Widget(2, config)
    #self.cols = 3
    self.cols = 2
    self.rgbw1.build(colors[1])
    self.add_widget(self.rgbw1)
    self.rgbw2.build(colors[2])
    self.add_widget(self.rgbw2)
    #self.add_widget(self.clr_picker)
  def build(self):
    return self



class OSD_Led_App (App) :
    title = "OpenSourceDomotics RGBW LED App"

    COLORS = dict ()

    def __init__(self, **kwargs):
        super(OSD_Led_App, self).__init__(**kwargs)
        self.colors = {1:(0, 0, 0, 0), 2:(0, 0, 0, 0)}

    def build_config (self, config) :
        config.setdefaults \
        ( "OSD_RGBW_Led_App",
            { "COLORS" : dict ()
            , "IP"     : HOST
            }
        )
    # end def build_config

    def build (self) :
        self.remote = (self.config.get ("OSD_RGBW_Led_App", "IP"), PORT, 0, 0)
        self.ep = coapy.connection.EndPoint (address_family = socket.AF_INET6)
        self.ep.socket.bind (("", coapy.COAP_PORT))

       # self.turned_off = False
        self.send_coap  = True
        self.COLORS [1] = eval (self.config.get ("OSD_RGBW_Led_App", "COLORS_1"))
        self.COLORS [2] = eval (self.config.get ("OSD_RGBW_Led_App", "COLORS_2"))
        print self.COLORS
        self.root = RGBW_Layout_Container (self.COLORS, self.config)
        return self.root

    def build_settings (self, settings) :
        json = \
             """[ { "type" : "string"
                  , "title" : "Node Address"
                  , "description" : "IPv6 Address of the RGBW-Led Node"
                  , "section" : "OSD_RGBW_Led_App"
                  , "key" : "IP"}
                ]
                """
        settings.add_json_panel \
            ( "OSD RGBW-Led Controller"
            , self.config
            , data = json
            )
    # end def build_settings

    def on_pause (self) :
        return True
    # end def on_pause

    ## def address_changed (self, *args, **kws) :
    ##     self.config.set ("OSD_RGBW_Led_App", "IP", self.root.ipv6_address.text)
    ##     self.remote = (self.root.ipv6_address.text, PORT, 0, 0)
    ## # end def address_changed"

    def do_color_change (self, send_coap, idx, red, green, blue, white, status) :
        print ("on_collor_changed callback called for idx{0}, send_coap:{1}, colors (r/g/b/w)=({2},{3},{4},{5})".format(idx, send_coap, red, green, blue, white))
        if send_coap :
            # idx == 1: first led stripe, idx == 2: second led stripe
            self.colors [idx] = (red / 4, green / 4, blue / 4, white / 4)

            params = \
                ( ( "r1=%d" % self.colors [1] [0])
                + ("&g1=%d" % self.colors [1] [1])
                + ("&b1=%d" % self.colors [1] [2])
                + ("&w1=%d" % self.colors [1] [3])
                + ("&r2=%d" % self.colors [2] [0])
                + ("&g2=%d" % self.colors [2] [1])
                + ("&b2=%d" % self.colors [2] [2])
                + ("&w2=%d" % self.colors [2] [3])
                )
            try :
                coapput.putResource \
                    (self.ep, PATH, self.remote, params, endless = False)
                status.text = "Ok"
            except Exception, e :
                status.text = repr (e)

# end class OSD_Led_App

if __name__ in ("__android__", "__main__") :
    OSD_Led_App ().run ()

### __END__ osd-led-app/main
