use super::{auth_db, history_interval, metrics_response, unix_now, HistoryQuery, MetricsState};
use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
};
use onlinerpg_shared::dungeon::{depth_band_start, DEPTH_BAND_FLOORS, MAX_DRAWN_FLOORS};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DungeonFloorCount {
    pub dungeon: String,
    pub depth: u8,
    pub players: u32,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct DungeonBandCount {
    pub dungeon: String,
    pub band: u8,
    pub players: f64,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct DungeonPopulationSample {
    pub timestamp: i64,
    pub sample_count: u32,
    pub bands: Vec<DungeonBandCount>,
}

#[derive(Debug, Serialize, Deserialize)]
struct DungeonInfo {
    id: String,
    name: String,
    floors: u8,
}

#[derive(Debug, Serialize, Deserialize)]
struct DungeonPopulation {
    from: i64,
    until: i64,
    sample_interval_seconds: i64,
    band_floors: u8,
    dungeons: Vec<DungeonInfo>,
    current: Vec<DungeonBandCount>,
    samples: Vec<DungeonPopulationSample>,
}

fn band_counts(floors: Vec<DungeonFloorCount>) -> Vec<DungeonBandCount> {
    let mut bands: BTreeMap<(String, u8), u32> = BTreeMap::new();
    for floor in floors {
        *bands
            .entry((floor.dungeon, depth_band_start(floor.depth)))
            .or_default() += floor.players;
    }
    bands
        .into_iter()
        .map(|((dungeon, band), players)| DungeonBandCount {
            dungeon,
            band,
            players: f64::from(players),
        })
        .collect()
}

pub(super) async fn dungeon_population(
    State(state): State<MetricsState>,
    Query(query): Query<HistoryQuery>,
) -> Response {
    let hours = query.hours.unwrap_or(24);
    let Some(interval) = history_interval(hours).filter(|_| matches!(hours, 24 | 168 | 720)) else {
        return (StatusCode::BAD_REQUEST, "hours must be 24, 168, or 720").into_response();
    };
    let current = band_counts(state.game.dungeon_floor_population().await);
    let dungeons = onlinerpg_shared::dungeon::entrances()
        .iter()
        .map(|def| DungeonInfo {
            id: def.id.clone(),
            name: def.name.clone(),
            // Seed-derived dungeons report their deepest possible floor.
            floors: def.floors.unwrap_or(MAX_DRAWN_FLOORS),
        })
        .collect();
    let until = unix_now();
    let from = until - i64::from(hours) * 3600;
    metrics_response(
        auth_db(move || state.auth.dungeon_population_samples(from, until, interval))
            .await
            .map(|samples| DungeonPopulation {
                from,
                until,
                sample_interval_seconds: interval,
                band_floors: DEPTH_BAND_FLOORS,
                dungeons,
                current,
                samples,
            }),
        "Dungeon population",
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{auth::AuthService, game_state::tests::make_test_game_state};
    use std::sync::Arc;

    #[test]
    fn band_counts_group_five_floors_per_dungeon() {
        let floor = |dungeon: &str, depth, players| DungeonFloorCount {
            dungeon: dungeon.into(),
            depth,
            players,
        };
        let band = |dungeon: &str, band, players| DungeonBandCount {
            dungeon: dungeon.into(),
            band,
            players,
        };
        assert_eq!(
            band_counts(vec![
                floor("orc_warrens", 10, 1),
                floor("old_crypt", 5, 2),
                floor("orc_warrens", 6, 3),
                floor("orc_warrens", 5, 4),
            ]),
            [
                band("old_crypt", 1, 2.0),
                band("orc_warrens", 1, 4.0),
                band("orc_warrens", 6, 4.0),
            ]
        );
    }

    #[tokio::test]
    async fn dungeon_population_api_lists_dungeons_and_validates_hours() {
        let dir = crate::test_util::unique_temp_dir("dungeon_population_api");
        let auth = Arc::new(AuthService::new(dir.join("game.db")).unwrap());
        let game = Arc::new(make_test_game_state("dungeon_population_api"));
        let now = unix_now();
        auth.record_dungeon_population(
            now - 120,
            &[DungeonFloorCount {
                dungeon: "orc_warrens".into(),
                depth: 7,
                players: 3,
            }],
        )
        .unwrap();
        let router = crate::metrics::metrics_routes(game, auth);
        let url = format!(
            "{}/api/metrics/dungeon-population",
            crate::test_util::serve(router).await
        );

        let response = reqwest::get(&url).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(response.headers()["cache-control"], "no-store");
        let data: DungeonPopulation = response.json().await.unwrap();
        assert_eq!(data.until - data.from, 24 * 3600);
        assert_eq!(data.sample_interval_seconds, 60);
        let orc = data
            .dungeons
            .iter()
            .find(|d| d.id == "orc_warrens")
            .unwrap();
        assert_eq!((orc.name.as_str(), orc.floors), ("Orc Warrens", 10));
        assert!(data.current.is_empty());
        assert_eq!(
            data.samples[0].bands,
            [DungeonBandCount {
                dungeon: "orc_warrens".into(),
                band: 6,
                players: 3.0,
            }]
        );

        for hours in ["1", "6", "4320", "8760", "x"] {
            let status = reqwest::get(format!("{url}?hours={hours}"))
                .await
                .unwrap()
                .status();
            assert_eq!(status, StatusCode::BAD_REQUEST, "hours={hours}");
        }
    }
}
