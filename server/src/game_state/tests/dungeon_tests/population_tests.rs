use super::respawn_tests::enter_floor;
use super::*;
use crate::metrics::DungeonFloorCount;

#[tokio::test]
async fn floor_population_counts_players_per_floor_without_npcs() {
    let game_state = make_test_game_state("dungeon_floor_population");
    enter_floor(&game_state, "alice", "orc_warrens", 2).await;
    enter_floor(&game_state, "bob", "orc_warrens", 2).await;
    enter_floor(&game_state, "carol", "old_crypt", 3).await;
    let npc = enter_floor(&game_state, "guide", "old_crypt", 1).await;
    game_state
        .players
        .write()
        .await
        .get_mut(&npc)
        .unwrap()
        .is_official_npc = true;

    let mut floors = game_state.dungeon_floor_population().await;
    floors.sort_by(|a, b| (&a.dungeon, a.depth).cmp(&(&b.dungeon, b.depth)));

    let floor = |dungeon: &str, depth, players| DungeonFloorCount {
        dungeon: dungeon.into(),
        depth,
        players,
    };
    assert_eq!(
        floors,
        [floor("old_crypt", 3, 1), floor("orc_warrens", 2, 2)]
    );
}
