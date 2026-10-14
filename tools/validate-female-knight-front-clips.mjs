import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import * as THREE from "../client/node_modules/three/build/three.module.js";
import { headlessThree, clipSampler, hash } from "./lib/headless-three.mjs";
import { ensureFemalePreview } from "./lib/ensure-female-preview.mjs";
await ensureFemalePreview("animations");

const version = process.argv[2] ?? "v35";
assert.ok(["v35", "v36", "v37", "v38", "v39", "v40", "v41", "v42"].includes(version));
const rear = process.argv[3] === "rear";
const region = rear ? "rear" : "front";
const directory = `assets/items/female_knight_bottom/tripo_v1/fitted_${version}`;
const path = `${directory}/bottom_female_knight.glb`;
const bootPath =
  "assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb";
const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`));
const { server, load } = await headlessThree();
try {
  const { bindModularPart } = await server.ssrLoadModule(
    "/src/lib/utils/modularCharacter.ts",
  );
  const base = await load(
    "assets/modular_human_female_01/rig_v1/female-base.glb",
  );
  const mesh = bindModularPart(base.scene, (await load(path)).scene)[0];
  const boots = bindModularPart(base.scene, (await load(bootPath)).scene);
  base.scene.updateMatrixWorld(true);
  const anchors = [];
  for (const side of [-1, 1]) {
    const vertices =
      fitting[`${region}_clip_alignment`]?.find((record) => record.side === side)
        ?.clip_vertices ??
      fitting.vertices.filter(
        (i) =>
          mesh.geometry.attributes.position.getX(i) * side > 0 &&
          mesh.geometry.attributes.position.getY(i) < 0.495,
      );
    let best;
    for (const boot of boots) {
      const p = boot.geometry.attributes.position,
        index = boot.geometry.index;
      for (let face = 0; face < index.count; face += 3) {
        const ids = [
          index.getX(face),
          index.getX(face + 1),
          index.getX(face + 2),
        ];
        const points = ids.map((i) =>
          new THREE.Vector3().fromBufferAttribute(p, i),
        );
        if (points.some((p) => p.x * side <= 0 || (rear ? p.y < 0.39 || p.z > -0.025 : p.y < 0.445 || p.z < 0.025)))
          continue;
        const triangle = new THREE.Triangle(...points);
        for (const vertex of vertices) {
          const point = mesh.getVertexPosition(vertex, new THREE.Vector3());
          const closest = triangle.closestPointToPoint(
            point,
            new THREE.Vector3(),
          );
          const gap = closest.distanceTo(point);
          if (!best || gap < best.gap)
            best = {
              side,
              vertex,
              boot,
              ids,
              barycentric: triangle.getBarycoord(closest, new THREE.Vector3()),
              gap,
            };
        }
      }
    }
    assert.ok(best && best.gap < 0.003, `Clip misses boot rim: ${best?.gap}`);
    anchors.push(best);
  }
  for (const data of JSON.parse(
    readFileSync("assets/modular_human_female_01/preview/animations.json"),
  ).clips) {
    const clip = THREE.AnimationClip.parse(data);
    const index = base.animations.findIndex((c) => c.name === clip.name);
    if (index < 0) base.animations.push(clip);
    else base.animations[index] = clip;
  }
  const sample = clipSampler(base.scene, {
    samples: 61,
    restore: mesh.skeleton.bones,
  });
  const clips = [];
  for (const clip of base.animations) {
    let maximumDrift = 0,
      maximumStrapBend = 0;
    for (const _ of sample(clip)) {
      for (const strap of fitting[`straight_${region}_straps`] ?? []) {
        const centers = strap.rings.map((ring) =>
          ring
            .reduce(
              (sum, vertex) =>
                sum.add(mesh.getVertexPosition(vertex, new THREE.Vector3())),
              new THREE.Vector3(),
            )
            .divideScalar(ring.length),
        );
        for (let i = 1; i < centers.length - 1; i++) {
          const incoming = centers[i].clone().sub(centers[i - 1]);
          const outgoing = centers[i + 1].clone().sub(centers[i]);
          maximumStrapBend = Math.max(
            maximumStrapBend,
            THREE.MathUtils.radToDeg(incoming.angleTo(outgoing)),
          );
        }
      }
      for (const anchor of anchors) {
        const point = mesh.getVertexPosition(
          anchor.vertex,
          new THREE.Vector3(),
        );
        const surface = anchor.ids.reduce(
          (sum, id, i) =>
            sum.addScaledVector(
              anchor.boot.getVertexPosition(id, new THREE.Vector3()),
              anchor.barycentric.getComponent(i),
            ),
          new THREE.Vector3(),
        );
        maximumDrift = Math.max(
          maximumDrift,
          Math.abs(point.distanceTo(surface) - anchor.gap),
        );
      }
    }
    if (
      fitting[`straight_${region}_straps`] &&
      ["idle1", "idle_armed"].includes(clip.name)
    )
      assert.ok(
        maximumStrapBend < 3,
        `${clip.name}: strap bends ${maximumStrapBend}`,
      );
    assert.ok(
      maximumDrift < 1e-6,
      `${clip.name}: clip attachment drifts ${maximumDrift}`,
    );
    clips.push({
      name: clip.name,
      frames: 61,
      maximum_attachment_drift: maximumDrift,
      ...(fitting[`straight_${region}_straps`]
        ? { maximum_strap_bend_degrees: maximumStrapBend }
        : {}),
    });
  }
  const report = {
    date: "2026-10-13",
    sha256: hash(path),
    boots_sha256: hash(bootPath),
    anchors: anchors.map(({ side, vertex, ids, barycentric, gap }) => ({
      side,
      vertex,
      boot_vertices: ids,
      barycentric: barycentric.toArray(),
      surface_gap: gap,
    })),
    clips,
    scope:
      "Nearest lower-clip contact with the thigh plate, tracked through every preview animation; not a full outfit collision test.",
  };
  writeFileSync(
    `${directory}/${rear ? "rear-" : ""}clip-attachment-validation.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report));
} finally {
  await server.close();
}
