import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import * as THREE from "../client/node_modules/three/build/three.module.js";
import { headlessThree, hash } from "./lib/headless-three.mjs";

const directory = "assets/items/female_barbarian_helmet/tripo_v2/fitted_v1";
const anchors = JSON.parse(
  readFileSync(`${directory}/hair-cheek-coverage-anchors.json`),
);
const bodyPath = "assets/modular_human_female_01/rig_v1/female-base.glb";
const hairPath =
  process.argv[2] ?? `${directory}/hair_bob_barbarian_helmet.glb`;
const { server, load } = await headlessThree();
try {
  assert.equal(hash(bodyPath), anchors.body_sha256);
  const { bindModularPart } = await server.ssrLoadModule(
    "/src/lib/utils/modularCharacter.ts",
  );
  const base = await load(bodyPath);
  const hair = bindModularPart(base.scene, (await load(hairPath)).scene);
  const helmet = bindModularPart(
    base.scene,
    (await load(`${directory}/helmet_female_barbarian.glb`)).scene,
  );
  let body;
  base.scene.traverse((node) => {
    if (
      node.isSkinnedMesh &&
      base.parser.associations.get(node)?.primitives === 0
    )
      body = node;
  });
  const clips = JSON.parse(
    readFileSync("assets/modular_human_female_01/preview/animations.json"),
  ).clips;
  const clip =
    base.animations.find((entry) => entry.name === anchors.pose) ??
    THREE.AnimationClip.parse(
      clips.find((entry) => entry.name === anchors.pose),
    );
  const mixer = new THREE.AnimationMixer(base.scene);
  mixer.clipAction(clip).play();
  mixer.setTime(anchors.time);
  base.scene.updateMatrixWorld(true);
  body.skeleton.update();
  for (const mesh of [...hair, ...helmet]) mesh.skeleton.update();
  const ray = new THREE.Raycaster();
  const target = new THREE.Vector3();
  const views = [
    { name: "oblique-cheek", camera: anchors.camera, targets: anchors.targets },
    ...(anchors.additional_views ?? []),
  ].map((view) => {
    const origin = new THREE.Vector3(...view.camera);
    const results = view.targets.map((point) => {
      target.fromArray(point).sub(origin);
      const maximumDistance = target.length() + (view.depth_tolerance ?? Infinity);
      ray.set(origin, target.normalize());
      const first = ray.intersectObjects([body, ...hair, ...helmet], false)[0];
      const hairFirst = !!first && hair.includes(first.object);
      return {
        hair_first: hairFirst,
        covered: hairFirst && first.distance <= maximumDistance,
        first_mesh: first?.object.name,
      };
    });
    return {
      name: view.name,
      samples: results.length,
      covered: results.filter((row) => row.covered).length,
      results,
    };
  });
  const results = views.flatMap((view) => view.results);
  const report = {
    hair_sha256: hash(hairPath),
    body_sha256: hash(bodyPath),
    samples: results.length,
    hair_first_hits: results.filter((row) => row.hair_first).length,
    covered: results.filter((row) => row.covered).length,
    scope:
      "Runtime binding and idle1 time 0; retain oblique skin coverage and the restored outer strand below the cheek tip in the near-front view. Depth tolerance prevents inner hair layers from masking a missing outer strand.",
    views,
  };
  if (!process.argv[2])
    writeFileSync(
      `${directory}/hair-cheek-coverage-validation.json`,
      JSON.stringify(report, null, 2) + "\n",
    );
  console.log(
    JSON.stringify({
      samples: report.samples,
      covered: report.covered,
    }),
  );
  assert.equal(
    report.covered,
    report.samples,
    "Hair coverage regressed at a reported cheek gap",
  );
} finally {
  await server.close();
}
