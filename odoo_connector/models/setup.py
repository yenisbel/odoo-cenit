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


class CenitConnection (models.Model):
    _name = 'cenit.connection'

    name = fields.Char('Name', required=True)
    url = fields.Char('URL', required=True)

    key = fields.Char('Key', readonly=True)
    token = fields.Char('Token', readonly=True)

    url_parameters = fields.One2many(
        'cenit.parameter',
        'conn_url_id',
        string='Parameters'
    )
    header_parameters = fields.One2many(
        'cenit.parameter',
        'conn_header_id',
        string='Header Parameters'
    )
    template_parameters = fields.One2many(
        'cenit.parameter',
        'conn_template_id',
        string='Template Parameters'
    )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'The name must be unique!'),
    ]


class CenitConnectionRole (models.Model):
    _name = 'cenit.connection.role'

    name = fields.Char('Name', required=True)

    connections = fields.Many2many(
        'cenit.connection',
        string='Connections'
    )

    webhooks = fields.Many2many(
        'cenit.webhook',
        string='Webhooks'
    )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'The name must be unique!'),
    ]


class CenitParameter (models.Model):
    _name = 'cenit.parameter'

    key = fields.Char('Key', required=True)
    value = fields.Char('Value', required=True)

    conn_url_id = fields.Many2one(
        'cenit.connection',
        string='Connection'
    )

    conn_header_id = fields.Many2one(
        'cenit.connection',
        string='Connection'
    )

    conn_template_id = fields.Many2one(
        'cenit.connection',
        string='Connection'
    )

    hook_url_id = fields.Many2one(
        'cenit.webhook',
        string='Webhook'
    )

    hook_header_id = fields.Many2one(
        'cenit.webhook',
        string='Webhook'
    )

    hook_template_id = fields.Many2one(
        'cenit.webhook',
        string='Webhook'
    )


class CenitWebhook (models.Model):

    @api.depends('method')
    def _compute_purpose(self):
        self.purpose = {
            'get': 'send'
        }.get(self.method, 'receive')

    _name = 'cenit.webhook'

    name = fields.Char('Name', required=True)
    path = fields.Char('Path', required=True)
    purpose = fields.Char(compute='_compute_purpose', store=True)
    method = fields.Selection(
        [
            ('get', 'HTTP GET'),
            ('put', 'HTTP PUT'),
            ('post', 'HTTP POST'),
            ('delete', 'HTTP DELETE'),
        ],
        'Method', default='post', required=True
    )

    url_parameters = fields.One2many(
        'cenit.parameter',
        'hook_url_id',
        string='Parameters'
    )
    header_parameters = fields.One2many(
        'cenit.parameter',
        'hook_header_id',
        string='Header Parameters'
    )
    template_parameters = fields.One2many(
        'cenit.parameter',
        'hook_template_id',
        string='Template Parameters'
    )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'The name must be unique!'),
    ]


class CenitEvent (models.Model):
    _name = "cenit.event"

    name = fields.Char('Name', required=True, unique=True)
    type_ = fields.Selection(
        [
            ('on_create', 'On Create'),
            ('on_write', 'On Update'),
            ('on_create_or_update', 'On Create or Update'),
            ('interval', 'Interval'),
            ('only_manual', 'Only Manual'),
        ],
        string="Type"
    )
    schema = fields.Many2one(
        'cenit.schema',
        string = 'Schema'
    )


