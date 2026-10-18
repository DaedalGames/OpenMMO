use super::*;

fn barkan_at(x: f32, z: f32) -> MonsterBrain {
    let mut brain = MonsterBrain::new(
        "barkan_1".into(),
        "barkan",
        "default".into(),
        Position { x, y: 0.0, z },
        600,
        600,
        3.0,
        3.0,
        2.6,
        DEFAULT_CHASE_RANGE,
        2800.0,
    );
    brain.target_player_id = Some(1.into());
    brain
}

fn tick(brain: &mut MonsterBrain, ms: f32, players: &[NearbyPlayer]) -> Vec<AiCommand> {
    let mut rng = SmallRng::seed_from_u64(7);
    brain.tick_with_behavior_tree(ms, players, &[], &attack_tree(), &DirectPath, &mut rng)
}

fn casts(commands: &[AiCommand]) -> usize {
    commands
        .iter()
        .filter(|c| matches!(c, AiCommand::CastSkill { .. }))
        .count()
}

fn strikes(commands: &[AiCommand]) -> Vec<(Position, f32)> {
    commands
        .iter()
        .filter_map(|c| match c {
            AiCommand::SkillStrike {
                position, rotation, ..
            } => Some((*position, *rotation)),
            _ => None,
        })
        .collect()
}

#[test]
fn barkan_swings_plainly_until_the_rune_slash_is_ready() {
    let mut brain = barkan_at(10.0, 10.0);
    let near = attacker_at(10.0, 12.0);
    let first = tick(&mut brain, 16.0, &near);
    assert!(first.iter().any(|c| matches!(c, AiCommand::Attack { .. })));
    assert_eq!(casts(&first), 0);

    let mut cast = Vec::new();
    for _ in 0..60 {
        cast = tick(&mut brain, 200.0, &near);
        if casts(&cast) > 0 {
            break;
        }
    }
    assert_eq!(
        casts(&cast),
        1,
        "the first cast comes once its cooldown runs out"
    );
    assert!(!cast.iter().any(|c| matches!(c, AiCommand::Attack { .. })));
    assert!(brain.is_casting());
}

#[test]
fn the_rune_slash_strikes_once_at_the_sweep_from_where_it_was_cast() {
    let mut brain = barkan_at(10.0, 10.0);
    brain.skill_cooldown_left_ms = 0.0;
    let near = attacker_at(10.0, 12.0);
    let cast = tick(&mut brain, 16.0, &near);
    let Some(AiCommand::CastSkill { rotation, .. }) = cast
        .iter()
        .find(|c| matches!(c, AiCommand::CastSkill { .. }))
    else {
        panic!("expected a cast, got {cast:?}");
    };
    let rotation = *rotation;

    // The target circles behind; the facing and the spot hold.
    let behind = attacker_at(10.0, 8.0);
    let mut elapsed = 0.0;
    while elapsed + 200.0 < RUNE_SLASH.strike_ms {
        let commands = tick(&mut brain, 200.0, &behind);
        elapsed += 200.0;
        assert!(strikes(&commands).is_empty(), "no damage at {elapsed}ms");
        assert!(
            !commands.iter().any(|c| matches!(c, AiCommand::Move { .. })),
            "a cast holds still"
        );
    }
    let strike = tick(&mut brain, 200.0, &behind);
    assert_eq!(
        strikes(&strike),
        vec![(
            Position {
                x: 10.0,
                y: 0.0,
                z: 10.0
            },
            rotation
        )]
    );
    for _ in 0..10 {
        assert!(strikes(&tick(&mut brain, 200.0, &behind)).is_empty());
    }
    assert!(!brain.is_casting());
}

#[test]
fn hits_do_not_stagger_a_cast() {
    let mut brain = barkan_at(10.0, 10.0);
    brain.skill_cooldown_left_ms = 0.0;
    let near = attacker_at(10.0, 12.0);
    tick(&mut brain, 16.0, &near);
    assert!(brain
        .handle_hit_with_behavior_tree(&1.into(), true, 5)
        .is_empty());
    assert_eq!(brain.state(), AiState::Attack);
    assert_eq!(brain.health, 595);
    assert!(brain.is_casting());
}

#[test]
fn a_cast_ends_if_barkan_dies() {
    let mut brain = barkan_at(10.0, 10.0);
    brain.skill_cooldown_left_ms = 0.0;
    let near = attacker_at(10.0, 12.0);
    tick(&mut brain, 16.0, &near);
    brain.handle_death();
    assert!(strikes(&tick(&mut brain, 3000.0, &near)).is_empty());
}
