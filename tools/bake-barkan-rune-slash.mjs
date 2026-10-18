// Adds RuneSlash and its WeaponSocket to the game GLB that animate_barkan.py writes.
// Run after: blender ... animate_barkan.py ... --game-output assets/monsters/barkan/game_v1/barkan.glb
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import * as THREE from "../client/node_modules/three/build/three.module.js";
import { hash, headlessThree, root } from "./lib/headless-three.mjs";
import { buildBarkanRuneSlash } from "./lib/barkan-rune-slash.mjs";

const SOURCE = "assets/monsters/barkan/game_v1/barkan.glb";
const OUTPUT = "client/public/models/monsters/barkan.glb";
const REPORT = "doc/assets/barkan-rune-slash-bake.json";
const SOCKET = "WeaponSocket";
const TIP = 1.617;

function readGlb(bytes) {
  assert.equal(bytes.readUInt32LE(0), 0x46546c67);
  const jsonLength = bytes.readUInt32LE(12);
  const json = JSON.parse(bytes.toString("utf8", 20, 20 + jsonLength));
  const binStart = 20 + jsonLength;
  const binLength = bytes.readUInt32LE(binStart);
  return {
    json,
    bin: bytes.subarray(binStart + 8, binStart + 8 + binLength),
  };
}

function writeGlb(json, bin) {
  const pad = (buffer, fill) =>
    Buffer.concat([buffer, Buffer.alloc((4 - (buffer.length % 4)) % 4, fill)]);
  const jsonChunk = pad(Buffer.from(JSON.stringify(json)), 0x20);
  const binChunk = pad(bin, 0);
  const header = Buffer.alloc(12);
  header.writeUInt32LE(0x46546c67, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + jsonChunk.length + 8 + binChunk.length, 8);
  const chunk = (data, type) => {
    const head = Buffer.alloc(8);
    head.writeUInt32LE(data.length, 0);
    head.writeUInt32LE(type, 4);
    return Buffer.concat([head, data]);
  };
  return Buffer.concat([
    header,
    chunk(jsonChunk, 0x4e4f534a),
    chunk(binChunk, 0x004e4942),
  ]);
}

