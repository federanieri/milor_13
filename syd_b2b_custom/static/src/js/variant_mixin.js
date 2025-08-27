odoo.define('syd_b2b_custom.VariantMixin', function (require) {
'use strict';

var VariantMixin = require('sale.VariantMixin');
var publicWidget = require('web.public.widget');
var ajax = require('web.ajax');
var core = require('web.core');
var QWeb = core.qweb;
var xml_load = ajax.loadXML(
	    '/syd_b2b_custom/static/src/xml/website_sale_stock_product_availability.xml',
	    QWeb
	);

/**
 * Addition to the variant_mixin._onChangeCombination
 *
 * This will prevent the user from selecting a quantity that is not available in the
 * stock for that product.
 *
 * It will also display various info/warning messages regarding the select product's stock.
 *
 * This behavior is only applied for the web shop (and not on the SO form)
 * and only for the main product.
 *
 * @param {MouseEvent} ev
 * @param {$.Element} $parent
 * @param {Array} combination
 */
VariantMixin._onChangeCombinationB2B = function (ev, $parent, combination) {
    
	var product_id = 0;
    // needed for list view of variants
    if ($parent.find('input.product_id:checked').length) {
        product_id = $parent.find('input.product_id:checked').val();
    } else {
        product_id = $parent.find('.product_id').val();
    }
    var isMainProduct = combination.product_id &&
        ($parent.is('.js_main_product') || $parent.is('.main_product')) &&
        combination.product_id === parseInt(product_id);

    if (!this.isWebsite || !isMainProduct){
        return;
    }

    var qty = $parent.find('input[name="add_qty"]').val();
    
    $('#variant_default_code').html(combination.default_code);
    $parent.find('#add_to_cart').removeClass('out_of_stock');
    $parent.find('#buy_now').removeClass('out_of_stock');
    $parent.find('#add_to_cart').removeClass('disabled');
    $parent.find('#buy_now').removeClass('disabled');
    $('div.out_of_collection_messages').html('');
    if (combination.out_of_collection_variant) {
        
            $parent.find('#add_to_cart').addClass('disabled out_of_stock');
            $parent.find('#buy_now').addClass('disabled out_of_stock');
            
            $('div.out_of_collection_messages').html('<i class="fa fa-exclamation-triangle" role="img" aria-label="Warning" title="Warning"></i>Out of collection');
    }
    
      
        
    
	if (combination.product_type === 'product' && _.contains(['sell_with_zero_stock'], combination.inventory_availability)) {
	    xml_load.then(function () {
	        $('.oe_website_sale')
	            .find('.availability_message_' + combination.product_template)
	            .remove();
	
	        var $message = $(QWeb.render(
	            'syd_b2b_custom.product_availability',
	            combination
	        ));
	        $('div.availability_messages').html($message);
	    });
	}
};

publicWidget.registry.WebsiteSale.include({
    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function (){
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationB2B.apply(this, arguments);
    }
});

return VariantMixin;

});
