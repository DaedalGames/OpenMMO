//! Server-driven monster brains (doc/SERVER_SIDE_MONSTER_AI.md).
use super::*;

async fn spawn_goblin(game_state: &GameState, x: f32) -> String {
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
        .expect("goblin spawns")
        .id
}

async fn monster_x(game_state: &GameState, id: &str) -> f32 {
    game_state.monsters.read().await[id].position.x
}

async fn health_of(game_state: &GameState, player_id: &PlayerId) -> u32 {
    game_state.players.read().await[player_id].health
}

#[tokio::test]
async fn server_brain_chases_and_attacks_the_player() {
    let game_state = make_flat_world_game_state("server_ai_chase");
    let player_id = pid("prey");
    game_state.add_player(make_player("prey", 0.0, 0.0)).await;
    let mut rx = game_state.register_direct_channel(&player_id).await;
    let goblin = spawn_goblin(&game_state, 12.0).await;

    let mut attacked = false;
    for _ in 0..60 {
        game_state.tick_monster_ai_by(200.0).await;
        if health_of(&game_state, &player_id).await < 10 {
            attacked = true;
            break;
        }
    }
    let x = monster_x(&game_state, &goblin).await;
    assert!(
        x < 12.0,
        "the brain must have walked the goblin toward the player, x={x}"
    );
    assert!(attacked, "12s of ticks must land at least one goblin hit");
    assert_eq!(game_state.brain_count().await, 1);

    let msgs = drain(&mut rx);
    let moved = msgs
        .iter()
        .any(|m| matches!(m, ServerMessage::MonsterMoved { .. }));
    assert!(moved, "server movement reaches the player: {msgs:?}");
}

#[tokio::test]
async fn a_closed_dungeon_door_hides_the_target_and_reopening_resumes_chase() {
    dungeon_door_chase_cycle(true).await;
    dungeon_door_chase_cycle(false).await;
}

async fn dungeon_door_chase_cycle(aggressive: bool) {
    use onlinerpg_shared::dungeon::interior_doors;

    let game_state = make_flat_world_game_state(&format!("server_ai_door_sensing_{aggressive}"));
    let entrance = game_state.dungeon_defs.get("skeleton_crypt").unwrap();
    game_state.ensure_dungeon_runtime(&entrance.id).await;
    {
        let mut dungeons = game_state.dungeons.write().await;
        let rt = dungeons.get_mut(&entrance.id).unwrap();
        rt.open_doors.insert(
            1,
            interior_doors(&rt.layouts[0])
                .iter()
                .map(|d| d.door_id)
                .collect(),
        );
    }
    game_state
        .rebuild_dungeon_floor_passability(&entrance.id, 1)
        .await;

    let player_id = pid("delver");
    let mut player = make_player("delver", -1035.2, 4263.0);
    player.position.y = entrance.y - 4.0;
    player.floor_level = -1;
    game_state.add_player(player).await;
    let skeleton = game_state
        .spawn_monster(
            "skeleton_weak".into(),
            Position {
                x: -1036.55,
                y: entrance.y - 4.0,
                z: 4265.14,
            },
            0.0,
            -1,
            MonsterLifecycle::DungeonSlot,
            None,
            aggressive,
        )
        .await
        .unwrap()
        .id;

    assert_eq!(
        game_state
            .toggle_dungeon_door(&player_id, &entrance.id, 1, 148025)
            .await,
        Some(false)
    );
    game_state.tick_monster_ai_by(200.0).await;
    assert_eq!(game_state.brain_target(&skeleton).await, None);
    assert_eq!(game_state.brain_pathfind_count().await, 0);
    assert_eq!(
        game_state
            .toggle_dungeon_door(&player_id, &entrance.id, 1, 148025)
            .await,
        Some(true)
    );
    if !aggressive {
        game_state.brain_hit(&skeleton, &player_id, false, 0).await;
    }
    game_state.tick_monster_ai_by(16.0).await;
    game_state.tick_monster_ai_by(16.0).await;
    assert_eq!(game_state.brain_target(&skeleton).await, Some(player_id));
    assert_eq!(
        game_state.monsters.read().await[&skeleton].state,
        MonsterState::Run
    );

    assert_eq!(
        game_state
            .toggle_dungeon_door(&player_id, &entrance.id, 1, 148025)
            .await,
        Some(false)
    );
    let queries = game_state.brain_pathfind_count().await;
    game_state.tick_monster_ai_by(200.0).await;
    assert_eq!(game_state.brain_target(&skeleton).await, None);
    assert_eq!(
        game_state.monsters.read().await[&skeleton].state,
        MonsterState::Idle
    );
    let stopped = game_state.monsters.read().await[&skeleton].position;
    for _ in 0..30 {
        game_state.tick_monster_ai_by(200.0).await;
    }
    assert_eq!(game_state.brain_pathfind_count().await, queries);
    assert_eq!(
        game_state.monsters.read().await[&skeleton].position,
        stopped
    );

    assert_eq!(
        game_state
            .toggle_dungeon_door(&player_id, &entrance.id, 1, 148025)
            .await,
        Some(true)
    );
    game_state.tick_monster_ai_by(200.0).await;
    assert_eq!(game_state.brain_target(&skeleton).await, Some(player_id));
    assert!(game_state.brain_pathfind_count().await > queries);
    game_state.tick_monster_ai_by(200.0).await;
    assert_ne!(
        game_state.monsters.read().await[&skeleton].position,
        stopped
    );
}

