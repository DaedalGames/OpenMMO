//! Combat logout (doc/COMBAT_LOGOUT.md): a disconnect mid-fight leaves the
//! character in the world until the fight ends, it dies, or the cap passes.

use super::GameState;
use crate::auth::AuthService;
use crate::types::{Player, PlayerId};
use tracing::info;

pub(super) const COMBAT_LOGOUT_MAX_MS: u64 = 60_000;

pub(super) struct LingeringBody {
    account: String,
    character_id: i64,
    pub(super) disconnected_at: u64,
}

/// Why a lingering body leaves the world now, if it does.
fn finalize_reason(player: &Player, body: &LingeringBody, now_ms: u64) -> Option<&'static str> {
    if player.health == 0 {
        Some("died")
    } else if !GameState::in_combat(player) {
        Some("out of combat")
    } else if now_ms.saturating_sub(body.disconnected_at) >= COMBAT_LOGOUT_MAX_MS {
        Some("time cap")
    } else {
        None
    }
}

/// The account's lingering body, as seen from its next game entry.
pub(crate) struct LingeringEntry {
    pub id: PlayerId,
    pub character_id: i64,
    pub remaining_secs: u64,
}

impl GameState {
    /// Session end for a dropped connection: lingers in combat, else cleans
    /// up now. Callers hold `character_session_lock`.
    pub(super) async fn end_player_session(
        &self,
        id: &PlayerId,
        account: &str,
        auth: &AuthService,
    ) {
        if !self.begin_linger(id, account, auth).await {
            self.cleanup_player_session(id, auth).await;
        }
    }

    async fn begin_linger(&self, id: &PlayerId, account: &str, auth: &AuthService) -> bool {
        let Some(character_id) = self.player_characters.read().await.get(id).map(|c| c.0) else {
            return false;
        };
        let name = {
            let players = self.players.read().await;
            match players.get(id) {
                Some(p) if p.health > 0 && Self::in_combat(p) => p.name.clone(),
                _ => return false,
            }
        };
        self.end_account_activity(id, auth).await;
        self.cancel_concentration_if_active(id).await;
        self.stop_player_attack(id).await;
        self.stop_bed_rest(id).await;
        self.clear_player_movement(id, "disconnect").await;
        self.drop_player_trade(id, "They left.").await;
        self.clear_shops_for_player(id).await;
        self.unregister_connection_channel(id).await;
        self.lingering_bodies.write().await.insert(
            *id,
            LingeringBody {
                account: account.to_ascii_lowercase(),
                character_id,
                disconnected_at: Self::now_ms(),
            },
        );
        self.mark_dirty(id).await;
        info!(player = %name, player_id = %id, "Disconnected in combat; body stays in the world");
        true
    }

    pub async fn tick_combat_logout(&self, auth: &AuthService) {
        if self.lingering_bodies.read().await.is_empty() {
            return;
        }
        let now = Self::now_ms();
        let due: Vec<(PlayerId, &'static str)> = {
            let bodies = self.lingering_bodies.read().await;
            let players = self.players.read().await;
            bodies
                .iter()
                .filter_map(|(id, body)| {
                    let reason = match players.get(id) {
                        Some(player) => finalize_reason(player, body, now)?,
                        None => "gone",
                    };
                    Some((*id, reason))
                })
                .collect()
        };
        for (id, reason) in due {
            let _sessions = self.character_session_lock.lock().await;
            if !self.lingering_bodies.read().await.contains_key(&id) {
                continue;
            }
            info!(player_id = %id, reason, "Lingering body leaves the world");
            self.cleanup_player_session(&id, auth).await;
        }
    }

    pub(crate) async fn lingering_body_of_account(&self, account: &str) -> Option<LingeringEntry> {
        let account = account.to_ascii_lowercase();
        let now = Self::now_ms();
        self.lingering_bodies
            .read()
            .await
            .iter()
            .find(|(_, body)| body.account == account)
            .map(|(id, body)| LingeringEntry {
                id: *id,
                character_id: body.character_id,
                remaining_secs: (body.disconnected_at + COMBAT_LOGOUT_MAX_MS)
                    .saturating_sub(now)
                    .div_ceil(1000),
            })
    }

    /// Rebind a lingering body to a new session, keeping its id, party, buffs
    /// and fight. `None` once it has left. Caller holds
    /// `character_session_lock`.
    pub(crate) async fn resume_lingering_body(
        &self,
        id: PlayerId,
        account: &str,
        session_id: u64,
    ) -> Option<Player> {
        if !self.lingering_bodies.read().await.contains_key(&id) {
            return None;
        }
        let player = {
            let mut players = self.players.write().await;
            let player = players.get_mut(&id)?;
            // Reloading must not buy an entry grace mid-fight.
            player.ready_at = 0;
            player.clone()
        };
        if !self
            .attach_player_to_account_session(account, session_id, id)
            .await
        {
            return None;
        }
        self.lingering_bodies.write().await.remove(&id);
        info!(player = %player.name, player_id = %id, "Lingering body resumed");
        Some(player)
    }

    /// What only a live body has, sent once its connection is registered.
    pub(crate) async fn send_resumed_state(&self, id: &PlayerId) {
        self.send_bow_mark_state(id).await;
        self.send_player_titles(id).await;
        let party = self
            .parties
            .read()
            .await
            .party_of(id)
            .map(|party| (party.leader, party.members.clone()));
        if let Some((leader, members)) = party {
            self.broadcast_party_state(leader, &members).await;
        }
    }
}
