from __future__ import absolute_import

import os
import re
import time
from xml.dom import minidom

from six.moves import urllib
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler

from .constants import RT_ALLPROP, RT_PROPNAME, RT_PROP


def gen_estring(ecode):
    """ generate an error string from the given code """
    ec = int(ecode)
    if ec in BaseHTTPRequestHandler.responses:
        return "HTTP/1.1 %s %s" % (ec, BaseHTTPRequestHandler.responses[ec][0])
    else:
        return "HTTP/1.1 %s" % ec


def parse_propfind(xml_doc):
    """
    Parse a propfind xml file and return a list of props
    """

    doc = minidom.parseString(xml_doc)

    request_type = None
    props = {}
    namespaces = []

    if doc.getElementsByTagNameNS("DAV:", "allprop"):
        request_type = RT_ALLPROP
    elif doc.getElementsByTagNameNS("DAV:", "propname"):
        request_type = RT_PROPNAME
    else:
        request_type = RT_PROP
        for i in doc.getElementsByTagNameNS("DAV:", "prop"):
            for e in i.childNodes:
                if e.nodeType != minidom.Node.ELEMENT_NODE:
                    continue
                ns = e.namespaceURI
                ename = e.localName
                if ns in props:
                    props[ns].append(ename)
                else:
                    props[ns] = [ename]
                    namespaces.append(ns)

    return request_type, props, namespaces


def create_treelist(dataclass, url):
    """ create a list of resources out of a tree

    This function is used for the COPY, MOVE and DELETE methods

    url - the root of the subtree to flatten

    It will return the flattened tree as list

    """
    queue = [url]
    treelist = [url]
    while len(queue):
        element = queue[-1]
        if dataclass.is_collection(element):
            childs = dataclass.get_childs(element)
        else:
            childs = []
        if len(childs):
            treelist = treelist + childs
        # update queue
        del queue[-1]
        if len(childs):
            queue = queue + childs
    return treelist


def is_prefix(url1, url2):
    """ returns True if url1 is a prefix of url2 """
    path1 = urllib.parse.urlparse(url1).path
    path2 = urllib.parse.urlparse(url2).path
    return os.path.commonpath([path1, path2]) == path1


def quote_url(url):
    """ quote a URL but not the protocol part """
    up = urllib.parse.urlparse(url)
    np = urllib.parse.quote(up[2])
    return urllib.parse.urlunparse((up[0], up[1], np, up[3], up[4], up[5]))


def get_urlparentpath(url):
    """ extract the url path and remove the last element """
    up = urllib.parse.urlparse(url)
    return "/".join(up[2].split("/")[:-1])


def get_urlfilename(url):
    """ extract the url path and return the last element """
    up = urllib.parse.urlparse(url)
    return up[2].split("/")[-1]


def get_parenturl(url):
    """ return the parent of the given resource"""
    up = urllib.parse.urlparse(url)
    np = "/".join(up[2].split("/")[:-1])
    return urllib.parse.urlunparse((up[0], up[1], np, up[3], up[4], up[5]))


# XML utilities

def make_xmlresponse(result):
    """ construct a response from a dict of url:error_code elements """
    doc = minidom.getDOMImplementation().createDocument(None, "multistatus",
                                                        None)
    doc.documentElement.setAttribute("xmlns:D", "DAV:")
    doc.documentElement.tagName = "D:multistatus"

    for el, ec in result.items():
        response = doc.createElementNS("DAV:", "response")
        hr = doc.createElementNS("DAV:", "href")
        st = doc.createElementNS("DAV:", "status")
        hurl = doc.createTextNode(quote_url(el))
        t = doc.createTextNode(gen_estring(ec))
        st.appendChild(t)
        hr.appendChild(hurl)
        response.appendChild(hr)
        response.appendChild(st)
        doc.documentElement.appendChild(response)

    return doc.toxml(encoding="utf-8") + b"\n"


# taken from App.Common

weekday_abbr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
weekday_full = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def rfc1123_date(ts=None):
    # Return an RFC 1123 format date string, required for
    # use in HTTP Date headers per the HTTP 1.1 spec.
    # 'Fri, 10 Nov 2000 16:21:09 GMT'
    if ts is None:
        ts = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekday_abbr[wd],
                                                    day, monthname[month],
                                                    year,
                                                    hh, mm, ss)


def iso8601_date(ts=None):
    # Return an ISO 8601 formatted date string, required
    # for certain DAV properties.
    # '2000-11-10T16:21:09-08:00
    if ts is None:
        ts = time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))


def rfc850_date(ts=None):
    # Return an HTTP-date formatted date string.
    # 'Friday, 10-Nov-00 16:21:09 GMT'
    if ts is None:
        ts = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(ts)
    return "%s, %02d-%3s-%2s %02d:%02d:%02d GMT" % (
        weekday_full[wd],
        day, monthname[month],
        str(year)[2:],
        hh, mm, ss)


# If: header handling support.  IfParser returns a sequence of
# TagList objects in the order they were parsed which can then
# be used in WebDAV methods to decide whether an operation can
# proceed or to raise HTTP Error 412 (Precondition failed)
IfHdr = re.compile(
    r"(?P<resource><.+?>)?\s*\((?P<listitem>[^)]+)\)"
)

ListItem = re.compile(
    r"(?P<not>not)?\s*(?P<listitem><[a-zA-Z]+:[^>]*>|\[.*?\])",
    re.I)


class TagList:
    def __init__(self):
        self.resource = None
        self.list = []
        self.NOTTED = 0


def IfParser(hdr):
    out = []
    i = 0
    while 1:
        m = IfHdr.search(hdr[i:])
        if not m:
            break

        i = i + m.end()
        tag = TagList()
        tag.resource = m.group('resource')
        if tag.resource:  # We need to delete < >
            tag.resource = tag.resource[1:-1]
        listitem = m.group('listitem')
        tag.NOTTED, tag.list = ListParser(listitem)
        out.append(tag)

    return out


def tokenFinder(token):
    # takes a string like '<opaquelocktoken:afsdfadfadf> and returns the token
    # part.
    if not token:  # An empty string was passed in
        return None
    if token[0] == '[':  # An Etag was passed in
        return None
    if token[0] == '<':
        token = token[1:-1]
    return token[token.find(':') + 1:]


def ListParser(listitem):
    out = []
    notted = 0
    i = 0
    while 1:
        m = ListItem.search(listitem[i:])
        if not m:
            break

        i = i + m.end()
        out.append(m.group('listitem'))
        if m.group('not'):
            notted = 1

    return notted, out
