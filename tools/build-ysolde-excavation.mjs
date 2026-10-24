import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import * as T from "../client/node_modules/three/build/three.module.js";
import { headlessThree } from "./lib/headless-three.mjs";

const out = new URL("../assets/npcs/ysolde/excavation/", import.meta.url);
mkdirSync(out, { recursive: true });
const { load, server, sources } = await headlessThree();
try {
  const { scene } = await load("assets/npcs/ysolde/rig_v1/ysolde.glb");
  const bones = [];
  scene.traverse((n) => {
    if (n.isBone) bones.push(n);
  });
  const rest = bones.map((bone) => ({
    bone,
    p: bone.position.clone(),
    q: bone.quaternion.clone(),
  }));
  const bone = (name) => {
    const node = scene.getObjectByName(name);
    assert.ok(node, name);
    return node;
  };
  const point = (name) => bone(name).getWorldPosition(new T.Vector3());
  const reset = () => {
    for (const { bone, p, q } of rest) {
      bone.position.copy(p);
      bone.quaternion.copy(q);
    }
    scene.updateMatrixWorld(true);
  };
  function worldRotation(node, quaternion) {
    node.quaternion.copy(
      node.parent
        .getWorldQuaternion(new T.Quaternion())
        .invert()
        .multiply(quaternion),
    );
    scene.updateMatrixWorld(true);
  }
  function aim(name, child, target) {
    const node = bone(name),
      origin = point(name);
    const before = point(child).sub(origin).normalize();
    const after = target.clone().sub(origin).normalize();
    const turn = new T.Quaternion().setFromUnitVectors(before, after);
    worldRotation(
      node,
      turn.multiply(node.getWorldQuaternion(new T.Quaternion())),
    );
  }
  function solve(root, joint, end, target, pole) {
    const start = point(root),
      l1 = start.distanceTo(point(joint)),
      l2 = point(joint).distanceTo(point(end));
    const axis = target.clone().sub(start),
      d = T.MathUtils.clamp(
        axis.length(),
        Math.abs(l1 - l2) + 0.001,
        l1 + l2 - 0.001,
      );
    axis.normalize();
    const along = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
    const across = pole
      .clone()
      .sub(start)
      .addScaledVector(axis, -pole.clone().sub(start).dot(axis))
      .normalize();
    const elbow = start
      .clone()
      .addScaledVector(axis, along)
      .addScaledVector(across, Math.sqrt(Math.max(0, l1 * l1 - along * along)));
    aim(root, joint, elbow);
    aim(joint, end, target);
  }
  const footQuaternions = Object.fromEntries(
    ["Left", "Right"].map((side) => [
      side,
      bone(`${side}Foot`).getWorldQuaternion(new T.Quaternion()),
    ]),
  );
  const donor = await load(
    "assets/modular_human_female_01/rig_v1/female-base.glb",
  );
  const armed = donor.animations.find((clip) => clip.name === "idle_armed");
  assert.ok(armed);
  const donorMixer = new T.AnimationMixer(donor.scene);
  donorMixer.clipAction(armed).play();
  donorMixer.update(0);
  donor.scene.updateMatrixWorld(true);
  function palmFrame(root, side = "Right") {
    const at = (name) => root.getObjectByName(name).getWorldPosition(new T.Vector3());
    const along = at(`${side}HandMiddle1`).sub(at(`${side}Hand`)).normalize();
    const across = at(`${side}HandIndex1`).sub(at(`${side}HandPinky1`));
    if (side === "Left") across.negate();
    across.addScaledVector(along, -across.dot(along)).normalize();
    return new T.Quaternion().setFromRotationMatrix(
      new T.Matrix4().makeBasis(across, along, across.clone().cross(along)),
    );
  }
  const donorPalmInverse = palmFrame(donor.scene).invert();
  const targetPalm = palmFrame(scene);
  const fingerGrip = new Map();
  const gripDirectionErrors = [];
  for (const digit of ["Thumb", "Index", "Middle", "Ring", "Pinky"]) {
    for (let segment = 1; segment <= 3; segment++) {
      const name = `RightHand${digit}${segment}`;
      const child = `RightHand${digit}${segment + 1}`;
      const direction = donor.scene.getObjectByName(child)
        .getWorldPosition(new T.Vector3())
        .sub(donor.scene.getObjectByName(name).getWorldPosition(new T.Vector3()))
        .normalize()
        .applyQuaternion(donorPalmInverse)
        .applyQuaternion(targetPalm);
      aim(name, child, point(name).add(direction));
      fingerGrip.set(name, bone(name).quaternion.clone());
      gripDirectionErrors.push(T.MathUtils.radToDeg(
        point(child).sub(point(name)).normalize().angleTo(direction),
      ));
    }
  }
  assert.equal(fingerGrip.size, 15);
  const gripDirectionErrorMax = Math.max(...gripDirectionErrors);
  assert.ok(gripDirectionErrorMax < 0.001);
  const { poseExcavationTool } = await server.ssrLoadModule(
    "/src/lib/utils/ysoldeExcavation.ts",
  );
  const attachment = new T.Object3D();
  poseExcavationTool(attachment);
  const hand = bone("RightHand");
  const indexJoints = [1, 2, 3, 4].map((segment) =>
    hand.worldToLocal(point(`RightHandIndex${segment}`)).toArray(),
  );
  reset();
  const supportLocalFrame = bone("LeftHand")
    .getWorldQuaternion(new T.Quaternion()).invert().multiply(palmFrame(scene, "Left"));
  const supportForward = new T.Vector3(0.25, 0, 1).normalize();
  const supportAcross = new T.Vector3(supportForward.z, 0, -supportForward.x);
  const supportRotation = new T.Quaternion().setFromRotationMatrix(
    new T.Matrix4().makeBasis(supportAcross, supportForward, new T.Vector3(0, -1, 0)),
  ).multiply(supportLocalFrame.clone().invert());
  supportRotation.premultiply(new T.Quaternion().setFromAxisAngle(supportForward, T.MathUtils.degToRad(-15)));
  supportRotation.premultiply(new T.Quaternion().setFromAxisAngle(supportAcross, T.MathUtils.degToRad(8)));
  const supportNormal = new T.Vector3(0, 0, 1).applyQuaternion(palmFrame(scene, "Left"));
  const supportGrip = new Map();
  for (const digit of ["Thumb", "Index", "Middle", "Ring", "Pinky"]) {
    for (let segment = 1; segment <= 3; segment++) {
      const name = `LeftHand${digit}${segment}`;
      const child = `LeftHand${digit}${segment + 1}`;
      const direction = point(child).sub(point(name));
      direction.addScaledVector(supportNormal, -direction.dot(supportNormal)).normalize();
      aim(name, child, point(name).add(direction));
      supportGrip.set(name, bone(name).quaternion.clone());
    }
  }
  const supportMeshes = [];
  scene.traverse((mesh) => {
    if (!mesh.isSkinnedMesh) return;
    const { skinIndex, skinWeight } = mesh.geometry.attributes;
    const vertices = [...new Set(mesh.geometry.index.array)].flatMap((id) => {
      const weights = new Map();
      for (let k = 0; k < 4; k++) {
        const name = mesh.skeleton.bones[skinIndex.getComponent(id, k)].name;
        if (name.startsWith("LeftHand")) {
          const part = name.slice(8).replace(/[1234]$/, "") || "Palm";
          weights.set(part, (weights.get(part) ?? 0) + skinWeight.getComponent(id, k));
        }
      }
      const [part] = [...weights].sort((a, b) => b[1] - a[1])[0] ?? [];
      const total = [...weights.values()].reduce((sum, weight) => sum + weight, 0);
      return total > 0.8 ? [{ id, part }] : [];
    });
    supportMeshes.push({ mesh, vertices });
  });
  function supportFloor(part) {
    let floor = Infinity;
    const vertex = new T.Vector3();
    for (const { mesh, vertices } of supportMeshes) {
      mesh.skeleton.update();
      for (const { id, part: name } of vertices) {
        if (part && part !== name) continue;
        mesh.getVertexPosition(id, vertex).applyMatrix4(mesh.matrixWorld);
        floor = Math.min(floor, vertex.y);
      }
    }
    return floor;
  }
  const supportPalmOffset = point("LeftHandMiddle1").sub(point("LeftHand"))
    .applyQuaternion(bone("LeftHand").getWorldQuaternion(new T.Quaternion()).invert())
    .applyQuaternion(supportRotation);
  const supportWrist = new T.Vector3(0.327 - supportPalmOffset.x, 0.03, 0.347 - supportPalmOffset.z);
  const supportHeights = [], supportPositions = [];
  reset();
  const gripSource =
    "Existing modular female idle_armed steel longsword grip; palm-frame transfer onto Ysolde's corrected index-root rig";
  const tracks = new Map(bones.map((b) => [b.name, []]));
  const hips = [],
    times = [],
    metrics = [],
    wristAngles = [];
  const duration = 3.6,
    frames = 109;
  for (let i = 0; i < frames; i++) {
    reset();
    const time = (duration * i) / (frames - 1),
      phase = (time / duration) * Math.PI * 2;
    const scrape = Math.sin(phase),
      lift = (1 - Math.cos(phase)) / 2;
    bone("Hips").position.set(0, 0.46 + 0.008 * lift, -0.16);
    bone("Hips").quaternion.multiply(
      new T.Quaternion().setFromAxisAngle(new T.Vector3(1, 0, 0), 0.5),
    );
    for (const [name, degrees] of [
      ["Spine", 35],
      ["Spine1", 26],
      ["Spine2", -3],
    ]) {
      bone(name).quaternion.multiply(
        new T.Quaternion().setFromAxisAngle(
          new T.Vector3(1, 0, 0),
          T.MathUtils.degToRad(degrees + (name === "Spine2" ? 2 * scrape : 0)),
        ),
      );
    }
    scene.updateMatrixWorld(true);
    worldRotation(bone("Spine"), new T.Quaternion().setFromEuler(
      new T.Euler(T.MathUtils.degToRad(15), 0, T.MathUtils.degToRad(-30)),
    ).multiply(bone("Spine").getWorldQuaternion(new T.Quaternion())));
    worldRotation(
      bone("Neck"),
      new T.Quaternion().setFromAxisAngle(
        new T.Vector3(1, 0, 0),
        T.MathUtils.degToRad(45),
      ),
    );
    worldRotation(
      bone("Head"),
      new T.Quaternion().setFromAxisAngle(
        new T.Vector3(1, 0, 0),
        T.MathUtils.degToRad(25),
      ),
    );
    worldRotation(bone("RightShoulder"), new T.Quaternion().setFromAxisAngle(
      new T.Vector3(0, 0, 1), T.MathUtils.degToRad(15),
    ).multiply(bone("RightShoulder").getWorldQuaternion(new T.Quaternion())));
    for (const [side, sign] of [
      ["Left", 1],
      ["Right", -1],
    ]) {
      solve(
        `${side}UpLeg`,
        `${side}Leg`,
        `${side}Foot`,
        new T.Vector3(sign * 0.18, 0.115, -0.53),
        new T.Vector3(sign * 0.18, 0.05, 0.4),
      );
      worldRotation(bone(`${side}Foot`), footQuaternions[side]);
    }
    const wrist = new T.Vector3(
      -0.25,
      0.265 + 0.06 * lift,
      0.42 + 0.04 * scrape,
    );
    solve(
      "RightArm",
      "RightForeArm",
      "RightHand",
      wrist,
      new T.Vector3(-0.7, 0.65, 0.05),
    );
    assert.ok(point("RightHand").distanceTo(wrist) < 0.00001, "Right hand cannot reach its grip position");
    const hand = bone("RightHand");
    const fingers = point("RightHandMiddle1")
      .sub(point("RightHand"))
      .normalize();
    const forearm = point("RightHand").sub(point("RightForeArm")).normalize();
    const alignment = new T.Quaternion().setFromUnitVectors(fingers, forearm);
    worldRotation(
      hand,
      alignment.multiply(hand.getWorldQuaternion(new T.Quaternion())),
    );
    const bladeDirection = new T.Vector3(1, 0, 0).applyQuaternion(
      hand.getWorldQuaternion(new T.Quaternion()),
    );
    const radialBlade = bladeDirection
      .clone()
      .addScaledVector(forearm, -bladeDirection.dot(forearm))
      .normalize();
    const bladeTarget = new T.Vector3(0, 1, 1);
    bladeTarget.addScaledVector(forearm, -bladeTarget.dot(forearm)).normalize();
    const roll = T.MathUtils.clamp(
      Math.atan2(
        forearm.dot(radialBlade.clone().cross(bladeTarget)),
        radialBlade.dot(bladeTarget),
      ),
      -Math.PI / 2,
      Math.PI / 2,
    );
    bone("RightForeArm").quaternion.multiply(
      new T.Quaternion().setFromAxisAngle(new T.Vector3(0, 1, 0), roll),
    );
    scene.updateMatrixWorld(true);
    function plantLeftHand() {
      solve("LeftArm", "LeftForeArm", "LeftHand", supportWrist,
        new T.Vector3(0.65, 0.35, -0.05));
      worldRotation(bone("LeftHand"), supportRotation);
      for (const [name, rotation] of supportGrip) bone(name).quaternion.copy(rotation);
      scene.updateMatrixWorld(true);
    }
    plantLeftHand();
    if (i === 0) {
      supportWrist.y += 0.003 - supportFloor("Palm");
      plantLeftHand();
      const thumbDirection = supportAcross.clone().multiplyScalar(-0.45)
        .addScaledVector(supportForward, 0.85).add(new T.Vector3(0, 0.12, 0)).normalize();
      aim("LeftHandThumb1", "LeftHandThumb2", point("LeftHandThumb1").add(thumbDirection));
      supportGrip.set("LeftHandThumb1", bone("LeftHandThumb1").quaternion.clone());
      const clearance = 0.003 - supportFloor();
      if (clearance > 0) supportWrist.y += clearance;
      plantLeftHand();
    }
    const supportHeight = supportFloor();
    const supportPosition = point("LeftHand");
    assert.ok(supportHeight > 0 && supportHeight < 0.006, `Left hand floor ${supportHeight}`);
    assert.ok(supportPosition.distanceTo(supportWrist) < 0.00001, "Left hand cannot reach the ground");
    supportHeights.push(supportHeight);
    supportPositions.push(supportPosition.toArray());
    for (const [name, rotation] of fingerGrip)
      bone(name).quaternion.copy(rotation);
    scene.updateMatrixWorld(true);
    const palmDirection = point("RightHandMiddle1")
      .sub(point("RightHand"))
      .normalize();
    const armDirection = point("RightHand")
      .sub(point("RightForeArm"))
      .normalize();
    const wristAngle = T.MathUtils.radToDeg(
      palmDirection.angleTo(armDirection),
    );
    assert.ok(wristAngle < 1, `Bent wrist at ${time}: ${wristAngle}`);
    wristAngles.push(wristAngle);
    times.push(time);
    hips.push(...bone("Hips").position.toArray());
    for (const b of bones) tracks.get(b.name).push(...b.quaternion.toArray());
    if (i % 27 === 0)
      metrics.push({
        time,
        rightShoulder: point("RightArm").toArray(),
        rightElbow: point("RightForeArm").toArray(),
        rightHand: point("RightHand").toArray(),
        rightKnee: point("RightLeg").toArray(),
        leftKnee: point("LeftLeg").toArray(),
        leftHand: point("LeftHand").toArray(),
        leftElbow: point("LeftForeArm").toArray(),
        head: point("Head").toArray(),
        neck: point("Neck").toArray(),
        tip: bone("RightHand")
          .localToWorld(new T.Vector3(0.24, 0, 0)
            .applyEuler(attachment.rotation).add(attachment.position))
          .toArray(),
      });
  }
  const clip = new T.AnimationClip("excavate", duration, [
    new T.VectorKeyframeTrack("Hips.position", times, hips),
    ...[...tracks].map(
      ([name, values]) =>
        new T.QuaternionKeyframeTrack(`${name}.quaternion`, times, values),
    ),
  ]);
  assert.ok(clip.validate());
  clip.optimize();
  writeFileSync(
    new URL("clip.json", out),
    JSON.stringify(T.AnimationClip.toJSON(clip)),
  );
  writeFileSync(
    new URL("validation.json", out),
    JSON.stringify(
      {
        date: "2026-10-24",
        revised: "2026-10-25",
        authoring:
          "Original analytic two-bone IK on the Ysolde rig with the existing female sword grip; no paid generation",
        license:
          "Project-authored motion with the existing modular female Mixamo-derived sword grip; existing asset licenses apply",
        sources,
        duration,
        frames,
        gripSource,
        donor_transfer_direction_error_degrees_max: gripDirectionErrorMax,
        index_grip: {
          tool_position_m: attachment.position.toArray(),
          hand_local_joints_m: indexJoints,
        },
        head_tilt_degrees: 25,
        neck_tilt_degrees: 45,
        upper_back_extension_degrees: 20,
        blade_direction:
          "Up and forward from the fist, matching the user's annotated reference",
        wrist_bend_degrees_max: Math.max(...wristAngles),
        left_support: {
          wrist_m: supportWrist.toArray(),
          skinned_floor_range_m: [Math.min(...supportHeights), Math.max(...supportHeights)],
          wrist_drift_m: Math.max(...supportPositions.map((p) => new T.Vector3(...p).distanceTo(supportWrist))),
          palm_direction: "Down, with open fingers resting along the ground",
          parts_floor_m: Object.fromEntries(["Palm", "Thumb", "Index", "Middle", "Ring", "Pinky"].map((part) => [part, supportFloor(part)])),
        },
        samples: metrics,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(JSON.stringify(metrics, null, 2));
} finally {
  await server.close();
}
