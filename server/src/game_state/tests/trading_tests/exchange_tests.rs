use super::*;
use onlinerpg_shared::messages::{DealKind, TradeLineItem};

async fn setup_exchange(game: &GameState, shards: u32) -> DirectRx {
    game.add_player(make_npc("npc_ysolde", "Ysolde", 0.0, 0.0))
        .await;
    game.add_player(make_player("buyer", 1.0, 0.0)).await;
    game.register_player_character(&pid("buyer"), 1, 0, attrs_with_cha(20), 100_000, None)
        .await;
    game.inventories.write().await.insert(
        pid("buyer"),
        PlayerInventory {
            bag: vec![bag_item(80, "terraclash_token", shards)],
            ..Default::default()
        },
    );
    game.register_direct_channel(&pid("buyer")).await
}

async fn count(game: &GameState, item_id: &str) -> u32 {
    game.inventories.read().await[&pid("buyer")]
        .bag
        .iter()
        .filter(|item| item.item_def_id == item_id)
        .map(|item| item.quantity)
        .sum()
}

fn line(qty: u32) -> TradeLineItem {
    TradeLineItem {
        item_def_id: "earth_shield".into(),
        qty,
    }
}

#[tokio::test]
async fn ysolde_field_cot_sleep_closes_the_exchange_until_six() {
    let game = make_test_game_state("ysolde_sleep_exchange");
    let mut rx = setup_exchange(&game, 30).await;
    let file: crate::npc_schedule::ScheduleFile = serde_json::from_str(include_str!(
        "../../../../../agent-client/data/npcs/ysolde/schedule.json"
    ))
    .unwrap();
    game.set_npc_schedule("Ysolde", file.schedule);
    for hour in [21, 23, 0, 5] {
        game.debug_set_datetime(&crate::types::GameDateTime {
            year: 217,
            month: 1,
            day: 1,
            hour,
            minute: 0,
        });
        assert!(game.is_npc_asleep("Ysolde"));
        game.buy_item(&pid("buyer"), &pid("npc_ysolde"), "earth_shield")
            .await;
        expect_trade_error(&mut rx, "asleep");
    }
    game.debug_set_datetime(&crate::types::GameDateTime {
        year: 217,
        month: 1,
        day: 1,
        hour: 6,
        minute: 0,
    });
    assert!(!game.is_npc_asleep("Ysolde"));
    game.buy_item(&pid("buyer"), &pid("npc_ysolde"), "earth_shield")
        .await;
    assert_eq!(count(&game, "earth_shield").await, 1);
}

#[tokio::test]
async fn exchange_spends_unlocked_shards_and_leaves_gold_untouched() {
    let game = make_test_game_state("exchange_shards");
    let _rx = setup_exchange(&game, 30).await;
    let mut locked = bag_item(81, "terraclash_token", 10);
    locked.locked = true;
    game.inventories
        .write()
        .await
        .get_mut(&pid("buyer"))
        .unwrap()
        .bag
        .push(locked);
    game.buy_item(&pid("buyer"), &pid("npc_ysolde"), "earth_shield")
        .await;
    assert_eq!(count(&game, "earth_shield").await, 1);
    assert_eq!(count(&game, "terraclash_token").await, 10);
    assert_eq!(game.get_player_gold(&pid("buyer")).await, 100_000);
    let shield_id = game.inventories.read().await[&pid("buyer")]
        .bag
        .iter()
        .find(|item| item.item_def_id == "earth_shield")
        .unwrap()
        .instance_id;
    game.equip_item(&pid("buyer"), shield_id).await;
    assert_eq!(
        game.inventories.read().await[&pid("buyer")].equipped[&EquipSlot::OffHand].item_def_id,
        "earth_shield"
    );
}

#[tokio::test]
async fn exchange_batch_is_atomic_and_gold_cannot_replace_shards() {
    let game = make_test_game_state("exchange_atomic");
    let mut rx = setup_exchange(&game, 59).await;
    game.buy_items(&pid("buyer"), &pid("npc_ysolde"), vec![line(2)])
        .await;
    expect_trade_error(&mut rx, "shards");
    assert_eq!(count(&game, "terraclash_token").await, 59);
    assert_eq!(count(&game, "earth_shield").await, 0);
    game.inventories
        .write()
        .await
        .get_mut(&pid("buyer"))
        .unwrap()
        .bag[0]
        .locked = true;
    game.buy_item(&pid("buyer"), &pid("npc_ysolde"), "earth_shield")
        .await;
    expect_trade_error(&mut rx, "shards");
    assert_eq!(game.get_player_gold(&pid("buyer")).await, 100_000);
    game.buy_items(
        &pid("buyer"),
        &pid("npc_ysolde"),
        vec![
            line(1),
            TradeLineItem {
                item_def_id: "iron_sword".into(),
                qty: 1,
            },
        ],
    )
    .await;
    expect_trade_error(&mut rx, "does not sell");
    game.sell_item(&pid("buyer"), &pid("npc_ysolde"), 80).await;
    expect_trade_error(&mut rx, "does not buy");
}

