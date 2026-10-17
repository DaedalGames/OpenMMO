# Combat Logout

전투 중 접속 종료 시 캐릭터를 월드에 남기는 규칙. **설계안 (미구현, 2026-10-17).**

## 문제

지금은 접속이 끊기면 `cleanup_player_session`이 즉시 돈다 (`server/src/game_state/player.rs`).

1. 저장 후 `remove_player`가 캐릭터를 `players`에서 지운다. 몬스터는 대상을 잃고, 지켜보는 사람이 없는 앰비언트 몬스터는 사라진다.
2. 재접속하면 DB에 저장된 HP 그대로 새 `Player`가 생긴다.
3. 새 `Player`는 `ready_at`(`WORLD_LOADING_GRACE_MS` 30초) 동안 피해를 받지 않는다. `WorldReady`나 첫 이동 요청이 오면 끝난다. 웹 클라이언트는 자동 재연결 후 다시 입장하면 곧바로 `WorldReady`를 보낸다.

그래서 죽기 직전에 새로고침하면 사망과 XP 페널티(구간 15%)를 피한다. `/escape`와 주문서가 전투 중(`in_combat`, 마지막 교전 후 10초)에 막혀 있는 것과도 맞지 않는다. 클라이언트 종류와 상관없이 같은 규칙이 적용되어야 하고, 사람도 탭 닫기·네트워크 끊김으로 같은 결과를 얻으므로 서버 규칙으로 막는다.

## 규칙

- 접속이 끊기는 순간 `in_combat`이면 캐릭터를 월드에 남긴다 ("남은 몸"). 전투 중이 아니면 지금처럼 즉시 정리한다.
- 남은 몸은 아무 행동도 하지 않는다. 자동 공격·목표 이동·집중 행동(낚시·굽기·연주)은 접속 종료 시점에 멈춘다.
- 몬스터 AI, 디버프 피해, 파티 상태는 그대로 동작한다. 몸이 `players`에 있으므로 별도 처리가 필요 없다.
- 다음 중 하나가 되면 정리한다.
  - `in_combat`이 풀림 (10초 동안 교전 없음)
  - 사망
  - 접속 종료 후 60초 (`COMBAT_LOGOUT_MAX_MS`). 몸이 계속 맞으면서 버티는 경우의 상한이다.
- 접속 종료 원인이 무엇이든 같다: 새로고침, 탭 닫기, heartbeat 타임아웃, 소켓 오류, 다른 기기 로그인으로 인한 세션 교체.
- 예외는 즉시 정리한다: 관리자 `/kick`·`/ban`, 서버 종료 드레인. 서버 종료 시 남은 몸은 `players`에 있으므로 `persist_shutdown_snapshot`이 함께 저장한다.
- 공식 NPC도 같은 규칙을 따른다. agent-client가 재시작하면 같은 캐릭터로 다시 들어와 몸을 승계한다.

## 상태

```rust
struct LingeringBody {
    account: String,      // 소문자 키
    character_id: i64,
    disconnected_at: u64, // ms
}
// GameState
lingering_bodies: Arc<RwLock<HashMap<PlayerId, LingeringBody>>>,
```

락 순서는 `character_session_lock` → `persistence_lock` → `lingering_bodies` → `players`. `mod.rs`의 락 순서 문서와 lockscan에 추가한다.

## 접속 종료

`cleanup_player_session`을 부르는 두 곳에서 분기한다: `end_account_session`(소켓 종료)과 `register_account_session_locked`(다른 기기 로그인으로 인한 세션 교체). `kick_player`는 분기하지 않는다.

- 전투 중이면 `begin_linger`:
  - `end_account_activity`, `cancel_concentration_if_active`, `stop_player_attack`, 목표 이동 취소, `drop_player_trade`, 상점 점유 해제.
  - `unregister_connection_channel`. `send_direct_message`는 채널이 없으면 아무것도 하지 않으므로 몸에게 가는 메시지는 조용히 버려진다.
  - `lingering_bodies`에 등록하고 `dirty_players`에 넣는다. DB 저장은 32초 주기의 `flush_dirty_saves`에 맡긴다. 그 사이 서버가 죽으면 최대 32초 전 상태로 돌아가는데, 지금 온라인 플레이어와 같은 조건이다.
  - `player_characters`, 인벤토리, 스킬, 파티, 버프, 던전 점유는 그대로 둔다.
- 아니면 지금의 `cleanup_player_session`.

## 정리

기존 1초 틱(HP 재생 틱 등) 하나에서 `lingering_bodies`를 훑는다. 읽기 락으로 먼저 확인하고 비어 있으면 `character_session_lock`을 잡지 않고 바로 돌아간다. 그러지 않으면 매초 모든 로그인과 경합한다. 남은 몸은 동시에 많아야 수십 개이고, 몸마다 tokio 작업을 띄우지 않는다.

정리 조건을 만족하면 `character_session_lock`을 잡고 항목이 아직 있는지 다시 확인한 뒤 제거하고, 지금의 `cleanup_player_session` 중 아직 하지 않은 단계(`persist_and_detach_player`, `unregister_player_character`, `remove_player`)를 실행한다. 재접속과 정리가 겹치면 락을 먼저 잡은 쪽이 이긴다.