class CenitFlow (models.Model):
    _name = "cenit.flow"

    name = fields.Char('Name', size=64, required=True, unique=True)
    event = fields.Many2one("cenit.event", string='Event')

    cron = fields.Many2one('ir.cron', string='Cron rules')
    base_action_rules = fields.Many2many(
        'base.action.rule', string='Action Rule'
    )

    format_ = fields.Selection(
        [
            ('application/json', 'JSON'),
            ('application/EDI-X12', 'EDI')
        ],
        'Format', default='application/json', required=True
    )

    schema = fields.Many2one(
        'cenit.schema', 'Schema', required=True
    )
    data_type = fields.Many2one(
        'cenit.data_type', string='Source data type'
    )

    webhook = fields.Many2one(
        'cenit.webhook', string='Webhook'
    )
    connection_role = fields.Many2one(
        'cenit.connection.role', string='Connection role'
    )

    method = fields.Selection(related="webhook.method")

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'The name must be unique!'),
    ]

    @api.onchange('webhook')
    def on_webhook_changed(self):
        return {
            'value': {
                'connection_role': ""
            },
            "domain": {
                "connection_role": [
                    ('webhooks', 'in', self.webhook.id)
                ]
            }
        }

    @api.onchange('schema')
    def on_schema_changed(self):
        return {
            'value': {
                'data_type': "",
                'event': "",
            },
            "domain": {
                "data_type": [
                    ('schema', '=', self.schema.id)
                ],
                'event': [
                    ('schema', 'in', [self.schema.id, False])
                ],
            }
        }

    @api.one
    def _get_direction (self):
        my_url = self.env['ir.config_parameter'].get_param(
            'web.base.url', default=''
        )

        conn = self.connection_role.connections and \
            self.connection_role.connections[0]
        my_conn = conn.url == my_url

        return {
            ('get', True): 'send',
            ('put', False): 'send',
            ('post', False): 'send',
            ('delete', False): 'send',
        }.get((self.webhook.method, my_conn), 'receive')

    @api.model
    def create(self, vals):
        local = (vals.get('cenitID', False) == False) or \
                (self.env.context.get('local'), False)
        obj = super(CenitFlow, self).create(vals)
        if not local:
            purpose = obj._get_direction()[0]
            method = 'set_%s_execution' % (purpose, )
            getattr(obj, method)()
        return obj

    @api.one
    def write(self, vals):
        prev_purpose = self._get_direction()[0]
        prev_sch = self.schema
        prev_dt = self.data_type
        res = super(CenitFlow, self).write(vals)
        new_purpose = self._get_direction()[0]
        if ((new_purpose != prev_purpose) or \
             (vals.get('event', False)) or \
             (prev_sch != self.schema) or \
             (prev_dt != self.data_type)):
            method = 'set_%s_execution' % new_purpose
            getattr(self, method)()
        return res

    @api.one
    def unlink(self):
        if self.base_action_rules:
            self.base_action_rules.unlink()
        if self.cron:
            self.cron.unlink()
        return super(CenitFlow, self).unlink()

    @api.model
    def find(self, model, purpose):
        domain = [('data_type.cenit_root', '=', model)]
        objs = self.search(domain)
        return objs and objs[0] or False

    @api.one
    def set_receive_execution(self):
        pass

    @api.model
    def receive(self, model, data):
        res = False
        context = self.env.context.copy() or {}
        obj = self.find(model.lower(), 'receive')
        if obj:
            klass = self.env[obj.data_type.model.model]
            if obj.format_ == 'application/json':
                action = context.get('action', 'push')
                wh = self.env['cenit.handler']
                context.update({'receive_object': True})
                action = getattr(wh, action, False)
                if action:
                    root = obj.data_type.cenit_root
                    res = action (data, root)
            elif obj.format_ == 'application/EDI-X12':
                for edi_document in data:
                    klass.edi_import(edi_document)
                res = True
        return res

    @api.one
    def set_send_execution(self):
        if self.data_type:
            dts = [self.data_type]
        else:
            dt_pool = self.env['cenit.data_type']
            domain = [('schema', '=', self.schema.id)]
            dts = dt_pool.search(domain)

        execution = {
            'only_manual': 'only_manual',
            'interval': 'interval',
            'on_create': 'on_create',
            'on_write': 'on_write'
        }.get(self.event.type_, 'on_create_or_write')

        if execution == 'only_manual':

            if self.base_action_rules:
                self.base_action_rules.unlink()

            elif self.cron:
                self.cron.unlink()

        if execution == 'interval':
            ic_obj = self.env['ir.cron']
            for data_type in dts:
                if self.cron:
                    _logger.info ("\n\nCronID\n")
                else:
                    vals_ic = {
                        'name': 'send_all_%s' % data_type.model.model,
                        'interval_number': 10,
                        'interval_type': 'minutes',
                        'numbercall': -1,
                        'model': 'cenit.flow',
                        'function': 'send_all',
                        'args': '(%s)' % str(self.id)
                    }
                    ic = ic_obj.create(vals_ic)
                    self.with_context(local=True).write({'cron': ic.id})
            if self.base_action_rules:
                self.base_action_rules.unlink()

        elif execution in ('on_create', 'on_write', 'on_create_or_write'):
            ias_obj = self.env['ir.actions.server']
            bar_obj = self.env['base.action.rule']

            if self.base_action_rules:
                for bar in self.base_action_rules:
                    bar.server_action_ids.unlink()
                self.base_action_rules.unlink()

            rules = []
            for data_type in dts:
                cd = "self.pool.get('cenit.flow').send(cr, uid, obj, %s)" % (
                    self.id,
                )
                vals_ias = {
                    'name': 'send_one_%s_as_%s' % (
                        data_type.model.model, self.schema.uri
                    ),
                    'model_id': data_type.model.id,
                    'state': 'code',
                    'code': cd
                }
                ias = ias_obj.create(vals_ias)
                vals_bar = {
                    'name': 'send_one_%s_as_%s' % (
                        data_type.model.model, self.schema.uri
                    ),
                    'active': True,
                    'kind': execution,
                    'model_id': data_type.model.id,
                    'server_action_ids': [(6, False, [ias.id])]
                }
                bar = bar_obj.create(vals_bar)
                rules.append((4, bar.id, False))

            self.with_context(local=True).write(
                {'base_action_rules': rules}
            )

            if self.cron:
                self.cron.unlink()
        _logger.info("\n\n[FINALLY] BAR: %s\n", self.base_action_rules)
        return True

    @api.model
    def send(self, obj, flow_id):
        dt_pool = self.env['cenit.data_type']
        ws = self.env['cenit.serializer']

        flow = self.browse(flow_id)

        if flow:
            data = None

            if flow.format_ == 'application/json':

                data_types = [flow.data_type]
                if not data_types[0]:
                    domain = [('schema', '=', flow.schema.id)]
                    data_types = dt_pool.search(domain)
                    if not data_types:
                        return False

                data = [ws.serialize(obj, dt) for dt in data_types]

            elif flow.format_ == 'application/EDI-X12':
                data = self.env[obj._name].edi_export([obj])

            return flow._send(data)

        return False

    @api.model
    def send_all(self, id_):
        flow = self.browse(id_)
        mo = self.env[flow.data_type.model.model]
        if mo:
            data = []
            objs = mo.search([])
            if flow.format_ == 'application/json':
                ws = self.env['cenit.serializer']
                for x in objs:
                    data.append(ws.serialize(x, flow.data_type))
            elif flow.format_ == 'application/EDI-X12' and \
                 hasattr(mo, 'edi_export'):
                data = mo.edi_export(objs)
            if data:
                return flow._send(data)
        return False

    @api.one
    def _send(self, data):
        method = "http_post"
        return getattr(self, method)(data)

    @api.one
    def http_post(self, data):
        path = "/push"
        root = self.schema.cenit_root()
        if isinstance(root, list):
            root = root[0]
        values = {root: data}
        rc = False
        try:
            rc = self.post(path, values)
        except Warning as e:
            _logger.exception(e)
        return rc
