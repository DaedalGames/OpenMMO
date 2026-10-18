import { readFileSync } from "node:fs";
import * as THREE from "../../client/node_modules/three/build/three.module.js";
import { root } from "./headless-three.mjs";

// Builds RuneSlash on `modelPath` exactly as the preview does, with the blade at its csv grip.
export async function buildBarkanRuneSlash(server, load, modelPath) {
  const { createBarkanRuneSlash, BARKAN_RUNE_SLASH: timing } =
    await server.ssrLoadModule("/src/lib/utils/barkanRuneSlash.ts");
  const { withBarkanRuneGrip } = await server.ssrLoadModule(
    "/src/lib/utils/barkanRuneGrip.ts",
  );
  const { retargetAnimationsForCharacterModel } = await server.ssrLoadModule(
    "/src/lib/utils/characterAnimationUtils.ts",
  );
  const [base, social, melee, sword] = await Promise.all([
    load(modelPath),
    load("client/public/models/characters/modular_male/animations/social.glb"),
    load(
      "client/public/models/characters/modular_male/animations/combat_melee.glb",
    ),
    load("client/public/models/weapons/rune_blade.glb"),
  ]);
  const model = base.scene;
  const originals = [social, melee].map((pack) =>
    pack.animations.map((clip) =>
      JSON.stringify(THREE.AnimationClip.toJSON(clip)),
    ),
  );
  const [[enchant], [slash]] = await Promise.all([
    retargetAnimationsForCharacterModel(
      model,
      social.scene,
      social.animations.filter((clip) => clip.name === "enchant_weapon"),
    ),
    retargetAnimationsForCharacterModel(
      model,
      melee.scene,
      melee.animations.filter((clip) => clip.name === "slash1"),
    ),
  ]);
  const weapon = sword.scene;
  weapon.name = "BarkanRuneBlade";
  weapon.position.set(0.019808135, 0.082672966, 0.04);
  weapon.rotation.z = THREE.MathUtils.degToRad(-3);
  model.getObjectByName("RightHand").add(weapon);
  const idle = withBarkanRuneGrip(
    base.animations.find((clip) => clip.name === "Idle"),
  );
  model.updateMatrixWorld(true);
  melee.scene.updateMatrixWorld(true);
  const profile = JSON.parse(
    readFileSync(
      new URL("assets/modular_human_male_01/animations/hand-grips.json", root),
    ),
  );
  const slashGrip = model
    .getObjectByName("RightHand")
    .getWorldQuaternion(new THREE.Quaternion())
    .invert()
    .multiply(
      melee.scene
        .getObjectByName("RightHand")
        .getWorldQuaternion(new THREE.Quaternion()),
    )
    .multiply(new THREE.Quaternion().fromArray(profile.iron_sword.quaternion));
  const clip = createBarkanRuneSlash(model, idle, enchant, slash, slashGrip);
  return {
    model,
    weapon,
    clip,
    timing,
    slash,
    social,
    melee,
    originals,
  };
}
