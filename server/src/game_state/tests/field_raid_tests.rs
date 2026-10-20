// ---- Altar offerings and the field raid -------------------------------------

use super::*;
use onlinerpg_shared::furniture::FurniturePlacement;
use onlinerpg_shared::inventory::EquipSlot;
use onlinerpg_shared::messages::AltarStatus;
use onlinerpg_shared::world::GameDateTime;

const ALTAR_ID: u32 = 7;

/// Day 14 of the calendar, midnight: Eldor is full and overhead.
fn full_moon() -> GameDateTime {
    GameDateTime {
        year: 217,
        month: 1,
        day: 15,
        hour: 0,
        minute: 0,
    }
}

fn half_moon() -> GameDateTime {
    GameDateTime {
        day: 10,
        hour: 12,
        ..full_moon()
    }
}

async fn setup(when: GameDateTime, amulets: u32) -> (GameState, PlayerId, DirectRx) {
    let game = make_test_game_state("field_raid");
    game.debug_set_datetime(&when);
    game.sync_region_furniture(
        0,
        0,
        &[FurniturePlacement {
            id: ALTAR_ID,
            type_id: "terraclash_altar".into(),
            x: 100.0,
            y: 5.0,
            z: 50.0,
            rotation_deg: 0.0,
            floor_level: 0,
        }],
    );
    let mut player = make_player("summoner", 100.0, 51.5);
    player.position.y = 5.0;
    let id = player.id;
    game.add_player(player).await;
    let rx = game.register_direct_channel(&id).await;
    let mut inv = PlayerInventory::default();
    if amulets > 0 {
        inv.bag.push(bag_item(41, "earth_amulet", amulets));
    }
    game.inventories.write().await.insert(id, inv);
    (game, id, rx)
}

async fn amulets(game: &GameState, id: &PlayerId) -> u32 {
    game.inventories.read().await[id]
        .bag
        .iter()
        .filter(|i| i.item_def_id == "earth_amulet")
        .map(|i| i.quantity)
        .sum()
}

fn statuses(rx: &mut DirectRx) -> Vec<AltarStatus> {
    drain(rx)
        .into_iter()
        .filter_map(|m| match m {
            ServerMessage::AltarStatus { status, .. } => Some(status),
            _ => None,
        })
        .collect()
}

async fn bosses(game: &GameState) -> Vec<crate::types::Monster> {
    game.monsters
        .read()
        .await
        .values()
        .filter(|m| m.monster_type == "terraclash")
        .cloned()
        .collect()
}

#[tokio::test]
async fn offering_consumes_one_amulet_and_opens_one_raid() {
    let (game, id, mut rx) = setup(full_moon(), 2).await;
    game.inspect_altar(&id, ALTAR_ID).await;
    assert!(matches!(statuses(&mut rx)[..], [AltarStatus::Ready { .. }]));

    game.offer_at_altar(&id, ALTAR_ID).await;
    assert_eq!(amulets(&game, &id).await, 1);
    assert!(game.field_raid.lock().await.is_some());

    drain(&mut rx);
    game.offer_at_altar(&id, ALTAR_ID).await;
    assert_eq!(
        amulets(&game, &id).await,
        1,
        "a second offering keeps its amulet"
    );
    assert_eq!(statuses(&mut rx), vec![AltarStatus::RaidActive]);
}

#[tokio::test]
async fn offering_outside_a_full_moon_keeps_the_amulet() {
    let (game, id, mut rx) = setup(half_moon(), 1).await;
    game.offer_at_altar(&id, ALTAR_ID).await;
    assert_eq!(amulets(&game, &id).await, 1);
    assert!(game.field_raid.lock().await.is_none());
    assert_eq!(statuses(&mut rx), vec![AltarStatus::NotFullMoon]);
}

#[tokio::test]
async fn a_worn_amulet_must_come_off_first() {
    let (game, id, mut rx) = setup(full_moon(), 0).await;
    game.inventories
        .write()
        .await
        .get_mut(&id)
        .unwrap()
        .equipped
        .insert(EquipSlot::Neck, bag_item(42, "earth_amulet", 1));
    game.inspect_altar(&id, ALTAR_ID).await;
    game.offer_at_altar(&id, ALTAR_ID).await;
    let expected = AltarStatus::OfferingEquipped {
        offering: "earth_amulet".into(),
    };
    assert_eq!(statuses(&mut rx), vec![expected.clone(), expected]);
    assert!(game.inventories.read().await[&id]
        .equipped
        .contains_key(&EquipSlot::Neck));
}

#[tokio::test]
async fn an_out_of_reach_altar_is_ignored() {
    let (game, id, mut rx) = setup(full_moon(), 1).await;
    game.players.write().await.get_mut(&id).unwrap().position.z = 60.0;
    game.offer_at_altar(&id, ALTAR_ID).await;
    assert_eq!(amulets(&game, &id).await, 1);
    assert!(statuses(&mut rx).is_empty());
}

#[tokio::test]
async fn the_boss_wakes_at_the_altar_spawn_and_its_death_ends_the_raid() {
    let (game, id, _rx) = setup(full_moon(), 1).await;
    let def = onlinerpg_shared::altar::altar_def("terraclash_altar").unwrap();
    let (wx, wz) = (100.0 + def.spawn.x, 50.0 + def.spawn.z);

    game.offer_at_altar(&id, ALTAR_ID).await;
    assert!(bosses(&game).await.is_empty(), "the tick spawns it");
    game.tick_field_raid().await;
    let boss = bosses(&game).await.pop().expect("terraclash awake");
    assert_eq!(boss.lifecycle, crate::types::MonsterLifecycle::FieldRaid);
    assert!((boss.position.x - wx).abs() < 0.01 && (boss.position.z - wz).abs() < 0.01);

    game.monsters.write().await.get_mut(&boss.id).unwrap().state = MonsterState::Dead;
    game.tick_field_raid().await;
    assert!(game.field_raid.lock().await.is_none());
}

#[tokio::test]
async fn an_empty_battle_zone_puts_the_boss_back_to_sleep() {
    let (game, id, _rx) = setup(full_moon(), 1).await;
    game.offer_at_altar(&id, ALTAR_ID).await;
    game.tick_field_raid().await;
    assert_eq!(bosses(&game).await.len(), 1);

    game.teleport_player(&id, pos3(300.0, 5.0, 50.0), 0.0, 0)
        .await;
    game.tick_field_raid().await;
    assert!(game.field_raid.lock().await.is_none());
    assert!(bosses(&game).await.is_empty());
    assert_eq!(
        amulets(&game, &id).await,
        0,
        "a failed raid keeps the offering"
    );
}
