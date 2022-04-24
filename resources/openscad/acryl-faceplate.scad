$fn=360;


module acryl_faceplate() {
    difference() {
        square([+90.0,+185.0], center=true);
        translate([+00.0,-42.5]) circle(d=+50.0);
    }
}

acryl_faceplate();
