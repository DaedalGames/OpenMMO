import assert from "node:assert/strict";
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { execFileSync } from "node:child_process";
import * as THREE from "../client/node_modules/three/build/three.module.js";
import { headlessThree, clipSampler, hash } from "./lib/headless-three.mjs";
import { ensureFemalePreview } from "./lib/ensure-female-preview.mjs";

await ensureFemalePreview("animations");
const directory = "assets/items/female_barbarian_helmet/tripo_v2/fitted_v1";
const { server, load } = await headlessThree();
const temporary = [];
try {
  const { bindModularPart } = await server.ssrLoadModule(
    "/src/lib/utils/modularCharacter.ts",
  );
  const base = await load(
    "assets/modular_human_female_01/rig_v1/female-base.glb",
  );
  for (const data of JSON.parse(
    readFileSync("assets/modular_human_female_01/preview/animations.json"),
  ).clips) {
    const clip = THREE.AnimationClip.parse(data);
    const index = base.animations.findIndex(
      (entry) => entry.name === clip.name,
    );
    if (index < 0) base.animations.push(clip);
    else base.animations[index] = clip;
  }
  const helmetPath = `${directory}/helmet_female_barbarian.glb`;
  const [helmet] = bindModularPart(base.scene, (await load(helmetPath)).scene);
  const skeleton = helmet.skeleton;
  const head = skeleton.bones.findIndex((bone) => bone.name === "Head");
  const inverse = new THREE.Matrix4();
  const point = new THREE.Vector3();
  const sample = clipSampler(base.scene, {
    samples: 17,
    restore: skeleton.bones,
  });
  for (const name of ["bob", "knight"]) {
    const path = `${directory}/hair_${name}_barbarian_helmet.glb`;
    const hair = bindModularPart(base.scene, (await load(path)).scene);
    for (const mesh of hair) {
      assert.equal(mesh.skeleton.bones.length, 65);
      for (let i = 0; i < 65; i++)
        assert.equal(mesh.skeleton.bones[i], skeleton.bones[i]);
    }
    const rows = [];
    const frames = [];
    let maximumRigidError = 0;
    const measure = (name, time) => {
      base.scene.updateMatrixWorld(true);
      skeleton.update();
      inverse
        .multiplyMatrices(
          skeleton.bones[head].matrixWorld,
          skeleton.boneInverses[head],
        )
        .invert();
      for (const mesh of hair) {
        mesh.skeleton.update();
        const attrs = mesh.geometry.attributes;
        for (let i = 0; i < attrs.position.count; i++) {
          mesh
            .getVertexPosition(i, point)
            .applyMatrix4(mesh.matrixWorld)
            .applyMatrix4(inverse);
          rows.push(point.x, point.y, point.z);
          let share = 0;
          for (let j = 0; j < 4; j++)
            if (attrs.skinIndex.getComponent(i, j) === head)
              share += attrs.skinWeight.getComponent(i, j);
          if (share > 0.9999999) {
            maximumRigidError = Math.max(
              maximumRigidError,
              point.distanceTo(
                new THREE.Vector3().fromBufferAttribute(attrs.position, i),
              ),
            );
          }
        }
      }
      frames.push({ name, time });
    };
    measure("rest", 0);
    for (const clip of base.animations)
      for (const { time } of sample(clip)) measure(clip.name, time);
    assert(
      maximumRigidError < 3.6e-6,
      "Rigid hair must follow the helmet Head space",
    );
    const prefix = `${directory}/hair-${name}-poses`;
    writeFileSync(prefix + ".bin", Buffer.from(new Float32Array(rows).buffer));
    writeFileSync(
      prefix + ".json",
      JSON.stringify({
        helmet_sha256: hash(helmetPath),
        hair_sha256: hash(path),
        frames,
        maximum_rigid_error: maximumRigidError,
        meshes: hair.map((mesh) => ({
          vertices: mesh.geometry.attributes.position.count,
          faces: Array.from(mesh.geometry.index.array),
        })),
      }),
    );
    temporary.push(prefix + ".bin", prefix + ".json");
    for (const mesh of hair) mesh.removeFromParent();
  }
  execFileSync(
    ".venv/bin/python",
    ["tools/validate-female-barbarian-helmet-hair.py"],
    { stdio: "inherit" },
  );
} finally {
  for (const file of temporary) unlinkSync(file);
  await server.close();
}