const { server, load } = await headlessThree();
try {
  const { model, weapon, clip, timing } = await buildBarkanRuneSlash(
    server,
    load,
    SOURCE,
  );
  const { json, bin } = readGlb(readFileSync(new URL(SOURCE, root)));
  assert.ok(!json.animations.some((animation) => animation.name === clip.name));
  const nodeIndex = (name) => {
    const index = json.nodes.findIndex((node) => node.name === name);
    assert.ok(index >= 0, name);
    return index;
  };
  const hand = json.nodes[nodeIndex("RightHand")];
  const socket = json.nodes.length;
  json.nodes.push({
    name: SOCKET,
    translation: weapon.position.toArray(),
    rotation: weapon.quaternion.toArray(),
  });
  hand.children = [...(hand.children ?? []), socket];

  const chunks = [bin];
  let offset = bin.length;
  const addAccessor = (values, type, extra = {}) => {
    const data = Buffer.from(new Float32Array(values).buffer);
    const pad = (4 - (offset % 4)) % 4;
    if (pad) chunks.push(Buffer.alloc(pad));
    offset += pad;
    json.bufferViews.push({
      buffer: 0,
      byteOffset: offset,
      byteLength: data.length,
    });
    chunks.push(data);
    offset += data.length;
    const size = { SCALAR: 1, VEC3: 3, VEC4: 4 }[type];
    json.accessors.push({
      bufferView: json.bufferViews.length - 1,
      componentType: 5126,
      count: values.length / size,
      type,
      ...extra,
    });
    return json.accessors.length - 1;
  };
  const times = Array.from(clip.tracks[0].times);
  const input = addAccessor(times, "SCALAR", {
    min: [times[0]],
    max: [times.at(-1)],
  });
  const samplers = [];
  const channels = [];
  for (const track of clip.tracks) {
    assert.equal(track.times.length, times.length);
    const [name, property] = track.name.split(".");
    const size = track.getValueSize();
    const values = Array.from(track.values);
    samplers.push({
      input,
      interpolation: "LINEAR",
      output: addAccessor(values, size === 4 ? "VEC4" : "VEC3"),
    });
    channels.push({
      sampler: samplers.length - 1,
      target: {
        node: name === weapon.name ? socket : nodeIndex(name),
        path: property === "quaternion" ? "rotation" : "translation",
      },
    });
  }
  json.animations.push({ name: clip.name, samplers, channels });
  json.buffers[0].byteLength = offset;
  writeFileSync(new URL(OUTPUT, root), writeGlb(json, Buffer.concat(chunks)));

  // The server's sweep: tip bearing about +Z (the model's facing) over the strike.
  const mixer = new THREE.AnimationMixer(model);
  mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1).play();
  const tip = new THREE.Vector3();
  const sweep = [];
  const steps = Math.round((timing.strikeEnd - timing.strikeStart) * 100);
  for (let step = 0; step <= steps; step++) {
    const time = THREE.MathUtils.lerp(
      timing.strikeStart,
      timing.strikeEnd,
      step / steps,
    );
    mixer.setTime(time);
    model.updateMatrixWorld(true);
    weapon.localToWorld(tip.set(TIP, 0, 0));
    sweep.push({
      time: Number(time.toFixed(3)),
      bearing_degrees: Number(
        THREE.MathUtils.radToDeg(Math.atan2(tip.x, tip.z)).toFixed(1),
      ),
      reach_m: Number(Math.hypot(tip.x, tip.z).toFixed(2)),
      height_m: Number(tip.y.toFixed(2)),
    });
  }
  // Reload the written GLB and play its clip with the blade under the socket.
  const [baked, blade] = await Promise.all([
    load(OUTPUT),
    load("client/public/models/weapons/rune_blade.glb"),
  ]);
  const bakedClip = baked.animations.find((c) => c.name === clip.name);
  assert.ok(bakedClip, "RuneSlash is in the written GLB");
  assert.ok(Math.abs(bakedClip.duration - clip.duration) < 1e-4);
  baked.scene.getObjectByName(SOCKET).add(blade.scene);
  const bakedMixer = new THREE.AnimationMixer(baked.scene);
  bakedMixer.clipAction(bakedClip).setLoop(THREE.LoopOnce, 1).play();
  const bakedTip = new THREE.Vector3();
  let roundtripError = 0;
  for (let step = 0; step <= 84; step++) {
    const time = (clip.duration * step) / 84;
    mixer.setTime(time);
    bakedMixer.setTime(time);
    model.updateMatrixWorld(true);
    baked.scene.updateMatrixWorld(true);
    weapon.localToWorld(tip.set(TIP, 0, 0));
    blade.scene.localToWorld(bakedTip.set(TIP, 0, 0));
    roundtripError = Math.max(roundtripError, tip.distanceTo(bakedTip));
  }
  assert.ok(roundtripError < 0.01, `Baked blade tip drifts ${roundtripError}m`);
  const report = {
    source: SOURCE,
    source_sha256: hash(SOURCE),
    output: OUTPUT,
    output_sha256: hash(OUTPUT),
    clip: clip.name,
    duration_s: clip.duration,
    fps: 60,
    weapon_socket: { name: SOCKET, parent: "RightHand" },
    strike_s: [timing.strikeStart, timing.strikeEnd],
    sideways_sweep_s: [timing.sweepStart, timing.sweepEnd],
    roundtrip_blade_tip_error_m: roundtripError,
    blade_tip_sweep: sweep,
  };
  writeFileSync(new URL(REPORT, root), JSON.stringify(report, null, 2) + "\n");
  console.log(
    JSON.stringify(
      sweep.filter((_, index) => index % 4 === 0 || index === steps),
      null,
      0,
    ),
  );
} finally {
  await server.close();
}
