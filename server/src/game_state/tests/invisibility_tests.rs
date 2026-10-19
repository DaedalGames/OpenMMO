//! Invisibility cloak (doc/INVISIBILITY.md).
use super::*;

const CLOAK_ID: u64 = 70;

async fn setup(game_state: &GameState) -> (DirectRx, DirectRx) {
    game_state.add_player(make_player("ghost", 0.0, 0.0)).await;
    game_state
        .add_player(make_player("watcher", 2.0, 0.0))
        .await;
    let mut inv = PlayerInventory::default();
    inv.bag.push(bag_item(CLOAK_ID, "invisibility_cloak", 1));
    game_state
        .inventories
        .write()
        .await
        .insert(pid("ghost"), inv);
    let ghost = game_state.register_direct_channel(&pid("ghost")).await;
    let watcher = game_state.register_direct_channel(&pid("watcher")).await;
    (ghost, watcher)
}

fn told(msgs: &[ServerMessage], expected: bool) -> bool {
    msgs.iter().any(
        |m| matches!(m, ServerMessage::InvisibilityChanged { invisible } if *invisible == expected),
    )
}

fn sees_ghost_as(game_state: &GameState, viewer: &str) -> bool {
    game_state
        .interest_lock()
        .watches_subject(pid(viewer), &format!("player:{}", pid("ghost")))
}

fn sees_ghost(game_state: &GameState) -> bool {
    sees_ghost_as(game_state, "watcher")
}

async fn wear_cloak(game_state: &GameState) {
    let mut inv = PlayerInventory::default();
    inv.equipped
        .insert(EquipSlot::Back, bag_item(CLOAK_ID, "invisibility_cloak", 1));
    game_state.set_player_gear(&pid("ghost"), &inv).await;
    game_state
        .inventories
        .write()
        .await
        .insert(pid("ghost"), inv);
}

async fn spawn_goblin(game_state: &GameState, x: f32) {
    game_state
        .spawn_monster(
            "goblin".to_string(),
            Position { x, y: 0.0, z: 0.0 },
            0.0,
            0,
            MonsterLifecycle::Ambient,
            None,
            true,
        )
        .await
        .expect("goblin spawns");
}

#[tokio::test]
async fn wearing_the_cloak_hides_and_taking_it_off_reveals() {
    let game_state = make_test_game_state("invisibility_equip");
    let (mut ghost, mut watcher) = setup(&game_state).await;
    assert!(sees_ghost(&game_state));

    game_state.equip_item(&pid("ghost"), CLOAK_ID).await;
    assert!(told(&drain(&mut ghost), true));
    assert!(!sees_ghost(&game_state));
    let gone = drain(&mut watcher).into_iter().any(|m| {
        matches!(m, ServerMessage::PlayerDisappeared { player_id } if player_id == pid("ghost"))
    });
    assert!(gone, "the watcher must lose the wearer");
    assert!(
        sees_ghost_as(&game_state, "ghost"),
        "the wearer still sees themselves"
    );

    walk_player_to(&game_state, &pid("ghost"), 4.0, 0.0).await;
    assert!(
        !sees_ghost(&game_state),
        "moving must not reveal the wearer"
    );
    let leaked = drain(&mut watcher).into_iter().any(|m| {
        matches!(m, ServerMessage::PlayerMoved { player_id, .. }
            | ServerMessage::PlayerAppeared { player: Player { id: player_id, .. } }
            if player_id == pid("ghost"))
    });
    assert!(!leaked, "no movement may reach the watcher");

    game_state
        .unequip_item(&pid("ghost"), EquipSlot::Back)
        .await;
    assert!(told(&drain(&mut ghost), false));
    assert!(sees_ghost(&game_state));
    let back = drain(&mut watcher).into_iter().any(
        |m| matches!(m, ServerMessage::PlayerAppeared { player } if player.id == pid("ghost")),
    );
    assert!(back, "the watcher must see the wearer again");
}

