//! A* search over the virtual 1m world grid with floor-level awareness.
//! Combines two cell types: regular floor cells (cardinal expansion via
//! the cell-edge mask) and stairwell intermediate cells (axis-only
//! expansion via the precomputed stair map). The goal is reachable at
//! any floor key on the goal floor — A* doesn't have to walk back to a
//! landing first if the goal cell is mid-stairwell.

use std::cmp::{Ordering, Reverse};
use std::collections::{BinaryHeap, HashMap, HashSet};

use super::query::{is_cardinal_move_blocked, is_movement_blocked_for_mover, snap_goal_into_floor};
use super::stair::{build_stair_cells, floor_to_key, is_regular_key, key_to_floor, AStarKey};
use super::{PassabilityCache, PathResult, PathWaypoint, DIRS};
use crate::world::wrap_world_x;

/// Default max nodes for A* expansion. Sized for multi-floor house traversal.
pub const DEFAULT_MAX_NODES: usize = 2000;
/// A search that comes within `SEALED_NEAR_H` of a goal under an overlay and
/// then spends `SEALED_STALL_NODES` more without reaching it checks whether the
/// goal sits in a small sealed pocket (a closed house) before spending the rest.
/// A pocket of `SEALED_MAX_CELLS` keeps its walls within `SEALED_NEAR_H`.
const SEALED_NEAR_H: u32 = 4;
const SEALED_STALL_NODES: usize = 32;
const SEALED_MAX_CELLS: usize = 64;

#[derive(Clone)]
struct AStarNode {
    x: i32,
    z: i32,
    /// Floor key: regular floors are multiples of FLOOR_SCALE,
    /// intermediate stairwell cells use values in between.
    fk: u16,
    g: u32,
    f: u32,
}

impl Eq for AStarNode {}
impl PartialEq for AStarNode {
    fn eq(&self, other: &Self) -> bool {
        self.f == other.f
    }
}
impl Ord for AStarNode {
    fn cmp(&self, other: &Self) -> Ordering {
        self.f.cmp(&other.f)
    }
}
impl PartialOrd for AStarNode {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

struct ClosedEntry {
    g: u32,
    parent: AStarKey,
}

/// Cells a search read; a cached failure stays valid while geometry around
/// this box is unchanged.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct SearchExtent {
    pub(super) expanded: usize,
    pub min: (i32, i32),
    pub max: (i32, i32),
    floors: [u64; 4],
}

impl SearchExtent {
    fn at(x: i32, z: i32, floor: u8) -> Self {
        let mut extent = Self {
            min: (x, z),
            max: (x, z),
            ..Self::default()
        };
        extent.include(x, z, floor);
        extent
    }

    fn include(&mut self, x: i32, z: i32, floor: u8) {
        self.min = (self.min.0.min(x), self.min.1.min(z));
        self.max = (self.max.0.max(x), self.max.1.max(z));
        self.floors[usize::from(floor / 64)] |= 1 << (floor % 64);
    }

    pub fn has_floor(&self, floor: u8) -> bool {
        self.floors[usize::from(floor / 64)] & (1 << (floor % 64)) != 0
    }

    fn absorb(&mut self, other: &Self) {
        self.expanded += other.expanded;
        self.min = (self.min.0.min(other.min.0), self.min.1.min(other.min.1));
        self.max = (self.max.0.max(other.max.0), self.max.1.max(other.max.1));
        for (a, b) in self.floors.iter_mut().zip(other.floors) {
            *a |= b;
        }
    }
}

/// Find a path on a virtual 1m world grid with floor-level awareness.
///
/// `start_floor`/`goal_floor` are floor *keys*, not "the floor nearest that Y":
/// an endpoint standing mid-stairwell belongs to the shallower connected floor
/// here. Resolve endpoints with [`super::start_floor_at`] rather than
/// [`super::get_floor_at_position`], or the search reaches the stairs only
/// through their far landing.
#[allow(clippy::too_many_arguments)]
pub fn find_path(
    start_x: f32,
    start_z: f32,
    start_floor: u8,
    goal_x: f32,
    goal_z: f32,
    goal_floor: u8,
    cache: &PassabilityCache,
    max_nodes: usize,
) -> PathResult {
    find_path_avoiding(
        start_x,
        start_z,
        start_floor,
        goal_x,
        goal_z,
        goal_floor,
        cache,
        max_nodes,
        &[],
    )
}

