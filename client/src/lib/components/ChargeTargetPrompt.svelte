<script lang="ts">
  import SkillTargetHint from './SkillTargetHint.svelte'
  import {
    VALHALLA_CHARGE,
    abilityEquipmentAllowed,
    isAbilityAvailable,
  } from '../data/abilities'
  import {
    cancelChargeTargeting,
    chargeTargeting,
  } from '../stores/chargeStrikeStore'
  import { gameStore } from '../stores/gameStore'
  import { inventoryStore } from '../stores/inventoryStore'
  import { mountOverlay } from '../stores/overlayStack'
  import { t } from '../i18n'
  import { isMounted } from '../utils/mounts'

  $effect(() => {
    if (!$chargeTargeting) return
    const player = $gameStore.currentPlayer
    if (
      !player ||
      !$gameStore.isConnected ||
      player.health <= 0 ||
      isMounted(player) ||
      !isAbilityAvailable(VALHALLA_CHARGE.id, player.characterClass) ||
      !abilityEquipmentAllowed(VALHALLA_CHARGE.id, $inventoryStore.equipped)
    )
      cancelChargeTargeting()
  })

  $effect(() => {
    if ($chargeTargeting)
      return mountOverlay('chargeTarget', cancelChargeTargeting)
  })
</script>

{#if $chargeTargeting}
  <SkillTargetHint
    icon={VALHALLA_CHARGE.icon}
    message={$t('ability.valhalla_charge.targetHint')}
    onCancel={cancelChargeTargeting}
  />
{/if}
