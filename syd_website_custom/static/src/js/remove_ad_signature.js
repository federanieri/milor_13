 odoo.define('syd_website_custom.remove_signatura_ad_button', function(require) { 
"use strict";
         
	    var publicWidget = require('web.public.widget');
	    var ajax = require('web.ajax');
	    require('website_sale.cart');
	    var core = require('web.core');
	    var productsSearchBar = publicWidget.registry.productsSearchBar;
	    var _t = core._t;
	    var qweb = core.qweb;
                  
        productsSearchBar.include({
	        xmlDependencies: (productsSearchBar.prototype.xmlDependencies || [])
	            .concat(['/syd_website_custom/static/src/xml/templates.xml']),
	        /**
     		 * @override
	         * @private
	         */
	        _render: function (res) {
	            var $prevMenu = this.$menu;
	            this.$el.toggleClass('dropdown show', !!res);
	            if (res) {
	                var products = res['products'];
	                var i;
					for (i=0; i<products.length; i++) {
						var display_name = products[i].display_name;
						if (display_name.includes('[')) {
							var default_code = display_name.match(/(?<=\[).*(?=\])/)[0];
							products[i].default_code = default_code;
						}
					}
					
					this.$menu = $(qweb.render('cartProductSearchingBar', {
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
	});     
});