/// Whether the 1m cell `(x, z)`, in any periodic frame, is in `blocked`.
pub(super) fn cell_blocked(blocked: &[(i32, i32)], x: i32, z: i32) -> bool {
    !blocked.is_empty() && blocked.contains(&(wrap_world_x(x as f32 + 0.5).floor() as i32, z))
}

/// Whether a mover walking `(x0, z0)`→`(x1, z1)` enters any of `cells`
/// (canonical, see `monster_ai::cell_of`). Sampled at quarter-cell steps so
/// no 1m cell is skipped; the start cell is exempt. The chase gate, the
/// occupied-leg check and the smoother all use this one sweep so they agree
/// on which cells a leg touches.
pub fn segment_enters_cells(x0: f32, z0: f32, x1: f32, z1: f32, cells: &[(i32, i32)]) -> bool {
    if cells.is_empty() {
        return false;
    }
    let dx = crate::world::shortest_world_delta_x(x0, x1);
    let dz = z1 - z0;
    let steps = ((dx * dx + dz * dz).sqrt() / 0.25).ceil().max(1.0) as i32;
    let start = (x0.floor() as i32, z0.floor() as i32);
    (1..=steps).any(|i| {
        let t = i as f32 / steps as f32;
        let cell = ((x0 + dx * t).floor() as i32, (z0 + dz * t).floor() as i32);
        cell != start && cell_blocked(cells, cell.0, cell.1)
    })
}

/// [`find_path`] that also refuses to enter `blocked` cells — standing
/// monsters, so a chase can detour around a queue instead of waiting in it.
#[allow(clippy::too_many_arguments)]
pub fn find_path_avoiding(
    start_x: f32,
    start_z: f32,
    start_floor: u8,
    goal_x: f32,
    goal_z: f32,
    goal_floor: u8,
    cache: &PassabilityCache,
    max_nodes: usize,
    blocked: &[(i32, i32)],
) -> PathResult {
    find_path_avoiding_counted(
        start_x,
        start_z,
        start_floor,
        goal_x,
        goal_z,
        goal_floor,
        cache,
        max_nodes,
        blocked,
        &mut SearchExtent::default(),
        true,
    )
}

