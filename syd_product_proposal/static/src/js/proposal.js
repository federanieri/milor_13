function disableItem(e) {
	opacity_level_disabled = "0.8";
	disabled_item = true //use this field as flag to enable/disabled the items
	
	id = e.id.substring(10, e.id.length ); 
	td_id = 'tr_id_'.concat(id);
	
	if(document.getElementById(td_id).style.opacity == opacity_level_disabled) {
		document.getElementById(td_id).style.opacity = opacity_level_disabled = "1.0"; 
		disabled_item = false
		
		document.getElementById("i_tag_id_".concat(id)).setAttribute("class", "")
		
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa")
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa-check-square-o")
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa-2x")
		
	} else {
		document.getElementById(td_id).style.opacity = "0.8";
		disabled_item = true; 
		
		document.getElementById("i_tag_id_".concat(id)).setAttribute("class", "")
		
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa")
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa-square-o")
		document.getElementById("i_tag_id_".concat(id)).classList.add("fa-2x")
	}
	
	qty_accepted = 'qtyaccepted_'.concat(id);
	if(disabled_item==false && document.getElementById('qty_proposed_'.concat(id)) != null && document.getElementById(qty_accepted)!=null){ 
		document.getElementById(qty_accepted).value = document.getElementById('qty_proposed_'.concat(id)).innerText;
		document.getElementById(qty_accepted).disabled = disabled_item;
		$("#"+qty_accepted).trigger("change");
		
		}
	else if (document.getElementById('qty_proposed_'.concat(id)) != null && document.getElementById(qty_accepted)!=null){
		document.getElementById(qty_accepted).value = 0.0;
		document.getElementById(qty_accepted).disabled = disabled_item;
		}
	else if (document.getElementById('qty_proposed_'.concat(id)) == null && document.getElementById(qty_accepted)!=null){
		document.getElementById(qty_accepted).value = 0.0;
		document.getElementById(qty_accepted).disabled = disabled_item;
	}
	
	
//	button_minus = 'button_minus_'.concat(id); 
//	if(document.getElementById(button_minus) != null) 
//		document.getElementById(button_minus).disabled = disabled_item;
//	
//	
//	button_plus = 'button_plus_'.concat(id);
//	if(document.getElementById(button_plus) != null) 
//		document.getElementById(button_plus).disabled = disabled_item;
		
	price_accepted = 'priceaccepted_'.concat(id);
	if(disabled_item==false && document.getElementById('price_proposed_'.concat(id)) != null && document.getElementById(price_accepted)!=null){ 
		document.getElementById(price_accepted).value = document.getElementById('price_proposed_'.concat(id)).innerText;
		document.getElementById(price_accepted).disabled = disabled_item;
		}
	else if (document.getElementById('price_proposed_'.concat(id)) != null && document.getElementById(price_accepted)!=null){
		document.getElementById(price_accepted).value = 0.0;
		document.getElementById(price_accepted).disabled = disabled_item;
		}	
			
	description = 'description_'.concat(id);
	if(document.getElementById(description) != null) 
		document.getElementById(description).disabled = disabled_item; 
	
	customer_product_code = 'customerpcode_'.concat(id);
	if(document.getElementById(customer_product_code) != null) 
		document.getElementById(customer_product_code).disabled = disabled_item; 
}
