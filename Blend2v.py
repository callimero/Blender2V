# Blender2v scope/vectrex output. Now supporting Modifiers
# 2016, 2017 cw@blenderbuch.de

# Zum Starten [Run Script] Button oder ALT-P über diesem Fenster!

COM="COM19"     # zu benutzender Serieller Port

# Zum Debuggen/entwickeln nicht den Handler verwenden, dieser lässt sich nicht
# 100% entfernen und blockiert dann die Serielle Schnittstelle.
HAND = True      # Handler benutzen
HAND = False     # Pro Aufruf einmal die Daten senden 

import serial
import bpy
import bpy_extras
from mathutils import Vector,Matrix
import math


class SerHandle(object):
    def __init__(self):
        self.sock=None
        self.sock = serial.Serial(COM, 9600,timeout=5)
        self.scene = bpy.context.scene
        self.cam = bpy.data.objects.get("Camera")
        if self.cam == None:
            print("Keine Kamera! / No Camera")
            self.sock.close()
            exit
                   
    def __del__(self):
        # Hmmm. Nicht automatisch?!
        print("Schließe Serielle!")
        self.sock.close()


    '''
     forked from https://bitbucket.org/marcusva/py-sdl2 (which has public-domain license)
     The MIT License (MIT)
     Copyright (c) 2014 Michael Hirsch
     reference: http://en.wikipedia.org/wiki/Cohen%E2%80%93Sutherland_algorithm
     * I have corrected errors in the cohensutherland code and compared cohensutherland with Matlab polyxpoly() results.
     * The best way to Numba JIT this would probably be in the function calling this, to include the loop itself
       inside the jit decoration.
    '''
    #@jit
    def cohensutherland(self, xmin, ymin, xmax, ymax, x1, y1, x2, y2):
        """Clips a line to a rectangular area.
        This implements the Cohen-Sutherland line clipping algorithm.  xmin,
        ymax, xmax and ymin denote the clipping area, into which the line
        defined by x1, y1 (start point) and x2, y2 (end point) will be
        clipped.
        If the line does not intersect with the rectangular clipping area,
        four None values will be returned as tuple. Otherwise a tuple of the
        clipped line points will be returned in the form (cx1, cy1, cx2, cy2).
        """
        INSIDE,LEFT, RIGHT, LOWER, UPPER = 0,1, 2, 4, 8
        
        def _getclip(xa, ya):
            p = INSIDE  #default is inside

            # consider x
            if xa < xmin:
                p |= LEFT
            elif xa > xmax:
                p |= RIGHT

            # consider y
            if ya < ymin:
                p |= LOWER # bitwise OR
            elif ya > ymax:
                p |= UPPER #bitwise OR
            return p

    # check for trivially outside lines
        k1 = _getclip(x1, y1)
        k2 = _getclip(x2, y2)

    #%% examine non-trivially outside points
        #bitwise OR |
        while (k1 | k2) != 0: # if both points are inside box (0000) , ACCEPT trivial whole line in box

            # if line trivially outside window, REJECT
            if (k1 & k2) != 0: #bitwise AND &
                 return None, None, None, None

            #non-trivial case, at least one point outside window
            # this is not a bitwise or, it's the word "or"
            opt = k1 or k2 # take first non-zero point, short circuit logic
            if opt & UPPER:
                x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1)
                y = ymax
            elif opt & LOWER:
                x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1)
                y = ymin
            elif opt & RIGHT:
                y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1)
                x = xmax
            elif opt & LEFT:
                y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1)
                x = xmin
            else:
                raise RuntimeError('Undefined clipping state')
            if opt == k1:
                x1, y1 = x, y
                k1 = _getclip(x1, y1)
            elif opt == k2:
                x2, y2 = x, y
                k2 = _getclip(x2, y2)
        return x1, y1, x2, y2
        
    def send2v(self):
        vbytes = bytearray(4)   # vier 0-bytes als Header
 
        # Faktoren für Umrechnung Weltkoordinaten auf Kamerasicht
        render_scale = self.scene.render.resolution_percentage / 100
        render_size = (int(self.scene.render.resolution_x * render_scale),int(self.scene.render.resolution_y * render_scale))
        up = self.cam.matrix_world.to_quaternion() * Vector((0.0, 1.0, 0.0))
        cam_direction = self.cam.matrix_world.to_quaternion() * Vector((0.0, 0.0, -1.0))

        # Nur über sichtbare Objekte in der Szene iterieren
        for obj in bpy.context.visible_objects:
            if (obj.type in ['MESH']):       # Nur Meshes
                # Modifier anwenden
                me = obj.to_mesh(self.scene, apply_modifiers=True,settings='PREVIEW')
                wx = obj.location.x
                wy = obj.location.y
                mat = obj.matrix_world
                verts = me.vertices
                edges = me.edges
                for ed in edges:
                    v0_2d = bpy_extras.object_utils.world_to_camera_view(
                                    self.scene, self.cam, mat*verts[ed.vertices[0]].co)
                    v1_2d = bpy_extras.object_utils.world_to_camera_view(
                                    self.scene, self.cam, mat*verts[ed.vertices[1]].co)
                    # Render Size ist 4096x4096 (siehe Dimension Panel)
                    # Aspect Ratio: je nach Seitenverhältnis des Oszis anpassen
                    x0=(v0_2d.x * render_size[0]) 
                    y0=(v0_2d.y * render_size[1]) 
                    x1=(v1_2d.x * render_size[0]) 
                    y1=(v1_2d.y * render_size[1])
                    
                    # Clipping
                    x0,y0,x1,y1=self.cohensutherland(0,0,render_size[0]-1,
                                                         render_size[1]-1,x0,y0,x1,y1)
                    # Bytes schubsen und shiften
                    if (x0!=None):
                        v  = (1) << 30 | (0 & 63) << 24 | (round(x0) & 4095) << 12 | (round(y0) & 4095) << 0
                        vbytes.append((v >> 24) & 0xFF)
                        vbytes.append((v >> 16) & 0xFF)
                        vbytes.append((v >>  8) & 0xFF)
                        vbytes.append((v >>  0) & 0xFF)
                        v  = (1) << 30 | (1 & 63) << 24 | (round(x1) & 4095) << 12 | (round(y1) & 4095) << 0
                        vbytes.append((v >> 24) & 0xFF)
                        vbytes.append((v >> 16) & 0xFF)
                        vbytes.append((v >>  8) & 0xFF)
                        vbytes.append((v >>  0) & 0xFF)

        # Footer
        vbytes.append(1)
        vbytes.append(1)
        vbytes.append(1)
        vbytes.append(1)

        # Auf seriellen Port schreiben
        if (self.sock!=None):
            self.sock.write(vbytes)

# Handler einrichten
class update_it(object):
    def __init__(self):
        self.handle=SerHandle()
        self.handle.send2v()
                       
    def __del__(self):
        bpy.app.handlers.scene_update_post.clear()
        del self.handle
    def __clear__(self):
        bpy.app.handlers.scene_update_post.clear()
        del self.handle

    def scene_update(self,object):
            objects = bpy.data.objects
            if objects.is_updated:
                self.handle.send2v()


# Hinweise wie man den Handler aus einem laufenden Blender stoppt und
# den seriellen Port schliesst willkommen!
if (not HAND):
    handle=SerHandle()
    handle.send2v()
    del handle
else:
# Append Handler
    upd=update_it()
    bpy.app.handlers.scene_update_post.append(upd.scene_update)


