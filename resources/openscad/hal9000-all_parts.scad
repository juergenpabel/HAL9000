include <hal9000.scad>

conf_display = "roundypi"; // "roundypi";

conf_panel_rfid = true;
conf_panel_rotary = true;
conf_panel_motion = true;

translate([+00.0,+37.5,+00.0]) hal9000_enclosure_bottom();
translate([+00.0,+35.0,+00.0]) hal9000_enclosure_top();
translate([140.0,+12.5,+00.0]) hal9000_enclosure_panel();
translate([140.0,+12.5,+00.0]) hal9000_enclosure_panel_addons();
translate([+47.5,195.0,+00.0]) hal9000_component_display_frame_bottom();
translate([+47.5,115.0,+00.0]) hal9000_component_display_frame_top();
translate([140.0,180.0,+00.0]) hal9000_component_display_cover();
translate([140.0,115.0,+00.0]) hal9000_component_display_ring();