#[tokio::test]
async fn attacking_reveals_until_the_cloak_is_put_on_again() {
    let game_state = make_test_game_state("invisibility_attack");
    let (mut ghost, _watcher) = setup(&game_state).await;
    game_state.equip_item(&pid("ghost"), CLOAK_ID).await;
    drain(&mut ghost);
    game_state
        .monsters
        .write()
        .await
        .insert("target".into(), make_monster("target", pos(2.0), 0));

    game_state
        .broadcast_player_attack(&pid("ghost"), "target".into())
        .await;
    let msgs = drain(&mut ghost);
    let revealed = msgs
        .iter()
        .position(|m| matches!(m, ServerMessage::InvisibilityChanged { invisible: false }));
    let attacked = msgs
        .iter()
        .position(|m| matches!(m, ServerMessage::PlayerAttacked { .. }));
    assert!(
        revealed.is_some() && revealed < attacked,
        "reveal before the attack goes out: {msgs:?}"
    );
    assert!(sees_ghost(&game_state));
    assert!(!game_state.players.read().await[&pid("ghost")].invisible);

    game_state
        .unequip_item(&pid("ghost"), EquipSlot::Back)
        .await;
    assert!(
        !told(&drain(&mut ghost), true),
        "taking it off stays visible"
    );
    game_state
        .players
        .write()
        .await
        .get_mut(&pid("ghost"))
        .unwrap()
        .last_combat_at = 0;
    game_state.equip_item(&pid("ghost"), CLOAK_ID).await;
    assert!(told(&drain(&mut ghost), true));
    assert!(!sees_ghost(&game_state));
}

#[tokio::test]
async fn monsters_ignore_an_invisible_player() {
    let game_state = make_flat_world_game_state("invisibility_monsters");
    game_state.add_player(make_player("ghost", 0.0, 0.0)).await;
    wear_cloak(&game_state).await;
    spawn_goblin(&game_state, 6.0).await;

    for _ in 0..30 {
        game_state.tick_monster_ai_by(200.0).await;
    }
    assert_eq!(game_state.players.read().await[&pid("ghost")].health, 10);
}

#[tokio::test]
async fn logging_in_with_the_cloak_on_never_shows_the_wearer() {
    let game_state = make_test_game_state("invisibility_login");
    game_state
        .add_player(make_player("watcher", 2.0, 0.0))
        .await;
    let mut watcher = game_state.register_direct_channel(&pid("watcher")).await;
    let mut ghost = make_player("ghost", 0.0, 0.0);
    ghost.invisible = true;
    game_state.add_player(ghost).await;

    assert!(!sees_ghost(&game_state));
    let shown = drain(&mut watcher).into_iter().any(|m| {
        matches!(m, ServerMessage::PlayerJoined { player } | ServerMessage::PlayerAppeared { player }
            if player.id == pid("ghost"))
    });
    assert!(!shown);
}

#[tokio::test]
async fn the_cloak_cannot_be_put_on_during_combat() {
    let game_state = make_test_game_state("invisibility_combat");
    let (mut ghost, _watcher) = setup(&game_state).await;
    put_in_combat(&game_state, &pid("ghost")).await;

    game_state.equip_item(&pid("ghost"), CLOAK_ID).await;
    assert!(!told(&drain(&mut ghost), true));
    assert!(sees_ghost(&game_state));
    let inv = game_state
        .get_player_inventory(&pid("ghost"))
        .await
        .unwrap();
    assert!(
        !inv.equipped.contains_key(&EquipSlot::Back),
        "the cloak stays in the bag"
    );
}

#[tokio::test]
async fn a_broken_chase_ends_on_the_wearers_screen() {
    let game_state = make_flat_world_game_state("invisibility_chase_end");
    game_state.add_player(make_player("ghost", 0.0, 0.0)).await;
    let mut rx = game_state.register_direct_channel(&pid("ghost")).await;
    spawn_goblin(&game_state, 12.0).await;
    for _ in 0..6 {
        game_state.tick_monster_ai_by(200.0).await;
    }
    let chased = drain(&mut rx).into_iter().any(|m| {
        matches!(
            m,
            ServerMessage::MonsterMoved {
                chasing: Some(_),
                ..
            }
        )
    });
    assert!(
        chased,
        "the goblin must be chasing before the cloak goes on"
    );

    wear_cloak(&game_state).await;
    for _ in 0..5 {
        game_state.tick_monster_ai_by(200.0).await;
    }
    let ended = drain(&mut rx)
        .into_iter()
        .any(|m| matches!(m, ServerMessage::MonsterMoved { chasing: None, .. }));
    assert!(ended, "the wearer must see the chase end");
}