/// `check_sealed` enables the sealed-goal shortcut; its own frontier leg
/// passes false so it cannot recurse.
#[allow(clippy::too_many_arguments)]
pub(super) fn find_path_avoiding_counted(
    start_x: f32,
    start_z: f32,
    start_floor: u8,
    goal_x: f32,
    goal_z: f32,
    goal_floor: u8,
    cache: &PassabilityCache,
    max_nodes: usize,
    blocked: &[(i32, i32)],
    extent: &mut SearchExtent,
    check_sealed: bool,
) -> PathResult {
    let (goal_x, goal_z) = snap_goal_into_floor(cache, goal_x, goal_z, goal_floor);
    let sx = start_x.floor() as i32;
    let sz = start_z.floor() as i32;
    let gx = goal_x.floor() as i32;
    let gz = goal_z.floor() as i32;
    *extent = SearchExtent::at(sx, sz, start_floor);
    extent.include(gx, gz, goal_floor);

    if sx == gx && sz == gz && start_floor == goal_floor {
        return PathResult {
            waypoints: vec![PathWaypoint {
                x: goal_x,
                z: goal_z,
                floor: goal_floor,
            }],
            found: true,
            termination: crate::pathfinding::PathTermination::Reached,
        };
    }

    let stair_cells = build_stair_cells(cache);

    // Build set of (x, z, real_floor) for stairwell cells.
    // Used to block regular-floor cardinal moves into stairwell interior cells,
    // but only for floors that the stairwell actually connects.
    let mut stair_positions: HashSet<(i32, i32, u8)> = HashSet::new();
    for &(x, z, fk) in stair_cells.keys() {
        stair_positions.insert((x, z, key_to_floor(fk)));
    }

    // Confine the search to a single floor when start and goal share it: a
    // same-floor room goal is always reachable without leaving the floor, so the
    // stairwell is never a legitimate shortcut. The exception is a click whose
    // target is the stairwell itself. Intermediate stair cells are keyed to the
    // shallower connected floor, so a landing→mid-stair click may have equal
    // start/goal floor numbers but still needs stair-axis expansion.
    let start_regular_key = (sx, sz, floor_to_key(start_floor));
    let start_is_stair_interior = stair_positions.contains(&(sx, sz, start_floor))
        && !stair_cells.contains_key(&start_regular_key);
    let goal_is_stair_position = stair_positions.contains(&(gx, gz, goal_floor));
    let confine_to_floor =
        start_floor == goal_floor && !start_is_stair_interior && !goal_is_stair_position;

    let start_fk = floor_to_key(start_floor);

    let mut open = BinaryHeap::new();
    let mut closed: HashMap<AStarKey, ClosedEntry> = HashMap::new();

    let h = |x: i32, z: i32, fk: u16| -> u32 {
        let real_f = key_to_floor(fk) as i32;
        let goal_f = goal_floor as i32;
        (x - gx).unsigned_abs() + (z - gz).unsigned_abs() + (real_f - goal_f).unsigned_abs() * 2
    };

    let start_h = h(sx, sz, start_fk);
    let start_key: AStarKey = (sx, sz, start_fk);
    open.push(Reverse(AStarNode {
        x: sx,
        z: sz,
        fk: start_fk,
        g: 0,
        f: start_h,
    }));
    closed.insert(
        start_key,
        ClosedEntry {
            g: 0,
            parent: start_key,
        },
    );

    // If start is on a stairwell intermediate cell, also seed that key
    // so the player doesn't have to walk back to entry landing first.
    // Skipped under floor confinement: those seeds only exist to start a
    // cross-floor climb/descent.
    if !confine_to_floor {
        for &key in stair_cells.keys() {
            let (kx, kz, kfk) = key;
            if kx == sx && kz == sz && key_to_floor(kfk) == start_floor && kfk != start_fk {
                let sh = h(sx, sz, kfk);
                open.push(Reverse(AStarNode {
                    x: sx,
                    z: sz,
                    fk: kfk,
                    g: 0,
                    f: sh,
                }));
                closed.insert(
                    key,
                    ClosedEntry {
                        g: 0,
                        parent: start_key,
                    },
                );
            }
        }
    }

    // A mover parked on furniture (a bed seals its own footprint) gets the same
    // one-step waiver the movement validator grants: out of a fully sealed start
    // cell across a `yields_to_trapped_mover` obstacle. Walls never yield, so a
    // sealed start opens only its furniture sides — never a route through a wall.
    // Consulted lazily, only for start-cell edges the cheap check refused.
    let (scx, scz) = (sx as f32 + 0.5, sz as f32 + 0.5);
    let start_escapes = |dx: i32, dz: i32| {
        !is_movement_blocked_for_mover(
            cache,
            scx,
            scz,
            scx + dx as f32,
            scz + dz as f32,
            start_floor,
            None,
        )
    };

    let mut best_h = start_h;
    let mut best_key = start_key;
    let mut termination = crate::pathfinding::PathTermination::Unreachable;
    let check_sealed = check_sealed
        && confine_to_floor
        && cache.values().any(|rp| {
            (rp.min_x..rp.max_x).contains(&(gx as f32))
                && (rp.min_z..rp.max_z).contains(&(gz as f32))
        });
    let mut stall_deadline = (start_h <= SEALED_NEAR_H).then_some(SEALED_STALL_NODES);

    while let Some(Reverse(cur)) = open.pop() {
        if extent.expanded >= max_nodes {
            termination = crate::pathfinding::PathTermination::NodeLimit;
            break;
        }
        extent.expanded += 1;
        extent.include(cur.x, cur.z, key_to_floor(cur.fk));

        let cur_key: AStarKey = (cur.x, cur.z, cur.fk);

        // Accept goal at exact fk or any intermediate stair fk on the same floor.
        // This handles clicking mid-stairwell where the cell is only reachable
        // via stair expansion with an intermediate fk, not the regular floor fk.
        if cur.x == gx && cur.z == gz && key_to_floor(cur.fk) == goal_floor {
            return PathResult {
                waypoints: reconstruct_path_vf(&closed, start_key, cur_key, goal_x, goal_z),
                found: true,
                termination: crate::pathfinding::PathTermination::Reached,
            };
        }

        if check_sealed && stall_deadline == Some(extent.expanded) {
            if let Some(cell) = sealed_goal_frontier(
                cache,
                &stair_positions,
                blocked,
                (sx, sz),
                (gx, gz),
                goal_floor,
                &start_escapes,
                extent,
            ) {
                let key = (cell.0, cell.1, start_fk);
                let waypoints = if cell == (sx, sz) {
                    Vec::new()
                } else if closed.contains_key(&key) {
                    reconstruct_path_vf(
                        &closed,
                        start_key,
                        key,
                        cell.0 as f32 + 0.5,
                        cell.1 as f32 + 0.5,
                    )
                } else {
                    let mut leg = SearchExtent::default();
                    let result = find_path_avoiding_counted(
                        start_x,
                        start_z,
                        start_floor,
                        cell.0 as f32 + 0.5,
                        cell.1 as f32 + 0.5,
                        goal_floor,
                        cache,
                        max_nodes.saturating_sub(extent.expanded),
                        blocked,
                        &mut leg,
                        false,
                    );
                    extent.absorb(&leg);
                    if !result.found {
                        return result;
                    }
                    result.waypoints
                };
                return PathResult {
                    waypoints,
                    found: false,
                    termination: crate::pathfinding::PathTermination::Unreachable,
                };
            }
        }

        if let Some(entry) = closed.get(&cur_key) {
            if cur.g > entry.g {
                continue;
            }
        }

        let on_regular = is_regular_key(cur.fk);
        let cur_floor = key_to_floor(cur.fk);

        // --- Regular floor expansion (cardinal neighbors) ---
        // Skip stairwell interior cells that aren't landings on this regular floor
        let is_stair_interior = stair_positions.contains(&(cur.x, cur.z, cur_floor))
            && !stair_cells.contains_key(&cur_key);
        if on_regular && !is_stair_interior {
            for &(dx, dz) in &DIRS {
                let nx = cur.x + dx;
                let nz = cur.z + dz;
                let new_g = cur.g + 1;

                if cell_blocked(blocked, nx, nz)
                    || (is_cardinal_move_blocked(cache, cur.x, cur.z, dx, dz, cur_floor)
                        && !(cur_key == start_key && start_escapes(dx, dz)))
                {
                    continue;
                }

                // Block moves into stairwell interior cells on regular floor.
                // A cell (nx, nz) is a stairwell interior if it belongs to a
                // stairwell but has no stair_cells entry at the current fk
                // (only landings match regular floor keys).
                if stair_positions.contains(&(nx, nz, cur_floor))
                    && !stair_cells.contains_key(&(nx, nz, cur.fk))
                {
                    continue;
                }

                let nkey: AStarKey = (nx, nz, cur.fk);
                if let Some(existing) = closed.get(&nkey) {
                    if existing.g <= new_g {
                        continue;
                    }
                }

                closed.insert(
                    nkey,
                    ClosedEntry {
                        g: new_g,
                        parent: cur_key,
                    },
                );
                let nh = h(nx, nz, cur.fk);
                open.push(Reverse(AStarNode {
                    x: nx,
                    z: nz,
                    fk: cur.fk,
                    g: new_g,
                    f: new_g + nh,
                }));
                if nh < best_h {
                    best_h = nh;
                    best_key = nkey;
                    if nh <= SEALED_NEAR_H {
                        stall_deadline.get_or_insert(extent.expanded + SEALED_STALL_NODES);
                    }
                }
            }
        }

        // --- Stairwell axis expansion (prev/next along stairwell) ---
        // Disabled under floor confinement so the search never leaves
        // start_floor via the stairs; the bool short-circuits the per-node
        // stair-cell lookup on that (dungeon-monster) hot path.
        if !confine_to_floor {
            if let Some(sc) = stair_cells.get(&cur_key) {
                for neighbor in [&sc.prev, &sc.next].into_iter().flatten() {
                    if cell_blocked(blocked, neighbor.x, neighbor.z) {
                        continue;
                    }
                    let new_g = cur.g + 1;
                    let nkey: AStarKey = (neighbor.x, neighbor.z, neighbor.fk);
                    if let Some(existing) = closed.get(&nkey) {
                        if existing.g <= new_g {
                            continue;
                        }
                    }
                    closed.insert(
                        nkey,
                        ClosedEntry {
                            g: new_g,
                            parent: cur_key,
                        },
                    );
                    let nh = h(neighbor.x, neighbor.z, neighbor.fk);
                    open.push(Reverse(AStarNode {
                        x: neighbor.x,
                        z: neighbor.z,
                        fk: neighbor.fk,
                        g: new_g,
                        f: new_g + nh,
                    }));
                    if nh < best_h {
                        best_h = nh;
                        best_key = nkey;
                    }
                }
            }
        }
    }

    // Partial path to closest node
    let (bx, bz, _) = best_key;
    if best_key != start_key {
        return PathResult {
            waypoints: reconstruct_path_vf(
                &closed,
                start_key,
                best_key,
                bx as f32 + 0.5,
                bz as f32 + 0.5,
            ),
            found: false,
            termination,
        };
    }

    PathResult {
        waypoints: Vec::new(),
        found: false,
        termination,
    }
}

