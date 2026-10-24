"""Build, bake, export and review the Earth Shield in Blender."""

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/items/earth_shield/blender_v1"
OUTLINE = [
    (0, .4), (.27, .30), (.269, .13), (.253, -.055),
    (.218, -.205), (.175, -.288), (.102, -.353), (0, -.4),
    (-.102, -.353), (-.175, -.288), (-.218, -.205), (-.253, -.055),
    (-.269, .13), (-.27, .30),
]
MED_Z = .06
PARTS = []
RNG = random.Random(241024)


def front(x, z):
    return .108 - .029 * (x / .27) ** 2 - .009 * (z / .4) ** 2


def node(tree, kind, **inputs):
    result = tree.nodes.new(kind)
    for key, value in inputs.items():
        result.inputs[key].default_value = value
    return result


def math_node(tree, operation, a, b=0):
    result = node(tree, "ShaderNodeMath")
    result.operation = operation
    for index, value in enumerate((a, b)):
        if isinstance(value, (int, float)):
            result.inputs[index].default_value = value
        else:
            tree.links.new(value, result.inputs[index])
    return result.outputs[0]


def ramp(tree, source, stops):
    result = node(tree, "ShaderNodeValToRGB")
    for element in list(result.color_ramp.elements)[2:]:
        result.color_ramp.elements.remove(element)
    for index, (position, color) in enumerate(stops):
        element = result.color_ramp.elements[index] if index < 2 else result.color_ramp.elements.new(position)
        element.position = position
        element.color = (*color, 1)
    tree.links.new(source, result.inputs[0])
    return result.outputs[0]


def mix(tree, factor, a, b, blend="MIX"):
    result = node(tree, "ShaderNodeMixRGB")
    result.blend_type = blend
    for key, value in ((0, factor), (1, a), (2, b)):
        if isinstance(value, (int, float)):
            result.inputs[key].default_value = value
        elif isinstance(value, tuple):
            result.inputs[key].default_value = (*value, 1)
        else:
            tree.links.new(value, result.inputs[key])
    return result.outputs[0]


