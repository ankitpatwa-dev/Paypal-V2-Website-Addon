# coding: utf-8

import json
import logging

import dateutil.parser
import pytz
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class AcquirerPaypal(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paypal_v2', 'Paypal V2')])
    paypal_client_id = fields.Char('Paypal Client ID', required_if_provider='paypal_v2', groups='base.group_user')
    paypal_client_secret_id = fields.Char(
        'Paypal Client Secret ID', required_if_provider='paypal_v2', groups='base.group_user')

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerPaypal, self)._get_feature_support()
        res['fees'].append('paypal')
        return res

    @api.model
    def _get_paypal_v2_urls(self, environment):
        """ Paypal URLS """
        if environment == 'prod':
            return 'https://api-m.paypal.com'
        else:
            return 'https://api-m.sandbox.paypal.com'



    @api.multi
    def paypal_v2_form_generate_values(self, values):
        base_url = self.get_base_url()

        paypal_tx_values = dict(values)
        paypal_tx_values.update({
            'cmd': '_xclick',
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').code or '',
            'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'paypal_client_id':self.paypal_client_id
        })
        return paypal_tx_values

    @api.multi
    def paypal_get_form_action_url(self):
        return self._get_paypal_v2_api_urls(self.environment)['paypal_form_url']

    @api.model
    def _get_paypal_v2_api_urls(self, environment):
        """ Paypal URLS """
        if environment == 'prod':
            return {
                'paypal_form_url': 'https://www.paypal.com/cgi-bin/webscr',
                'paypal_rest_url': 'https://api.paypal.com/v1/oauth2/token',
            }
        else:
            return {
                'paypal_form_url': 'https://www.sandbox.paypal.com/cgi-bin/webscr',
                'paypal_rest_url': 'https://api.sandbox.paypal.com/v1/oauth2/token',
            }


class TxPaypal(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _paypal_v2_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('item_number'), data.get('id')
        if not reference or not txn_id:
            error_msg = _('Paypal: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.multi
    def _paypal_v2_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        _logger.info('Received a notification from Paypal with IPN version %s', data.get('notify_version'))
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Paypal using sandbox'
            ),

        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('id') != self.acquirer_reference:
            invalid_parameters.append(('id', data.get('id'), self.acquirer_reference))
        if self.payment_token_id and data.get('payer_id') != self.payment_token_id.acquirer_ref:
            invalid_parameters.append(('payer_id', data.get('payer_id'), self.payment_token_id.acquirer_ref))
        # check seller
        if data.get('receiver_id') and self.acquirer_id.paypal_seller_account and data['receiver_id'] != self.acquirer_id.paypal_seller_account:
            invalid_parameters.append(('receiver_id', data.get('receiver_id'), self.acquirer_id.paypal_seller_account))

        return invalid_parameters

    @api.multi
    def _paypal_v2_form_validate(self, data):
        status = data.get('status')
        transaction_status = {
            'COMPLETED': {
                'state': 'done',
                'acquirer_reference': data.get('id'),
                'date_validate': fields.Datetime.now(),
            },
            'authorized': {
                'state': 'authorized',
                'acquirer_reference': data.get('id'),
                'date_validate': fields.Datetime.now(),
            },
            'error': {
                'state': 'error',
                'acquirer_reference': data.get('id'),
                'date_validate': fields.Datetime.now(),
            },
        }
        vals = transaction_status.get(status, False)
        if not vals:
            vals = transaction_status['error']
            _logger.info(vals['state_message'])
        return self.write(vals)
