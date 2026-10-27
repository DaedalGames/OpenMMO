<script lang="ts">
  import HistoryChart from './HistoryChart.svelte'
  import MetricsError from './MetricsError.svelte'
  import PeriodFilter from './PeriodFilter.svelte'
  import type { MetricsResource } from './metricsResource.svelte'
  import { formatCount, formatDateTime, linePath, type ChartMarker } from './metrics'
  import { bandPlayers, dungeonPopulationPeriods, seriesFor, type DungeonPopulation, type DungeonPopulationHours } from './dungeonPopulation'

  let { hours = $bindable<DungeonPopulationHours>(24), resource, markers = [] }: { hours?: DungeonPopulationHours; resource: MetricsResource<DungeonPopulation>; markers?: ChartMarker[] } = $props()
  let { history, loading, refreshing, error, refresh } = $derived(resource)
  let period = $derived(dungeonPopulationPeriods.find((period) => period.hours === hours)!)
  let selected = $state('all')
  let dungeon = $derived(history?.dungeons.find((dungeon) => dungeon.id === selected))
  let columns = $derived(history ? Array.from({ length: Math.ceil(Math.max(0, ...history.dungeons.map((dungeon) => dungeon.floors)) / history.band_floors) }, (_, index) => index * history!.band_floors + 1) : [])
  let series = $derived(history ? seriesFor(history, dungeon) : [])
  let peak = $derived(history?.samples.length && series.length ? Math.max(...history.samples.map((sample) => Math.max(...series.map((line) => line.value(sample))))) : null)
</script>

<section class="chart-panel" aria-labelledby="dungeon-population-title" aria-busy={loading}>
  <div class="chart-heading">
    <div>
      <h2 id="dungeon-population-title">던전 층별 인원</h2>
      <p>던전마다 {history?.band_floors ?? 5}층 단위로 묶은 플레이어 수 · 공식 NPC 제외</p>
    </div>
    <PeriodFilter bind:hours options={dungeonPopulationPeriods} label="던전 인원 조회 기간" />
  </div>
  <MetricsError {error} until={history?.until} {refreshing} {refresh} />
  {#if history}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="table-scroll" tabindex="0" role="region" aria-label="던전 층별 현재 인원 표">
      <table>
        <caption>현재 인원 · {formatDateTime(history.until)} KST</caption>
        <thead>
          <tr>
            <th scope="col">던전</th>
            {#each columns as band (band)}
              <th scope="col" class="num">{band}–{band + history.band_floors - 1}층</th>
            {/each}
            <th scope="col" class="num">합계</th>
          </tr>
        </thead>
        <tbody>
          {#each history.dungeons as entry (entry.id)}
            <tr>
              <th scope="row" class="name">{entry.name}</th>
              {#each columns as band (band)}
                {@const players = bandPlayers(history.current, entry.id, band)}
                <td class="num" class:empty={band > entry.floors} class:busy={players > 0}>{band > entry.floors ? '' : formatCount(players)}</td>
              {/each}
              <td class="num strong">{formatCount(bandPlayers(history.current, entry.id))}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="chart-meta">
      <label>추이 <select bind:value={selected} aria-label="던전 인원 그래프 대상">
        <option value="all">던전별 합계</option>
        {#each history.dungeons as entry (entry.id)}<option value={entry.id}>{entry.name} 층별</option>{/each}
      </select></label>
      <span>{period.intervalLabel}</span>
    </div>
    {#if history.samples.length && series.length}
      {#key selected}
        <HistoryChart {history} {peak} value={series[0].value} {markers} legend={dungeon ? `${dungeon.name} 층별 인원` : '던전별 인원'} legendLabel={series[0].label} valueLabel={series[0].label} unit="명" peakLabel="기간 최고">
          {#snippet layers(segment, x, y)}
            {#each series.slice(1) as line (line.label)}
              {#if segment.length > 1}
                <path d={linePath(segment, line.value, x, y)} fill="none" stroke={line.color} stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
              {:else}
                <circle cx={x(segment[0].timestamp)} cy={y(line.value(segment[0]))} r="3.5" fill={line.color} />
              {/if}
            {/each}
          {/snippet}
          {#snippet detail(sample)}
            {#each series.slice(1) as line (line.label)}<span>{line.label} {formatCount(line.value(sample))}명</span>{/each}
          {/snippet}
          {#snippet legends()}
            {#each series.slice(1) as line (line.label)}<span class="legend"><i style:background={line.color}></i>{line.label}</span>{/each}
          {/snippet}
        </HistoryChart>
      {/key}
    {:else}
      <div class="chart-empty" role="status"><strong>이 기간에 수집된 기록이 없어요</strong><p>새 기록은 1분마다 쌓입니다.</p></div>
    {/if}
  {:else}
    <div class="chart-empty" role="status">
      <strong>{loading ? '던전 인원 기록을 불러오고 있어요' : '던전 인원 기록에 연결할 수 없어요'}</strong>
      <p>{loading ? '잠시만 기다려 주세요.' : '연결이 복구되면 자동으로 갱신됩니다.'}</p>
    </div>
  {/if}
  <div class="chart-footer">
    <span>{history ? `${formatDateTime(history.from)} — ${formatDateTime(history.until)}` : `최근 ${period.label}`} <span class="timezone">KST</span></span>
    <span>1분 갱신</span>
  </div>
</section>

<style>
  .table-scroll { overflow: auto; margin: 18px 0; }
  table { width: 100%; min-width: 560px; border-collapse: collapse; font-size: 13px; }
  caption { padding-bottom: 8px; color: #74857d; font-size: 11px; text-align: left; }
  th, td { padding: 11px 12px; border-bottom: 1px solid #edf1ee; text-align: left; }
  thead th { background: #f6f8f7; color: #74857d; font-size: 11px; font-weight: 500; white-space: nowrap; }
  tbody tr:last-child > * { border-bottom: 0; }
  .name { font-weight: 500; overflow-wrap: anywhere; }
  .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .strong { font-weight: 600; }
  .busy { color: #166d5e; font-weight: 600; }
  .empty { background: #fafbfa; }
  select { margin-left: 8px; background: white; border: 1px solid #dde5e0; border-radius: 6px; padding: 4px; color: inherit; }
  .chart-empty { min-height: 150px; }
</style>
