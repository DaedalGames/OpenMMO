<script lang="ts" generics="Module">
  import type { Snippet } from 'svelte'
  import { t } from '../i18n'

  let {
    load,
    children,
  }: {
    load: () => Promise<Module>
    children: Snippet<[Module]>
  } = $props()

  let attempt = $state(0)
  const pending = $derived.by(() => {
    void attempt
    return load()
  })
</script>

{#await pending then module}
  {@render children(module)}
{:catch}
  <div class="load-error" role="alert">
    <span>{$t('loading.failed')}</span>
    <button onclick={() => attempt++}>{$t('loading.retry')}</button>
  </div>
{/await}

<style>
  .load-error {
    position: absolute;
    inset: 16px auto auto 16px;
    z-index: 100;
    padding: 12px;
    background: #222;
    color: #fff;
    border-radius: 6px;
  }

  button {
    margin-left: 12px;
  }
</style>
