  var kmzPath = "http://www.wallace.gen.nz/maps/";
  var map;
  var layers = new Array();
  
  var tree;
  
  function initialize() {
    mapInit()
    treeInit();
    updateMapDisp();
  }
  
  function mapInit() {
    var latlng = new google.maps.LatLng(-41.079351, 173.254395)
    var myOptions = {
      zoom: 3,
      center: latlng,
      mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    map = new google.maps.Map(document.getElementById("map_canvas"),
        myOptions);
        
    loadLayers();
  }

  function treeInit() {
    tree = new YAHOO.widget.TreeView("treeDiv1");
    loadTree();
    tree.subscribe('clickEvent',onTreeClick);
    tree.setNodesProperty('propagateHighlightUp',true); 
    tree.setNodesProperty('propagateHighlightDown',true);
    highlightTree();
    tree.render();
  }
  
  function onTreeClick(oArgs){
    tree.onEventToggleHighlight(oArgs);
    updateMapDisp();
    return(false);
  }
  
  function updateMapDisp() {
    var leaves = tree.getNodesByProperty('children',false)
    for (var i = 0; i < leaves.length; i++) {
      if (leaves[i].highlightState == 1){
        layers[leaves[i].label].setMap(map);
      }
      else {
        layers[leaves[i].label].setMap(null);
      }
    }
  }
