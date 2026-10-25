<script lang="ts">
  import type { ComponentProps } from 'svelte'
  import MapEditorCursor from './MapEditorCursor.svelte'
  import ZoneOverlay from './ZoneOverlay.svelte'
  import RoadOverlay from './RoadOverlay.svelte'
  import NpcWaypointOverlay from './NpcWaypointOverlay.svelte'

  let props: ComponentProps<typeof MapEditorCursor> = $props()
</script>

<MapEditorCursor {...props} />
<ZoneOverlay />
<RoadOverlay />
<NpcWaypointOverlay />
