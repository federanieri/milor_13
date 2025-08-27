function change_qty_to_do(e) {
	var id = e.id.substring(13, e.id.length); 
	var product_qty = document.getElementById("product_qty_" + id).innerHTML;
	var qty_todo = "qtytodo_" + id;
 	document.getElementById(qty_todo).value = product_qty - e.value;

} 