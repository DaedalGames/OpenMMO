//! Telegraphed boss skills: the brain casts, holds still, and strikes once.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MonsterSkillId {
    RuneSlash,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MonsterSkill {
    pub id: MonsterSkillId,
    /// The skill clip's length; the brain stands still and ignores staggers
    /// this long.
    pub cast_ms: f32,
    /// Damage lands once, when the blade starts its sideways sweep.
    pub strike_ms: f32,
    pub cooldown_ms: f32,
    /// Cooldown already running when the brain spawns, so the first cast comes
    /// after a few plain swings.
    pub first_cast_ms: f32,
    /// Fan radius and half-angle about the facing locked at cast start.
    pub range: f32,
    pub half_angle: f32,
    pub damage_multiplier: u32,
    /// The fan is dodged by stepping out, not by armor.
    pub ignores_guard: bool,
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
    range: 4.0,
    half_angle: std::f32::consts::FRAC_PI_4,
    damage_multiplier: 5,
    ignores_guard: true,
};

pub fn skill_by_id(id: MonsterSkillId) -> &'static MonsterSkill {
    match id {
        MonsterSkillId::RuneSlash => &RUNE_SLASH,
    }
}

pub fn skill_for(monster_type: &str) -> Option<&'static MonsterSkill> {
    match monster_type {
        "barkan" => Some(&RUNE_SLASH),
        _ => None,
    }
}

/// Allowance for a body straddling the fan's sides.
const BODY_RADIUS: f32 = 0.4;

impl MonsterSkill {
    /// Whether `target` stands in the fan cast from `origin` facing `rotation`.
    pub fn fan_contains(
        &self,
        origin: &crate::Position,
        rotation: f32,
        target: &crate::Position,
    ) -> bool {
        let dist_sq = origin.dist_xz_sq(target);
        if !dist_sq.is_finite() || dist_sq > self.range.powi(2) {
            return false;
        }
        let Some(bearing) = origin.bearing_xz_to(target) else {
            return true;
        };
        let off = crate::mount_movement::angle_delta(rotation, bearing);
        let edge = (BODY_RADIUS / dist_sq.sqrt()).min(1.0).asin();
        off.abs() <= self.half_angle + edge
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
