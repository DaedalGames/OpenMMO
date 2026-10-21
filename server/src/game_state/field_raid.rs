//! Altar offerings and the field raid they open (doc/TIER5_FIELD_RAID.md).

use super::bed_rest::within_reach;
use super::inventory::consume_one;
use super::passability::regions_around;
use super::player_interaction::placement_position;
use super::GameState;
use crate::types::{MonsterLifecycle, PlayerId};
use onlinerpg_shared::altar::{altar_def, is_stand_in, AltarDef};
use onlinerpg_shared::furniture::FurniturePlacement;
use onlinerpg_shared::messages::{AltarStatus, FieldRaidOutcome};
use onlinerpg_shared::moon::is_full_moon_night;
use onlinerpg_shared::{MonsterState, Position, ServerMessage};
use std::borrow::Cow;
use std::time::Duration;
use tracing::{info, warn};

/// Living characters within this of the boss keep the raid going.
const BATTLE_ZONE_RADIUS_M: f32 = 40.0;
/// Who hears how the raid ended.
const NOTICE_RADIUS_M: f32 = 100.0;
pub(crate) const FIELD_RAID_TICK: Duration = Duration::from_secs(1);
/// Raid ticks from the offering to the boss standing up, so the client's
/// crumbling stand-in has time to play.
pub(super) const WAKE_TICKS: u8 = 3;
/// When the client collapses the stand-in. The spawn lands on the last wake
/// tick, up to one tick period later, inside the dust.
const WAKE_IN_MS: u32 = (WAKE_TICKS as u32 - 1) * FIELD_RAID_TICK.as_millis() as u32;
/// A stand-in this close to the boss is the one it rose from
/// (`WOKEN_RADIUS_M` in the client's ObjectOverlay).
const STAND_IN_RADIUS_M: f32 = 8.0;

#[derive(Clone)]
pub(crate) struct FieldRaid {
    monster_type: String,
    position: Position,
    rotation: f32,
    phase: Phase,
    /// The offering character, by character id since a reconnect changes
    /// the player id mid-raid.
    summoner: Option<i64>,
    reward: Option<String>,
    summoner_hit: bool,
}

#[derive(Clone)]
enum Phase {
    /// Offered; the boss spawns outside the offering's locks on the tick
    /// that brings this to zero.
    Waking {
        ticks_left: u8,
    },
    Fighting {
        monster_id: String,
    },
}

impl GameState {
    /// The altar placement `object_id` the player can reach, with its definition.
    async fn reachable_altar(
        &self,
        player_id: &PlayerId,
        object_id: u32,
    ) -> Option<(FurniturePlacement, &'static AltarDef)> {
        let players = self.players.read().await;
        let player = players.get(player_id)?;
        let index = self
            .interaction_furniture
            .read()
            .unwrap_or_else(|e| e.into_inner());
        regions_around(player.position.x, player.position.z)
            .filter_map(|key| index.get(&key))
            .flatten()
            .filter(|p| p.id == object_id)
            .filter_map(|p| Some((p, altar_def(&p.type_id)?)))
            .find(|(p, _)| within_reach(player, placement_position(p), p.floor_level as i8))
            .map(|(p, def)| (p.clone(), def))
    }

    /// What the altar would do for the player now, and the bag item it would take.
    async fn altar_status(
        &self,
        player_id: &PlayerId,
        def: &AltarDef,
    ) -> (AltarStatus, Option<u64>) {
        if self.field_raid.lock().await.is_some() {
            return (AltarStatus::RaidActive, None);
        }
        if !is_full_moon_night(&self.current_game_datetime()) {
            return (AltarStatus::NotFullMoon, None);
        }
        let inventories = self.inventories.read().await;
        let Some(inv) = inventories.get(player_id) else {
            return (AltarStatus::NoOffering, None);
        };
        if let Some(item) = inv
            .bag
            .iter()
            .find(|i| i.item_def_id == def.offering && i.quantity > 0)
        {
            let status = AltarStatus::Ready {
                offering: def.offering.clone(),
                monster: def.monster.clone(),
            };
            (status, Some(item.instance_id))
        } else if inv.equipped.values().any(|i| i.item_def_id == def.offering) {
            let status = AltarStatus::OfferingEquipped {
                offering: def.offering.clone(),
            };
            (status, None)
        } else {
            (AltarStatus::NoOffering, None)
        }
    }

    pub async fn inspect_altar(&self, player_id: &PlayerId, object_id: u32) {
        let Some((_, def)) = self.reachable_altar(player_id, object_id).await else {
            return;
        };
        let (status, _) = self.altar_status(player_id, def).await;
        self.send_direct_message(player_id, ServerMessage::AltarStatus { object_id, status })
            .await;
    }

