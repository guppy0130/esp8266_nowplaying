paneltype=4; // [2:P2, 2.5:P2.5, 3:P3, 4:P4, 5:P5, 6:P6]
LEDsPerRow=16;  // [8,16,32,64,128]
wallheight=3; // [2:.2:6]
wallwidth=.3; // [.1:.1:2]
borders=4; // [3,4]
height=wallheight;
xcells=LEDsPerRow; 
ycells=LEDsPerRow; 

cavity=paneltype-wallwidth;  // Size to remove

difference() {
    union() {
        for (x = [paneltype:paneltype:xcells*paneltype],
             y = [paneltype:paneltype:ycells*paneltype] ) 
            difference() {
               translate([x-paneltype,y-paneltype,0]) cube([paneltype,paneltype,height],false);
               translate([x-paneltype-.1,y-paneltype-.1,-.1]) cube([cavity+.1,cavity+.1,height+.2]);
            }
        translate([-wallwidth,0,0]) scale([1,1,1]) cube([wallwidth,paneltype*xcells,height],false);
        if (borders==4) { translate([-wallwidth,-wallwidth,0]) scale([1,1,1]) cube([(paneltype*xcells)+wallwidth,wallwidth,height],false); }  

    }
}
