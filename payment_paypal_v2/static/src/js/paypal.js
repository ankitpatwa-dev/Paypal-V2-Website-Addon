odoo.define('paypal_payment.paypal', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;

let provider_form = $('form[provider="paypal_v2"]')
let get_input_value = (name) => {
     return provider_form.find('input[name="' + name + '"]').val();
}

const paypal_sdk_url = "https://www.paypal.com/sdk/js";
const client_id = get_input_value('paypal_client_id');
const item_number = get_input_value('item_number');
const currency = get_input_value('currency_code');
const amount = get_input_value('amount');
const intent = "capture";




let create_modal = () => {
  const modal_html = `<div class="modal fade" id="paypalModal" tabindex="-1" role="dialog" aria-labelledby="exampleModalCenterTitle" data-backdrop="static" data-keyboard="false" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="exampleModalLongTitle">Pay From Paypal</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true" onclick="location.reload();">&times;</span>
        </button>
      </div>
      <div class="modal-body">
        <div id='paypal_payment_options'> </div>
      </div>
    </div>
  </div>
</div>`
    let div_ele = document.createElement('div')
    div_ele.innerHTML = modal_html;
    document.body.appendChild(div_ele);

}

create_modal();

// Helper / Utility functions
let url_to_head = (url) => {
    return new Promise(function(resolve, reject) {
        var script = document.createElement('script');
        script.src = url;

        script.onload = function() {
            resolve();
        };
        script.onerror = function(error) {
            reject('Error loading script.');
        };
        document.head.appendChild(script);

    });
}


//PayPal Code
//https://developer.paypal.com/sdk/js/configuration/#link-queryparameters
url_to_head(paypal_sdk_url + "?client-id=" + client_id + "&enable-funding=venmo&currency=" + currency + "&intent=" + intent)
.then(() => {
    //Handle loading spinner

    $("#paypalModal").modal();
    let paypal_buttons = paypal.Buttons({ // https://developer.paypal.com/sdk/js/reference
        onClick: (data) => { // https://developer.paypal.com/sdk/js/reference/#link-oninitonclick
            //Custom JS here
        },
        style: { //https://developer.paypal.com/sdk/js/reference/#link-style
            shape: 'rect',
            color: 'gold',
            layout: 'vertical',
            label: 'paypal'
        },

        createOrder: function(data, actions) { //https://developer.paypal.com/docs/api/orders/v2/#orders_create

            return fetch("/create_order", {
                method: "post", headers: { "Content-Type": "application/json; charset=utf-8" },
                body: JSON.stringify({jsonrpc: "2.0",params:{ "intent": intent,'item_number':item_number,'currency':currency,'amount':amount}})
            })
            .then((response) => {
            console.log(response,'response');
                return response.json()
               }
            )
            .then((order) => {
                console.log('order',order)
                return order?.result?.id;
            });
        },

        onApprove: function(data, actions) {
            let order_id = data.orderID;
//            salmankhan bug-id 2520 added
            $('#paypalModal').modal('hide');
//            salmankhan bug-id 2520 end
            console.log('data order_id',order_id)
            return fetch("/complete_order", {
                method: "post", headers: { "Content-Type": "application/json; charset=utf-8" },
                body: JSON.stringify({
                jsonrpc: "2.0",
                params:{
                    "intent": intent,
                    "order_id": order_id,
                    'item_number':item_number,
                }})
            })
            .then((response) => response.json())
            .then((order_details) => {
                console.log(order_details); //https://developer.paypal.com/docs/api/orders/v2/#orders_capture!c=201&path=create_time&t=response
                let result = order_details.result
                const return_url = result.return_url
                //Custom Successful Message
                console.log('Payment Successfull')
                 $('#paypalModal').modal('hide');
                paypal_buttons.close();
                window.location.href = return_url;
             })
             .catch((error) => {
                console.log(error);
                alert('An Error Ocurred!')
                $('#paypalModal').modal('hide');
                window.location.reload()
             });
        },

        onCancel: function (data) {
            alert('Payment Cancelled')
            $('#paypalModal').modal('hide');
            window.location.reload()

        },

        onError: function(err) {
        alert(`the error ${err}`)
            console.log('the error',err);
            $('#paypalModal').modal('hide');
            window.location.reload()

        }
    });
    paypal_buttons.render('#paypal_payment_options');

})
.catch((error) => {
    console.log(error)
    console.error(error);
});


});
