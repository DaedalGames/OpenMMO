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
    brain.skill_cooldowns_ms.fill(0.0);
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
    brain.skill_cooldowns_ms.fill(0.0);
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
    brain.skill_cooldowns_ms.fill(0.0);
    let near = attacker_at(10.0, 12.0);
    tick(&mut brain, 16.0, &near);
    brain.handle_death();
    assert!(strikes(&tick(&mut brain, 3000.0, &near)).is_empty());
}

#[test]
fn the_plain_swing_waits_a_full_cooldown_after_the_cast() {
    let mut brain = barkan_at(10.0, 10.0);
    brain.skill_cooldowns_ms.fill(0.0);
    let near = attacker_at(10.0, 12.0);
    tick(&mut brain, 16.0, &near);
    let mut elapsed = 16.0;
    let mut swung_at = None;
    while elapsed < RUNE_SLASH.cast_ms + 4000.0 {
        let commands = tick(&mut brain, 100.0, &near);
        elapsed += 100.0;
        if commands
            .iter()
            .any(|c| matches!(c, AiCommand::Attack { .. }))
        {
            swung_at = Some(elapsed);
            break;
        }
    }
    let swung_at = swung_at.expect("a plain swing follows the cast");
    assert!(
        swung_at >= RUNE_SLASH.cast_ms + 2800.0,
        "swung {swung_at}ms after the cast began"
    );
}

fn terraclash() -> MonsterBrain {
    let mut brain = MonsterBrain::new(
        "terraclash_1".into(),
        "terraclash",
        "brave".into(),
        Position {
            x: 0.0,
            y: 0.0,
            z: 0.0,
        },
        80_000,
        80_000,
        0.0,
        0.0,
        3.0,
        40.0,
        3000.0,
    );
    brain.ranged_range = 11.0;
    brain.body = crate::monster_body::BodyFootprint::parse("4.8|3.2|3.0");
    brain.target_player_id = Some(1.into());
    brain
}

fn raider(id: u64, x: f32, z: f32) -> NearbyPlayer {
    NearbyPlayer {
        id: id.into(),
        position: Position { x, y: 0.0, z },
        health: 100,
        drank_recently: false,
    }
}

/// The front line and two archers standing back.
fn raid() -> Vec<NearbyPlayer> {
    vec![
        raider(1, 0.0, 4.5),
        raider(2, 2.0, 4.5),
        raider(3, -9.0, 9.0),
        raider(4, 0.0, -12.0),
    ]
}

fn cast_of(commands: &[AiCommand]) -> Option<(MonsterSkillId, f32, Vec<Position>)> {
    commands.iter().find_map(|c| match c {
        AiCommand::CastSkill {
            skill,
            rotation,
            spots,
        } => Some((*skill, *rotation, spots.clone())),
        _ => None,
    })
}

/// Casts seen over `ms`, with when each began.
fn casts_over(
    brain: &mut MonsterBrain,
    players: &[NearbyPlayer],
    ms: f32,
) -> Vec<(f32, MonsterSkillId, Vec<AiCommand>)> {
    let mut rng = SmallRng::seed_from_u64(11);
    let mut seen = Vec::new();
    let mut elapsed = 0.0;
    while elapsed < ms {
        let commands = brain.tick_with_behavior_tree(
            100.0,
            players,
            &[],
            &attack_tree(),
            &DirectPath,
            &mut rng,
        );
        elapsed += 100.0;
        if let Some((skill, ..)) = cast_of(&commands) {
            seen.push((elapsed, skill, commands));
        }
    }
    seen
}

fn force(brain: &mut MonsterBrain, skill: &MonsterSkill) {
    let set = brain.skills.unwrap();
    for (i, (s, _)) in set.skills.iter().enumerate() {
        brain.skill_cooldowns_ms[i] = if s.id == skill.id { 0.0 } else { f32::MAX };
    }
}

#[test]
fn terraclash_casts_all_three_skills_with_a_gap_between() {
    let mut brain = terraclash();
    let casts = casts_over(&mut brain, &raid(), 600_000.0);
    let kinds: std::collections::HashSet<_> = casts.iter().map(|(_, s, _)| *s).collect();
    assert_eq!(kinds.len(), 3, "got {kinds:?}");
    for pair in casts.windows(2) {
        let (at, skill, _) = &pair[0];
        let gap = pair[1].0 - at;
        assert!(
            gap >= skill_by_id(*skill).cast_ms + TERRACLASH_SKILLS.gap_ms,
            "{:?} came {gap}ms after {skill:?}",
            pair[1].1
        );
    }
    let roars = casts
        .iter()
        .filter(|(_, s, _)| *s == MonsterSkillId::EarthRoar)
        .count();
    assert!(
        roars * 2 < casts.len() - roars,
        "the roar comes least often: {roars} of {}",
        casts.len()
    );
}