    pub async fn offer_at_altar(&self, player_id: &PlayerId, object_id: u32) {
        if self
            .reject_if_defeated(player_id, "You can't do that while defeated")
            .await
        {
            return;
        }
        let Some((altar, def)) = self.reachable_altar(player_id, object_id).await else {
            return;
        };
        let (status, instance_id) = self.altar_status(player_id, def).await;
        let Some(instance_id) = instance_id else {
            self.send_direct_message(player_id, ServerMessage::AltarStatus { object_id, status })
                .await;
            return;
        };
        if self
            .reject_if_trade_reserved(player_id, instance_id, "offer")
            .await
        {
            return;
        }
        let (x, z, rotation) = def.spawn_pose(&altar);
        // Ground, not the stand-in's base: that sits sunk into a slope.
        let y = match self.ground_and_depth_at(x, z).await {
            Some((ground, _)) => ground,
            None => altar.y,
        };
        let position = Position { x, y, z };
        let summoner = self.character_id_of(player_id).await;
        // Raid state and the item go together, so a valid offering always
        // opens exactly one raid and a refused one keeps its item.
        let snapshot = {
            let mut raid = self.field_raid.lock().await;
            let mut inventories = self.inventories.write().await;
            let consumed = inventories
                .get_mut(player_id)
                .filter(|_| raid.is_none())
                .filter(|inv| {
                    inv.bag
                        .iter()
                        .any(|i| i.instance_id == instance_id && i.item_def_id == def.offering)
                })
                .and_then(|inv| consume_one(inv, instance_id).map(|_| inv.clone()));
            if consumed.is_some() {
                *raid = Some(FieldRaid {
                    monster_type: def.monster.clone(),
                    position,
                    rotation,
                    phase: Phase::Waking {
                        ticks_left: WAKE_TICKS,
                    },
                    summoner,
                    reward: def.reward.clone(),
                    summoner_hit: false,
                });
            }
            consumed
        };
        let Some(snapshot) = snapshot else {
            // Another offering got there first, or the item moved: say why.
            self.inspect_altar(player_id, object_id).await;
            return;
        };
        self.mark_inventory_dirty(player_id).await;
        self.send_inventory_snapshot(player_id, snapshot).await;
        self.log_consumed(player_id, [def.offering.as_str()]).await;
        info!(
            "{player_id} offered at {} ({:.1},{:.1}); {} wakes at ({x:.1},{z:.1})",
            altar.type_id, altar.x, altar.z, def.monster,
        );
        let nearby = self
            .player_ids_within_position(&position, 0, NOTICE_RADIUS_M)
            .await;
        self.send_direct_message_to_players(
            &nearby,
            ServerMessage::FieldBossWaking {
                monster: def.monster.clone(),
                position,
                wake_in_ms: WAKE_IN_MS,
            },
        )
        .await;
    }

    /// A damaging hit on the raid boss; only the summoner's first one matters.
    pub(super) async fn record_field_raid_hit(&self, player_id: &PlayerId, damage: u32) {
        if damage == 0 {
            return;
        }
        let summoner = match self.field_raid.lock().await.as_ref() {
            Some(raid) if !raid.summoner_hit => raid.summoner,
            _ => return,
        };
        if summoner.is_none() || self.character_id_of(player_id).await != summoner {
            return;
        }
        if let Some(raid) = self.field_raid.lock().await.as_mut() {
            raid.summoner_hit = true;
        }
    }

    /// Wake the boss after an offering; end the raid on a kill, a set moon or
    /// an empty battle zone. Only this tick advances a raid, so it works from a
    /// copy and never holds `field_raid` across the spawn and despawn it sets off.
    pub async fn tick_field_raid(&self) {
        let Some(raid) = self.field_raid.lock().await.clone() else {
            return;
        };
        match raid.phase {
            Phase::Waking { ticks_left } if ticks_left > 1 => {
                if let Some(raid) = self.field_raid.lock().await.as_mut() {
                    raid.phase = Phase::Waking {
                        ticks_left: ticks_left - 1,
                    };
                }
            }
            Phase::Waking { .. } => match self.wake_field_boss(&raid).await {
                Some(monster_id) => {
                    if let Some(raid) = self.field_raid.lock().await.as_mut() {
                        raid.phase = Phase::Fighting { monster_id };
                    }
                    self.set_field_boss_up_at(raid.position, true);
                }
                None => {
                    warn!(
                        "Field raid: {} failed to spawn; raid dropped",
                        raid.monster_type
                    );
                    *self.field_raid.lock().await = None;
                }
            },
            Phase::Fighting { ref monster_id } => {
                let alive = self
                    .monsters
                    .read()
                    .await
                    .get(monster_id)
                    .is_some_and(|m| m.state != MonsterState::Dead);
                let outcome = if !alive {
                    FieldRaidOutcome::Defeated
                } else if !is_full_moon_night(&self.current_game_datetime()) {
                    FieldRaidOutcome::MoonSet
                } else if self.living_near(&raid.position).await.is_empty() {
                    FieldRaidOutcome::Wiped
                } else {
                    return;
                };
                self.end_field_raid(&raid, monster_id, outcome).await;
            }
        }
    }

