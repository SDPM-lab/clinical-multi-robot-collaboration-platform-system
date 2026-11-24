"""Render static proof frames directly from MediSync GLBs and its feature layout."""
import json, math, struct, tempfile
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

video=Path(__file__).resolve().parents[1]
source=video.parent/"frontend/public"
out=video/"public/ppo-spatial"
out.mkdir(exist_ok=True)
mapping=json.loads((source/"generated/dispatch-route-mapping.json").read_text())
annotations = {}

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=24
    scene.cycles.use_denoising=False
    scene.render.resolution_x=1600
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new("Soft studio")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.78,.83,.93,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value=.56
    scene.view_settings.view_transform="AgX"

def imported(path):
    previous=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in previous]

def load_floor():
    # Match DispatchMapScene's selected GLTF scene; other bundled scenes are variants.
    data=(source/"models/L1__flat.glb").read_bytes()
    n,_=struct.unpack_from("<II",data,12)
    document=json.loads(data[20:20+n])
    document["scenes"]=[s for s in document["scenes"] if s.get("name")==mapping["glbScene"]]
    assert len(document["scenes"])==1
    document["scene"]=0
    buf=json.dumps(document,separators=(",",":")).encode()
    buf+=b" "*((-len(buf))%4)
    tail=data[20+n:]
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"model.glb"
        p.write_bytes(struct.pack("<4sIIII",b"glTF",2,20+len(buf)+len(tail),len(buf),0x4e4f534a)+buf+tail)
        objects=imported(p)
    for o in objects:
        if o.type in {"CAMERA","LIGHT"} or o.name.startswith(("Route_","RouteNode_","Preview_Ground","Label_")):
            o.hide_render=True

def orient(obj,p):
    obj.rotation_euler=(Vector(p)-obj.location).to_track_quat("-Z","Y").to_euler()

def rig(target, delta, span, area):
    scene=bpy.context.scene
    bpy.ops.object.camera_add(location=Vector(target)+Vector(delta))
    camera=bpy.context.object
    orient(camera,target)
    camera.data.type="ORTHO"
    camera.data.ortho_scale=span
    scene.camera=camera
    for offset, strength, tint in [((-0.6,-0.7,1.3),1.15,(1,.89,.76)),((.65,.12,.95),.63,(.78,.87,1)),((.04,.75,.8),.8,(1,.94,.86))]:
        position=Vector(target)+Vector(offset)*area
        bpy.ops.object.light_add(type="AREA",location=position)
        light=bpy.context.object
        light.data.energy=strength*area*area*75
        light.data.color=tint
        light.data.shape="DISK"
        light.data.size=area*1.0
        orient(light,target)
    return camera

def waypoint(key):
    x,y,z=mapping["displayNodes"][key]["position"]
    return Vector((x,-z,y))

def robot_template():
    objs=imported(source/"models/AGIBOT_A2D.glb")
    bpy.context.view_layer.update()
    meshes=[(o.data,o.matrix_world.copy()) for o in objs if o.type=="MESH"]
    corners=[o.matrix_world@Vector(c) for o in objs if o.type=="MESH" for c in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in corners) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in corners) for i in range(3)))
    center=(lo+hi)/2
    center.z=lo.z
    for o in objs:bpy.data.objects.remove(o,do_unlink=True)
    return meshes,center,hi.z-lo.z

def robot(template,name,where,height,muted=False):
    meshes,center,original=template
    transform=Matrix.Translation(where)@Matrix.Scale(height/original,4)@Matrix.Translation(-center)
    for i,(mesh,matrix) in enumerate(meshes):
        o=bpy.data.objects.new(f"{name} mesh {i}",mesh)
        bpy.context.collection.objects.link(o)
        o.matrix_world=transform@matrix
        if muted:
            for slot in o.material_slots:
                if slot.material:
                    slot.link="OBJECT"
                    slot.material=quiet

def material(name,color,rough=.55):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*color,1)
    bsdf.inputs["Roughness"].default_value=rough
    return m

def cube(name,point,dimensions,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=point)
    obj=bpy.context.object;obj.name=name;obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat)
    mod=obj.modifiers.new("Machined edges","BEVEL");mod.width=bevel;mod.segments=3
    obj.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    return obj

def render(name, camera, labels=()):
    scene=bpy.context.scene
    scene.render.filepath=str(out/(name+".png"))
    bpy.context.view_layer.update()
    coords={}
    for label,pos in labels:
        q=world_to_camera_view(scene,camera,Vector(pos))
        coords[label]=[round(q.x,4),round(1-q.y,4)]
    annotations[name]=coords
    bpy.ops.render.render(write_still=True)

reset()
load_floor()
cam=rig((.6,1,.1),(18,-27,33),43,39)
rooms=[(label,waypoint(key)) for label,key in [
    ("Pharmacy","pharmacy_dock"),("Ward A","ward_a_dock"),("Nurse Station","nurse_station_dock")]]
render("hospital",cam,rooms)

# Spatial demo positions, separate from the offline encoder's snapshot.
# The map's published dock stations determine their room anchors.
template=robot_template()
quiet=material("De-emphasized candidates",(.30,.32,.35))
deploy=[
    ("M01","pharmacy_dock",(.0,.0,0),True),
    ("M02","ward_a_dock",(0,0,0),True),
    ("C01","laboratory_dock",(0,0,0),False),
    ("C02","nurse_station_dock",(0,0,0),False),
    ("W01","charging_dock",(-.18,-.45,0),False),
    ("W02","charging_dock",(.35,.1,0),False),
    ("W03","charging_dock",(-.12,.61,0),False),
]
labels=[]
for name,room,offset,active in deploy:
    if room not in mapping["displayNodes"]:
        room="nurse_station_dock"
    pos=waypoint(room)+Vector(offset)
    robot(template,name,pos,1.28,not active)
    labels.append((name,pos+Vector((0,0,1.62))))
render("candidates",cam,labels)

reset()
template=robot_template()
robot(template,"M01",(0,0,0),1.65)
platform=material("Ceramic display riser",(.76,.73,.70))
cube("Studio plinth",(0,0,-.085),(1.85,1.85,.17),platform,.065)
cam=rig((0,0,.74),(2.9,-4.8,2.15),3.8,3.9)
render("hero",cam)

reset()
load_floor()
template=robot_template()
pos=waypoint("pharmacy_dock")
robot(template,"M01",pos,1.28)
cam=rig(pos+Vector((-1.5,1.65,-.25)),(12,-20,9),11.8,15)
render("match",cam,[("M01",pos+Vector((0,0,1.62)))])

reset()
bases=[material("Task one-hots",(.80,.29,.085)),material("Robot state",(.31,.32,.34)),material("Projected work",(.55,.36,.27))]
surface=material("Feature plane",(.79,.75,.69))
labels=[]
for i,(count,columns) in enumerate([(41,9),(35,7),(22,7)]):
    z=1.35-i*.65
    cube(f"Feature group {i+1}",(0,0,z),(4.25,2.8,.11),surface,.075)
    for k in range(count):
        x=-1.70+(k%columns)*.385
        y=.92-(k//columns)*.44
        cube(f"Feature {i+1}.{k+1}",(x,y,z+.095),(.26,.29,.08),bases[i],.033)
    labels.append((str(count),(2.10,-1.4,z+.055)))
cam=rig((0,0,.52),(5,-7,5.5),6.8,5.7)
render("matrix",cam,labels)

(video/"src/ppo-spatial-anchors.json").write_text(json.dumps(annotations,indent=2)+"\n")
