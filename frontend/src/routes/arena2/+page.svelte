<script lang="ts">
	import { getArena, setArena } from '#lib/utils/arena.svelte.ts';
	import './layout.css';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';
	import DrawPileButton from './DrawPileButton.svelte';
	import DiscardPileButton from './DiscardPileButton.svelte';
	setArena();
</script>

<div class="relative h-dvh overflow-hidden bg-gray-950 select-none">
	<Slots />
	<Hand />
	<DrawPileButton />
	<DiscardPileButton />
</div>
