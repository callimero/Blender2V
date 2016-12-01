# Curves zu C Export für teensyv/V.st
# cw@blenderbuch.de 2016

import bpy

scale=10       # Skalierung
out=""

# über selektierte Objekte iterieren
for ob in bpy.context.selected_objects:
    count=0
    if (ob.type in ['CURVE']):  # nur Curves
        me = ob.data
        wx = ob.location.x
        wy = ob.location.y
        mat = ob.matrix_world
        splines = ob.data.splines
        splines[0].use_cyclic_u
        sptxt=""        
        for idx,spline in enumerate(splines):
            if (idx>0): # Ende des vorherigen Kurvenzugs
                sptxt+="-127,-127,\n"
                count+=1
            
            for point in spline.points:
                count+=1
                pscale = point.co*scale
                sptxt+=str(int(pscale.x))+","+str(int(pscale.y))+",\n"
            if(spline.use_cyclic_u):    # Wenn geschlossene Kurve
                count+=1
                sptxt+=str(int(spline.points[0].co.x*scale))+","+str(int(spline.points[0].co.y*scale))+",\n"
        
        out += "{"+str(count)+",          //"+ob.name+"\n"
        out += sptxt

    out+="},\n\n"

print(out)  # Konsole
txt = bpy.data.texts.new(name=bpy.context.active_object.name+".c")   # neuer Textpuffer         
txt.write(out)  # in Textpuffer
