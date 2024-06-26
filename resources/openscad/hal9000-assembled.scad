include <hal9000.scad>
// this rendering is best viewed if in openscad preview mode, because colors are shown

conf_display = "roundypi";

conf_panel_rfid = true;
conf_panel_rotary = true;
conf_panel_motion = true;

translate([+00.0,+00.0,+00.0]) rotate([+00,+00,+00]) hal9000_enclosure();
translate([+47.5,+18.5,235.0]) rotate([180,+00,+00]) hal9000_enclosure_panel();
translate([+47.5,+30.0,+97.5]) rotate([+90,+00,+00]) hal9000_component_display_frame_bottom();
translate([+47.5,+05.5,+97.5]) rotate([-90,+00,+00]) hal9000_component_display_frame_top();
translate([+47.5,+13.5,+97.5]) rotate([-90,+00,+00]) hal9000_component_display_cover();
translate([+47.5,+01.0,+97.5]) rotate([-90,+00,+00]) hal9000_component_display_ring();
translate([+47.5,+01.5,140.0]) rotate([-90,+00,+00]) hal9000_material_acryl();
translate([+47.5,+01.5,+97.5]) rotate([+90,+00,+00]) hal9000_material_fisheye();
translate([+47.5,+01.6,+25.0]) rotate([-90,+00,+00]) hal9000_material_wiremesh();
