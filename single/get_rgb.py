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
#    get_rgb
#
# Purpose
#    get rgb values from single rgb actor
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

import json

class Client (object):
    def __init__ (self, protocol) :
        self.protocol = protocol
        reactor.callLater (0, self.get_rgb)
    # end def __init__

    def get_rgb (self) :
        request = coap.Message (code = coap.GET)
        request.opt.uri_path = ["a", "rgb_leds"]
        request.remote = \
            (ip_address ("aaaa::221:2eff:ff00:26e7"), coap.COAP_PORT)
        d = protocol.request (request)
        d.addCallback (self.print_rgb_values)
        d.addErrback (self.print_error)
    # end def get_rgb

    def print_rgb_values (self, response) :
        res = response.payload.split ("&")
        print "red:  ", res [0] [2:]
        print "green:", res [1] [2:]
        print "blue: ", res [2] [2:]
        reactor.stop ()
    # end def print_rgb_values

    def print_error (self, error) :
        print error
        reactor.stop ()
    # end def print_error
# end class Client

log.startLogging (sys.stdout)

endpoint = resource.Endpoint (None)
protocol = coap.Coap         (endpoint)
client   = Client            (protocol)

reactor.listenUDP (61616, protocol, interface = "::0")
reactor.run ()

### __END__ get_rgb


