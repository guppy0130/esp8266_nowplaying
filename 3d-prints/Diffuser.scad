paneltype=4; // [2:P2, 2.5:P2.5, 3:P3, 4:P4, 5:P5, 6:P6]
LEDsPerRow=16;  // [8,16,32,64,128]
height=.2; // [.12:.04:.28]
xcells=LEDsPerRow; 
ycells=LEDsPerRow;

cube(size=[paneltype*xcells, paneltype*ycells, height]);