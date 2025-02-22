# -*- coding: utf-8 -*-

import json
import logging
import pprint
import base64
import requests
import werkzeug
from werkzeug import urls
import json
from odoo import http
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaypalV2Controller(http.Controller):
    _notify_url = '/payment/paypal/ipn/'
    _return_url = '/payment/paypal/dpn/'
    _cancel_url = '/payment/paypal/cancel/'



    def get_access_token(self,item_number=False):
        if item_number:
            res = {}
            payment_id = request.env['payment.transaction'].search([('reference','=',item_number)])
            acquirer_id = payment_id.acquirer_id
            endpoint_url = request.env['payment.acquirer']._get_paypal_v2_urls(acquirer_id.environment or 'prod')
            try:
                if acquirer_id:
                    auth = '{}:{}'.format(acquirer_id.paypal_client_id,acquirer_id.paypal_client_secret_id)
                    data = 'grant_type=client_credentials'
                    encoded_credentials = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
                    header = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'Basic {}'.format(encoded_credentials)
                    }
                    url = endpoint_url + '/v1/oauth2/token'
                    fetch_api = requests.post(url,data=data,headers=header)
                    print(fetch_api)
                    res = json.loads(fetch_api.text)
            except Exception as e:
                print(e)
                return False
            return res['access_token']


    @http.route('/create_order', type='json', auth='none', methods=['POST'], csrf=False)
    def paypal_create_order(self, **post):
        print('paypal_create_order',post)
        try:
            item_number = post.get('item_number')
            intent = post.get('intent')
            access_token = self.get_access_token(item_number)
            payment_id = request.env['payment.transaction'].search([('reference', '=', item_number)])
            acquirer_id = payment_id.acquirer_id
            endpoint_url = request.env['payment.acquirer']._get_paypal_v2_urls(acquirer_id.environment or 'prod')
            url = endpoint_url + '/v2/checkout/orders'
            header = {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer {}'.format(access_token)
                    }
            order_data_json = {
                'intent': intent.upper(),
                'purchase_units': [{
                    'amount': {
                        'currency_code': post.get('currency'),
                        'value': post.get('amount'),
                    }
                }]
            }
            print(order_data_json)
            data = json.dumps(order_data_json)
            fetch_api = requests.post(url, headers=header,data=data)
            res = json.loads(fetch_api.text)
            print(res)
        except Exception as e:
            print(e)
            return False
        return res

    @http.route('/complete_order', type='json', auth='none', methods=['POST'], csrf=False)
    def paypal_complete_order(self, **post):
        print('paypal_create_order', post)
        res= {}
        try:
            item_number = post.get('item_number')
            intent = post.get('intent')
            order_id = post.get('order_id')
            access_token = self.get_access_token(item_number)
            payment_id = request.env['payment.transaction'].search([('reference', '=', item_number)])
            acquirer_id = payment_id.acquirer_id
            endpoint_url = request.env['payment.acquirer']._get_paypal_v2_urls(acquirer_id.environment or 'prod')
            url = endpoint_url + '/v2/checkout/orders/' + order_id + '/' + intent
            header = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {}'.format(access_token)
            }
            fetch_api = requests.post(url, headers=header)
            res = json.loads(fetch_api.text)
            print(res)
            if res.get('status') == 'COMPLETED':
                res['item_number'] = item_number
                request.env['payment.transaction'].sudo().form_feedback(res, 'paypal_v2')
        except Exception as e:
            print(e)
        res['return_url'] = '/shop/payment/validate'
        return res
