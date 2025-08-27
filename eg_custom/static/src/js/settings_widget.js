odoo.define('eg_custom.SettingsWidget', function (require) {
'use strict';

var SettingsWidget = require('stock_barcode.SettingsWidget');

var CustomSettingsWidget = SettingsWidget.include({
    events: _.extend({}, SettingsWidget.prototype.events || {}, {
        'click .o_print_small_qvc_barcodes_zpl': '_onClickPrintSmallQVCBarcodesZpl',
    }),

     _onClickPrintSmallQVCBarcodesZpl: function (ev) {
        ev.stopPropagation();
        this.trigger_up('picking_print_small_qvc_barcodes_zpl');
    },

});

return CustomSettingsWidget;

});