/// The cell to approach when the goal's pocket is sealed off from `start`:
/// outside the pocket, across one of its walls, nearest the goal, and not a
/// `blocked` cell the route could never end on. `None` when the pocket leaks
/// (outgrows `SEALED_MAX_CELLS`, touches stairs, or `start` enters it through
/// an open edge or the furniture waiver). Walks the reverse moves, so a one-way
/// edge counts the way A* would cross it. Every cell read is charged to `extent`.
#[allow(clippy::too_many_arguments)]
fn sealed_goal_frontier(
    cache: &PassabilityCache,
    stair_positions: &HashSet<(i32, i32, u8)>,
    blocked: &[(i32, i32)],
    start: (i32, i32),
    goal: (i32, i32),
    floor: u8,
    start_escapes: &impl Fn(i32, i32) -> bool,
    extent: &mut SearchExtent,
) -> Option<(i32, i32)> {
    let mut pocket = vec![goal];
    let mut walled = Vec::new();
    let sealed = 'fill: {
        let mut next = 0;
        while let Some(&(x, z)) = pocket.get(next) {
            next += 1;
            for &(dx, dz) in &DIRS {
                let n = (x + dx, z + dz);
                if pocket.contains(&n) {
                    continue;
                }
                let walls = is_cardinal_move_blocked(cache, n.0, n.1, -dx, -dz, floor);
                if n == start && (!walls || start_escapes(-dx, -dz)) {
                    break 'fill false;
                }
                if walls {
                    walled.push(n);
                    continue;
                }
                if stair_positions.contains(&(n.0, n.1, floor)) || pocket.len() >= SEALED_MAX_CELLS
                {
                    break 'fill false;
                }
                pocket.push(n);
            }
        }
        true
    };
    for &(x, z) in &pocket {
        extent.include(x, z, floor);
    }
    extent.expanded += pocket.len();
    if !sealed {
        return None;
    }
    let dist = |a: (i32, i32), b: (i32, i32)| (a.0 - b.0).abs() + (a.1 - b.1).abs();
    walled
        .into_iter()
        .filter(|&cell| !pocket.contains(&cell) && !cell_blocked(blocked, cell.0, cell.1))
        .min_by_key(|&cell| (dist(cell, goal), dist(cell, start)))
}

