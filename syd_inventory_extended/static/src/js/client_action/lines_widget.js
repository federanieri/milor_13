odoo.define('stock_barcode.LinesAcceptWidget', function (require) {
'use strict';

var LinesWidget = require('stock_barcode.LinesWidget');

var LinesAcceptWidget = LinesWidget.include({
    events: _.extend({}, LinesWidget.prototype.events, {
        'click .o_check_accept': '_onClickAccept',
    }),

    init: function (parent, page, pageIndex, nbPages) {
        this._super.apply(this, arguments);
        this.picking_accepted = parent.currentState.picking_accepted;
        this.cannot_put_in_pack = parent.currentState.cannot_put_in_pack;
        this.product_status = parent.currentState.product_status;
        this.total_line_processed_goods = parent.currentState.total_line_processed_goods;
        this.total_line_goods = parent.currentState.total_line_goods;
        this.not_correct = parent.currentState.not_correct;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the click on the `Quality Checks` button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAccept: function (ev) {
        ev.stopPropagation();
        this.trigger_up('picking_accept');
    },
});

return LinesAcceptWidget;

});
