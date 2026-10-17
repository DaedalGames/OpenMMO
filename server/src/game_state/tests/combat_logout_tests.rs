use super::*;
use crate::game_state::combat_logout::COMBAT_LOGOUT_MAX_MS;

struct Online {
    auth: crate::auth::AuthService,
    account: String,
    character_id: i64,
    id: PlayerId,
    session: u64,
}

/// A real character in game at x=7, attached to its account session.
async fn online(game: &GameState, test: &str, in_combat: bool) -> Online {
    let auth = make_test_auth(test);
    let account = auth.login_npc(&format!("npc_{test}")).unwrap();
    let record = add_db_player(game, &auth, &account, "Lingerer", 7.0, 0.0, 0).await;
    let id = pid("Lingerer");
    if in_combat {
        put_in_combat(game, &id).await;
    }
    let (tx, _rx) = tokio::sync::mpsc::unbounded_channel();
    let session = game.register_account_session(&account, tx, &auth).await;
    game.attach_player_to_account_session(&account, session, id)
        .await;
    Online {
        auth,
        account,
        character_id: record.id,
        id,
        session,
    }
}

async fn calm_down(game: &GameState, id: &PlayerId) {
    game.players
        .write()
        .await
        .get_mut(id)
        .unwrap()
        .last_combat_at = 0;
}

async fn in_world(game: &GameState, id: &PlayerId) -> bool {
    game.players.read().await.contains_key(id)
}

async fn disconnect(game: &GameState, o: &Online) {
    game.end_account_session(&o.account, o.session, &o.auth)
        .await;
}

#[tokio::test]
async fn disconnect_mid_fight_lingers_until_the_fight_ends() {
    let game = make_test_game_state("linger_until_calm");
    let o = online(&game, "linger_until_calm", true).await;

    disconnect(&game, &o).await;
    game.tick_combat_logout(&o.auth).await;
    assert!(in_world(&game, &o.id).await);
    assert!(game.character_in_game(o.character_id).await);

    calm_down(&game, &o.id).await;
    game.tick_combat_logout(&o.auth).await;
    assert!(!in_world(&game, &o.id).await);
    assert!(!game.character_in_game(o.character_id).await);
    assert!(game.lingering_body_of_account(&o.account).await.is_none());
    let saved = o
        .auth
        .get_character_for_account(&o.account, o.character_id)
        .unwrap();
    assert_eq!(saved.last_x, 7.0);
}

#[tokio::test]
async fn disconnect_out_of_combat_leaves_at_once() {
    let game = make_test_game_state("linger_calm");
    let o = online(&game, "linger_calm", false).await;
    disconnect(&game, &o).await;
    assert!(!in_world(&game, &o.id).await);
}

#[tokio::test]
async fn a_body_that_dies_is_saved_dead_where_it_fell() {
    let game = make_test_game_state("linger_death");
    let o = online(&game, "linger_death", true).await;
    disconnect(&game, &o).await;

    game.players.write().await.get_mut(&o.id).unwrap().health = 0;
    game.on_player_died(&o.id, "test").await;
    game.tick_combat_logout(&o.auth).await;

    assert!(!in_world(&game, &o.id).await);
    let saved = o
        .auth
        .get_character_for_account(&o.account, o.character_id)
        .unwrap();
    assert_eq!(saved.health, Some(0));
    assert_eq!(saved.last_x, 7.0);
}

#[tokio::test]
async fn a_body_kept_in_combat_leaves_at_the_cap() {
    let game = make_test_game_state("linger_cap");
    let o = online(&game, "linger_cap", true).await;
    disconnect(&game, &o).await;

    game.lingering_bodies
        .write()
        .await
        .get_mut(&o.id)
        .unwrap()
        .disconnected_at -= COMBAT_LOGOUT_MAX_MS;
    game.tick_combat_logout(&o.auth).await;
    assert!(!in_world(&game, &o.id).await);
}

#[tokio::test]
async fn a_resumed_body_keeps_its_id_and_no_longer_times_out() {
    let game = make_test_game_state("linger_resume");
    let o = online(&game, "linger_resume", true).await;
    disconnect(&game, &o).await;

    let entry = game.lingering_body_of_account(&o.account).await.unwrap();
    assert_eq!((entry.id, entry.character_id), (o.id, o.character_id));
    assert!(entry.remaining_secs > 0 && entry.remaining_secs <= 60);

    let (tx, _rx) = tokio::sync::mpsc::unbounded_channel();
    let session = game.register_account_session(&o.account, tx, &o.auth).await;
    let player = game
        .resume_lingering_body(o.id, &o.account, session)
        .await
        .unwrap();
    assert_eq!((player.id, player.ready_at), (o.id, 0));
    assert!(game.is_current_account_session(&o.account, session).await);

    calm_down(&game, &o.id).await;
    game.tick_combat_logout(&o.auth).await;
    assert!(in_world(&game, &o.id).await, "resumed, not lingering");
}

#[tokio::test]
async fn replacement_login_mid_fight_leaves_a_body() {
    let game = make_test_game_state("linger_replaced");
    let o = online(&game, "linger_replaced", true).await;
    let (tx, _rx) = tokio::sync::mpsc::unbounded_channel();
    game.register_account_session(&o.account, tx, &o.auth).await;
    assert!(in_world(&game, &o.id).await);
    assert!(game.lingering_body_of_account(&o.account).await.is_some());
}

#[tokio::test]
async fn eviction_removes_the_account_body_at_once() {
    let game = make_test_game_state("linger_evict");
    let o = online(&game, "linger_evict", true).await;
    disconnect(&game, &o).await;

    let _sessions = game.lock_character_sessions().await;
    game.evict_account_session_locked(&o.account, "banned", None, &o.auth)
        .await;
    assert!(!in_world(&game, &o.id).await);
}

#[tokio::test]
async fn kick_removes_a_lingering_body() {
    let game = make_test_game_state("linger_kick");
    let o = online(&game, "linger_kick", true).await;
    disconnect(&game, &o).await;

    game.kick_player(&o.id, "kicked", None, &o.auth).await;
    assert!(!in_world(&game, &o.id).await);
    assert!(game.lingering_body_of_account(&o.account).await.is_none());
}
