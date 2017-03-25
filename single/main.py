# -*- coding: iso-8859-1 -*-
# Copyright (C) 2013-2017 Marcus Priesch, All rights reserved
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
import json
import re
import sys
from urlparse import urlsplit, urlunsplit
import socket
import copy
import time

from kivy.support import install_twisted_reactor
from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.config import Config

install_twisted_reactor()

from twisted.internet import reactor, defer, threads, task
from twisted.python import log

import txthings.coap as coap
import txthings.resource as resource
import txthings

from ipaddress import ip_address

PORT = 5683
HOST = "aaaa::221:2eff:ff00:26e7"
PATH = "a/rgb_leds"


#Netloc parser assembled from various bits on stack overflow and regexlib
NETLOC_RE = re.compile(r'''^
                        (?:([^@])+@)?
                        (?:\[((?:(?:(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){6}:[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){5}:(?:[0-9A-Fa-f]{1,4}:)?[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){4}:(?:[0-9A-Fa-f]{1,4}:){0,2}[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){3}:(?:[0-9A-Fa-f]{1,4}:){0,3}[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){2}:(?:[0-9A-Fa-f]{1,4}:){0,4}[0-9A-Fa-f]{1,4})|
                        (?:(?:[0-9A-Fa-f]{1,4}:){6}(?:(?:\b(?:(?:25[0-5])|(?:1\d{2})|(?:2[0-4]\d)|
                        (?:\d{1,2}))\b)\.){3}(?:\b(?:(?:25[0-5])|
                        (?:1\d{2})|(?:2[0-4]\d)|(?:\d{1,2}))\b))|
                        (?:(?:[0-9A-Fa-f]{1,4}:){0,5}:(?:(?:\b(?:(?:25[0-5])|
                        (?:1\d{2})|(?:2[0-4]\d)|(?:\d{1,2}))\b)\.){3}(?:\b(?:(?:25[0-5])|
                        (?:1\d{2})|(?:2[0-4]\d)|(?:\d{1,2}))\b))|
                        (?:::(?:[0-9A-Fa-f]{1,4}:){0,5}(?:(?:\b(?:(?:25[0-5])|
                        (?:1\d{2})|(?:2[0-4]\d)|(?:\d{1,2}))\b)\.){3}(?:\b(?:(?:25[0-5])|
                        (?:1\d{2})|(?:2[0-4]\d)|(?:\d{1,2}))\b))|(?:[0-9A-Fa-f]{1,4}::(?:[0-9A-Fa-f]{1,4}:){0,5}[0-9A-Fa-f]{1,4})|
                        (?:::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4})|(?:(?:[0-9A-Fa-f]{1,4}:){1,7}:)))\]|
                        ((?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|
                        ((?:(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*(?:[A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])))
                        (?::(\d+))?$
                        ''', re.VERBOSE)

class InvalidURI(Exception):
    """Raised when URI is not valid."""

class FragmentNotAllowed(Exception):
    """Raised when URI contains fragment marker."""

def parseURI(uri_string):
    """
    Parse an URI into five components and set appropriate
    options.
    """
    #TODO: Don't know why Twisted Web forbids unicode strings - check that
    #if isinstance(uri_string, unicode):
    #    raise TypeError("uri must be str, not unicode")
    scheme, netloc, path, query, fragment = urlsplit(uri_string)
    if isinstance(scheme, unicode):
        scheme = scheme.encode('ascii')
        netloc = netloc.encode('ascii')
        path = path.encode('ascii')

    p_list = path.split("?")
    if len(p_list) > 0:
        path = p_list[0]
    if len(p_list) > 1:
        query = p_list[1]
    if len(p_list) > 2:
        return defer.fail(InvalidURI())
    if "#" in path or "#" in query:
        return defer.fail(FragmentNotAllowed())
    match = NETLOC_RE.match(netloc)
    if match:
        if match.group(5):
            port = int(match.group(5))
        else:
            port = coap.COAP_PORT
        if match.group(2):
            host = match.group(2)
            return defer.succeed(iter([(scheme, host, port, path, query)]))
        elif match.group(3):
            host = "::ffff:"+match.group(3)
            return defer.succeed(iter([(scheme, host, port, path, query)]))
        elif match.group(4):
            d = threads.deferToThread(socket.getaddrinfo, match.group(4), port, 0, socket.SOCK_DGRAM)
            d.addCallback(process_name, (scheme, port, path, query))
            return d
    return defer.fail(InvalidURI())

