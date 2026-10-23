use super::{auth_db, metrics_response, unix_now, MetricsState};
use axum::{extract::State, response::Response};
use onlinerpg_shared::field_boss::field_boss_defs;
use onlinerpg_shared::messages::FieldRaidOutcome;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct FieldRaidEvent {
    pub timestamp: i64,
    pub boss: String,
    /// `None` for the summon, then how the raid ended.
    pub outcome: Option<FieldRaidOutcome>,
}

impl FieldRaidEvent {
    pub fn storage_key(&self) -> &'static str {
        match self.outcome {
            None => "summoned",
            Some(FieldRaidOutcome::Defeated) => "defeated",
            Some(FieldRaidOutcome::MoonSet) => "moon_set",
            Some(FieldRaidOutcome::Dawn) => "dawn",
            Some(FieldRaidOutcome::Wiped) => "wiped",
        }
    }
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct FieldRaidTally {
    pub summons: u64,
    pub defeated: u64,
    pub moon_set: u64,
    pub dawn: u64,
    pub wiped: u64,
    pub last_defeated_at: Option<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
struct FieldRaidCounts {
    boss: String,
    name: String,
    #[serde(flatten)]
    tally: FieldRaidTally,
}

#[derive(Debug, Serialize, Deserialize)]
struct FieldRaids {
    until: i64,
    collection_started_at: i64,
    bosses: Vec<FieldRaidCounts>,
}

pub(super) async fn field_raids(State(state): State<MetricsState>) -> Response {
    state.game.flush_field_raid_events(&state.auth).await;
    let until = unix_now();
    metrics_response(
        auth_db(move || {
            let (collection_started_at, mut tallies) = state.auth.field_raid_tallies(until)?;
            let (_, monsters, _) = state.game.loot_defs();
            let bosses = field_boss_defs()
                .iter()
                .map(|def| FieldRaidCounts {
                    boss: def.id.clone(),
                    name: monsters
                        .get(&def.monster)
                        .map_or_else(|| def.monster.clone(), |m| m.name.clone()),
                    tally: tallies.remove(&def.id).unwrap_or_default(),
                })
                .collect();
            Ok(FieldRaids {
                until,
                collection_started_at,
                bosses,
            })
        })
        .await,
        "Field raids",
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{auth::AuthService, game_state::tests::make_test_game_state};
    use axum::http::StatusCode;
    use std::sync::Arc;

    #[tokio::test]
    async fn field_raids_count_saved_and_pending_events_per_boss() {
        let dir = crate::test_util::unique_temp_dir("field_raids_api");
        let auth = Arc::new(AuthService::new(dir.join("game.db")).unwrap());
        let game = Arc::new(make_test_game_state("field_raids_api"));
        let now = unix_now();
        let event = |timestamp, outcome| FieldRaidEvent {
            timestamp,
            boss: "terraclash".into(),
            outcome,
        };
        auth.record_field_raid_events(&[
            event(now - 300, None),
            event(now - 200, Some(FieldRaidOutcome::Wiped)),
            event(now - 100, None),
        ])
        .unwrap();
        game.pending_field_raid_events()
            .push(event(now, Some(FieldRaidOutcome::Defeated)));
        let router = crate::metrics::metrics_routes(Arc::clone(&game), Arc::clone(&auth));
        let url = format!(
            "{}/api/metrics/field-raids",
            crate::test_util::serve(router).await
        );

        let response = reqwest::get(&url).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(response.headers()["cache-control"], "no-store");
        let data: FieldRaids = response.json().await.unwrap();
        let terraclash = data.bosses.iter().find(|b| b.boss == "terraclash").unwrap();
        assert_eq!(terraclash.name, "Terraclash");
        let tally = &terraclash.tally;
        assert_eq!(tally.summons, 2);
        assert_eq!(tally.defeated, 1);
        assert_eq!(tally.wiped, 1);
        assert_eq!(tally.moon_set + tally.dawn, 0);
        assert_eq!(tally.last_defeated_at, Some(now));
        assert!(game.pending_field_raid_events().is_empty());
    }
}
