function hideDiv() {
		if (document.getElementById("other_reason") != null){
			var other_reason_id = document.getElementById("other_reason").value;
		}
	  	if(document.getElementById('reason') != null){ 
  			var op = document.getElementById('reason').value;
			var div_text_area = document.getElementById("reason_text_area");
			var text_area = document.getElementById("closing_text");
			if (op == other_reason_id) {
				div_text_area.style.display = "block";        
				text_area.setAttribute('required','1');
			} else {
				div_text_area.style.display = "none";        
				text_area.removeAttribute('required');
			}
		}
}

function hideSpecific(e) {
		var e = parseInt(e);
		if (document.getElementById("other_reason") != null){
			var other_reason_id = document.getElementById("other_reason").value;
		}
	  	if(document.getElementsByName('reason') != null){ 
  			var op = document.getElementsByName('reason')[e].value;
			var id = "reason_text_area_" + e;
			var div_text_area = document.getElementById(id);
			var text_area = document.getElementById("closing_text_" + e);
			if (op == other_reason_id) {
				div_text_area.style.display = "block";        
				text_area.setAttribute('required','1');
			} else {
				div_text_area.style.display = "none";        
				text_area.removeAttribute('required');
			}
		}
}

function show_modal(id) {
	var button = document.getElementById(id);
	var id = "#hidden_box_" + id;
    $(id).modal('show'); 

}