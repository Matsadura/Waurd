<script lang="ts">
	import { setArena } from '#lib/utils/arena.svelte.ts';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';

	setArena();
</script>

<div class="relative h-dvh overflow-hidden bg-gray-950 select-none">
	<Slots />
	<Hand />
</div>
