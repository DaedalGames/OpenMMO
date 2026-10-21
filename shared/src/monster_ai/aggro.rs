//! Threat-based targeting for raid bosses (doc/TIER5_FIELD_RAID.md 패턴): the
//! top recent damage dealer in reach draws the swings, and now and then a potion
//! drinker or an idler, near or far, is struck instead.

use super::{NearbyPlayer, PathProvider};
use crate::PlayerId;
use rand::seq::SliceRandom;
use rand::Rng;
use std::collections::HashMap;

#[derive(Debug, PartialEq)]
pub struct AggroRules {
    /// Chance per swing to strike a distraction target instead.
    pub distraction_chance: f32,
    /// A player who has not swung at the boss for this long is idle.
    pub idle_ms: f32,
    /// Ground-strike reach for a distraction swing, from the engage point.
    pub far_reach: f32,
    /// Damage threat halves over this long, so a past burst gives way to
    /// whoever keeps hitting now.
    pub threat_half_life_ms: f32,
}

pub const TERRACLASH_AGGRO: AggroRules = AggroRules {
    distraction_chance: 0.25,
    idle_ms: 10_000.0,
    far_reach: 20.0,
    threat_half_life_ms: 30_000.0,
};

/// How long a potion drinker counts as one ([`super::NearbyPlayer::drank_recently`]);
/// a bit over one Terraclash swing cooldown, so the drinker sees a roll.
pub const DRANK_RECENTLY_MS: u64 = 5_000;

pub fn aggro_for(monster_type: &str) -> Option<&'static AggroRules> {
    match monster_type {
        "terraclash" => Some(&TERRACLASH_AGGRO),
        _ => None,
    }
}

/// Per-player tally, keyed by player id: a reconnect starts from zero.
#[derive(Debug, Clone, PartialEq)]
pub(super) struct Aggro {
    pub(super) rules: &'static AggroRules,
    threat: HashMap<PlayerId, f32>,
    last_swing_ms: HashMap<PlayerId, f32>,
    clock_ms: f32,
    /// A swing went out since the last pick, so the next one may roll for a
    /// distraction.
    pub(super) roll_due: bool,
    /// The current target is a distraction, struck at far reach; cleared once
    /// struck.
    pub(super) far: bool,
}

impl Aggro {
    pub(super) fn new(rules: &'static AggroRules) -> Self {
        Self {
            rules,
            threat: HashMap::new(),
            last_swing_ms: HashMap::new(),
            clock_ms: 0.0,
            roll_due: true,
            far: false,
        }
    }

    pub(super) fn advance(&mut self, delta_ms: f32) {
        self.clock_ms += delta_ms;
        let keep = 0.5f32.powf(delta_ms / self.rules.threat_half_life_ms);
        self.threat.values_mut().for_each(|t| *t *= keep);
    }

    /// A swing at the boss, hit or miss.
    pub(super) fn record(&mut self, attacker: PlayerId, damage: u32) {
        *self.threat.entry(attacker).or_default() += damage as f32;
        self.last_swing_ms.insert(attacker, self.clock_ms);
    }

    fn threat_of(&self, player: &PlayerId) -> f32 {
        self.threat.get(player).copied().unwrap_or(0.0)
    }

    fn is_idle(&self, player: &PlayerId) -> bool {
        self.last_swing_ms
            .get(player)
            .is_none_or(|at| self.clock_ms - at >= self.rules.idle_ms)
    }
}

impl super::MonsterBrain {
    /// Keep a reachable target; when a swing is due, re-pick by threat and
    /// roll once for a distraction.
    pub(super) fn update_aggro_target(
        &mut self,
        nearby_players: &[NearbyPlayer],
        path_provider: &dyn PathProvider,
        rng: &mut impl Rng,
    ) {
        let Some(aggro) = &self.aggro else {
            return;
        };
        // Until someone swings at it, the tree's own nearest-target pick applies.
        if aggro.last_swing_ms.is_empty() || self.swing_left_ms > 0.0 || self.is_casting() {
            return;
        }
        let range = self.attack_range;
        let roll = aggro.roll_due && self.attack_cooldown_left_ms <= 0.0;
        let reach = |p: &NearbyPlayer, far| {
            self.swing_reach(range, &p.position, self.ground_reach(far), path_provider)
        };
        let current_ok = self
            .current_target(nearby_players)
            .is_some_and(|t| reach(t, aggro.far).is_some());
        if current_ok && !roll {
            return;
        }
        let living = || nearby_players.iter().filter(|p| p.health > 0);

        let distraction = (roll && rng.gen::<f32>() < aggro.rules.distraction_chance)
            .then(|| {
                let candidates: Vec<PlayerId> = living()
                    .filter(|p| p.drank_recently || aggro.is_idle(&p.id))
                    .filter(|p| reach(p, true).is_some())
                    .map(|p| p.id)
                    .collect();
                candidates.choose(rng).copied()
            })
            .flatten();
        let target = distraction.or_else(|| {
            living()
                .filter(|p| reach(p, false).is_some())
                .max_by(|a, b| {
                    aggro
                        .threat_of(&a.id)
                        .total_cmp(&aggro.threat_of(&b.id))
                        .then_with(|| {
                            self.position
                                .dist_xz_sq(&b.position)
                                .total_cmp(&self.position.dist_xz_sq(&a.position))
                        })
                })
                .map(|p| p.id)
        });

        let aggro = self.aggro.as_mut().expect("checked above");
        if roll {
            aggro.roll_due = false;
        }
        aggro.far = distraction.is_some();
        if target != self.target_player_id {
            self.target_player_id = target;
            self.retry_chase();
        }
    }

    /// Ground-strike reach: stretched for a distraction swing.
    pub(super) fn ground_reach(&self, far: bool) -> f32 {
        match &self.aggro {
            Some(aggro) if far => aggro.rules.far_reach,
            _ => self.ranged_range,
        }
    }
}
