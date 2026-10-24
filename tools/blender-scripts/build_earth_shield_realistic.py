"""Photoreal Earth Shield revision, using the project concept as a texture source."""

import importlib.util
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise


SCRIPT = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location("earth_shield_base", SCRIPT.with_name("build_earth_shield.py"))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUT = base.ROOT / "assets/items/earth_shield/blender_v2_realistic"
REFERENCE = base.ROOT / "assets/items/earth_shield/concept_v1/concept.png"
PHOTO_ROWS = [(18,529,529),(72,445,665),(130,335,859),(200,197,976),(350,201,964),
              (538,200,948),(700,220,928),(900,261,880),(1100,357,770),(1200,432,678),(1284,550,550)]
PHOTO_PLATES = [
    [(237,244),(461,133),(480,188),(478,252),(468,310),(484,335),(469,386),(434,427),(389,456),(344,427),(302,401),(267,367),(243,349)],
    [(240,365),(267,366),(307,405),(345,425),(384,448),(424,452),(405,490),(394,513),(240,512)],
    [(564,123),(833,179),(854,227),(838,275),(835,349),(798,390),(796,438),(749,469),(718,510),(634,511),(592,477),(575,448),(574,384),(551,336),(550,273),(555,207)],
    [(838,181),(879,195),(876,259),(851,282),(840,255)],
    [(875,275),(909,295),(895,463),(849,500),(731,508),(753,474),(792,444),(803,394),(832,359),(840,315)],
    [(248,591),(388,586),(407,629),(429,655),(472,664),(485,742),(465,803),(432,848),(396,839),(369,817),(321,804),(282,764),(256,703)],
    [(284,780),(322,803),(363,818),(399,849),(438,853),(459,900),(456,964),(424,970),(393,955),(356,923),(326,875),(306,843)],
    [(358,938),(406,962),(454,974),(469,1030),(483,1080),(483,1138),(449,1111),(417,1071),(393,1030),(374,987)],
    [(635,583),(861,577),(845,693),(816,792),(770,793),(729,772),(690,762),(659,743),(652,714),(628,684),(615,648)],
    [(650,762),(695,776),(726,788),(769,803),(813,809),(777,906),(737,971),(700,1024),(658,1078),(631,1058),(594,1001),(569,978),(548,961),(549,915),(564,872),(586,837),(605,800)],
    [(554,1002),(585,1014),(612,1058),(633,1091),(610,1136),(574,1172),(550,1191)],
]

def interpolate(rows, value):
    if value <= rows[0][0]:
        return rows[0][1:]
    for a, b in zip(rows, rows[1:]):
        if value <= b[0]:
            t = (value - a[0]) / (b[0] - a[0])
            return tuple(x + (y - x) * t for x, y in zip(a[1:], b[1:]))
    return rows[-1][1:]

def extent(z):
    rows = sorted({(round(p[1], 6), round(abs(p[0]), 6)) for p in base.OUTLINE if p[0] >= 0})
    return max(.00001, interpolate(rows, z)[0])

def photo_point(u, v):
    z = .06 + (538 - v) / (1529.4117647 if v < 538 else 1621.7391304)
    left, right = interpolate(PHOTO_ROWS, v)
    center = interpolate([(18,529),(538,535),(1284,550)], v)[0]
    x = (center - u) / max(1, center - left if u < center else right - center) * extent(z)
    return x, z

def reference_uv(x, z):
    v = 538 - (z - .06) * (1529.4117647 if z > .06 else 1621.7391304)
    left, right = interpolate(PHOTO_ROWS, v)
    center = interpolate([(18,529),(538,535),(1284,550)], v)[0]
    u = center - x / extent(z) * (center - left if x >= 0 else right - center)
    return u / 1145, 1 - v / 1374

def photo_color(tree, image):
    uv = base.node(tree, "ShaderNodeUVMap")
    uv.uv_map = "ReferenceUV"
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tree.links.new(uv.outputs[0], tex.inputs["Vector"])
    return tex.outputs["Color"]

def magma_mask(tree, color):
    rgb = base.node(tree, "ShaderNodeSeparateColor")
    tree.links.new(color, rgb.inputs[0])
    a = base.math_node(tree, "GREATER_THAN", rgb.outputs[0], .50)
    b = base.math_node(tree, "GREATER_THAN", rgb.outputs[0], base.math_node(tree, "MULTIPLY", rgb.outputs[1], 1.8))
    c = base.math_node(tree, "GREATER_THAN", rgb.outputs[1], base.math_node(tree, "MULTIPLY", rgb.outputs[2], 2.1))
    return base.math_node(tree, "MULTIPLY", a, base.math_node(tree, "MULTIPLY", b, c))

