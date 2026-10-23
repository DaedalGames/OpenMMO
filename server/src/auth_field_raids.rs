use super::{AuthError, AuthService};
use crate::metrics::{FieldRaidEvent, FieldRaidTally};
use rusqlite::{params, Connection};
use std::collections::HashMap;

impl AuthService {
    pub(super) fn ensure_field_raid_events_schema(
        conn: &Connection,
    ) -> Result<(), rusqlite::Error> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS field_raid_collection (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                started_at INTEGER NOT NULL
             );
             INSERT OR IGNORE INTO field_raid_collection (id, started_at) VALUES (1, unixepoch());
             CREATE TABLE IF NOT EXISTS field_raid_events (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                boss TEXT NOT NULL,
                event TEXT NOT NULL
             );",
        )
    }

    pub fn record_field_raid_events(&self, events: &[FieldRaidEvent]) -> Result<(), AuthError> {
        if events.is_empty() {
            return Ok(());
        }
        let conn = self.open_connection()?;
        let transaction = conn.unchecked_transaction()?;
        {
            let mut statement = transaction.prepare_cached(
                "INSERT INTO field_raid_events (timestamp, boss, event) VALUES (?1, ?2, ?3)",
            )?;
            for event in events {
                statement.execute(params![event.timestamp, event.boss, event.storage_key()])?;
            }
        }
        transaction.commit()?;
        Ok(())
    }

    /// Collection start, and each boss's tally up to `until`.
    pub fn field_raid_tallies(
        &self,
        until: i64,
    ) -> Result<(i64, HashMap<String, FieldRaidTally>), AuthError> {
        let conn = self.open_connection()?;
        let started_at = conn.query_row(
            "SELECT started_at FROM field_raid_collection WHERE id = 1",
            [],
            |row| row.get(0),
        )?;
        let mut statement = conn.prepare(
            "SELECT boss,
                    SUM(event = 'summoned'), SUM(event = 'defeated'), SUM(event = 'moon_set'),
                    SUM(event = 'dawn'), SUM(event = 'wiped'),
                    MAX(CASE WHEN event = 'defeated' THEN timestamp END)
             FROM field_raid_events WHERE timestamp <= ?1 GROUP BY boss",
        )?;
        let tallies = statement
            .query_map([until], |row| {
                Ok((
                    row.get(0)?,
                    FieldRaidTally {
                        summons: row.get(1)?,
                        defeated: row.get(2)?,
                        moon_set: row.get(3)?,
                        dawn: row.get(4)?,
                        wiped: row.get(5)?,
                        last_defeated_at: row.get(6)?,
                    },
                ))
            })?
            .collect::<Result<_, _>>()?;
        Ok((started_at, tallies))
    }
}
