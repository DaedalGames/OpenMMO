import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import * as THREE from "../client/node_modules/three/build/three.module.js";
import { headlessThree, clipSampler } from "./lib/headless-three.mjs";
import { ensureFemalePreview } from "./lib/ensure-female-preview.mjs";
await ensureFemalePreview("animations");
const { server, load } = await headlessThree();
try {
  const { bindModularPart } = await server.ssrLoadModule(
    "/src/lib/utils/modularCharacter.ts",
  );
  const base = await load(
    "assets/modular_human_female_01/rig_v1/female-base.glb",
  );
  const mesh = bindModularPart(
    base.scene,
    (
      await load(
        "assets/items/female_knight_bottom/tripo_v1/fitted_v36/bottom_female_knight.glb",
      )
    ).scene,
  )[0];
  const skeleton = mesh.skeleton,
    poses = [];
  const save = (name, time) => {
    base.scene.updateMatrixWorld(true);
    poses.push({
      name,
      time,
      matrices: ["Hips", "LeftUpLeg", "RightUpLeg"].map((name) => {
        const i = skeleton.bones.findIndex((b) => b.name === name);
        return new THREE.Matrix4().multiplyMatrices(
          skeleton.bones[i].matrixWorld,
          skeleton.boneInverses[i],
        ).elements;
      }),
    });
  };
  save("rest", 0);
  for (const data of JSON.parse(
    readFileSync("assets/modular_human_female_01/preview/animations.json"),
  ).clips) {
    const c = THREE.AnimationClip.parse(data);
    const i = base.animations.findIndex((v) => v.name === c.name);
    if (i >= 0) base.animations[i] = c;
    else base.animations.push(c);
  }
  for (const name of ["idle1", "walk"])
    for (const { time } of clipSampler(base.scene, {
      samples: 21,
      restore: skeleton.bones,
    })(base.animations.find((c) => c.name === name)))
      save(name, time);
  const directory = "assets/items/female_knight_bottom/tripo_v1/fitted_v37";
  mkdirSync(directory, { recursive: true });
  writeFileSync(`${directory}/strap-poses.json`, JSON.stringify(poses));
} finally {
  await server.close();
}
