# -*- coding: utf-8 -*-

# Copyright (c) 2011-2015, Camptocamp SA
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPBadGateway, HTTPForbidden, \
    HTTPInternalServerError

import httplib2
from urlparse import urlparse
from json import dumps, loads

from c2cgeoportal.lib.filter_capabilities import get_protected_layers, \
    get_private_layers

import logging
log = logging.getLogger(__name__)


class PdfReport:  # pragma: no cover

    def __init__(self, request):
        self.request = request
        self.config = self.request.registry.settings.get('pdfreport', {})

    def do_print(self, spec):
        """ Get created PDF. """
        url = self.config['print_url'] + "/print/buildreport.pdf"
        http = httplib2.Http()
        h = dict(self.request.headers)
        h["Content-Type"] = "application/json"
        if urlparse(url).hostname != 'localhost':
            h.pop('Host')
        try:
            resp, content = http.request(
                url, method='POST', headers=h, body=dumps(spec)
            )
        except:
            return HTTPBadGateway()

        headers = {}
        if 'content-type' in resp:
            headers['content-type'] = resp['content-type']
        if 'content-disposition' in resp:
            headers['content-disposition'] = resp['content-disposition']
        return Response(
            content, status=resp.status, headers=headers
        )

    @view_config(route_name='pdfreport', renderer="json")
    def getreport(self):
        id = int(self.request.matchdict['id'])
        layername = self.request.matchdict['layername']
        featureid = layername + "." + str(id)

        # check user credentials
        role_id = None if self.request.user is None else \
            self.request.user.role.id

        # FIXME: support of mapserver groups
        if layername in get_private_layers() and \
                layername not in get_protected_layers(role_id):
            raise HTTPForbidden

        srs = self.config.get('srs')
        if srs is None:
            raise HTTPInternalServerError(
                'Missing "srs" in service configuration'
            )
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typeName': layername,
            'featureid': featureid,
            'srsName': srs
        }

        mapserv_url = self.request.route_url('mapserverproxy')
        vector_request_url = mapserv_url + "?" \
            + "&".join(["%s=%s" % i for i in params.items()])

        backgroundlayers = self.config.get("layers", {}). \
            get(layername, {}).get('backgroundlayers')
        if backgroundlayers is None:
            backgroundlayers = self.config.get('default_backgroundlayers', '""')

        imageformat = self.config.get("layers", {}). \
            get(layername, {}).get('imageformat')
        if imageformat is None:
            imageformat = self.config.get('default_imageformat', 'image/png')

        spec_template = self.config.get("spec_template")
        if spec_template is None:
            spec_template = {
                "layout": "%(layername)s",
                "outputFormat": "pdf",
                "attributes": {
                    "paramID": "%(id)d",
                    "map": {
                        "projection": "%(srs)s",
                        "dpi": 254,
                        "rotation": 0,
                        "bbox": [0, 0, 1000000, 1000000],
                        "zoomToFeatures": {
                            "zoomType": "center",
                            "layer": "vector",
                            "minScale": 25000
                        },
                        "layers": [{
                            "type": "gml",
                            "name": "vector",
                            "style": {
                                "version": "2",
                                "[1 > 0]": {
                                    "fillColor": "red",
                                    "fillOpacity": 0.2,
                                    "symbolizers": [{
                                        "strokeColor": "red",
                                        "strokeWidth": 1,
                                        "type": "point",
                                        "pointRadius": 10
                                    }]
                                }
                            },
                            "opacity": 1,
                            "url": "%(vector_request_url)s"
                        }, {
                            "baseURL": "%(mapserv_url)s",
                            "opacity": 1,
                            "type": "WMS",
                            "serverType": "mapserver",
                            "layers": ["%(backgroundlayers)s"],
                            "imageFormat": "%(imageformat)s"
                        }]
                    }
                }
            }
        spec = dumps(spec_template) % {
            'layername': layername, 'id': id, 'srs': srs,
            'mapserv_url': mapserv_url,
            'vector_request_url': vector_request_url,
            'imageformat': imageformat,
            'backgroundlayers': backgroundlayers
        }

        return self.do_print(loads(spec))
