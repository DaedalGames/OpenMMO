//! Price index (doc/PRICING.md) pieces shared by the server and NPC clients.

use serde::{Deserialize, Serialize};

pub fn item_currency_price(base: i64, modifier_pct: i32) -> i64 {
    ((base * (100 + i64::from(modifier_pct)) + 99) / 100).max(1)
}

/// Unit base for a merchant purchase: consumables carry the index.
pub fn indexed_base_price(base: i64, consumable: bool, index_percent: u32) -> i64 {
    if consumable {
        (base * i64::from(index_percent) / 100).max(1)
    } else {
        base
    }
}

/// Where the next meeting is heading.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Trend {
    Rising,
    Falling,
    Steady,
}

/// The market picture the server pushes to NPC clients.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PricingNotice {
    /// 100 = base.
    pub index_percent: u32,
    /// Percentage points decided at the last meeting.
    pub last_change_pct: i32,
    pub trend: Trend,
    /// 0 = tonight.
    pub meeting_in_days: i64,
}