def metal_materials():
    materials = [None]
    for name, low, high, metal, roughness in [
        ("V2 hammered iron", (.012,.014,.014), (.095,.079,.058), .86, .49),
        ("V2 weathered bronze", (.10,.063,.027), (.40,.30,.17), .88, .44),
        ("V2 charred crevice", (.005,.003,.002), (.028,.017,.009), 0, .94),
        ("V2 worn leather", (.011,.005,.002), (.075,.032,.013), 0, .81),
    ]:
        mat=base.material(name,low,roughness,metal)
        tree=mat.node_tree
        bsdf=tree.nodes.get("Principled BSDF")
        color=base.ramp(tree,base.noise(tree,65,4),[(.25,low),(.77,high)])
        rust=base.math_node(tree,"GREATER_THAN",base.noise(tree,250,3),.64)
        rust=base.math_node(tree,"MULTIPLY",rust,.6 if metal else 0)
        tree.links.new(base.mix(tree,rust,color,(.13,.042,.012)),bsdf.inputs["Base Color"])
        if metal:
            tree.links.new(base.math_node(tree,"SUBTRACT",metal,base.math_node(tree,"MULTIPLY",rust,.7)),bsdf.inputs["Metallic"])
            tree.links.new(base.math_node(tree,"ADD",roughness,base.math_node(tree,"MULTIPLY",rust,.45)),bsdf.inputs["Roughness"])
        bevel=base.node(tree,"ShaderNodeBevel",Radius=.0007)
        bevel.samples=4
        bump=base.node(tree,"ShaderNodeBump",Strength=.45,Distance=.00019 if metal else .00045)
        tree.links.new(base.noise(tree,760,3),bump.inputs["Height"])
        tree.links.new(bevel.outputs[0],bump.inputs["Normal"])
        tree.links.new(bump.outputs[0],bsdf.inputs["Normal"])
        materials.append(mat)
    return materials + [None]

