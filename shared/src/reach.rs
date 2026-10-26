//! Player weapon reach, shared by the server's swing gate and the Rust clients.

/// Reach of a weapon with no `range` column (items.csv).
pub const PLAYER_MELEE_REACH_METERS: f32 = 2.0;
/// The server accepts a swing this far beyond the reach, absorbing the lag in
/// the client's view of the target.
pub const REACH_SLACK_METERS: f32 = 0.5;
