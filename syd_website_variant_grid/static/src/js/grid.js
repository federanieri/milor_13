odoo.define('website_variant_grid.grid', function (require) {
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var qweb = core.qweb;
    var _t = core._t;

    publicWidget.registry.productVariantGrid = publicWidget.Widget.extend({
        selector: '.o_product_variant_grid',
        xmlDependencies: ['/product_matrix/static/src/xml/product_matrix.xml'],
        events: {
            'click': '_onClickVariantGridButton',
        },
        /*
            @constructor
        */
        init: function() {
            this._super.apply(this, arguments);
            this.matrix = {};
        },
        /* 
            @override
        */
        start: function() {
            var self = this;
            this.productTemplateId = parseFloat($('.o_product_variant_grid').data('template_id'));
            var ready = this._fetch_matrix().then( matrix => {self.matrix=matrix});
            return Promise.all([this._super.apply(this, arguments), ready]);
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _fetch_matrix: function () {
            return this._rpc({
                route: '/shop/fetch/product/matrix',
                params: {
                    productTemplateId: this.productTemplateId,
                },
            });
        },
        /**  
            Open Variant Grid View
            @Private
        */
       _onClickVariantGridButton: function(ev) {
           ev.preventDefault();
           this._openMatrixDialog();
       },
       /** 
        * @private
       */
       _openMatrixDialog: function() {
            var self = this;
            var MatrixDialog = new Dialog(this, {
                title: _t('Choose Product Variants'),
                size: 'extra-large', // adapt size depending on matrix size?
                $content: $(qweb.render(
                    'product_matrix.matrix', {
                        header: self.matrix.header,
                        rows: self.matrix.matrix,
                    }
                )),
                buttons: [
                    {text: _t('Confirm'), classes: 'btn-primary btn-confirm', close: false, click: function (ev) {
                        var $inputs = this.$('.o_matrix_input');
                        var $button = $(ev.currentTarget);
                        var matrixChanges = [];
                        var dialog = this;
                        _.each($inputs, function (matrixInput) {
                            if (matrixInput.value && matrixInput.value !== matrixInput.attributes.value.nodeValue) {
                                matrixChanges.push({
                                    qty: parseFloat(matrixInput.value),
                                    ptav_ids: matrixInput.attributes.ptav_ids.nodeValue.split(",").map(function (id) {
                                        return parseInt(id);
                                    }),
                                });
                            }
                        });
                        if (matrixChanges.length > 0) {
                            var $spinner = $("<span class='ml8 fa fa-spinner fa-spin'>");
                            $spinner.appendTo($button);
                            self._applyGrid(matrixChanges).then(result => {
                                dialog.close();
                                window.location.href = '/shop/cart';
                            });
                        }
                    }},
                    {text: _t('Close'), close: true},
                ],
            }).open();
       },
       /** 
        * @private
        * @returns Promise
       */
       _applyGrid: function(matrix) {
            return this._rpc({
                route: '/shop/apply/product/matrix',
                params: {
                    productTemplateId: this.productTemplateId,
                    matrix: matrix,
                },
            });
       }

    });
});