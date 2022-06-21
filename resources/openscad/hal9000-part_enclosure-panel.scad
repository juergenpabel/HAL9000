include <hal9000.scad>

conf_rfid = true;
conf_rotary = true;
conf_button = false;
conf_motion = true;

rotate([+00.0,+00.0,+90.0]) hal9000_enclosure_panel();
//translate([-03.5-2,+00.0,+16.5]) cube([11,39,22],center=true);

//translate([-03.5+3.0,+00.0+10,+17.5]) cube([6.5,12,8],center=true);
//translate([-03.5-4.5,+00.0,+17.5]) cube([6.5,32,23],center=true);