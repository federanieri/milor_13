odoo.define('stock_barcode.picking_accept_client_action', function (require) {
'use strict';

var core = require('web.core');
var PickingClientAction = require('stock_barcode.picking_client_action');

var _t = core._t;

var PickingAcceptClientAction = PickingClientAction.include({
    custom_events: _.extend({}, PickingClientAction.prototype.custom_events, {
        'picking_accept': '_onAccept',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _accept: function () {
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self._rpc({
                    'model': 'stock.picking',
                    'method': 'accept_picking',
                    'args': [[self.actionParams.pickingId],[true]],
                }).then(function(res) {
                    
                	var def = Promise.resolve();
                    if (_.isObject(res)) {
                    	var exitCallback = function (infos) {
                    		self.do_notify(_t("Success"), _t("The transfer has been accepted"));
                        };
                        var options = {
                            on_close: exitCallback,
                        };
                        return def.then(function () {
                        	
                            return self.do_action(res, options);
                        });
                    } else {
                    	self.trigger_up('exit');
                    }
                   
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAccept: function (ev) {
        ev.stopPropagation();
        this._accept();
    },

});
return PickingAcceptClientAction;

});
