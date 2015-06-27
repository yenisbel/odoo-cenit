#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  connection.py
#
#  Copyright 2015 D.H. Bahr <dhbahr@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import logging
import simplejson

from openerp import models, fields, api

from datetime import datetime


_logger = logging.getLogger(__name__)


def post (self, url, vals, headers):
    payload = simplejson.dumps(vals)

    r = requests.post(url, data=payload, headers=headers)
    if 200 <= r.status_code < 300:
        return simplejson.loads(r.content)

    _logger.exception(simplejson.loads(r.content))
    raise Warning('Error trying to push to Odoo.')


class CenitFlow (models.Model):
    _inherit = "cenit.flow"

    @api.one
    def _send(self, data):
        method = "http_post"
        if self.env.context.get('send_method'):
            method = self.env.context['send_method']
        return getattr(self, method)(data)

    @api.one
    def local_post(self, data):
        # TODO: get partner_data from partner
        partner_data = context.get('partner_data')
        
        root = self.schema.cenit_root()
        if isinstance(root, list):
            root = root[0]

        rc = False
        try:
            url = '%s/push' % partner_data['host']
            values = {root: data}
            headers = {
                'HTTP_X_HUB_STORE': partner_data['key'],
                'HTTP_X_HUB_ACCESS_TOKEN': partner_data['token'],
                'HTTP_TENANT_DB': partner_data['db']
            }
            rc = post(url, values, headers)
        except Warning as e:
            _logger.exception(e)

        return rc
