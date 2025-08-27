odoo.define('theme_clarico.website_recently_viewed', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');
//    var wSaleWishList = require('theme_clarico.wishlist_animate');
    var wSaleUtils = require('website_sale.utils');
    var productsRecentlyViewedSnippet = new publicWidget.registry.productsRecentlyViewedSnippet();
    var core = require('web.core');
    var qweb = core.qweb;
    //--------------------------------------------------------------------------
    // Recently viewed product slider add to cart animation
    //--------------------------------------------------------------------------
    publicWidget.registry.productsRecentlyViewedSnippet.include({
    	xmlDependencies: ['/theme_clarico/static/src/xml/website_sale_recently_viewed.xml'],
        _onAddToCart: function (ev) {
            var self = this;
            var $card = $(ev.currentTarget).closest('.card');
            this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: $card.find('input[data-product-id]').data('product-id'),
                    add_qty: 1
                },
            }).then(function (data) {
                wSaleUtils.updateCartNavBar(data);
                var $navButton = self.getCustomNavBarButton('.o_wsale_my_cart');
                var fetch = self._fetch();
                var animation = wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.o_carousel_product_card'), 17, 16);
                Promise.all([fetch, animation]).then(function (values) {
                    self._render(values[0]);
                });
            });
        },
        // Recently viewed product slider get add to cart selector based on header
        getCustomNavBarButton: function(selector) {
            var $affixedHeaderButton = $('header.affixed ' + selector);
            if ($affixedHeaderButton.length) {
                return $affixedHeaderButton;
            } else {
                var $header = $('div.te_header_before_overlay '+ selector);
                if($header.length){
                    return $header;
                } else {
                    return $('header ' + selector).first();
                }
            }
        },
        _render: function (res) {
            var products = res['products'];
            var mobileProducts = [], webProducts = [], productsTemp = [];
            _.each(products, function (product) {
                if (productsTemp.length === 4) {
                    webProducts.push(productsTemp);
                    productsTemp = [];
                }
                productsTemp.push(product);
                mobileProducts.push([product]);
            });
            if (productsTemp.length) {
                webProducts.push(productsTemp);
            }

            this.mobileCarousel = $(qweb.render('theme_clarico.productsRecentlyViewed', {
                uniqueId: this.uniqueId,
                productFrame: 1,
                productsGroups: mobileProducts,
            }));
            this.webCarousel = $(qweb.render('theme_clarico.productsRecentlyViewed', {
                uniqueId: this.uniqueId,
                productFrame: 4,
                productsGroups: webProducts,
            }));
            this._addCarousel();
            this.$el.toggleClass('d-none', !(products && products.length));
        },
    });

});