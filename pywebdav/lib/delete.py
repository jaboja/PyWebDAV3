from __future__ import absolute_import

from .utils import make_xmlresponse


class DELETE:

    def __init__(self, url, dataclass):
        self.__dataclass = dataclass
        self.__url = url

    def delcol(self):
        """ delete a collection """

        dc = self.__dataclass
        result = dc.deltree(self.__url)

        if not len(list(result.items())):
            return None  # everything ok

        # create the result element
        return make_xmlresponse(result)

    def delone(self):
        """ delete a resource """

        dc = self.__dataclass
        return dc.delone(self.__url)