#[tokio::test]
async fn brain_is_dropped_when_the_monster_dies() {
    let game_state = make_flat_world_game_state("server_ai_death");
    game_state.add_player(make_player("slayer", 0.0, 0.0)).await;
    let goblin = spawn_goblin(&game_state, 2.0).await;
    game_state.tick_monster_ai_by(200.0).await;
    assert_eq!(game_state.brain_count().await, 1);

    game_state.monsters.write().await.mark_dead(&goblin);
    game_state.tick_monster_ai_by(200.0).await;
    assert_eq!(game_state.brain_count().await, 0, "a corpse keeps no brain");
}

#[tokio::test]
async fn a_hit_monster_retaliates() {
    let game_state = make_flat_world_game_state("server_ai_retaliate");
    let player_id = pid("poker");
    game_state.add_player(make_player("poker", 0.0, 0.0)).await;
    let goblin = game_state
        .spawn_monster(
            "goblin".to_string(),
            Position {
                x: 2.5,
                y: 0.0,
                z: 0.0,
            },
            0.0,
            0,
            MonsterLifecycle::Ambient,
            None,
            false,
        )
        .await
        .expect("goblin spawns")
        .id;
    game_state.tick_monster_ai_by(200.0).await;

    game_state
        .broadcast_player_attack(&player_id, goblin.clone())
        .await;
    let mut attacked = false;
    for _ in 0..40 {
        game_state.tick_monster_ai_by(200.0).await;
        if health_of(&game_state, &player_id).await < 10 {
            attacked = true;
            break;
        }
    }
    assert!(attacked, "a poked brave goblin must swing back within 8s");
}

