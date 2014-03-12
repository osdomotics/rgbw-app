import sys
import getopt
import coapy.connection
import time
import socket

verbose = False

def wait_for_response (ep, txr, endless = True):
    global verbose

    while True:
        rxr = ep.process(500)
        if rxr is None:
            if not endless :
                print "No message received; quit"
                break
            print 'No message received; waiting'
            continue
        if verbose:
            print rxr.message
            print "\n".join(['  %s' % (str(_o),) for _o in rxr.message.options])
            print '  %s' % (rxr.message.payload,)
        if rxr.pertains_to != txr:
            print 'Irrelevant; waiting'
            continue
        return rxr.message

def getResource (ep, uri_path, remote):
    msg = coapy.connection.Message(code=coapy.GET, uri_path=uri_path)
    resp = wait_for_response(ep, ep.send(msg, remote))
    return resp.payload

def putResource (ep, uri_path, remote, value, endless = True):
    msg = coapy.connection.Message(code=coapy.PUT, payload=value, uri_path=uri_path)
    resp = wait_for_response(ep, ep.send(msg, remote), endless)
    if resp :
        return resp.payload
    else :
        return None

if __name__ == "__main__" :
    uri_path = 'sink'
    host = 'ns.tzi.org'
    port = 61616
    verbose = False
    address_family = socket.AF_INET

    try:
        opts, args = getopt.getopt \
           ( sys.argv[1:]
           , 'u:h:p:v46'
           , [ 'uri-path='
             , 'host='
             , 'port='
             , 'verbose'
             , '--ipv4'
             , '--ipv6'
             ]
           )
        for (o, a) in opts:
            if o in ('-u', '--uri-path'):
                uri_path = a
            elif o in ('-h', '--host'):
                host = a
            elif o in ('-p', '--port'):
                port = int(a)
            elif o in ('-v', '--verbose'):
                verbose = True
            elif o in ('-4', '--ipv4'):
                address_family = socket.AF_INET
            elif o in ('-6', '--ipv6'):
                address_family = socket.AF_INET6

    except getopt.GetoptError, e:
        print 'Option error: %s' % (e,)
        sys.exit(1)

    if socket.AF_INET == address_family:
        remote = (host, port)
    elif socket.AF_INET6 == address_family:
        remote = (host, port, 0, 0)

    ep = coapy.connection.EndPoint(address_family = address_family)
    ep.socket.bind(('', coapy.COAP_PORT))

    data = getResource(ep, uri_path, remote)
    print 'Initial setting: %s' % (data,)
    print "put value: %r" % args [0]
    resp = putResource(ep, uri_path, remote, args[0])
    print 'Put returned: %s' % (resp,)
    data = getResource(ep, uri_path, remote)
    print 'Get returned: %s' % (data,)
