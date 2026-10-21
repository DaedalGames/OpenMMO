//! Telegraphed boss skills: the brain casts, holds still, and strikes once.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MonsterSkillId {
    RuneSlash,
    EarthRoar,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SkillArea {
    /// Radius and half-angle about the facing locked at cast start.
    Fan { range: f32, half_angle: f32 },
    /// Everyone within `radius` of the caster's body, walls aside.
    Zone { radius: f32 },
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SkillDamage {
    /// The plain swing's roll, times `multiplier`.
    Scaled {
        multiplier: u32,
        ignores_guard: bool,
    },
    /// Always lands for exactly this much; only a full health bar outlasts it.
    Fixed(u32),
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MonsterSkill {
    pub id: MonsterSkillId,
    /// The skill clip's length; the brain stands still and ignores staggers
    /// this long.
    pub cast_ms: f32,
    /// Damage lands once, this far into the cast.
    pub strike_ms: f32,
    pub cooldown_ms: f32,
    /// Cooldown already running when the brain spawns, so the first cast comes
    /// after a few plain swings.
    pub first_cast_ms: f32,
    pub area: SkillArea,
    pub damage: SkillDamage,
}

/// Times follow `BARKAN_RUNE_SLASH` and the blade sweep measured into
/// doc/assets/barkan-rune-slash-bake.json: the raised-sword telegraph runs to
/// 2.25s, the blade circles overhead, then sweeps right to left from 2.55s.
pub const RUNE_SLASH: MonsterSkill = MonsterSkill {
    id: MonsterSkillId::RuneSlash,
    cast_ms: 4200.0,
    strike_ms: 2550.0,
    cooldown_ms: 15000.0,
    first_cast_ms: 6000.0,
    area: SkillArea::Fan {
        range: 4.0,
        half_angle: std::f32::consts::FRAC_PI_4,
    },
    // The fan is dodged by stepping out, not by armor.
    damage: SkillDamage::Scaled {
        multiplier: 5,
        ignores_guard: true,
    },
};

/// Terraclash's roar (doc/TIER5_FIELD_RAID.md 대지의 포효), as far as its
/// ranged swing reaches (`rangedAttackRange`), which is a bow shot. 165 is what the lowest max HP
/// above level 35 survives once. The strike follows the roar pose in
/// `tools/blender-scripts/rig_terraclash.py`.
pub const EARTH_ROAR: MonsterSkill = MonsterSkill {
    id: MonsterSkillId::EarthRoar,
    cast_ms: 6200.0,
    strike_ms: 4000.0,
    cooldown_ms: 60_000.0,
    first_cast_ms: 30_000.0,
    area: SkillArea::Zone { radius: 11.0 },
    damage: SkillDamage::Fixed(165),
};

/// Eruption radius of a ranged plain swing (`MonsterGroundStrike`).
pub const GROUND_STRIKE_RADIUS: f32 = 1.5;

pub fn skill_by_id(id: MonsterSkillId) -> &'static MonsterSkill {
    match id {
        MonsterSkillId::RuneSlash => &RUNE_SLASH,
        MonsterSkillId::EarthRoar => &EARTH_ROAR,
    }
}

pub fn skill_for(monster_type: &str) -> Option<&'static MonsterSkill> {
    match monster_type {
        "barkan" => Some(&RUNE_SLASH),
        "terraclash" => Some(&EARTH_ROAR),
        _ => None,
    }
}

/// Allowance for a body straddling the fan's sides.
const BODY_RADIUS: f32 = 0.4;

impl MonsterSkill {
    /// How far from the caster the skill reaches.
    pub fn range(&self) -> f32 {
        match self.area {
            SkillArea::Fan { range, .. } => range,
            SkillArea::Zone { radius } => radius,
        }
    }

    /// Whether `target` stands in the fan cast from `origin` facing `rotation`.
    pub fn fan_contains(
        &self,
        origin: &crate::Position,
        rotation: f32,
        target: &crate::Position,
    ) -> bool {
        let SkillArea::Fan { range, half_angle } = self.area else {
            return false;
        };
        let dist_sq = origin.dist_xz_sq(target);
        if !dist_sq.is_finite() || dist_sq > range.powi(2) {
            return false;
        }
        let Some(bearing) = origin.bearing_xz_to(target) else {
            return true;
        };
        let off = crate::mount_movement::angle_delta(rotation, bearing);
        let edge = (BODY_RADIUS / dist_sq.sqrt()).min(1.0).asin();
        off.abs() <= half_angle + edge
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Position;

    fn at(x: f32, z: f32) -> Position {
        Position { x, y: 0.0, z }
    }

    #[test]
    fn rune_slash_fan_covers_the_front_only() {
        let origin = at(0.0, 0.0);
        assert!(RUNE_SLASH.fan_contains(&origin, 0.0, &at(0.0, 3.0)));
        assert!(RUNE_SLASH.fan_contains(&origin, 0.0, &at(-2.0, 2.2)));
        assert!(!RUNE_SLASH.fan_contains(&origin, 0.0, &at(-2.5, 0.5)));
        assert!(!RUNE_SLASH.fan_contains(&origin, 0.0, &at(0.0, -2.0)));
        assert!(!RUNE_SLASH.fan_contains(&origin, 0.0, &at(0.0, 5.0)));
        let east = std::f32::consts::FRAC_PI_2;
        assert!(RUNE_SLASH.fan_contains(&origin, east, &at(3.0, 0.0)));
        assert!(!RUNE_SLASH.fan_contains(&origin, east, &at(-3.0, 0.0)));
    }
}