def material(name, base, roughness=.75, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def noise(tree, scale, detail=3):
    result = node(tree, "ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=.72)
    coords = node(tree, "ShaderNodeTexCoord")
    tree.links.new(coords.outputs["Object"], result.inputs["Vector"])
    return result.outputs["Fac"]


def surface_materials():
    stone = material("Weathered granite", (.14, .12, .09), .88)
    tree = stone.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    broad = noise(tree, 19, 5)
    colors = ramp(tree, broad, [(.28, (.025, .019, .013)), (.69, (.21, .155, .10))])
    grain_node = node(tree, "ShaderNodeTexVoronoi", Scale=660)
    grain_coords = node(tree, "ShaderNodeTexCoord")
    tree.links.new(grain_coords.outputs["Object"], grain_node.inputs["Vector"])
    grain = grain_node.outputs["Distance"]
    flecks = ramp(tree, grain, [(.18, (.10, .095, .083)), (.66, (.78, .74, .66))])
    colors = mix(tree, .62, colors, flecks, "MULTIPLY")
    mineral = ramp(tree, noise(tree, 450, 2), [(.51, (.0, .0, .0)), (.74, (.12, .11, .09))])
    colors = mix(tree, .42, colors, mineral, "ADD")
    fracture = node(tree, "ShaderNodeTexVoronoi", Scale=39)
    fracture.feature = "DISTANCE_TO_EDGE"
    tree.links.new(grain_coords.outputs["Object"], fracture.inputs["Vector"])
    cracks = math_node(tree, "LESS_THAN", fracture.outputs["Distance"], .013)
    cracks = math_node(tree, "MULTIPLY", cracks, math_node(tree, "GREATER_THAN", broad, .53))
    colors = mix(tree, cracks, colors, (.017, .012, .009))
    coords = node(tree, "ShaderNodeTexCoord")
    sep = node(tree, "ShaderNodeSeparateXYZ")
    tree.links.new(coords.outputs["Object"], sep.inputs[0])
    masks = []
    for x, z, rx, rz in [(-.195, -.16 - MED_Z, .048, .12), (.208, .17 - MED_Z, .038, .10)]:
        dx = math_node(tree, "DIVIDE", math_node(tree, "SUBTRACT", sep.outputs["X"], x), rx)
        dz = math_node(tree, "DIVIDE", math_node(tree, "SUBTRACT", sep.outputs["Z"], z), rz)
        dist = math_node(tree, "ADD", math_node(tree, "MULTIPLY", dx, dx), math_node(tree, "MULTIPLY", dz, dz))
        masks.append(math_node(tree, "SUBTRACT", 1, dist))
    moss = math_node(tree, "MAXIMUM", masks[0], masks[1])
    moss = math_node(tree, "MULTIPLY", moss, math_node(tree, "GREATER_THAN", noise(tree, 240, 3), .56))
    moss = math_node(tree, "MAXIMUM", moss, 0)
    colors = mix(tree, moss, colors, (.038, .052, .009))
    tree.links.new(colors, bsdf.inputs["Base Color"])
    spalls = node(tree, "ShaderNodeBump", Strength=.85, Distance=.019)
    tree.links.new(noise(tree, 36, 3), spalls.inputs["Height"])
    bump = node(tree, "ShaderNodeBump", Strength=.9, Distance=.018)
    tree.links.new(spalls.outputs["Normal"], bump.inputs["Normal"])
    height = math_node(tree, "SUBTRACT", noise(tree, 70, 5), math_node(tree, "MULTIPLY", cracks, .25))
    tree.links.new(height, bump.inputs["Height"])
    fine = node(tree, "ShaderNodeBump", Strength=.65, Distance=.0008)
    tree.links.new(grain, fine.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], fine.inputs["Normal"])
    tree.links.new(fine.outputs["Normal"], bsdf.inputs["Normal"])
    rough = node(tree, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = .59
    rough.inputs["To Max"].default_value = .92
    tree.links.new(broad, rough.inputs["Value"])
    tree.links.new(rough.outputs[0], bsdf.inputs["Roughness"])

    materials = [stone]
    for name, low, high, metal in [
        ("Blackened forged iron", (.013, .013, .013), (.055, .050, .041), .86),
        ("Worn bronze", (.105, .061, .027), (.38, .255, .112), .82),
        ("Burnt stone edges", (.009, .006, .004), (.051, .036, .022), 0),
        ("Brown grip leather", (.018, .009, .005), (.073, .032, .014), 0),
    ]:
        mat = material(name, low, .67 if metal else .9, metal)
        tree = mat.node_tree
        bsdf = tree.nodes.get("Principled BSDF")
        tree.links.new(ramp(tree, noise(tree, 145, 3), [(.25, low), (.77, high)]), bsdf.inputs["Base Color"])
        bump = node(tree, "ShaderNodeBump", Strength=.38, Distance=.00025)
        tree.links.new(noise(tree, 950, 2), bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        materials.append(mat)

    magma = material("Recessed magma fissures", (.42, .035, .002), .8)
    tree = magma.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    glow = ramp(tree, noise(tree, 50, 3), [(.38, (.015, .0005, .0001)), (.54, (1, .18, .002)), (.64, (1, .55, .025))])
    tree.links.new(glow, bsdf.inputs["Base Color"])
    tree.links.new(glow, bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1
    materials.append(magma)
    return materials


def mesh(name, vertices, faces, mats, indices=None, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for mat in mats:
        data.materials.append(mat)
    if indices:
        for poly, index in zip(data.polygons, indices):
            poly.material_index = index
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for poly in data.polygons:
        poly.use_smooth = smooth
    PARTS.append(obj)
    return obj


def inset(poly, amount):
    result = []
    for i, point in enumerate(poly):
        p = Vector(point)
        before = (p - Vector(poly[i - 1])).normalized()
        after = (Vector(poly[(i + 1) % len(poly)]) - p).normalized()
        n1, n2 = Vector((before.y, -before.x)), Vector((after.y, -after.x))
        delta = (n1 + n2) * (amount / max(.12, 1 + n1.dot(n2)))
        result.append(tuple(p + delta))
    return result


def clip(poly, nx, nz, offset):
    result = []
    for i, b in enumerate(poly):
        a = poly[i - 1]
        da, db = a[0] * nx + a[1] * nz - offset, b[0] * nx + b[1] * nz - offset
        if (da <= 0) != (db <= 0):
            t = da / (da - db)
            result.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if db <= 0:
            result.append(b)
    return result


def irregular(poly):
    result = []
    for i, end in enumerate(poly):
        start = poly[i - 1]
        a, b = sorted((tuple(round(v, 6) for v in start), tuple(round(v, 6) for v in end)))
        rng = random.Random(repr((a, b)))
        delta = Vector(b) - Vector(a)
        normal = Vector((-delta.y, delta.x)).normalized()
        count = max(1, round(delta.length / .045))
        points = []
        for step in range(count + 1):
            t = step / count
            p = Vector(a).lerp(Vector(b), t)
            if step not in (0, count):
                p += normal * rng.uniform(-.007, .007)
            points.append(tuple(p))
        if tuple(round(v, 6) for v in start) != a:
            points.reverse()
        result.extend(points[:-1])
    return result


def stone_plates(mats):
    seeds = [(-.145, .267), (.121, .26), (-.211, .086), (-.068, .075),
             (.155, .065), (-.177, -.087), (.02, -.075), (.194, -.102),
             (-.106, -.235), (.103, -.24), (-.04, -.345), (.05, -.353)]
    boundary = inset(OUTLINE, .012)
    for index, seed in enumerate(seeds):
        poly = boundary[:]
        for other in seeds:
            if seed == other:
                continue
            nx, nz = other[0] - seed[0], other[1] - seed[1]
            poly = clip(poly, nx, nz, (other[0] ** 2 + other[1] ** 2 - seed[0] ** 2 - seed[1] ** 2) / 2)
        poly = irregular(poly)
        center = sum((Vector(p) for p in poly), Vector((0, 0))) / len(poly)
        outer = [tuple(Vector(p).lerp(center, .013)) for p in poly]
        inner = [tuple(Vector(p).lerp(center, .115)) for p in poly]
        count = len(poly)
        vertices = []
        tilt_x, tilt_z = RNG.uniform(-.035, .035), RNG.uniform(-.025, .025)
        for ring, depth in [(outer, -.047), (outer, -.007), (inner, .003)]:
            for x, z in ring:
                y = front(x, z) + depth
                if ring is inner:
                    y += RNG.uniform(-.0035, .0035) + tilt_x * (x - center.x) + tilt_z * (z - center.y)
                vertices.append((x, y, z))
        vertices.append((center.x + RNG.uniform(-.012, .012), front(*center) + RNG.uniform(.004, .012), center.y))
        faces = [tuple(reversed(range(count)))]
        indices = [0]
        for k in range(2):
            for i in range(count):
                j = (i + 1) % count
                faces.append((k * count + i, k * count + j, (k + 1) * count + j, (k + 1) * count + i))
                indices.append(1 if k == 0 else 0)
        for i in range(count):
            faces.append((2 * count + i, 2 * count + (i + 1) % count, 3 * count))
            indices.append(0)
        obj = mesh(f"Granite plate {index + 1:02d}", vertices, faces, [mats[0], mats[3]], indices)
        for p in obj.data.polygons:
            p.use_smooth = False


def ring_strip(name, outline, cross_section, mats, indices=None):
    count = len(outline)
    vertices = []
    for distance, depth in cross_section:
        for x, z in inset(outline, distance):
            vertices.append((x, front(x, z) + depth, z))
    faces, mat_indices = [], []
    for k in range(len(cross_section)):
        next_k = (k + 1) % len(cross_section)
        for i in range(count):
            j = (i + 1) % count
            faces.append((k * count + i, k * count + j, next_k * count + j, next_k * count + i))
            mat_indices.append(indices[k] if indices else 0)
    return mesh(name, vertices, faces, mats, mat_indices)


def prism(name, poly, depth, thickness, mat, bevel=0):
    count = len(poly)
    vertices = [(x, depth, z) for x, z in poly] + [(x, depth - thickness, z) for x, z in poly]
    faces = [tuple(range(count)), tuple(reversed(range(count, 2 * count)))]
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, j + count, i + count))
    obj = mesh(name, vertices, faces, [mat])
    if bevel:
        modifier = obj.modifiers.new("Small edge bevel", "BEVEL")
        modifier.width, modifier.segments = bevel, 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def rectangle(x, z, w, h):
    return [(x - w / 2, z + h / 2), (x + w / 2, z + h / 2),
            (x + w / 2, z - h / 2), (x - w / 2, z - h / 2)]


def band(name, points, width, offset, mat):
    vertices = []
    for i, (x, z) in enumerate(points):
        tangent = Vector(points[min(i + 1, len(points) - 1)]) - Vector(points[max(0, i - 1)])
        normal = Vector((-tangent.y, tangent.x)).normalized()
        for side, depth in [(-1, .0), (1, .0), (1, -.007), (-1, -.007)]:
            px, pz = Vector((x, z)) + normal * (side * width / 2)
            vertices.append((px, front(px, pz) + offset + depth, pz))
    faces = [(3, 2, 1, 0)]
    for i in range(len(points) - 1):
        for j in range(4):
            faces.append((4 * i + j, 4 * i + (j + 1) % 4, 4 * (i + 1) + (j + 1) % 4, 4 * (i + 1) + j))
    faces.append(tuple(4 * (len(points) - 1) + j for j in range(4)))
    obj = mesh(name, vertices, faces, [mat])
    modifier = obj.modifiers.new("Band edge bevel", "BEVEL")
    modifier.width, modifier.segments = .001, 1
    modifier.affect = "EDGES"
    modifier.angle_limit = math.radians(32)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def radial(name, profile, mat, segments=48, start=0, stop=math.tau):
    closed = abs(stop - start - math.tau) < .001
    n = segments if closed else segments + 1
    vertices = []
    for radius, y in profile:
        for i in range(n):
            angle = start + (stop - start) * i / segments
            vertices.append((radius * math.cos(angle), y, MED_Z + radius * math.sin(angle)))
    faces = []
    for k in range(len(profile)):
        next_k = (k + 1) % len(profile)
        for i in range(segments):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, next_k * n + j, next_k * n + i))
    if not closed:
        faces.extend([tuple(k * n for k in reversed(range(len(profile)))), tuple(k * n + n - 1 for k in range(len(profile)))])
    return mesh(name, vertices, faces, [mat], smooth=True)


def hardware(mats):
    iron, bronze = mats[1:3]
    ring_strip("Forged perimeter", OUTLINE,
               [(0, -.045), (0, .003), (.002, .006), (.018, .006), (.021, .003), (.021, -.043)], [iron])
    ring_strip("Bronze outer edge", OUTLINE, [(.001, .006), (.003, .007), (.0045, .006), (.003, .003)], [bronze])
    ring_strip("Bronze inner edge", OUTLINE, [(.017, .0065), (.0185, .007), (.020, .004), (.019, .002)], [bronze])
    band("Vertical reinforcement", [(0, -.388 + .778 * i / 8) for i in range(9)], .032, .021, iron)
    band("Horizontal reinforcement", [(-.263 + .526 * i / 8, MED_Z) for i in range(9)], .032, .021, iron)
    radial("Medallion backing", [(0, .126), (.087, .126), (.092, .121), (.092, .112), (0, .112)], iron, 40)
    radial("Medallion bronze border", [(.089, .126), (.086, .129), (.0815, .129), (.080, .126)], bronze, 40)
    radial("Seal inner plate", [(0, .131), (.078, .131), (.078, .125), (0, .125)], iron, 40)
    for label, start, stop in [("Right", -80, 80), ("Left", 100, 260)]:
        radial(label + " broken seal arc", [(.067, .135), (.059, .135), (.059, .131), (.067, .131)], bronze, 20,
               math.radians(start), math.radians(stop))
    prism("Seal vertical stroke", rectangle(0, MED_Z, .009, .144), .136, .005, bronze, .0008)
    for side in (-1, 1):
        prism("Seal triangle", [(side * .061, MED_Z + .010), (side * .078, MED_Z), (side * .061, MED_Z - .010)], .135, .004, bronze)
    mounts = [(0, .367, .042, .052), (-.244, .289, .041, .044), (.244, .289, .041, .044),
              (-.246, MED_Z, .041, .046), (.246, MED_Z, .041, .046),
              (-.161, -.282, .036, .043), (.161, -.282, .036, .043), (0, -.368, .040, .044),
              (0, .183, .034, .034), (0, -.072, .034, .034),
              (-.121, MED_Z, .033, .034), (.121, MED_Z, .033, .034)]
    for index, (x, z, w, h) in enumerate(mounts):
        depth = front(x, z) + .028
        prism(f"Rivet mounting plate {index:02d}", rectangle(x, z, w, h), depth, .006, iron, .001)
        ring_strip(f"Mount bronze edge {index:02d}", rectangle(x, z, w - .003, h - .003),
                   [(0, .029), (.001, .030), (.0017, .029), (.001, .027)], [bronze])
        vertices = [(x - .008, depth + .001, z - .008), (x + .008, depth + .001, z - .008),
                    (x + .008, depth + .001, z + .008), (x - .008, depth + .001, z + .008),
                    (x + .0007, depth + .007, z + .0004)]
        mesh(f"Pyramid rivet {index:02d}", vertices, [(0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], [bronze])


def cylinder_between(name, a, b, radius, mat, vertices=10):
    a, b = Vector(a), Vector(b)
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=delta.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    PARTS.append(obj)
    return obj


def rear_fittings(mats):
    iron, bronze, leather = mats[1], mats[2], mats[4]
    band("Rear vertical spine", [(0, -.36 + .72 * i / 4) for i in range(5)], .022, -.052, iron)
    band("Rear horizontal support", [(-.23 + .46 * i / 4, MED_Z) for i in range(5)], .023, -.052, iron)
    for x in (-.072, .072):
        cylinder_between("Grip standoff", (x, .0, MED_Z), (x, front(x, MED_Z) - .049, MED_Z), .008, iron, 8)
        prism("Rear grip foot", rectangle(x, MED_Z, .027, .046), front(x, MED_Z) - .050, .003, iron, .001)
    cylinder_between("Leather-wrapped handgrip", (-.072, 0, MED_Z), (.072, 0, MED_Z), .0105, leather, 12)
    for i in range(9):
        x = -.062 + .124 * i / 8
        cylinder_between("Leather wrap seam", (x - .0006, 0, MED_Z), (x + .0006, 0, MED_Z), .0111, leather, 12)
    vertices = []
    for i in range(13):
        t = i / 12
        x = .105 + .095 * t
        y = front(x, -.065) - .050 - .075 * math.sin(math.pi * t)
        for dz, dy in [(-.015, 0), (.015, 0), (.015, -.004), (-.015, -.004)]:
            vertices.append((x, y + dy, -.065 + dz))
    faces = [(3, 2, 1, 0)]
    for i in range(12):
        for j in range(4):
            faces.append((4 * i + j, 4 * i + (j + 1) % 4, 4 * (i + 1) + (j + 1) % 4, 4 * (i + 1) + j))
    faces.append(tuple(48 + j for j in range(4)))
    mesh("Leather forearm strap", vertices, faces, [leather], smooth=True)
    for x in (.105, .2):
        prism("Strap mounting tab", rectangle(x, -.065, .022, .042), front(x, -.065) - .053, .003, iron, .001)
        cylinder_between("Strap rivet", (x, front(x, -.065) - .058, -.065),
                         (x, front(x, -.065) - .062, -.065), .004, bronze, 8)


def core(mats):
    outline = inset(OUTLINE, .014)
    n = len(outline)
    vertices = [(x, front(x, z) - .0065, z) for x, z in outline]
    vertices += [(x, front(x, z) - .050, z) for x, z in outline]
    vertices += [(x * .5, front(x * .5, z * .5) - .0065, z * .5) for x, z in outline]
    vertices.append((0, front(0, 0) - .0065, 0))
    vertices.append((0, front(0, 0) - .050, 0))
    faces, indices = [], []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([(i, j, 2 * n + j, 2 * n + i), (2 * n + i, 2 * n + j, 3 * n),
                      (i + n, 3 * n + 1, j + n), (i, i + n, j + n, j)])
        indices.extend([0, 0, 1, 1])
    mesh("Continuous shield core", vertices, faces, [mats[5], mats[0]], indices)


def join_and_unwrap():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in PARTS:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = "earth_shield"
    for vertex in obj.data.vertices:
        vertex.co.z -= MED_Z
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    triangulate = obj.modifiers.new("Export triangulation", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    obj.data.name = "EarthShield"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.004, area_weight=.35)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.data.uv_layers.active.name = "UVMap"
    return obj


def bake(obj, resolution):
    scene = bpy.context.scene
    scene.cycles.samples = 16
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = 12
    original_materials = list(obj.data.materials)
    images = {}
    for channel, kind, color_space in [
        ("base_color", "EMIT", "sRGB"), ("roughness", "EMIT", "Non-Color"),
        ("normal", "NORMAL", "Non-Color"), ("emission", "EMIT", "sRGB"),
        ("metallic", "EMIT", "Non-Color"),
    ]:
        image = bpy.data.images.new("earth_shield_" + channel, resolution, resolution, alpha=False)
        image.colorspace_settings.name = color_space
        targets, outputs = [], []
        for mat in original_materials:
            tree = mat.node_tree
            target = tree.nodes.new("ShaderNodeTexImage")
            target.image = image
            tree.nodes.active = target
            targets.append((tree, target))
            if channel in ("base_color", "roughness", "metallic"):
                out = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
                original = out.inputs["Surface"].links[0].from_socket
                bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
                emit = node(tree, "ShaderNodeEmission")
                socket = bsdf.inputs[{"base_color": "Base Color", "roughness": "Roughness", "metallic": "Metallic"}[channel]]
                if socket.is_linked:
                    tree.links.new(socket.links[0].from_socket, emit.inputs["Color"])
                else:
                    value = socket.default_value
                    emit.inputs["Color"].default_value = (value, value, value, 1) if isinstance(value, (int, float)) else value
                tree.links.new(emit.outputs[0], out.inputs["Surface"])
                outputs.append((tree, out, original, emit))
        print("BAKE", channel, flush=True)
        bpy.ops.object.bake(type=kind)
        image.filepath_raw = str(OUT / "textures" / (channel + ".png"))
        image.file_format = "PNG"
        image.save()
        image.pack()
        images[channel] = image
        for tree, out, original, emit in outputs:
            tree.links.new(original, out.inputs["Surface"])
            tree.nodes.remove(emit)
        for tree, target in targets:
            tree.nodes.remove(target)

    mat = material("Earth Shield | baked PBR", (.5, .5, .5))
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    for channel, socket in [("base_color", "Base Color"), ("roughness", "Roughness"),
                            ("metallic", "Metallic"), ("emission", "Emission Color")]:
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = images[channel]
        tree.links.new(tex.outputs["Color"], bsdf.inputs[socket])
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = images["normal"]
    normal = node(tree, "ShaderNodeNormalMap")
    tree.links.new(tex.outputs["Color"], normal.inputs["Color"])
    tree.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Emission Strength"].default_value = 1
    for poly in obj.data.polygons:
        poly.material_index = 0
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Neutral studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.21, .23, .26, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .45
    scene.world = world
    for name, position, power, size, color in [
        ("Soft key", (-1.1, 1.2, 1.5), 105, 1.3, (1, .91, .79)),
        ("Cool fill", (1.0, .65, .45), 45, 1.0, (.73, .84, 1)),
        ("Rim", (.2, -.9, 1.1), 85, 1.0, (1, .91, .79)),
    ]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size, light.color = power, "DISK", size, color
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        aim(obj, (0, .06, -.06))
    camera = bpy.data.objects.new("Review camera", bpy.data.cameras.new("Review camera"))
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = .94
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    return camera


def render_views(camera, prefix="", resolution=900):
    scene = bpy.context.scene
    scene.render.resolution_x = round(resolution * .85)
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    for name, location in [
        ("front", (0, 2.0, -.06)), ("three_quarter", (-.68, 2, .12)),
        ("rear", (.60, -2, .22)), ("side", (-2, .05, -.06)),
    ]:
        camera.location = location
        aim(camera, (0, .045, -.06))
        scene.render.filepath = str(OUT / (prefix + name + ".png"))
        bpy.ops.render.render(write_still=True)
    camera.location = (-.68, 2, .12)
    aim(camera, (0, .045, -.06))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--texture-size", type=int, default=2048)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "textures").mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 16
    mats = surface_materials()
    core(mats)
    stone_plates(mats)
    hardware(mats)
    rear_fittings(mats)
    obj = join_and_unwrap()
    obj.data.calc_loop_triangles()
    print("GEOMETRY", len(obj.data.loop_triangles), "triangles", tuple(obj.dimensions), flush=True)
    if not args.preview:
        bake(obj, args.texture_size)
        obj.data.calc_loop_triangles()
        for poly in obj.data.polygons:
            if poly.area < 1e-12:
                print("DEGENERATE", poly.index)
        obj["asset"] = "Shield of the Earth"
        obj["grip_origin"] = "Rear handgrip center"
        obj["front_axis_blender"] = "+Y"
        obj["up_axis_blender"] = "+Z"
        obj["body_thickness_m"] = .060
        bpy.ops.export_scene.gltf(filepath=str(OUT / "earth_shield.glb"), export_format="GLB",
                                  use_selection=True, use_active_scene=True, export_apply=True, export_texcoords=True,
                                  export_normals=True, export_tangents=True, export_extras=True)
    camera = studio()
    render_views(camera, "preview_" if args.preview else "", 800 if args.preview else 1200)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / ("earth_shield_preview.blend" if args.preview else "earth_shield.blend")))
    bpy.context.view_layer.update()
    obj.data.calc_loop_triangles()
    bounds = [[min(v.co[i] for v in obj.data.vertices), max(v.co[i] for v in obj.data.vertices)] for i in range(3)]
    report = {
        "date": "2026-10-24", "tool": "Blender " + bpy.app.version_string,
        "method": "Procedural bpy modeling; the delivered asset also received interactive Blender MCP review on pc4090.",
        "reference": "assets/items/earth_shield/concept_v1/concept.png",
        "triangles": len(obj.data.loop_triangles),
    }
    report.update(dimensions_m=list(obj.dimensions), bounds_blender_m=bounds,
                  origin_blender_m=list(obj.location), scale=list(obj.scale), rotation_euler=list(obj.rotation_euler),
                  texture_resolution=args.texture_size, preview=args.preview)
    (OUT / ("preview_geometry.json" if args.preview else "generation.json")).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
