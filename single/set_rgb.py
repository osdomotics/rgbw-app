# -*- coding: iso-8859-1 -*-
# Copyright (C) 2015-2017 Marcus Priesch, All rights reserved
# In Prandnern 31, A--2122 Riedenthal, Austria. office@priesch.co.at
# ****************************************************************************
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# ****************************************************************************
#
#++
# Name
#    set_rgb
#
# Purpose
#    set rgb values from single rgb actor
#
# Revision Dates
#    25-Jun-2015 (MPR) Creation
#    ««revision-date»»···
#--
import sys

from twisted.internet.defer import Deferred
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import log

import txthings.coap as coap
import txthings.resource as resource
from ipaddress import ip_address

import json, time

class Client (object):
    def __init__ (self, protocol, rgb) :
        self.protocol = protocol
        self.rgb      = rgb
        reactor.callLater (0, self.set_rgb)
    # end def __init_

    def set_rgb (self, rgb = None) :
        print "set_rgb"
        if rgb is None :
            rgb = self.rgb
        request = coap.Message (code = coap.PUT)
        request.opt.uri_path = ["a", "rgb_leds"]
        request.remote = (ip_address("aaaa::221:2eff:ff00:26e7"), coap.COAP_PORT)
        request.payload = "r=%(r)d&g=%(g)d&b=%(b)d" % rgb
        d = protocol.request (request)
        d.addCallback (self.finished)
        d.addErrback (self.print_error)
    # end def set_rgb

    def finished (self, response) :
        print "finished %r" % response.payload
        reactor.stop ()
    # end def finished

    def print_error (self, error) :
        print "print_error", error
        reactor.stop ()
    # end def print_error
# end class Client

log.startLogging (sys.stdout)

if len (sys.argv) == 4 :
    rgb = dict \
        ( r = int (sys.argv [1])
        , g = int (sys.argv [2])
        , b = int (sys.argv [3])
        )
else :
    rgb = dict (r = 100, g = 100, b = 100)

endpoint = resource.Endpoint (None)
protocol = coap.Coap         (endpoint)
client   = Client            (protocol, rgb)

reactor.listenUDP (61616, protocol, interface = "::0")
reactor.run ()

### __END__ set_rgb
