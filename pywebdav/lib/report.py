from __future__ import absolute_import

from xml.dom import minidom

from .propfind import PROPFIND

domimpl = minidom.getDOMImplementation()

from .utils import get_parenturl


class REPORT(PROPFIND):

    def __init__(self, url, dataclass, depth, body):
        PROPFIND.__init__(self, url, dataclass, depth, body)

        doc = minidom.parseString(body)

        self.filter = doc.documentElement

    def create_propname(self):
        """ create a multistatus response for the prop names """

        dc = self._dataclass
        # create the document generator
        doc = domimpl.createDocument(None, "multistatus", None)
        ms = doc.documentElement
        ms.setAttribute("xmlns:D", "DAV:")
        ms.tagName = 'D:multistatus'

        if self._depth == "0":
            if self._url in self._dataclass.get_childs(get_parenturl(self._url),
                                                       self.filter):
                pnames = dc.get_propnames(self._url)
                re = self.mk_propname_response(self._url, pnames, doc)
                ms.appendChild(re)

        elif self._depth == "1":
            if self._url in self._dataclass.get_childs(get_parenturl(self._url),
                                                       self.filter):
                pnames = dc.get_propnames(self._url)
                re = self.mk_propname_response(self._url, pnames, doc)
                ms.appendChild(re)

            for newurl in dc.get_childs(self._url, self.filter):
                pnames = dc.get_propnames(newurl)
                re = self.mk_propname_response(newurl, pnames, doc)
                ms.appendChild(re)
        elif self._depth == 'infinity':
            url_list = [self._url]
            while url_list:
                url = url_list.pop()
                if url in self._dataclass.get_childs(get_parenturl(url),
                                                     self.filter):
                    pnames = dc.get_propnames(url)
                    re = self.mk_propname_response(url, pnames, doc)
                    ms.appendChild(re)
                url_childs = self._dataclass.get_childs(url)
                if url_childs:
                    url_list.extend(url_childs)

        return doc.toxml(encoding="utf-8") + b"\n"

    def create_prop(self):
        """ handle a <prop> request

        This will

        1. set up the <multistatus>-Framework

        2. read the property values for each URI 
           (which is dependant on the Depth header)
           This is done by the get_propvalues() method.

        3. For each URI call the append_result() method
           to append the actual <result>-Tag to the result
           document.

        We differ between "good" properties, which have been
        assigned a value by the interface class and "bad" 
        properties, which resulted in an error, either 404
        (Not Found) or 403 (Forbidden).

        """

        # create the document generator
        doc = domimpl.createDocument(None, "multistatus", None)
        ms = doc.documentElement
        ms.setAttribute("xmlns:D", "DAV:")
        ms.tagName = 'D:multistatus'

        if self._depth == "0":
            if self._url in self._dataclass.get_childs(get_parenturl(self._url),
                                                       self.filter):
                gp, bp = self.get_propvalues(self._url)
                res = self.mk_prop_response(self._url, gp, bp, doc)
                ms.appendChild(res)

        elif self._depth == "1":
            if self._url in self._dataclass.get_childs(get_parenturl(self._url),
                                                       self.filter):
                gp, bp = self.get_propvalues(self._url)
                res = self.mk_prop_response(self._url, gp, bp, doc)
                ms.appendChild(res)

            for newurl in self._dataclass.get_childs(self._url, self.filter):
                gp, bp = self.get_propvalues(newurl)
                res = self.mk_prop_response(newurl, gp, bp, doc)
                ms.appendChild(res)
        elif self._depth == 'infinity':
            url_list = [self._url]
            while url_list:
                url = url_list.pop()
                if url in self._dataclass.get_childs(get_parenturl(url),
                                                     self.filter):
                    gp, bp = self.get_propvalues(url)
                    res = self.mk_prop_response(url, gp, bp, doc)
                    ms.appendChild(res)
                url_childs = self._dataclass.get_childs(url)
                if url_childs:
                    url_list.extend(url_childs)

        return doc.toxml(encoding="utf-8") + b"\n"
