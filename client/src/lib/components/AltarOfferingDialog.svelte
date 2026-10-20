<script lang="ts">
  import { tick } from 'svelte'
  import { t } from '../i18n'
  import { getItemDef, itemDisplayName } from '../data/itemDefs'
  import { monsterName } from '../network/altarMessages'
  import { mountOverlay } from '../stores/overlayStack'
  import type { AltarOffering } from '../stores/altarStore'

  let {
    offering,
    onConfirm,
    onCancel,
  }: {
    offering: AltarOffering
    onConfirm: (objectId: number) => void
    onCancel: () => void
  } = $props()

  let dialog = $state<HTMLDivElement>()
  const def = $derived(getItemDef(offering.offering))
  const item = $derived(itemDisplayName(offering.offering))

  $effect(() => mountOverlay('altarOffering', onCancel))
  $effect(() => {
    tick().then(() => dialog?.focus())
  })
</script>

<div class="altar-backdrop">
  <div
    class="altar-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="altar-title"
    tabindex="-1"
    bind:this={dialog}
  >
    <div class="eyebrow">{$t('altar.eyebrow')}</div>
    <div class="offering">
      {#if def}
        <img src="/items/{def.icon}" alt="" width="48" height="48" />
      {/if}
      <h2 id="altar-title">{$t('altar.title', { item })}</h2>
    </div>
    <p class="warning">{$t('altar.lost')}</p>
    <p class="wakes">
      {$t('altar.wakes', { monster: monsterName(offering.monster) })}
    </p>
    <div class="actions">
      <button class="secondary" onclick={onCancel}>{$t('altar.cancel')}</button>
      <button class="offer" onclick={() => onConfirm(offering.objectId)}
        >{$t('altar.confirm')}</button
      >
    </div>
  </div>
</div>

<style>
  .altar-backdrop {
    position: absolute;
    inset: 0;
    z-index: 45;
    display: grid;
    place-items: center;
    padding: 16px;
    box-sizing: border-box;
    background: rgba(8, 5, 4, 0.58);
    backdrop-filter: blur(2px);
  }
  .altar-dialog {
    width: min(400px, calc(100vw - 32px));
    box-sizing: border-box;
    padding: 22px;
    border: 1px solid rgba(232, 128, 52, 0.7);
    border-radius: 12px;
    outline: none;
    background:
      linear-gradient(145deg, rgba(120, 58, 20, 0.3), transparent 45%), #18130f;
    color: #f3e8d2;
    box-shadow:
      0 22px 55px rgba(0, 0, 0, 0.55),
      inset 0 1px rgba(255, 255, 255, 0.05);
    font-family: sans-serif;
  }
  .eyebrow {
    margin-bottom: 10px;
    color: #e88034;
    font:
      700 10px 'Courier New',
      monospace;
    letter-spacing: 0.18em;
  }
  .offering {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .offering img {
    flex: none;
    border: 1px solid rgba(226, 185, 59, 0.3);
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.3);
  }
  h2 {
    margin: 0;
    color: #fff4df;
    font: 700 20px/1.3 sans-serif;
  }
  .warning {
    margin: 16px 0 0;
    padding: 12px;
    border-left: 3px solid #b95749;
    border-radius: 4px;
    background: rgba(145, 55, 44, 0.16);
    color: #c9bbb0;
    font-size: 12px;
    line-height: 1.45;
  }
  .wakes {
    margin: 12px 0 0;
    color: #dbc98f;
    font-size: 12px;
    line-height: 1.5;
  }
  .actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 20px;
  }
  button {
    padding: 9px 12px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }
  button.secondary {
    border: 1px solid #675b4e;
    background: #2b251f;
    color: #ddd1bf;
  }
  button.offer {
    border: 1px solid #e88034;
    background: #8a3d14;
    color: #fff1eb;
  }
  button:hover {
    filter: brightness(1.12);
  }
</style>