def traced_materials():
    materials = metal_materials()
    image = bpy.data.images.load(str(REFERENCE), check_existing=True)
    for name, target in [("V2 reference granite", 0), ("V2 deep rock fissures", 5)]:
        mat = base.material(name, (.08, .06, .04), .79)
        tree = mat.node_tree
        bsdf = tree.nodes.get("Principled BSDF")
        color = photo_color(tree, image)
        shade = base.node(tree, "ShaderNodeHueSaturation", Value=.70)
        tree.links.new(color, shade.inputs["Color"])
        geometry = base.node(tree, "ShaderNodeNewGeometry")
        normal = base.node(tree, "ShaderNodeSeparateXYZ")
        tree.links.new(geometry.outputs["Normal"], normal.inputs[0])
        front_mask = base.math_node(tree, "GREATER_THAN", normal.outputs["Y"], .25)
        rear = base.ramp(tree, base.noise(tree, 190, 4), [(.25, (.03, .023, .017)), (.75, (.16, .12, .08))])
        tree.links.new(base.mix(tree, front_mask, rear, shade.outputs["Color"]), bsdf.inputs["Base Color"])
        emission = base.mix(tree, base.math_node(tree, "MULTIPLY", magma_mask(tree, color), front_mask), (0,0,0), color)
        tree.links.new(emission, bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.6
        bw = base.node(tree, "ShaderNodeRGBToBW")
        tree.links.new(color, bw.inputs[0])
        bump = base.node(tree, "ShaderNodeBump", Strength=.55, Distance=.00065)
        tree.links.new(bw.outputs[0], bump.inputs["Height"])
        tree.links.new(bump.outputs[0], bsdf.inputs["Normal"])
        materials[target] = mat
    return materials

def traced_stones(materials):
    for index, source in enumerate(PHOTO_PLATES):
        poly = [photo_point(u,v) for u,v in source]
        area = sum(poly[i-1][0]*p[1]-p[0]*poly[i-1][1] for i,p in enumerate(poly))
        if area > 0:
            poly.reverse()
        center = sum((Vector(p) for p in poly),Vector((0,0))) / len(poly)
        n = len(poly)
        vertices = []
        for factor, depth in [(0,-.046), (0,-.008), (.08,.004), (.52,.014)]:
            for point in poly:
                x,z = Vector(point).lerp(center,factor)
                y = base.front(x,z)+depth
                if factor:
                    y += noise.noise_vector(Vector((x*46,z*46,index*3.1))).x*.004
                vertices.append((x,y,z))
        vertices.append((center.x,base.front(*center)+.016,center.y))
        faces=[tuple(reversed(range(n)))]
        indices=[0]
        for k in range(3):
            for i in range(n):
                j=(i+1)%n
                faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
                indices.append(1 if k==0 else 0)
        for i in range(n):
            faces.append((3*n+i,3*n+(i+1)%n,4*n))
            indices.append(0)
        obj=base.mesh(f"Traced granite fragment {index:02}",vertices,faces,[materials[0],materials[3]],indices)
        for p in obj.data.polygons:
            p.use_smooth=p.index>2*n
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        for e in bm.edges:
            if len(e.link_faces)==2 and e.link_faces[0].smooth != e.link_faces[1].smooth:
                e.smooth=False
        bm.to_mesh(obj.data)
        bm.free()

def create_scene():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "textures").mkdir(exist_ok=True)
    scene = bpy.data.scenes.new("Earth Shield — realistic")
    bpy.context.window.scene = scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    base.PARTS.clear()
    mats = traced_materials()
    base.core(mats)
    traced_stones(mats)
    base.hardware(mats)
    old_centers=[(0,.367),(-.244,.289),(.244,.289),(-.246,.06),(.246,.06),(-.161,-.282),(.161,-.282),(0,-.368),(0,.183),(0,-.072),(-.121,.06),(.121,.06)]
    photo_centers=[(519,72),(900,192),(220,244),(881,540),(219,551),(790,972),(346,927),(532,1229),(516,382),(513,698),(647,545),(375,542)]
    for index,(old,image_point) in enumerate(zip(old_centers,photo_centers)):
        x,z=photo_point(*image_point)
        for obj in base.PARTS:
            if any(obj.name.startswith(label+f" {index:02}") for label in ["Rivet mounting plate","Mount bronze edge","Pyramid rivet"]):
                for v in obj.data.vertices:
                    v.co.x += x-old[0]
                    v.co.z += z-old[1]
                    v.co.y += base.front(x,z)-base.front(*old)
    for obj in base.PARTS:
        if "Medallion" in obj.name or "Seal inner" in obj.name or "seal arc" in obj.name:
            modifier = obj.modifiers.new("Crisp metal profile", "EDGE_SPLIT")
            modifier.split_angle = math.radians(32)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        if any(word in obj.name for word in ["Medallion", "Seal ", "seal arc"]):
            for v in obj.data.vertices:
                v.co.x *= .91
                v.co.z = base.MED_Z + (v.co.z-base.MED_Z)*.84
    base.rear_fittings(mats)
    shield = base.join_and_unwrap()
    shield.name = "earth_shield_realistic"
    uv=shield.data.uv_layers.new(name="ReferenceUV")
    for loop in shield.data.loops:
        p=shield.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=reference_uv(p.x,p.z+base.MED_Z)
    shield.data.uv_layers.active_index=0
    shield.data.uv_layers["UVMap"].active_render=True
    shield.data.calc_loop_triangles()
    camera = base.studio()
    camera.location = (-.68, 2, .12)
    base.aim(camera, (0, .045, -.06))
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .22
    for name, size, energy in [("Soft key", .65, 110), ("Cool fill", 1.0, 28), ("Rim", .65, 90)]:
        lamp = next(o for o in scene.objects if o.type == "LIGHT" and o.name.startswith(name))
        lamp.data.size, lamp.data.energy = size, energy
    scene.render.resolution_x, scene.render.resolution_y = 1020, 1200
    scene.cycles.samples = 64
    scene.cycles.device = "GPU"
    return scene, shield, camera

def bake(shield, resolution=2048):
    base.OUT = OUT
    for mat in shield.data.materials:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            bsdf.inputs["Emission Strength"].default_value = 1
    base.bake(shield, resolution)
    mat = shield.data.materials[0]
    mat.use_backface_culling = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 1.6
    shield.data.uv_layers.remove(shield.data.uv_layers["ReferenceUV"])