    /// `placements` minus a stand-in the raid boss stands on.
    pub(super) fn without_woken_stand_in<'a>(
        &self,
        placements: &'a [FurniturePlacement],
    ) -> Cow<'a, [FurniturePlacement]> {
        let Some(at) = *self
            .field_boss_up_at
            .read()
            .unwrap_or_else(|e| e.into_inner())
        else {
            return Cow::Borrowed(placements);
        };
        let woken = |p: &FurniturePlacement| {
            is_stand_in(&p.type_id)
                && placement_position(p).dist_xz_sq(&at) <= STAND_IN_RADIUS_M * STAND_IN_RADIUS_M
        };
        if !placements.iter().any(woken) {
            return Cow::Borrowed(placements);
        }
        placements.iter().filter(|p| !woken(p)).cloned().collect()
    }

    /// Record the boss up or down and rebuild the stand-in regions' collision.
    fn set_field_boss_up_at(&self, at: Position, up: bool) {
        *self
            .field_boss_up_at
            .write()
            .unwrap_or_else(|e| e.into_inner()) = up.then_some(at);
        let regions: Vec<_> = {
            let index = self
                .interaction_furniture
                .read()
                .unwrap_or_else(|e| e.into_inner());
            regions_around(at.x, at.z)
                .filter_map(|key| Some((key, index.get(&key)?)))
                .filter(|(_, placements)| placements.iter().any(|p| is_stand_in(&p.type_id)))
                .map(|(key, placements)| (key, placements.clone()))
                .collect()
        };
        for ((rx, rz), placements) in regions {
            self.sync_region_furniture(rx, rz, &placements);
        }
    }

    /// Living characters in the battle zone.
    async fn living_near(&self, center: &Position) -> Vec<PlayerId> {
        let mut ids = self
            .player_ids_within_position(center, 0, BATTLE_ZONE_RADIUS_M)
            .await;
        let players = self.players.read().await;
        ids.retain(|id| players.get(id).is_some_and(|p| p.health > 0));
        ids
    }

    async fn wake_field_boss(&self, raid: &FieldRaid) -> Option<String> {
        self.spawn_monster(
            raid.monster_type.clone(),
            raid.position,
            raid.rotation,
            0,
            MonsterLifecycle::FieldRaid,
            None,
            true,
        )
        .await
        .map(|m| m.id)
    }

    /// A defeated boss is left to the kill's own corpse timer.
    async fn end_field_raid(&self, raid: &FieldRaid, monster_id: &str, outcome: FieldRaidOutcome) {
        *self.field_raid.lock().await = None;
        self.set_field_boss_up_at(raid.position, false);
        if outcome != FieldRaidOutcome::Defeated {
            self.despawn_monsters(vec![monster_id.to_string()]).await;
        }
        info!("Field raid {} ended: {outcome:?}", raid.monster_type);
        let rewarded = match outcome {
            FieldRaidOutcome::Defeated => self.grant_summoner_reward(raid).await,
            _ => None,
        };
        // The raiders gathered before the offering; only those around hear it.
        let nearby = self
            .player_ids_within_position(&raid.position, 0, NOTICE_RADIUS_M)
            .await;
        let notice = |reward| ServerMessage::FieldRaidNotice {
            monster: raid.monster_type.clone(),
            outcome,
            reward,
        };
        self.send_direct_message_to_players_except(&nearby, notice(None), rewarded.as_ref())
            .await;
        if let Some(summoner) = rewarded {
            self.send_direct_message(&summoner, notice(raid.reward.clone()))
                .await;
        }
    }

    /// The summoner earns the altar's reward by hitting the boss and standing
    /// alive in the battle zone when it falls (doc/TIER5_FIELD_RAID.md).
    async fn grant_summoner_reward(&self, raid: &FieldRaid) -> Option<PlayerId> {
        let reward = raid.reward.as_deref()?;
        if !raid.summoner_hit {
            return None;
        }
        let player_id = self.player_id_of_character(raid.summoner?).await?;
        if !self.living_near(&raid.position).await.contains(&player_id) {
            return None;
        }
        self.award_item(&player_id, reward).await;
        info!(
            "Field raid {}: summoner {} earned {reward}",
            raid.monster_type,
            self.player_name_of(&player_id).await
        );
        Some(player_id)
    }

    pub(super) fn full_moon_command(&self) -> Result<String, String> {
        match self.debug_jump_to_full_moon() {
            Some(at) => Ok(format!("Fullmoon: clock moved to {at}.")),
            None => Err("Fullmoon: none within 60 days.".to_string()),
        }
    }
}