fn reconstruct_path_vf(
    closed: &HashMap<AStarKey, ClosedEntry>,
    start: AStarKey,
    end: AStarKey,
    final_x: f32,
    final_z: f32,
) -> Vec<PathWaypoint> {
    let mut path = Vec::new();
    let mut key = end;

    while key != start {
        let (cx, cz, fk) = key;
        // Stair steps are interpolated client-side; keep only landings and the endpoint.
        if key == end {
            path.push(PathWaypoint {
                x: final_x,
                z: final_z,
                floor: key_to_floor(fk),
            });
        } else if is_regular_key(fk) {
            path.push(PathWaypoint {
                x: cx as f32 + 0.5,
                z: cz as f32 + 0.5,
                floor: key_to_floor(fk),
            });
        }
        let entry = match closed.get(&key) {
            Some(e) => e,
            None => break,
        };
        key = entry.parent;
    }

    path.reverse();
    path
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pathfinding::tests::perimeter_walls;
    use crate::pathfinding::{PathTermination, RuntimeFloorGrid, RuntimePassability, EDGE_S};

    /// Prod house r-30_+81_7, a 6×4 room whose door is the +Z wall's fourth
    /// segment; a monster waited outside it on 10/26 for a player shut inside.
    fn house(door_open: bool) -> PassabilityCache {
        let mut cells = perimeter_walls(6, 4);
        if door_open {
            cells[3 * 6 + 3] &= !EDGE_S;
        }
        let mut cache = PassabilityCache::new();
        cache.insert(
            "r-30_+81_7".into(),
            RuntimePassability {
                house_origin_x: -1882.0,
                house_origin_z: 5212.0,
                min_x: -1882.0,
                max_x: -1876.0,
                min_z: 5212.0,
                max_z: 5216.0,
                floors: vec![RuntimeFloorGrid {
                    floor_level: 0,
                    origin_x: 0,
                    origin_z: 0,
                    width: 6,
                    depth: 4,
                    y_base: 1.15,
                    wall_height: 3.0,
                    cells,
                }],
                stairwells: vec![],
                yields_to_trapped_mover: false,
                allows_projectiles: false,
                is_ground: true,
            },
        );
        cache
    }

    fn path_into_house(
        cache: &PassabilityCache,
        start: (f32, f32),
        blocked: &[(i32, i32)],
    ) -> (PathResult, SearchExtent) {
        let mut extent = SearchExtent::default();
        let result = find_path_avoiding_counted(
            start.0,
            start.1,
            0,
            -1876.5,
            5215.5,
            0,
            cache,
            DEFAULT_MAX_NODES,
            blocked,
            &mut extent,
            true,
        );
        (result, extent)
    }

    #[test]
    fn a_closed_house_goal_stops_early_at_the_wall() {
        let cache = house(false);
        for start in [(-1878.5, 5216.5), (-1878.5, 5240.5)] {
            let (result, extent) = path_into_house(&cache, start, &[]);
            assert!(!result.found);
            assert_eq!(result.termination, PathTermination::Unreachable);
            assert!(extent.expanded < 300, "expanded {}", extent.expanded);
            let last = result.waypoints.last().expect("a leg to the wall");
            assert_eq!((last.x, last.z), (-1876.5, 5216.5));
            assert!(extent.min.1 <= 5212 && extent.max.0 >= -1877);
        }
    }

    #[test]
    fn a_monster_in_the_doorway_is_not_the_cell_to_approach() {
        let (result, extent) = path_into_house(&house(false), (-1878.5, 5240.5), &[(-1877, 5216)]);
        assert_eq!(result.termination, PathTermination::Unreachable);
        assert!(extent.expanded < 300, "expanded {}", extent.expanded);
        let last = result.waypoints.last().unwrap();
        assert_ne!((last.x, last.z), (-1876.5, 5216.5));
    }

    #[test]
    fn open_ground_searches_skip_the_check() {
        let cache = PassabilityCache::new();
        let run = |check_sealed| {
            let mut extent = SearchExtent::default();
            let result = find_path_avoiding_counted(
                0.5,
                0.5,
                0,
                60.5,
                40.5,
                0,
                &cache,
                DEFAULT_MAX_NODES,
                &[],
                &mut extent,
                check_sealed,
            );
            (result.found, extent.expanded)
        };
        assert_eq!(run(true), run(false));
    }

    #[test]
    fn an_open_door_still_leads_inside() {
        let (result, _) = path_into_house(&house(true), (-1878.5, 5240.5), &[]);
        assert!(result.found);
        let last = result.waypoints.last().unwrap();
        assert_eq!((last.x, last.z), (-1876.5, 5215.5));
    }
}
