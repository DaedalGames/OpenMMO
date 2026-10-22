import { describe, expect, it, vi } from 'vitest'

vi.mock('../wasm/onlinerpg_shared', () => ({
  monster_body_engage_point: vi.fn(),
  passability_remove_monster_body: vi.fn(),
  passability_set_monster_body: vi.fn(() => false),
}))
vi.mock('./sfxManager', () => ({
  getMaterialHitSoundUrl: vi.fn(),
  getMaterialMissSoundUrl: vi.fn(),
  playBowSound: vi.fn(),
  playSwordHitSound: vi.fn(),
  playSwordMissSound: vi.fn(),
}))

const { monsterManager } = await import('./monsterManager')

function spawn(id: string, type: string) {
  monsterManager.spawnWithId({
    id,
    monster_type: type,
    position: { x: 0, y: 0, z: 0 },
    rotation: 0,
    state: 'idle',
    health: 100,
    max_health: 100,
    floor_level: 0,
  } as never)
  return monsterManager.monsters.get(id)!
}

function landHit(id: string) {
  const monster = monsterManager.monsters.get(id)!
  ;(
    monsterManager as unknown as {
      applyMonsterPose: (m: typeof monster, u: { state: 'hit' }) => void
    }
  ).applyMonsterPose(monster, { state: 'hit' })
  return monster.state
}

describe('hit flinch', () => {
  it('flinches an ordinary monster but not a raid boss', () => {
    spawn('kobold_1', 'kobold')
    spawn('terraclash_1', 'terraclash')
    expect(landHit('kobold_1')).toBe('hit')
    expect(landHit('terraclash_1')).toBe('idle')
  })

  it('leaves the killing blow to deathPlaysHit', () => {
    const boss = spawn('terraclash_2', 'terraclash')
    boss.isDeadPending = true
    expect(landHit('terraclash_2')).toBe('hit')
  })
})