/// The registry learns a running monster's position only at each network
/// sync, so between syncs it trails the brain. A swing must be judged on
/// where the brain has the monster, or a charge is refused at contact.
#[tokio::test]
async fn a_swing_is_judged_on_the_brain_not_the_synced_registry() {
    let game_state = make_flat_world_game_state("server_ai_swing_at_charger");
    let player_id = pid("swinger");
    game_state
        .add_player(make_player("swinger", 0.0, 0.0))
        .await;
    let mut rx = game_state.register_direct_channel(&player_id).await;
    let goblin = spawn_goblin(&game_state, 4.2).await;

    // Melee reach is 2m + 1m tolerance: wait for a tick that leaves the brain
    // inside it while the registry still holds a pose outside it.
    let mut staggered = false;
    for _ in 0..10 {
        game_state.tick_monster_ai_by(200.0).await;
        let brain_x = game_state
            .brain_position_now(&goblin)
            .await
            .expect("the goblin has a brain")
            .x;
        let registry_x = monster_x(&game_state, &goblin).await;
        if brain_x <= 2.9 && registry_x > 3.0 {
            staggered = true;
            break;
        }
    }
    assert!(staggered, "the setup never produced a registry lag to test");
    drain(&mut rx);

    game_state
        .broadcast_player_attack(&player_id, goblin.clone())
        .await;

    let msgs = drain(&mut rx);
    assert!(
        msgs.iter()
            .any(|m| matches!(m, ServerMessage::PlayerAttacked { .. })),
        "the swing must land on the brain's position: {msgs:?}"
    );
    assert!(
        !msgs
            .iter()
            .any(|m| matches!(m, ServerMessage::PlayerAttackRejected { .. })),
        "{msgs:?}"
    );
}

#[tokio::test]
async fn a_monster_blocked_from_returning_can_be_attacked_and_retaliate() {
    use onlinerpg_shared::pathfinding::{RuntimeFloorGrid, RuntimePassability};

    const EDGE_N: u8 = 1;
    const EDGE_E: u8 = 2;
    const EDGE_S: u8 = 4;
    const EDGE_W: u8 = 8;

    let game_state = make_flat_world_game_state("server_ai_blocked_return");
    let player_id = pid("lurer");
    game_state.add_player(make_player("lurer", 15.0, 0.0)).await;
    let mut rx = game_state.register_direct_channel(&player_id).await;
    let goblin = spawn_goblin(&game_state, 5.0).await;

    for _ in 0..200 {
        let x = game_state
            .brain_position_now(&goblin)
            .await
            .map_or(5.0, |p| p.x);
        game_state
            .teleport_player(
                &player_id,
                Position {
                    x: x + 10.0,
                    y: 0.0,
                    z: 0.0,
                },
                0.0,
                0,
            )
            .await;
        game_state.tick_monster_ai_by(200.0).await;
        let monsters = game_state.monsters.read().await;
        if monsters[&goblin].position.x > 55.0 && monsters[&goblin].state == MonsterState::Walk {
            break;
        }
    }
    let returning = game_state.monsters.read().await[&goblin].clone();
    assert!(
        returning.position.x > 55.0,
        "the monster must leave its leash"
    );
    assert_eq!(returning.state, MonsterState::Walk);

    let mut cells = vec![0; 80 * 4];
    for x in 0..80 {
        cells[x] |= EDGE_N;
        cells[x + 240] |= EDGE_S;
    }
    for z in 0..4 {
        cells[z * 80] |= EDGE_W;
        cells[z * 80 + 79] |= EDGE_E;
        cells[z * 80 + 49] |= EDGE_E;
        cells[z * 80 + 50] |= EDGE_W;
    }
    game_state.passability_write().insert(
        "closed_return_door".into(),
        RuntimePassability {
            house_origin_x: 0.0,
            house_origin_z: -2.0,
            min_x: 0.0,
            max_x: 80.0,
            min_z: -2.0,
            max_z: 2.0,
            floors: vec![RuntimeFloorGrid {
                floor_level: 0,
                origin_x: 0,
                origin_z: 0,
                width: 80,
                depth: 4,
                y_base: 0.0,
                wall_height: 3.0,
                cells,
            }],
            stairwells: vec![],
            yields_to_trapped_mover: false,
            allows_projectiles: false,
            is_ground: false,
        },
    );
    game_state.tick_monster_ai_by(600.0).await;
    assert_ne!(
        game_state.monsters.read().await[&goblin].state,
        MonsterState::Walk
    );

    let position = game_state.brain_position_now(&goblin).await.unwrap();
    game_state
        .teleport_player(
            &player_id,
            Position {
                x: position.x + 1.0,
                ..position
            },
            0.0,
            0,
        )
        .await;
    drain(&mut rx);
    game_state
        .broadcast_player_attack(&player_id, goblin.clone())
        .await;
    let messages = drain(&mut rx);
    assert!(messages
        .iter()
        .any(|m| matches!(m, ServerMessage::PlayerAttacked { .. })));
    assert!(messages
        .iter()
        .all(|m| !matches!(m, ServerMessage::PlayerAttackRejected { .. })));

    let mut retaliated = false;
    for _ in 0..10 {
        game_state.tick_monster_ai_by(200.0).await;
        retaliated |= drain(&mut rx).iter().any(|m| {
            matches!(
                m,
                ServerMessage::MonsterAttackedPlayer { monster_id, player_id: target, .. }
                    if monster_id == &goblin && *target == player_id
            )
        });
    }
    assert!(retaliated, "the trapped monster must fight back");
    assert!(monster_x(&game_state, &goblin).await >= 50.0);
}

