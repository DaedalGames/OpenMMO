import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const worldDelta = (from, to) => ((to - from + 49152) % 32768) - 16384;
const regionName = (value) =>
  `${value < 0 ? "-" : "+"}${Math.abs(value).toString().padStart(2, "0")}`;

// Mirrors server/src/land_grades.rs: [inner, outer] rings per anchor kind.
const RINGS = {
  capital: [180, 400],
  city: [120, 320],
  town: [80, 250],
  entrance: [60, 150],
};

function readCsv(file) {
  const [header, ...lines] = fs.readFileSync(file, "utf8").trim().split("\n");
  const fields = header.split(",");
  return lines.map((line) =>
    Object.fromEntries(line.split(",").map((value, i) => [fields[i], value])),
  );
}

export function loadAnchors() {
  const labels = JSON.parse(
    fs.readFileSync(path.join(repo, "data/map_labels.json"), "utf8"),
  );
  const entrances = readCsv(path.join(repo, "data-src/dungeons.csv")).map(
    (row) => ({ kind: "entrance", x: Number(row.x), z: Number(row.z) }),
  );
  return [...Object.values(labels), ...entrances]
    .filter((anchor) => RINGS[anchor.kind])
    .map(({ kind, x, z }) => ({
      x,
      z,
      inner: RINGS[kind][0],
      outer: RINGS[kind][1],
    }));
}

// The grades the server serves for a region without an edited file.
export function defaultGrades(anchors, rx, rz) {
  const grades = Buffer.alloc(1024, 1);
  for (let index = 0; index < 1024; index++) {
    const tile = Math.floor(index / 4);
    const q = index % 4;
    const cx = (rx * 16 + (tile % 16)) * 64 - 16 + (q % 2) * 32;
    const cz =
      (rz * 16 + Math.floor(tile / 16)) * 64 - 16 + Math.floor(q / 2) * 32;
    for (const anchor of anchors) {
      const distance = Math.hypot(worldDelta(anchor.x, cx), cz - anchor.z);
      if (distance < anchor.inner) {
        grades[index] = 0;
        break;
      }
      if (distance <= anchor.outer) grades[index] = 2;
    }
  }
  return grades;
}

// `anchors` is set only for sites missing from the registry: the defaults
// omit them, so their regions get a grade file seeded from the defaults.
export function planReservation(terrainDir, dungeon, plots, anchors = null) {
  const x = Number(dungeon.x);
  const z = Number(dungeon.z);
  if (!Number.isFinite(x) || !Number.isFinite(z))
    throw new Error("Invalid dungeon coordinates");
  for (const plot of plots) {
    const { tile_x: tx, tile_z: tz, quadrant: q } = plot;
    if (![tx, tz, q].every(Number.isInteger) || q < 0 || q > 3)
      throw new Error("Invalid ownership row");
    const cx = tx * 64 - 16 + (q % 2) * 32;
    const cz = tz * 64 - 16 + Math.floor(q / 2) * 32;
    const distance = Math.hypot(
      Math.max(Math.abs(worldDelta(x, cx)) - 16, 0),
      Math.max(Math.abs(cz - z) - 16, 0),
    );
    if (distance <= 150)
      throw new Error(`Owned plot overlaps the 150m ring: ${tx}, ${tz}, ${q}`);
  }
  const changes = [];
  for (
    let rx = Math.floor((x - 150 + 32) / 1024);
    rx <= Math.floor((x + 150 + 32) / 1024);
    rx++
  ) {
    for (
      let rz = Math.floor((z - 150 + 32) / 1024);
      rz <= Math.floor((z + 150 + 32) / 1024);
      rz++
    ) {
      const canonicalRx = ((rx + 48) % 32) - 16;
      const file = path.join(
        terrainDir,
        "land-grades",
        `r${regionName(canonicalRx)}_${regionName(rz)}.bin`,
      );
      const exists = fs.existsSync(file);
      if (!exists && !anchors) continue;
      const before = exists
        ? fs.readFileSync(file)
        : defaultGrades(anchors, canonicalRx, rz);
      if (before.length !== 1024 || before.some((grade) => grade > 2))
        throw new Error(`Invalid land grades: ${file}`);
      const after = Buffer.from(before);
      let count = 0;
      for (let index = 0; index < 1024; index++) {
        const tile = Math.floor(index / 4);
        const q = index % 4;
        const cx = (canonicalRx * 16 + (tile % 16)) * 64 - 16 + (q % 2) * 32;
        const cz =
          (rz * 16 + Math.floor(tile / 16)) * 64 - 16 + Math.floor(q / 2) * 32;
        const distance = Math.hypot(worldDelta(x, cx), cz - z);
        if (distance > 150) continue;
        const grade = distance < 60 || before[index] === 0 ? 0 : 2;
        if (before[index] !== grade) {
          after[index] = grade;
          count++;
        }
      }
      if (count) changes.push({ file, before, after, count, exists });
    }
  }
  return changes;
}

function main() {
  const { values } = parseArgs({
    options: {
      dungeon: { type: "string" },
      x: { type: "string" },
      z: { type: "string" },
      label: { type: "string" },
      ownership: { type: "string" },
      terrain: { type: "string", default: path.join(repo, "data/terrain") },
      apply: { type: "boolean", default: false },
    },
  });
  const byCoords = values.x !== undefined || values.z !== undefined;
  if (
    !values.ownership ||
    (values.dungeon ? byCoords : !(values.x && values.z && values.label))
  )
    throw new Error(
      "Use --dungeon ID or --x X --z Z --label NAME, with --ownership owned-plots.json [--terrain DIR] [--apply]",
    );
  const dungeon = byCoords
    ? { id: values.label, x: values.x, z: values.z }
    : readCsv(path.join(repo, "data-src/dungeons.csv")).find(
        (row) => row.id === values.dungeon,
      );
  if (!dungeon) throw new Error(`Unknown dungeon: ${values.dungeon}`);
  const plots = JSON.parse(fs.readFileSync(values.ownership, "utf8"));
  if (!Array.isArray(plots)) throw new Error("Ownership must be a JSON array");
  const changes = planReservation(
    values.terrain,
    dungeon,
    plots,
    byCoords ? loadAnchors() : null,
  );
  for (const change of changes) {
    console.log(
      `${values.apply ? "Apply" : "Preview"} ${change.file}: ${change.count} plots${change.exists ? "" : " (new file from defaults)"}`,
    );
    if (!values.apply) continue;
    if (!change.exists) {
      fs.mkdirSync(path.dirname(change.file), { recursive: true });
      fs.writeFileSync(change.file, change.after, { flag: "wx" });
      continue;
    }
    if (!fs.readFileSync(change.file).equals(change.before))
      throw new Error(`Land grades changed: ${change.file}`);
    fs.copyFileSync(
      change.file,
      `${change.file}.before-${dungeon.id}-${Date.now()}`,
      fs.constants.COPYFILE_EXCL,
    );
    const temporary = `${change.file}.${process.pid}.tmp`;
    try {
      fs.writeFileSync(temporary, change.after, { flag: "wx" });
      fs.renameSync(temporary, change.file);
    } finally {
      fs.rmSync(temporary, { force: true });
    }
  }
  if (!byCoords)
    console.log(
      "Regions without edited grade files use the dungeon registry defaults.",
    );
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
)
  main();
