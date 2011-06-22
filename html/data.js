  function loadLayers() {
    layers['Beacons'] = new google.maps.KmlLayer(kmzPath + "beacons.kmz", { map: map });
    layers['Digipeaters'] = new google.maps.KmlLayer(kmzPath + "digipeaterss.kmz", { map: map });
    layers['Repeaters'] = new google.maps.KmlLayer(kmzPath + "repeaters.kmz", { map: map });
    layers['Sites'] = new google.maps.KmlLayer(kmzPath + "sites.kmz", { map: map });
  }
  
  function loadTree() {
    var root = tree.getRoot();
    var licencesNode = new YAHOO.widget.TextNode("Licences", root, true);
    var tmpNode = new YAHOO.widget.TextNode("Beacons", licencesNode, false);
    tmpNode = new YAHOO.widget.TextNode("Digipeaters", licencesNode, false);
    tmpNode = new YAHOO.widget.TextNode("Repeaters", licencesNode, false);
    tmpNode = new YAHOO.widget.TextNode("Sites", root, false);
  }
  
  function highlightTree() {
    tree.getNodeByProperty ( 'label' , 'Licences' ).highlight(false);
  }
