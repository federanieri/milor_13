/*global $, _, PDFJS */
var scene,camera,renderer,loader;
odoo.define('website.stl_viewer', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');
var local_storage = require('web.local_storage');
require('root.widget');

var _t = core._t;
var page_widgets = {};

(function () {
    var widget_parent = $('body');


     var StlViewerButton = Widget.extend({
    	
        setElement: function($el){
            this._super.apply(this, arguments);
            this.$el.on('click', this, _.bind(this.apply_action, this));
        },
        loadStl(url,id){
        	loader = new THREE.STLLoader();
        	$('#stl_viewer_canvas').hide();
        	loadStl(url,id);
        	
        },
        createActionBar:function(container){
        	var div1 = document.createElement("div");
        	div1.className = "btn-toolbar stl_viewer_canvas";
        	div1.style = "justify-content: center; display: flex;";
        	container.appendChild(div1);	
        	
        	
        },
        apply_action:function(ev) {
        	
        	var button = $(ev.currentTarget);
        	var id = button.data().id;
        	var url = button.data().url;
        	var container;
        	$('#modal_stl_viewer').modal();
        	
        	/* Get the button target*/
        	var i = 0
        	var parent_node_id; 

			container = document.getElementById('modal_container');


			var loader = document.createElement("div");
		    loader.className = "waiting_loader";
		    loader.id = "waiting_loader";
		    
		    var modal_container = document.createElement("div");
		    modal_container.id="modal_container";
		    
		    container.innerHTML = "";
		    container.appendChild(modal_container);
		    modal_container.appendChild(loader);   
            // renderer
            renderer = new THREE.WebGLRenderer( { antialias: true } );
            renderer.setSize( 390, 390  );
            renderer.setClearColor( 0xffffff);
            renderer.domElement.className = "stl_viewer_canvas";
            renderer.domElement.id = "stl_viewer_canvas";
            modal_container.appendChild( renderer.domElement )
           
            this.createActionBar(container);
            
            // scene
            scene = new THREE.Scene();

            // camera
            camera = new THREE.PerspectiveCamera( 35, renderer.getSize().x / renderer.getSize().y, 1, 10000 );
            camera.position.set( 0, 0, 80 );
            scene.add( camera ); // required, because we are adding a light as a child of the camera

            // Controls
            var controls = new THREE.OrbitControls( camera, renderer.domElement );

            // lights
            scene.add( new THREE.AmbientLight( 0x222222 ) );

            var light = new THREE.PointLight( 0xffffff, 0.8 );
            camera.add( light );

            // object
            var size = 100;
            var divisions = 100;


            
            this.loadStl(url,id);
            
            
            
            
            render();
            
        },
        

        
        
    });

    page_widgets['stlViewerButton'] = new StlViewerButton(widget_parent).setElement($('.oe_stl_viewer'));

})();

return {
    page_widgets: page_widgets,
};

});
function render() {

  requestAnimationFrame(render);
  renderer.render(scene, camera);
  
  
  
}

function loadStl(url,id) {
	loader.load(url, function ( geometry ) {
		
        var material = new THREE.MeshPhongMaterial( { color: 0xFFE4E1 } );
        var mesh = new THREE.Mesh( geometry, material )
        scene.add( mesh );
        $('#stl_viewer_canvas').show();
        $('#waiting_loader').hide();
    } );
};