#[tokio::test]
async fn barkans_rune_slash_strikes_the_fan_in_front_after_the_windup() {
    let game_state = make_flat_world_game_state("barkan_rune_slash");
    let front = pid("front");
    let side = pid("side");
    for (name, x, z) in [
        ("front", 0.0, 2.0),
        ("side", 1.5, 2.0),
        ("flank", 2.5, 0.5),
        ("behind", 0.0, -2.5),
    ] {
        game_state.add_player(make_player(name, x, z)).await;
        let mut players = game_state.players.write().await;
        let player = players.get_mut(&pid(name)).unwrap();
        player.health = 100_000;
        player.max_health = 100_000;
        player.invulnerable = name == "front";
    }
    let mut rx = game_state.register_direct_channel(&front).await;
    let barkan = game_state
        .spawn_monster(
            "barkan".to_string(),
            Position {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            0.0,
            0,
            MonsterLifecycle::Ambient,
            None,
            true,
        )
        .await
        .expect("barkan spawns")
        .id;

    let mut started = None;
    for _ in 0..80 {
        game_state.tick_monster_ai_by(200.0).await;
        started = drain(&mut rx).into_iter().find_map(|m| match m {
            ServerMessage::MonsterSkillStarted {
                monster_id,
                rotation,
                ..
            } if monster_id == barkan => Some(rotation),
            _ => None,
        });
        if started.is_some() {
            break;
        }
    }
    let rotation = started.expect("barkan casts the rune slash");
    assert!(rotation.abs() < 0.1, "faces the front player: {rotation}");

    let struck = |messages: &[ServerMessage]| -> Vec<PlayerId> {
        messages
            .iter()
            .filter_map(|m| match m {
                ServerMessage::MonsterAttackedPlayer {
                    monster_id,
                    player_id,
                    ..
                } if monster_id == &barkan => Some(*player_id),
                _ => None,
            })
            .collect()
    };
    let mut elapsed = 0.0;
    while elapsed + 200.0 < onlinerpg_shared::monster_ai::RUNE_SLASH.strike_ms {
        game_state.tick_monster_ai_by(200.0).await;
        elapsed += 200.0;
        assert!(
            struck(&drain(&mut rx)).is_empty(),
            "no damage at {elapsed}ms"
        );
    }
    game_state.tick_monster_ai_by(200.0).await;
    let hit: HashSet<PlayerId> = struck(&drain(&mut rx)).into_iter().collect();
    assert_eq!(
        hit,
        HashSet::from([front, side]),
        "the flank and the back stand outside the fan"
    );
    assert_eq!(
        health_of(&game_state, &front).await,
        100_000,
        "/god takes the blow without losing health"
    );
}

/// The roar takes a fixed 165, whatever the armor, from everyone within 11m
/// of the body, front or back; /god and those farther out are spared. Its
/// front reach starts 4m out from the centre, its back 3.8m.
#[tokio::test(start_paused = true)]
async fn terraclashs_roar_strikes_around_its_body_for_a_fixed_amount() {
    let game_state = make_flat_world_game_state("terraclash_roar");
    let names = [("near", 6.0), ("edge", 14.5), ("god", -14.0), ("far", 16.0)];
    let mut channels = Vec::new();
    for (name, z) in names {
        game_state.add_player(make_player(name, 0.0, z)).await;
        {
            let mut players = game_state.players.write().await;
            let player = players.get_mut(&pid(name)).unwrap();
            player.health = 100_000;
            player.max_health = 100_000;
            player.invulnerable = name == "god";
        }
        channels.push(game_state.register_direct_channel(&pid(name)).await);
    }
    let boss = game_state
        .spawn_monster(
            "terraclash".into(),
            Position {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            0.0,
            0,
            MonsterLifecycle::Ambient,
            None,
            false,
        )
        .await
        .unwrap()
        .id;
    game_state.tick_monster_ai_by(200.0).await;
    game_state
        .broadcast_player_attack(&pid("near"), boss.clone())
        .await;

    let roar = onlinerpg_shared::monster_ai::EARTH_ROAR;
    assert_eq!(
        roar.range(),
        game_state
            .monster_defs
            .get("terraclash")
            .unwrap()
            .ranged_attack_range,
        "the roar reaches as far as the ranged swing"
    );
    let mut warned = HashSet::new();
    let mut struck = Vec::new();
    let mut elapsed = 0.0;
    let mut cast_at = None;
    while elapsed < roar.first_cast_ms + roar.cast_ms + 1000.0 {
        game_state.tick_monster_ai_by(200.0).await;
        elapsed += 200.0;
        for (rx, (name, _)) in channels.iter_mut().zip(names) {
            for message in drain(rx) {
                match message {
                    ServerMessage::MonsterSkillStarted {
                        skill: onlinerpg_shared::monster_ai::MonsterSkillId::EarthRoar,
                        ..
                    } => {
                        warned.insert(name);
                        cast_at.get_or_insert(elapsed);
                    }
                    ServerMessage::MonsterAttackedPlayer {
                        player_id,
                        damage: 165,
                        ..
                    } if player_id == pid(name) => struck.push((name, elapsed)),
                    _ => {}
                }
            }
        }
    }
    let cast_at = cast_at.expect("terraclash roars once its first cast is due");
    assert_eq!(warned, HashSet::from(["near", "edge", "god", "far"]));
    let names: HashSet<_> = struck.iter().map(|(name, _)| *name).collect();
    assert_eq!(names, HashSet::from(["near", "edge", "god"]));
    for (name, at) in &struck {
        assert!(
            at - cast_at >= roar.strike_ms - 200.0,
            "{name} struck {}ms into the cast",
            at - cast_at
        );
    }
    assert_eq!(health_of(&game_state, &pid("god")).await, 100_000);
    assert_eq!(health_of(&game_state, &pid("far")).await, 100_000);
}

async fn terraclash_facing(game_state: &GameState, player_z: f32) -> (PlayerId, DirectRx, String) {
    let player_id = pid("archer");
    game_state
        .add_player(make_player("archer", 0.0, player_z))
        .await;
    {
        let mut players = game_state.players.write().await;
        let player = players.get_mut(&player_id).unwrap();
        player.health = 100_000;
        player.max_health = 100_000;
    }
    let rx = game_state.register_direct_channel(&player_id).await;
    let boss = game_state
        .spawn_monster(
            "terraclash".into(),
            Position {
                x: 0.0,
                y: 0.0,
                z: 0.0,
            },
            0.0,
            0,
            MonsterLifecycle::Ambient,
            None,
            false,
        )
        .await
        .unwrap()
        .id;
    game_state.tick_monster_ai_by(200.0).await;
    game_state
        .broadcast_player_attack(&player_id, boss.clone())
        .await;
    (player_id, rx, boss)
}

fn boss_blows(messages: &[ServerMessage], boss: &str) -> (Option<Position>, Vec<bool>) {
    let strike = messages.iter().find_map(|m| match m {
        ServerMessage::MonsterGroundStrike {
            monster_id,
            position,
            ..
        } if monster_id == boss => Some(*position),
        _ => None,
    });
    let hits = messages
        .iter()
        .filter_map(|m| match m {
            ServerMessage::MonsterAttackedPlayer {
                monster_id, ranged, ..
            } if monster_id == boss => Some(*ranged),
            _ => None,
        })
        .collect();
    (strike, hits)
}

/// Terraclash cannot walk: a target past its 3m reach but within 11m gets
/// the ground it stood on struck after the slam lands; anyone farther is safe.
#[tokio::test(start_paused = true)]
async fn terraclash_strikes_the_ground_under_a_distant_target() {
    // Its reach starts 4m in front of the centre.
    for (z, ground) in [(5.5, false), (9.0, true)] {
        let game_state = make_flat_world_game_state(&format!("terraclash_swing_{z}"));
        let (_, mut rx, boss) = terraclash_facing(&game_state, z).await;
        let mut messages = Vec::new();
        for _ in 0..6 {
            game_state.tick_monster_ai_by(200.0).await;
            messages.extend(drain(&mut rx));
        }
        tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
        messages.extend(drain(&mut rx));
        let (strike, hits) = boss_blows(&messages, &boss);
        assert_eq!(strike.is_some(), ground, "target at z={z}");
        assert_eq!(hits.first(), Some(&ground), "target at z={z}");
    }

    let game_state = make_flat_world_game_state("terraclash_swing_far");
    let (_, mut rx, boss) = terraclash_facing(&game_state, 16.5).await;
    for _ in 0..10 {
        game_state.tick_monster_ai_by(200.0).await;
    }
    tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
    assert_eq!(boss_blows(&drain(&mut rx), &boss), (None, vec![]));
}

#[tokio::test(start_paused = true)]
async fn stepping_off_the_mark_dodges_the_ground_strike() {
    let game_state = make_flat_world_game_state("terraclash_dodge");
    let (player_id, mut rx, boss) = terraclash_facing(&game_state, 9.0).await;
    let mut strike = None;
    for _ in 0..6 {
        game_state.tick_monster_ai_by(200.0).await;
        strike = strike.or(boss_blows(&drain(&mut rx), &boss).0);
    }
    let strike = strike.expect("ground strike launched");
    game_state
        .players
        .write()
        .await
        .get_mut(&player_id)
        .unwrap()
        .position
        .x = strike.x + 2.5;
    tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
    assert_eq!(boss_blows(&drain(&mut rx), &boss).1, Vec::<bool>::new());
}

/// A ground strike lands out to the reach the brain swung with, no farther.
#[tokio::test(start_paused = true)]
async fn terraclash_ground_strike_is_bounded_by_its_swing_reach() {
    // Reach is measured from 4m in front of the centre.
    let far_reach = onlinerpg_shared::monster_ai::aggro_for("terraclash")
        .unwrap()
        .far_reach;
    // The server allows 4m of drift past it.
    for (z, struck) in [
        (4.0 + far_reach - 1.0, true),
        (4.0 + far_reach + 5.0, false),
    ] {
        let game_state = make_flat_world_game_state(&format!("terraclash_far_{z}"));
        let (player_id, mut rx, boss) = terraclash_facing(&game_state, z).await;
        game_state
            .monster_ground_strike(&boss, &player_id, far_reach)
            .await;
        assert_eq!(
            boss_blows(&drain(&mut rx), &boss).0.is_some(),
            struck,
            "target at z={z}"
        );
    }
}
