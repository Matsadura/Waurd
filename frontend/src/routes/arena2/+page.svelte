<script lang="ts">
	import { getArena, setArena } from '#lib/utils/arena.svelte.ts';
	import './layout.css';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';
	import PileButton from './PileButton.svelte';
	import CastButton from './CastButton.svelte';

	setArena();
</script>

<div class="relative flex h-dvh flex-col justify-end gap-5 overflow-hidden bg-gray-950 select-none">
	<Hand />
	<Slots />
	<div class="mr-10 w-fit self-end lg:mr-32">
		<CastButton />
	</div>
	<div class="my-0 flex w-dvw items-end justify-between px-20 md:my-10">
		<PileButton glyphs={Object.values(getArena().drawPile)} title="Draw pile" />
		<PileButton glyphs={Object.values(getArena().discardPile)} title="Discard pile" />
	</div>
</div>

