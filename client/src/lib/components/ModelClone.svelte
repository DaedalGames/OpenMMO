<script lang="ts">
  import { T } from '@threlte/core'
  import type * as THREE from 'three'
  import { disposeObjectTree } from '../utils/disposeObjectTree'

  let { source }: { source: THREE.Object3D } = $props()

  const clone = $derived(source.clone(true))
  $effect(() => {
    const c = clone
    return () => disposeObjectTree(c)
  })
</script>

<T is={clone} dispose={false} />
