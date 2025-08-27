odoo.define('syd_custom.picking_client_action', function (require) {
'use strict';

var ClientAction = require('stock_barcode.picking_client_action');

var CustomPickingClientAction = ClientAction.include({
    custom_events: _.extend({}, ClientAction.prototype.custom_events, {
        'picking_print_qvc_barcodes_zpl': '_onPrintQVCBarcodesZpl',
    }),

    _printQVCBarcodesZpl: function () {
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self.do_action(self.currentState.actionReportBarcodesQVCZplId, {
                    'additional_context': {
                        'active_id': self.actionParams.pickingId,
                        'active_ids': [self.actionParams.pickingId],
                        'active_model': 'stock.picking',
                    }
                });
            });
        });
    },

    _onPrintQVCBarcodesZpl: function (ev) {
        ev.stopPropagation();
        this._printQVCBarcodesZpl();
    },

});

return CustomPickingClientAction;

});
