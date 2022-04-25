include <hal9000.scad>

conf_rfid = false;
conf_rotary = false;
conf_button = false;

translate([+00.0,+37.5,+00.0]) hal9000_enclosure_bottom();
translate([+00.0,+35.0,+00.0]) hal9000_enclosure_top();
translate([140.0,+16.5,+00.0]) hal9000_enclosure_panel();
translate([+47.5,195.0,+00.0]) hal9000_component_display_frame_bottom();
translate([+47.5,115.0,+00.0]) hal9000_component_display_frame_top();
translate([140.0,175.0,+00.0]) hal9000_component_display_cover();
translate([140.0,115.0,+00.0]) hal9000_component_display_ring();