def process_name(gaiResult, netloc_fragments):
    scheme, port, path, query = netloc_fragments
    for family, socktype, proto, canonname, sockaddr in gaiResult:
        if family in [socket.AF_INET6]:
            yield (scheme, sockaddr[0],port, path, query)
    for family, socktype, proto, canonname, sockaddr in gaiResult:
        if family in [socket.AF_INET]:
            yield (scheme, "::ffff:"+sockaddr[0], port, path, query)







class RGBW_Led_Widget (BoxLayout) :
    red             = ObjectProperty (None)
    green           = ObjectProperty (None)
    blue            = ObjectProperty (None)
    #white           = ObjectProperty (None)
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
        self.remote_ip = self.config.get ("OSD_RGBW_Led_App", "IP")
        self.send_coap = True
        self.dont_change = False
        self.need_to_set_leds = None

        endpoint = resource.Endpoint(None)
        self.protocol = coap.Coap(endpoint)
        reactor.listenUDP(0, self.protocol, interface="::0")

        self.turned_off = False
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

        self.root.status.text = "fetching current color ..."
        self.prepare_request (method = coap.GET)

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
        if self.dont_change :
            print "color_changed: dont change"
            return
        else :
            print "color_changed", args, kws

        red   = self.root.red.value
        green = self.root.green.value
        blue  = self.root.blue.value
#        white = self.root.white.value
        bri   = self.root.brightness.value_normalized

        red   = int (red   * bri)
        green = int (green * bri)
        blue  = int (blue  * bri)
#        white = int (white * bri)

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
            self.set_leds (red, green, blue)#, white)

        if not self.root.switch.active :
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
            print self.COLORS,type (self.COLORS)
            [r,g,b,w,bri]         = self.COLORS [number]

            self.dont_change = True
            self.root.red.value   = r
            self.root.green.value = g
            self.root.blue.value  = b