## 사망

남은 몸이 죽으면 `on_player_died`가 평소대로 돈다: XP 페널티, 버프·디버프 제거, 거래 취소. 이어서 사망 틱에서 정리 조건을 만족하므로 HP 0, 사망 위치·층으로 저장된다.

재접속하면 HP 0으로 들어오고 사망 대화상자가 뜬다. `RequestRespawn`으로 여관에서 부활하거나 불사조의 부적으로 그 자리에서 부활한다. 지금도 죽은 채로 나갔다 들어오면 같은 흐름이므로 새 경로가 아니다. 구현 시 HP 0 입장이 사망 대화상자로 이어지는지 테스트로 고정한다.

## 재접속 시 세션 승계

클라이언트는 재연결 때 같은 캐릭터로 `EnterGame`을 보낸다 (`socket.ts`의 `lastCharacterId`). 서버의 `EnterGame` 처리에서 DB 로드 전에 확인한다.

- **같은 캐릭터의 남은 몸이 있음** → 승계:
  - `lingering_bodies`에서 제거 (정리 취소).
  - 같은 `PlayerId`를 그대로 쓴다. 몬스터 대상, 파티, 버프, 디버프, 피해 로그가 이어진다.
  - DB에서 다시 읽지 않는다. 메모리 상태가 DB보다 새롭다. 스킬·인벤토리·칭호·던전 기록 로드도 건너뛴다.
  - `register_connection_channel`, `attach_player_to_account_session`, `reset_world_view`, 그리고 지금 `EnterGame` 응답이 보내는 본인 상태(인벤토리·스킬·칭호·파티 등)를 본인에게만 보낸다.
  - `add_player`를 거치지 않으므로 `PlayerJoined`를 방송하지 않는다. 다른 사람은 이미 몸을 보고 있다.
  - **`ready_at`을 다시 걸지 않는다.** 로딩 무적을 주면 새로고침이 다시 회피 수단이 된다. 클라이언트가 월드를 불러오는 동안에도 몸은 맞는다.
- **같은 계정의 다른 캐릭터를 고름** → 거절하고 남은 시간을 알린다 ("전투 중인 캐릭터가 아직 월드에 있습니다. N초 후 다시 시도하세요"). 계정당 월드에 있는 캐릭터는 하나라는 불변식을 유지한다.
- 남은 몸이 있는 캐릭터의 이름 변경·삭제 예약도 같은 메시지로 거절한다.
- 재인증 시 캐릭터 목록은 DB에서 읽으므로 남은 몸의 최신 레벨·장비가 아직 반영되지 않았을 수 있다. 목록 표시만의 문제라 그대로 둔다.

## 던전 복귀

- 남은 몸은 던전 층에 그대로 있다. 지금 `remove_player`가 하는 던전 퇴장(`handle_player_floor_change` → 0층)은 정리 시점으로 미뤄진다. 그동안 몸이 층을 지켜보므로 그 층 몬스터도 남는다.
- 승계하면 몸이 이미 던전 층에 있으므로 `rehydrate_dungeon_player`를 거치지 않는다. 클라이언트는 받은 `floor_level`로 던전 층을 그린다.
- 몸이 남은 사이에 밤 리셋이 오면 `reset_dungeons`가 다른 온라인 플레이어와 똑같이 입구로 내보낸다.
- 정리된 뒤 재접속하면 지금처럼 `dungeon_epoch`으로 판단한다: 같은 밤이면 저장 위치로, 리셋이 지났으면 입구로.

## 다른 사람에게 보이는 것

남은 몸은 평범한 `Player`로 보인다. 이름표에 "(연결 끊김)" 표시는 선택 사항이다. 추가한다면 `Player`에 브로드캐스트 필드를 하나 두고 프로토콜 버전을 올린다.

## 클라이언트

필수 변경은 없다. 재연결은 이미 같은 캐릭터로 `EnterGame`을 보내고, HP 0 입장은 사망 대화상자로 이어진다. 다른 캐릭터를 고를 때 오는 거절 메시지는 기존 `CharacterError`로 보여준다.

## 테스트

- 전투 중 접속 종료 → 몸이 `players`에 남고, 10초 무교전 후 정리.
- 전투 중이 아닐 때 접속 종료 → 즉시 정리 (지금 동작 유지).
- 남은 몸이 몬스터에게 죽음 → XP 페널티 적용, HP 0·사망 위치로 저장.
- 60초 상한에서 정리.
- 승계: 같은 `PlayerId`, HP·버프·파티 유지, `ready_at == 0`.
- 다른 캐릭터 `EnterGame`, 남은 몸 캐릭터의 이름 변경·삭제 예약 거절.
- 다른 기기 로그인으로 세션이 교체될 때도 몸이 남음.
- 던전 층에서 남은 몸 → 정리 시 던전 퇴장, 승계 시 같은 층.
- 정리와 승계 경합: 한쪽만 이긴다.
- `/kick`·서버 종료는 즉시 정리.
