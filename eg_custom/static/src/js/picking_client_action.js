odoo.define('eg_custom.picking_client_action', function (require) {
'use strict';

var ClientAction = require('stock_barcode.picking_client_action');

var CustomPickingClientAction = ClientAction.include({
    custom_events: _.extend({}, ClientAction.prototype.custom_events, {
        'picking_print_small_qvc_barcodes_zpl': '_onPrintSmallQVCBarcodesZpl',
    }),

    _printSmallQVCBarcodesZpl: function () {
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self.do_action(self.currentState.actionReportBarcodesSmallQVCZplId, {
                    'additional_context': {
                        'active_id': self.actionParams.pickingId,
                        'active_ids': [self.actionParams.pickingId],
                        'active_model': 'stock.picking',
                    }
                });
            });
        });
    },

    _onPrintSmallQVCBarcodesZpl: function (ev) {
        ev.stopPropagation();
        this._printSmallQVCBarcodesZpl();
    },

});

return CustomPickingClientAction;

});