#[test]
fn formation_break_aims_the_fan_and_pools_the_archers_outside_it() {
    let mut brain = terraclash();
    force(&mut brain, &FORMATION_BREAK);
    // The target stands far off to the side; the fan turns only so far.
    let players = [
        raider(1, 9.0, 0.5),
        raider(2, 0.0, 4.5),
        raider(3, -9.0, 9.0),
        raider(4, 0.0, -12.0),
    ];
    let mut rng = SmallRng::seed_from_u64(3);
    let commands =
        brain.tick_with_behavior_tree(16.0, &players, &[], &attack_tree(), &DirectPath, &mut rng);
    let (skill, rotation, spots) = cast_of(&commands).expect("formation break");
    assert_eq!(skill, MonsterSkillId::FormationBreak);
    assert!(
        (rotation - 60f32.to_radians()).abs() < 1e-3,
        "aimed {rotation}"
    );
    let mut spots: Vec<_> = spots.iter().map(|p| (p.x, p.z)).collect();
    spots.sort_by(|a, b| a.0.total_cmp(&b.0));
    assert_eq!(
        spots,
        vec![(-9.0, 9.0), (0.0, -12.0)],
        "the front line and the target in the fan get no pool"
    );
}

#[test]
fn a_bodys_fan_reaches_past_its_front_corners() {
    let rotation = 0.0;
    let origin = Position {
        x: 0.0,
        y: 0.0,
        z: 0.0,
    };
    let at = |x, z| Position { x, y: 0.0, z };
    assert!(FORMATION_BREAK.fan_contains(&origin, rotation, &at(4.0, 4.2)));
    assert!(FORMATION_BREAK.fan_contains(&origin, rotation, &at(0.0, 11.5)));
    assert!(!FORMATION_BREAK.fan_contains(&origin, rotation, &at(5.8, 0.0)));
    assert!(!FORMATION_BREAK.fan_contains(&origin, rotation, &at(0.0, -4.0)));
}

#[test]
fn the_earthquake_marks_raiders_and_bare_ground_without_overlap() {
    let mut brain = terraclash();
    force(&mut brain, &EARTHQUAKE);
    let mut rng = SmallRng::seed_from_u64(5);
    let commands =
        brain.tick_with_behavior_tree(16.0, &raid(), &[], &attack_tree(), &DirectPath, &mut rng);
    let (skill, _, spots) = cast_of(&commands).expect("earthquake");
    assert_eq!(skill, MonsterSkillId::Earthquake);
    let rule = EARTHQUAKE.spots.unwrap();
    assert_eq!(spots.len(), rule.count);
    for (i, a) in spots.iter().enumerate() {
        for b in &spots[i + 1..] {
            assert!(
                a.dist_xz_sq(b) >= rule.radius.powi(2),
                "{a:?} overlaps {b:?}"
            );
        }
        let edge = crate::monster_body::reach_point(brain.body, brain.position, 0.0, a);
        assert!(
            edge.dist_xz_sq(a) <= rule.max_reach.powi(2),
            "{a:?} is too far"
        );
    }
    for p in raid() {
        assert!(
            EARTHQUAKE.spots_contain(&spots, &p.position),
            "{:?} stands clear of every mark",
            p.position
        );
    }
}

#[test]
fn at_five_percent_terraclash_roars_five_times_ten_seconds_apart() {
    let mut brain = terraclash();
    brain.health = 4000;
    let mut rng = SmallRng::seed_from_u64(9);
    let players = raid();
    let mut roars: Vec<f32> = Vec::new();
    let mut swings = Vec::new();
    let mut elapsed = 0.0;
    while elapsed < 80_000.0 {
        let commands = brain.tick_with_behavior_tree(
            100.0,
            &players,
            &[],
            &attack_tree(),
            &DirectPath,
            &mut rng,
        );
        elapsed += 100.0;
        if let Some((skill, ..)) = cast_of(&commands) {
            assert_eq!(
                skill,
                MonsterSkillId::EarthRoar,
                "only the roar at {elapsed}ms"
            );
            roars.push(elapsed);
        }
        if commands
            .iter()
            .any(|c| matches!(c, AiCommand::Attack { .. }))
        {
            swings.push(elapsed);
        }
    }
    assert_eq!(roars.len(), 5, "roared at {roars:?}");
    assert!(roars[0] <= 100.0, "the first roar is at once");
    for pair in roars.windows(2) {
        assert!((pair[1] - pair[0] - 10_000.0).abs() <= 100.0, "{roars:?}");
    }
    assert!(
        swings.iter().all(|&s| s > roars[4]),
        "no swing between the roars: {swings:?}"
    );
    assert!(!swings.is_empty(), "plain swings resume after the fifth");
}