#            self.root.white.value = w
            self.root.brightness.value = bri
            self.dont_change = False

            self.color_changed ()

        else :
            # store currently selected color
            color = \
                [ self.root.red.value
                , self.root.green.value
                , self.root.blue.value
                , 0 #self.root.white.value
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

    def set_leds (self, red, green, blue, white = 0) :
        if self.send_coap :
            self.send_coap = False
            print "set_leds"
            self.root.status.text = "set_leds to %d, %d, %d" % (red, green, blue)
            self.prepare_request \
                ( method = coap.PUT
                , payload = "r=%d&g=%d&b=%d" % (red, green, blue)
                )
            self.need_to_set_leds = None
        else :
            self.root.status.text = "too fast"
            print "remember to send the following", red, green, blue
            self.need_to_set_leds = (red, green, blue)
    # end def set_leds

    def prepare_request(self, **args):
        method = args.get ("method")
        request = coap.Message (code = method)
        if method == coap.PUT :
            payload = args.get ("payload")
            payload = payload.encode('utf-8')
            request.payload = payload

        self.remote_ip = self.config.get ("OSD_RGBW_Led_App", "IP")
        uri = "coap://[" + self.remote_ip + "]/" + PATH
        print "uri =", uri
        d = parseURI(uri)
        print "d %r" % d
        d.addCallback(self.send_request, request)
        d.addCallback(self.process_response)
        d.addErrback(self.print_error)
        self.deferred = d

    def send_request(self, result, request):

        def block1_callback(response, deferred):
            if response.code is coap.CONTINUE:
                for d in pending:
                    if d is not deferred:
                        d.cancel()
                    if lc.running:
                        lc.stop()
            return defer.succeed(True)

        def block2_callback(response, deferred):
            if response.code is coap.CONTENT:
                for d in pending:
                    if d is not deferred:
                        d.cancel()
                    if lc.running:
                        lc.stop()
            return defer.succeed(True)

        def remove_from_pending(response, deferred):
            pending.remove(deferred)
            return response

        def set_winner(response):
            if lc.running:
                lc.stop()

            successful.append(True)
            for d in pending:
                d.cancel()
            winner.callback(response)
            return None

        def check_done():
            if dns_result_list_exhausted and not pending and not successful:
                winner.errback(failures.pop())

        def request_failed(reason):
            failures.append(reason)
            check_done()
            return None

        def cancel_request(d):
            for d in pending:
                d.cancel()

        def iterate_requests():
            try:
                scheme, host, port, path, query = next(result)
            except StopIteration:
                lc.stop()
                dns_result_list_exhausted.append(True)
                check_done()
            else:
                print "iterate_requests: Request to %s" % host
                print scheme, port, path, query
                print request.code, request.payload
                request_copy = copy.deepcopy(request)
                if scheme != "coap":
                    print 'Error: URI scheme should be "coap"'
                request_copy.remote = (ip_address (host), port)
                if path != "" and path != "/":
                    path = path.lstrip("/")
                    request_copy.opt.uri_path = path.split("/")
                if query != "":
                    request_copy.opt.uri_query = query.split("&")
                d = None
                d = self.protocol.request \
                    ( request_copy
                    , self.observe_callback
                    , block1_callback
                    , block2_callback
                    , observeCallbackArgs=[]
                    , block1CallbackArgs=[d]
                    , block2CallbackArgs=[d]
                    )
                pending.append(d)
                d.addBoth(remove_from_pending, d)
                d.addCallback(set_winner)
                d.addErrback(request_failed)

        pending = []
        dns_result_list_exhausted = []
        successful = []
        failures = []
        winner = defer.Deferred(canceller=cancel_request)
        lc = task.LoopingCall(iterate_requests)
        lc.start(0.3)
        return winner

    def process_response(self, response):
        print '[b]Code:[/b] ' + coap.responses[response.code]
        print "[b]Type:[/b] " + coap.types[response.mtype]
        print "[b]ID:[/b] " + hex(response.mid)
        print "[b]Token:[/b] 0x" + response.token.encode('hex')
        formatted_options = "[b]Options:[/b]"
        for option in response.opt.optionList():
            formatted_options += "\n- "
            if option.number in coap.options:
                formatted_options += coap.options[option.number]
            else:
                formatted_options += "Unknown"
            formatted_options += " (" + str(option.number) + ")"
            if option.value is not None:
                formatted_options += " : " + str(option.value)
        print formatted_options
        print '[b]Response:[/b] ' + response.payload

        if response.payload :
            # can only be one here as we only set/get a/rgb
            try :
                if response.payload :
                    res = {}
                    rgb = response.payload.split ("&")
                    res ["r"] = int (rgb [0] [2:])
                    res ["g"] = int (rgb [1] [2:])
                    res ["b"] = int (rgb [2] [2:])
                else :
                    res = None
                #res = json.loads ("{"+response.payload.replace+"}")
            except :
                import traceback
                traceback.print_exc ()
                res = None

            if res :
                self.dont_change = True
                self.root.red.value   = res ["r"]
                self.root.green.value = res ["g"]
                self.root.blue.value  = res ["b"]
                #self.root.white.value = 0
                self.root.brightness.value = 255
                self.dont_change = False

                self.color_changed ()

        self.send_coap = True

        if self.need_to_set_leds :
            self.set_leds (*self.need_to_set_leds)


    def observe_callback(self, response):
        self.process_response(response)

    def print_error(self, failure):
        r = failure.trap \
            ( InvalidURI
            , FragmentNotAllowed
            , socket.gaierror
            , socket.error
            , defer.CancelledError
            , txthings.error.RequestTimedOut
            )
        if r == InvalidURI:
            msg = "Error: invalid URI"
        elif r == FragmentNotAllowed:
            msg = "Error: fragment found"
        elif r == socket.gaierror or r == socket.error:
            msg = "Error: hostname not found"
        elif r == txthings.error.RequestTimedOut :
            msg = "Error: request timeout"

        log.msg (msg)
        self.root.status.text = msg

        self.send_coap = True

# end class OSD_Led_App

if __name__ in ("__android__", "__main__") :
    log.startLogging(sys.stdout)
    OSD_Led_App ().run ()

### __END__ osd-led-app/main
