odoo.define('syd_website_b2b_addon.cart_product_search', function (require) {
"use strict";
    require('web.dom_ready');
    
    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    require('website_sale.cart');
    var core = require('web.core');
    var productsSearchBar = publicWidget.registry.productsSearchBar;
    var _t = core._t;
    var qweb = core.qweb;

    publicWidget.registry.CartProductSearch = productsSearchBar.extend({
        selector: '.o_cart_products_searchbar_form',
        events: _.extend({}, productsSearchBar.prototype.events || {}, { 
            'click .oe_search_button': '_onClickSearch',
        }),
        xmlDependencies: (productsSearchBar.prototype.xmlDependencies || [])
            .concat(['/syd_website_b2b_addon/static/src/xml/shop_cart.xml']),
        /**
         * @private
         */
        _render: function (res) {
            var $prevMenu = this.$menu;
            this.$el.toggleClass('dropdown show', !!res);
            if (res) {
                var products = res['products'];
                this.$menu = $(qweb.render('cartProductSearchBar', {
                    products: products,
                    hasMoreProducts: products.length < res['products_count'],
                    currency: res['currency'],
                    widget: this,
                }));
                this.$menu.css('min-width', this.autocompleteMinWidth);
                this.$el.append(this.$menu);
            }
            if ($prevMenu) {
                $prevMenu.remove();
            }
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$('.oe_search_box').focus();
        },

        /**
         * @private
         */
        _fetch: function () {
            return this._rpc({
                route: '/shop/cart/product/autocomplete',
                params: {
                    'term': this.$input.val(),
                    'options': {
                        'order': this.order,
                        'limit': this.limit,
                        'display_description': this.displayDescription,
                        'display_price': this.displayPrice,
                        'max_nb_chars': Math.round(Math.max(this.autocompleteMinWidth, parseInt(this.$el.width())) * 0.22),
                    },
                },
            });
        },
        _onClickSearch: function(ev) {
            ev.preventDefault();
            if (this.$menu) {
                let $elem = this.$menu.children().first();
                $elem.focus();
                $elem[0].click() //wierd way
            }
        },
        /**
         * @private
         */
        _onKeydown: function (ev) {
            this._super.apply(this, arguments);
            switch (ev.which) {
                case $.ui.keyCode.ENTER:
                    ev.preventDefault();
                    if(this.$menu) {
                        let $elem = this.$menu.children().first();
                        $elem.focus();
                        $elem[0].click() //wierd way
                    }
                    break;
            }
        }
    });
});
