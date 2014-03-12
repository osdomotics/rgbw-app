# -*- coding: iso-8859-1 -*-
# Copyright (C) 2013 Marcus Priesch, All rights reserved
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
#    ««revision-date»»···
#--
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

PORT = 5683
HOST = "aaaa::221:2eff:ff00:266c"
PATH = "actuators/RGBWLed"

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
# end class RGBW_Led_Widget

class OSD_Led_App (App) :
    title = "OpenSourceDomotics RGBW LED App"

    COLORS = dict ()

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

        self.turned_off = False
        self.send_coap  = True
        self.root = RGBW_Led_Widget ()

        self.COLORS = eval (self.config.get ("OSD_RGBW_Led_App", "COLORS"))
        print self.COLORS

        for btn in self.root.buttoncontainer.children :
            idx = btn.idx
            val = self.COLORS.get (idx)
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

        self.root.switch.bind (active = self.color_changed)
        return self.root
    # end def build

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
    ## # end def address_changed

    def color_changed (self, *args, **kws) :
        print "color_changed", args, kws
        red   = self.root.red.value
        green = self.root.green.value
        blue  = self.root.blue.value
        white = self.root.white.value
        bri   = self.root.brightness.value_normalized

        red   = int (red   * bri)
        green = int (green * bri)
        blue  = int (blue  * bri)
        white = int (white * bri)

        with self.root.color.canvas.before :
            Color (red / 255.0, green / 255.0, blue / 255.0)
#            Rectangle ( pos  = self.root.color.pos
#                      , size = self.root.color.size
#                      )

        if not self.root.switch.active :
            red = green = blue = 0
        else :
            self.turned_off = False

        if not self.turned_off :
            self.set_leds (red, green, blue, white)

        if not self.root.switch.active :
            self.turned_off = True
    # end def color_changed

    def set_leds (self, red, green, blue, white) :
        if self.send_coap :
            params = \
                ( "red=%d&green=%d&blue=%d&white=%d"
                % (red, green, blue, white)
                )
            try :
                coapput.putResource \
                    (self.ep, PATH, self.remote, params, endless = False)
                self.root.status.text = "Ok"
            except Exception, e :
                self.root.status.text = repr (e)
    # end def set_leds

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
            print self.COLORS,type (self.COLORS)
            [r,g,b,w,bri]         = self.COLORS [number]
            self.send_coap        = False
            self.root.red.value   = r
            self.root.green.value = g
            self.root.blue.value  = b
            self.root.white.value = w
            self.root.brightness.value = bri
            self.send_coap        = True
            r = int (r * bri / 255.0)
            g = int (g * bri / 255.0)
            b = int (b * bri / 255.0)
            w = int (w * bri / 255.0)
            self.set_leds (r, g, b, w)

        else :
            # store currently selected color
            color = \
                [ self.root.red.value
                , self.root.green.value
                , self.root.blue.value
                , self.root.white.value
                , self.root.brightness.value
                ]
            self.COLORS [number] = color
            self.config.set \
                ("OSD_RGBW_Led_App", "COLORS", self.COLORS)
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


# end class OSD_Led_App

if __name__ in ("__android__", "__main__") :
    OSD_Led_App ().run ()

### __END__ osd-led-app/main
