// BUKIFON v0.3  | UNITS mm | PROVISIONAL CONCEPT / NOT MANUFACTURING READY
// KiCad coordinates and actual Lapka case mounting have NOT been imported.
// Front is 380 x 210 x 3, split into six printable sections <= 220 x 220.
// Normal mounting for low-profile Choc MUST be a separate 1.3-1.6mm switch plate;
// the 3.0mm PETG casing is structural, not a Choc snap-in plate.
$fn=48;
show_keys=true;
show_envelopes=false;
show_chassis=false; // rough 63 mm deep envelope; not a mechanical housing
export_part=-1; // -1 assembled, 0..5 a single printable front tile
module panel2d() {
  square([380,210]);
}
module hole_set() {
  translate([136,29]) square([108,64.8]); // zero-bezel active-area opening
  for(i=[0:9]) translate([140.5+i*11,11]) circle(d=6);
  for(x=[22,49,76,103,277,304,331,358])
    for(y=[30.5,57.5]) translate([x,y]) circle(d=7.2); // verify selected encoder bushing
  for(x=[180,200]) translate([x-1.25,117.5]) square([2.5,63]);
}
module piece(poly) {
  linear_extrude(height=3) difference(){polygon(poly);hole_set();}
}
if(export_part==-1 || export_part==0) color([0.76,0.80,0.82]) piece([[0,0],[124,0],[124,75],[0,75]]); // controls_L
if(export_part==-1 || export_part==1) color([0.84,0.87,0.88]) piece([[124,0],[256,0],[256,103],[124,103]]); // display
if(export_part==-1 || export_part==2) color([0.76,0.80,0.82]) piece([[256,0],[380,0],[380,75],[256,75]]); // controls_R
if(export_part==-1 || export_part==3) color([0.69,0.74,0.77]) piece([[0,75],[124,75],[124,103],[164,103],[164,210],[0,210]]); // deck_L
if(export_part==-1 || export_part==4) color([0.79,0.83,0.85]) piece([[164,103],[216,103],[216,210],[164,210]]); // faders
if(export_part==-1 || export_part==5) color([0.69,0.74,0.77]) piece([[256,75],[380,75],[380,210],[216,210],[216,103],[256,103]]); // deck_R

if(show_keys && export_part==-1) {
  // Reference visual caps only; they are NOT switch holes or proof of PCB fit.
  color([0.94,0.95,0.91]) translate([73.6667,95.6013,4]) rotate([0,0,13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([306.3333,95.6013,4]) rotate([0,0,-13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([95.8889,96.5163,4]) rotate([0,0,17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([284.1111,96.5163,4]) rotate([0,0,-17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([115.6275,106.8431,4]) rotate([0,0,22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([264.3725,106.8431,4]) rotate([0,0,-22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([136.1503,114.2941,4]) rotate([0,0,24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([243.8497,114.2941,4]) rotate([0,0,-24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([50.0065,103.8366,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([329.9935,103.8366,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([69.8758,112.7255,4]) rotate([0,0,13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([310.1242,112.7255,4]) rotate([0,0,-13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([91.4444,113.7712,4]) rotate([0,0,17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([288.5556,113.7712,4]) rotate([0,0,-17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([109.7451,123.7059,4]) rotate([0,0,22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([270.2549,123.7059,4]) rotate([0,0,-22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([128.0458,129.9804,4]) rotate([0,0,24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([251.9542,129.9804,4]) rotate([0,0,-24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([31.8366,100.9608,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([348.1634,100.9608,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([46.8693,121.8758,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([333.1307,121.8758,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([65.8235,130.6340,4]) rotate([0,0,13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([314.1765,130.6340,4]) rotate([0,0,-13.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([85.1699,130.8954,4]) rotate([0,0,17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([294.8301,130.8954,4]) rotate([0,0,-17.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([103.4706,141.2222,4]) rotate([0,0,22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([276.5294,141.2222,4]) rotate([0,0,-22.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([121.9020,147.1046,4]) rotate([0,0,24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([258.0980,147.1046,4]) rotate([0,0,-24.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([28.5686,119.9150,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([351.4314,119.9150,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([43.8627,140.0458,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([336.1373,140.0458,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([101.7712,166.5817,4]) rotate([0,0,21.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([278.2288,166.5817,4]) rotate([0,0,-21.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([25.3007,138.3464,4]) rotate([0,0,8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([354.6993,138.3464,4]) rotate([0,0,-8.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([120.4641,176.3856,4]) rotate([0,0,35.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([259.5359,176.3856,4]) rotate([0,0,-35.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([138.5033,190.2418,4]) rotate([0,0,44.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
  color([0.94,0.95,0.91]) translate([241.4967,190.2418,4]) rotate([0,0,-44.0000]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);
}
// Encoder knobs, jack rings, fader caps: presentation solids.
if(export_part==-1) for(x=[22,49,76,103,277,304,331,358]) for(y=[30.5,57.5])
  color([0.18,0.20,0.23]) translate([x,y,3]) cylinder(h=8,d=14);
if(export_part==-1) for(i=[0:9]) color([0.25,0.28,0.30]) translate([140.5+i*11,11,3]) difference() {cylinder(h=2,d=9);cylinder(h=2.1,d=5.7);}
if(export_part==-1) for(x=[180,200]) color([0.2,0.24,0.28]) translate([x-8,143,4]) cube([16,12,5]);
// Black physical LCD is hidden behind the nominal 108 x 64.8 window.
if(show_envelopes && export_part==-1) {
 color([0.15,0.3,0.65,0.15]) translate([129.65,23.5,-5]) cube([120.7,75.8,5]);
 for(x=[180,200])color([0.6,0.1,0.1,0.35])translate([x-8,111.5,-8]) cube([16,75,8]);
}
if(show_chassis && export_part==-1){
  // ENVELOPE only: rear skirt 60 mm below 3 mm front, printed as separate parts.
  color([0.25,0.28,0.30,0.35]) translate([0,0,-60]) {
    cube([190,3,60]); translate([190,0,0]) cube([190,3,60]);
    translate([0,207,0]) cube([190,3,60]); translate([190,207,0]) cube([190,3,60]);
    cube([3,210,60]); translate([377,0,0]) cube([3,210,60]);
  }
}
