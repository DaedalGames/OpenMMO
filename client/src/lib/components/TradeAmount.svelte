<script lang="ts">
  import { locale } from '../i18n'
  import { displayName, getItemDef } from '../data/itemDefs'
  import GoldAmount from './GoldAmount.svelte'

  let { amount, currencyItem }: { amount: number; currencyItem?: string } =
    $props()
  const currency = $derived(currencyItem ? getItemDef(currencyItem) : undefined)
</script>

{#if currency}
  <span class="currency-amount" title={displayName(currency, 0, $locale)}>
    <img src="/items/{currency.icon}" alt={displayName(currency, 0, $locale)} />
    {amount.toLocaleString($locale)}
  </span>
{:else}
  <GoldAmount copper={amount} />
{/if}

<style>
  .currency-amount {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }
  img {
    width: 20px;
    height: 20px;
    object-fit: contain;
  }
</style>
