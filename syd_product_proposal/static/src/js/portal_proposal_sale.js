odoo.define('syd_product_proposal.proposal_sale_order_content', function (require) {
'use strict';

    var publicWidget = require('web.public.widget');
    var config = require('web.config');

    publicWidget.registry.PortalProposalOrder = publicWidget.Widget.extend({
        selector: '#proposal_sale_order_content',
        events: {
            'change input.qty_accepted': '_onChangeQuantityAccpted',
            'change input.price_accepted': '_onChangePriceAccepted',
            'click .proposal-submit': '_onClickSubmit',
            'click button.js_add_cart_json': '_onClickAddCartJSON',
        },
        /**
         * @override
         */
        start: function () {
            var self = this;
            var def = this._super.apply(this, arguments);
            this._startZoom();
            return def;
        },

        

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {Event} ev
         */
        _onClickAddCartJSON: function (ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.closest('.input-group').find("input.qty_accepted");
            var min = parseFloat($input.data("min") || 1);
            var max = parseFloat($input.data("max") || Infinity);
            var previousQty = parseFloat($input.val() || 0, 10);
            var quantity = ($link.has(".fa-minus").length ? -1 : 1) + previousQty;
            var newQty = quantity > min ? (quantity < max ? quantity : max) : min;

            if (newQty !== previousQty) {
                $input.val(newQty).trigger('change');
            }
            return false;
        },

        /**
         * @private
         * @param {Event} ev
         */
        _onChangeQuantityAccpted: function (ev) {
            this._updateTotalAccepted();
        },

        /**
         * @private
         * @param {Event} ev
         */
        _onChangePriceAccepted: function (ev) {
            this._updateTotalAccepted();
        },

        /**
         * @private
         * @param {Event} events
         */
        _onClickSubmit: function (ev) {
            var $aSubmit = $(ev.currentTarget);
            var $form = $aSubmit.parents().find('form.proposal_order_form')
            $form.submit();
        },

        /**
         * @private
         */
        _updateTotalAccepted: function() {
            var total_accepted = 0;
            _.each(this.$('.proposal_line'), function(line) {
                var qty = $(line).find('.qty_accepted').val() || 0;
                var price = $(line).find('.price_accepted').val() || $(line).find('.price_proposed').val() || 0;
                total_accepted = total_accepted + (parseFloat(qty) * parseFloat(price));
            });
            this.$('span[data-id="total_accepted"] > .oe_currency_value').text(total_accepted.toFixed(2));
        },
        _startZoom: function () {
            // Do not activate image zoom for mobile devices, since it might prevent users from scrolling the page
            if (!config.device.isMobile) {
                var attach = '#form_proposal_order';
                _.each($('img[data-zoom]'), function (el) {
                    onImageLoaded(el, function () {
                        var $img = $(el);
                        $img.zoomOdoo({
                            attachToTarget: true,
                            event: 'mouseenter',
                            attach: attach,
                            beforeAttach: function () {
                                this.$flyout.css({ width: '512px', height: '512px' });
                            },
                        });
                    });
                });
            }
    
            function onImageLoaded(img, callback) {
                // On Chrome the load event already happened at this point so we
                // have to rely on complete. On Firefox it seems that the event is
                // always triggered after this so we can rely on it.
                //
                // However on the "complete" case we still want to keep listening to
                // the event because if the image is changed later (eg. product
                // configurator) a new load event will be triggered (both browsers).
                $(img).on('load', function () {
                    callback();
                });
                if (img.complete) {
                    callback();
                }
            }
        },

    });

});
