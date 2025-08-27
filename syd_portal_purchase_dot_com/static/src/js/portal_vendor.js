function po_excel_submit()
{
      //var myparam = "abc";

     // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('xls'); 
	$("#po_list_form").submit(); 
}


function po_pdf_submit()
{
      //var myparam = "abc";

     // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('pdf'); 
      $("#po_list_form").submit(); 
}

function po_pdf_product_submit()
{
      //var myparam = "abc";

     // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('pdf_product'); 
      $("#po_list_form").submit(); 
}

function po_take_in_charge()
{
    //var myparam = "abc";

   // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('action'); 
    $("#po_list_form").submit(); 
}

function po_spedito()
{
    //var myparam = "abc";

   // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('action_spedito'); 
    $("#po_list_form").submit(); 
}

function po_spedito_galvanica()
{
    //var myparam = "abc";

   // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('action_galvanica'); 
    $("#po_list_form").submit(); 
}

function po_txt_submit()
{
      //var myparam = "abc";

     // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('txt'); 
      $("#po_list_form").submit(); 
}

function po_stl_submit()
{
      //var myparam = "abc";

     // add hidden field to your form name="myparam" and value="abc"
	$("#report_type").val('stl'); 
      $("#po_list_form").submit(); 
}

function po_vendor_info_submit() {
	$("#report_type").val('zip'); 
    $("#po_list_form").submit(); 
}

function toggle(source) {
	checkboxes = document.getElementsByClassName('js_porder');
  	for(var i=0, n=checkboxes.length;i<n;i++) {
    	checkboxes[i].checked = source.checked;
    }
}
