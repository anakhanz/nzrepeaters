  var kmzPath = "http://www.wallace.gen.nz/maps/";
  var gm = google.maps;
  var bounds = new gm.LatLngBounds();
  var map;
  var oms;
  
  var shadow = new gm.MarkerImage(
        'https://www.google.com/intl/en_ALL/mapfiles/shadow50.png',
        new gm.Size(37, 34),  // size   - for sprite clipping
        new gm.Point(0, 0),   // origin - ditto
        new gm.Point(10, 34)  // anchor - where to meet map location
      );

  var markers = new Array();
  var links = new Array();
  var tree;
  
  function initialize() {
    mapInit()
    treeInit();
    updateMapDisp();
  }
  
  function mapInit() {
    var latlng = new gm.LatLng(-41.079351, 173.254395)
    var myOptions = {
      zoom: 8,
      center: latlng,
      mapTypeId: gm.MapTypeId.ROADMAP
    };
    map = new gm.Map(document.getElementById("map_canvas"),
        myOptions);
        
    // set-up spiderer
    var iw = new gm.InfoWindow();
    oms = new OverlappingMarkerSpiderfier(map);
    
    oms.addListener('click', function(marker) {
      iw.setContent(marker.desc);
      iw.open(map, marker);
    });
    oms.addListener('spiderfy', function(markers) {
      for(var i = 0; i < markers.length; i ++) {
        markers[i].setIcon(itemIcon(markers[i].type, true));
        markers[i].setShadow(null);
      } 
      iw.close();
    });
    oms.addListener('unspiderfy', function(markers) {
      for(var i = 0; i < markers.length; i ++) {
        markers[i].setIcon(itemIcon(markers[i].type, false));
        markers[i].setShadow(shadow);
      }
    });
    loadLayers();
    map.fitBounds(bounds);
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
    var leafName;
    var leafState;
    var leaves = tree.getNodesByProperty('children',false)
    for (var i = 0; i < leaves.length; i++) {
      leafState =  (leaves[i].highlightState == 1);
      if (leaves[i].label == 'Links' || leaves[i].label == 'General' || leaves[i].label == 'National System' || leaves[i].label == 'DMR') {
        if (leaves[i].label == 'Links') {
          leafName = 'General';
        } else {
          leafName = leaves[i].label;
        }
        for (var j = 0; j < links[leafName].length; j++) {
          if (leafState) {
            links[leafName][j].setMap(map);
          }
          else {
            links[leafName][j].setMap(null);
          }
        }
      }
      else {
        if (leaves[i].label == 'Sites') {
          leafName = 'Sites';
        }
        else {
          leafName = leaves[i].parent.label + '-' + leaves[i].label;
        }
        for (var j = 0; j < markers[leafName].length; j++) {
          markers[leafName][j].setVisible(leafState);
        }
      }
    }
  }

  function createMarker(type, band, lat, lng, title, content) {
    var markerLatLng = new gm.LatLng(lat, lng);
    var marker = new gm.Marker({
        position: markerLatLng,
        map: map,
        title: title,
        desc: content,
        type: type,
        band: band,
        icon: itemIcon(type, false),
        shadow: shadow
    });
    var typeBand;
    oms.addMarker(marker);
    if (type == 'Site') {
      typeBand = 'Sites';
    }
    else {
      typeBand = type + 's-' + band;
    }
    bounds.extend(markerLatLng);
    markers[typeBand].push(marker);
    return (marker);
  }
  
  function createLink(type, lat1 , lon1, lat2, lon2, name) {
    var linkLatLng1 = new google.maps.LatLng(lat1, lon1);
    var linkLatLng2 = new google.maps.LatLng(lat2, lon2);
    var linkCoordinates = [
        linkLatLng1,
        linkLatLng2
    ];
    var link = new google.maps.Polyline({
      path: linkCoordinates,
      strokeColor: "#5AFD82",
      strokeOpacity: 1.0,
      strokeWeight: 2
    });
    link.setMap(map);
    links[type].push(link);
    bounds.extend(linkLatLng1);
    bounds.extend(linkLatLng2);
    return link;
  }

  function itemIcon(type, spiderified) {
    switch(type) {
      case 'Amateur Beacon':
        if (spiderified) {
          color = '55DAFF';
        } else {
          color = '5588FF';
        }
        chst='d_map_xpin_letter';
        type = 'pin';
        text = '+';
        break;
      case 'Amateur Digipeater':
        if (spiderified) {
          color = 'FF71FF';
        } else {
          color = 'EE4499';
        }
        chst='d_map_xpin_letter';
        type = 'pin';
        text = '+';
        break;
      case 'Amateur Repeater':
        if (spiderified) {
          color = '90EE90';
        } else {
          color = '00FF00';
        }
        chst='d_map_xpin_letter';
        type = 'pin';
        text = '+';
        break;
      default:
        if (spiderified) {
          color = 'FFEE22';
        } else {
          color = 'EEBB22';
        }
        chst='d_map_xpin_letter';
        type = 'pin';
        text = '+';
    }
    return 'http://chart.googleapis.com/chart?chst=' + chst + '&chld=' + type + '|' + text + '|' + color + '|000000|ffff00';
  }
