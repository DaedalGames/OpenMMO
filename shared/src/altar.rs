//! Offering altars: catalog objects that consume an item to wake a field boss
//! (doc/TIER5_FIELD_RAID.md).

use std::collections::HashMap;
use std::sync::OnceLock;

use crate::furniture::FurniturePlacement;

static CATALOG_JSON: &str = include_str!("../../data/object_catalog.json");

#[derive(Debug, Clone, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AltarDef {
    pub offering: String,
    pub monster: String,
    /// Boss position in the altar's frame (+Z = altar front), so moving or
    /// turning the altar in the editor carries the wake spot with it.
    pub spawn: AltarSpawn,
}

#[derive(Debug, Clone, Copy, serde::Deserialize)]
pub struct AltarSpawn {
    pub x: f32,
    pub z: f32,
    /// Degrees, added to the altar's yaw.
    #[serde(default)]
    pub rotation: f32,
}

#[derive(serde::Deserialize)]
struct CatalogEntry {
    id: String,
    altar: Option<AltarDef>,
}

fn altars() -> &'static HashMap<String, AltarDef> {
    static TABLE: OnceLock<HashMap<String, AltarDef>> = OnceLock::new();
    TABLE.get_or_init(|| {
        let entries: Vec<CatalogEntry> =
            serde_json::from_str(CATALOG_JSON).expect("data/object_catalog.json is malformed");
        entries
            .into_iter()
            .filter_map(|e| Some((e.id, e.altar?)))
            .collect()
    })
}

pub fn altar_def(type_id: &str) -> Option<&'static AltarDef> {
    altars().get(type_id)
}

impl AltarDef {
    /// World (x, z) and facing in radians of the boss for a placed altar, with
    /// the placement yaw convention of `furniture::footprint_cells`.
    pub fn spawn_pose(&self, altar: &FurniturePlacement) -> (f32, f32, f32) {
        let yaw = altar.rotation_deg.to_radians();
        let (s, c) = yaw.sin_cos();
        let (lx, lz) = (self.spawn.x, self.spawn.z);
        (
            crate::world::wrap_world_x(altar.x + lx * c + lz * s),
            altar.z - lx * s + lz * c,
            (altar.rotation_deg + self.spawn.rotation).to_radians(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terraclash_altar_wakes_the_boss_behind_it() {
        let def = altar_def("terraclash_altar").expect("terraclash_altar has an altar entry");
        assert_eq!(def.offering, "earth_amulet");
        assert_eq!(def.monster, "terraclash");
        let altar = FurniturePlacement {
            id: 3,
            type_id: "terraclash_altar".into(),
            x: -1842.4,
            y: 16.5,
            z: 5516.8,
            rotation_deg: 270.0,
            floor_level: 0,
        };
        let (x, z, facing) = def.spawn_pose(&altar);
        assert!(
            (x - -1828.7).abs() < 0.01 && (z - 5519.9).abs() < 0.01,
            "({x}, {z})"
        );
        assert!((facing - 270f32.to_radians()).abs() < 1e-4);
    }
}
