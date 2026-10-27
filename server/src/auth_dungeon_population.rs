use super::{AuthError, AuthService};
use crate::metrics::{
    DungeonBandCount, DungeonFloorCount, DungeonPopulationSample,
    CONCURRENT_SAMPLE_INTERVAL_SECONDS,
};
use onlinerpg_shared::dungeon::DEPTH_BAND_FLOORS;
use rusqlite::{params, Connection};

impl AuthService {
    /// A row per sampled minute tells an empty minute from a missed one.
    pub(super) fn ensure_dungeon_population_schema(
        conn: &Connection,
    ) -> Result<(), rusqlite::Error> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS dungeon_population_samples (
                timestamp INTEGER PRIMARY KEY
             );
             CREATE TABLE IF NOT EXISTS dungeon_population_floors (
                timestamp INTEGER NOT NULL,
                dungeon TEXT NOT NULL,
                depth INTEGER NOT NULL CHECK (depth >= 1),
                players INTEGER NOT NULL CHECK (players > 0),
                PRIMARY KEY (timestamp, dungeon, depth)
             );",
        )
    }

    /// Keeps the first sample of each minute.
    pub fn record_dungeon_population(
        &self,
        now: i64,
        floors: &[DungeonFloorCount],
    ) -> Result<(), AuthError> {
        let timestamp = now - now.rem_euclid(CONCURRENT_SAMPLE_INTERVAL_SECONDS);
        let conn = self.open_connection()?;
        let transaction = conn.unchecked_transaction()?;
        let inserted = transaction.execute(
            "INSERT OR IGNORE INTO dungeon_population_samples (timestamp) VALUES (?1)",
            [timestamp],
        )?;
        if inserted > 0 {
            let mut statement = transaction.prepare_cached(
                "INSERT INTO dungeon_population_floors (timestamp, dungeon, depth, players)
                 VALUES (?1, ?2, ?3, ?4)",
            )?;
            for floor in floors {
                statement.execute(params![
                    timestamp,
                    floor.dungeon,
                    floor.depth,
                    floor.players
                ])?;
            }
        }
        transaction.commit()?;
        Ok(())
    }

    /// Average players per dungeon band in each `interval` bucket of sampled
    /// minutes within `[from, until]`.
    pub fn dungeon_population_samples(
        &self,
        from: i64,
        until: i64,
        interval: i64,
    ) -> Result<Vec<DungeonPopulationSample>, AuthError> {
        let conn = self.open_connection()?;
        let mut buckets = conn.prepare(
            "SELECT timestamp / ?3, CASE WHEN ?3 = 60 THEN MIN(timestamp)
                    ELSE MAX(timestamp / ?3 * ?3, ?1) END, COUNT(*)
             FROM dungeon_population_samples WHERE timestamp BETWEEN ?1 AND ?2
             GROUP BY 1 ORDER BY 1",
        )?;
        let mut samples = Vec::new();
        let mut bucket_ids = Vec::new();
        for row in buckets.query_map(params![from, until, interval], |row| {
            Ok((row.get::<_, i64>(0)?, row.get(1)?, row.get(2)?))
        })? {
            let (bucket, timestamp, sample_count) = row?;
            bucket_ids.push(bucket);
            samples.push(DungeonPopulationSample {
                timestamp,
                sample_count,
                bands: Vec::new(),
            });
        }
        let mut floors = conn.prepare(
            "SELECT timestamp / ?3, dungeon, (depth - 1) / ?4 * ?4 + 1, SUM(players)
             FROM dungeon_population_floors WHERE timestamp BETWEEN ?1 AND ?2
             GROUP BY 1, 2, 3 ORDER BY 1, 2, 3",
        )?;
        let mut index = 0;
        for row in floors.query_map(params![from, until, interval, DEPTH_BAND_FLOORS], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get::<_, i64>(3)?,
            ))
        })? {
            let (bucket, dungeon, band, players) = row?;
            while bucket_ids.get(index).is_some_and(|&id| id < bucket) {
                index += 1;
            }
            if bucket_ids.get(index) != Some(&bucket) {
                continue;
            }
            let sample = &mut samples[index];
            sample.bands.push(DungeonBandCount {
                dungeon,
                band,
                players: players as f64 / f64::from(sample.sample_count),
            });
        }
        Ok(samples)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn floor(dungeon: &str, depth: u8, players: u32) -> DungeonFloorCount {
        DungeonFloorCount {
            dungeon: dungeon.into(),
            depth,
            players,
        }
    }

    fn band(dungeon: &str, band: u8, players: f64) -> DungeonBandCount {
        DungeonBandCount {
            dungeon: dungeon.into(),
            band,
            players,
        }
    }

    #[test]
    fn dungeon_population_averages_bands_over_sampled_minutes() {
        let dir = crate::test_util::unique_temp_dir("dungeon_population_samples");
        let auth = AuthService::new(dir.join("game.db")).unwrap();
        auth.record_dungeon_population(
            3600,
            &[floor("orc_warrens", 6, 2), floor("orc_warrens", 9, 1)],
        )
        .unwrap();
        // Same minute again: the first sample stands.
        auth.record_dungeon_population(3630, &[floor("orc_warrens", 6, 9)])
            .unwrap();
        auth.record_dungeon_population(3660, &[]).unwrap();
        auth.record_dungeon_population(3720, &[floor("old_crypt", 1, 4)])
            .unwrap();
        auth.record_dungeon_population(7200, &[]).unwrap();
        auth.record_dungeon_population(10800, &[floor("orc_warrens", 1, 1)])
            .unwrap();

        assert_eq!(
            auth.dungeon_population_samples(3600, 7200, 3600).unwrap(),
            [
                DungeonPopulationSample {
                    timestamp: 3600,
                    sample_count: 3,
                    bands: vec![band("old_crypt", 1, 4.0 / 3.0), band("orc_warrens", 6, 1.0)],
                },
                DungeonPopulationSample {
                    timestamp: 7200,
                    sample_count: 1,
                    bands: vec![],
                },
            ]
        );
        let minutes = auth.dungeon_population_samples(3600, 3660, 60).unwrap();
        assert_eq!(
            minutes.iter().map(|s| s.timestamp).collect::<Vec<_>>(),
            [3600, 3660]
        );
        assert_eq!(minutes[0].bands, [band("orc_warrens", 6, 3.0)]);
        assert!(minutes[1].bands.is_empty());
    }
}