#[tokio::test]
async fn exchange_haggle_rounds_up_and_covers_one_unit_across_duplicate_lines() {
    let game = make_test_game_state("exchange_haggle");
    let _rx = setup_exchange(&game, 53).await;
    game.offer_deal(
        &pid("npc_ysolde"),
        &pid("buyer"),
        "earth_shield",
        DealKind::Buy,
        -100,
        "research help",
    )
    .await;
    game.buy_items(&pid("buyer"), &pid("npc_ysolde"), vec![line(1), line(1)])
        .await;
    assert_eq!(count(&game, "earth_shield").await, 2);
    assert_eq!(count(&game, "terraclash_token").await, 0);
    assert!(game
        .active_deals_for(&pid("buyer"), "Ysolde")
        .await
        .is_empty());
    assert_eq!(game.get_player_gold(&pid("buyer")).await, 100_000);
}

#[tokio::test]
async fn failed_exchange_preserves_payment_and_haggled_deal() {
    let game = make_test_game_state("exchange_weight");
    let _rx = setup_exchange(&game, 30).await;
    game.inventories
        .write()
        .await
        .get_mut(&pid("buyer"))
        .unwrap()
        .bag
        .push(bag_item(82, "stone_hearth", 1));
    game.offer_deal(
        &pid("npc_ysolde"),
        &pid("buyer"),
        "earth_shield",
        DealKind::Buy,
        -10,
        "research help",
    )
    .await;
    game.buy_items(&pid("buyer"), &pid("npc_ysolde"), vec![line(1)])
        .await;
    assert_eq!(count(&game, "terraclash_token").await, 30);
    assert_eq!(count(&game, "earth_shield").await, 0);
    assert_eq!(
        game.active_deals_for(&pid("buyer"), "Ysolde").await.len(),
        1
    );
    game.inventories
        .write()
        .await
        .get_mut(&pid("buyer"))
        .unwrap()
        .bag
        .retain(|item| item.instance_id != 82);
    game.buy_items(&pid("buyer"), &pid("npc_ysolde"), vec![line(1)])
        .await;
    assert_eq!(count(&game, "terraclash_token").await, 3);
    assert_eq!(count(&game, "earth_shield").await, 1);
}

#[tokio::test]
async fn concurrent_exchanges_cannot_double_spend_shards() {
    let game = make_test_game_state("exchange_concurrent");
    let _rx = setup_exchange(&game, 30).await;
    let buyer = pid("buyer");
    let npc = pid("npc_ysolde");
    tokio::join!(
        game.buy_item(&buyer, &npc, "earth_shield"),
        game.buy_item(&buyer, &npc, "earth_shield")
    );
    assert_eq!(count(&game, "earth_shield").await, 1);
    assert_eq!(count(&game, "terraclash_token").await, 0);
}

#[tokio::test]
async fn shard_discounts_have_separate_limited_daily_budgets() {
    let game = make_test_game_state("exchange_budgets");
    let _rx = setup_exchange(&game, 60).await;
    game.add_player(make_npc("npc_rica", "Rica", 0.0, 0.0))
        .await;
    game.offer_deal(
        &pid("npc_ysolde"),
        &pid("buyer"),
        "earth_shield",
        DealKind::Buy,
        -25,
        "research help",
    )
    .await;
    game.clear_deal_cooldowns_for_test().await;
    game.offer_deal(
        &pid("npc_ysolde"),
        &pid("buyer"),
        "earth_shield",
        DealKind::Buy,
        -25,
        "another discount",
    )
    .await;
    let (npc_cost, player_cost, _) = game.deal_ledger_state_for_test("Ysolde", "buyer").await;
    assert_eq!((npc_cost, player_cost), (7, 7));
    game.offer_deal(
        &pid("npc_rica"),
        &pid("buyer"),
        "healing_potion",
        DealKind::Buy,
        -25,
        "loyal customer",
    )
    .await;
    let (_, gold_discount, _) = game.deal_ledger_state_for_test("Rica", "buyer").await;
    assert_eq!(gold_discount, 150);
}
