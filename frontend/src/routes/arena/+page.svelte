<script lang="ts">
	import { getArena, setArena } from '#lib/utils/arena.svelte.ts';
	import './layout.css';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';
	import PileButton from './PileButton.svelte';
	import CastButton from './CastButton.svelte';
	import PerksRack from '#lib/components/arena/PerksRack.svelte';
	import { slide } from 'svelte/transition';
	import PerksButton from './PerksButton.svelte';

	setArena();
	let arena = getArena();
</script>

<div class="bg relative flex h-dvh flex-col justify-end gap-5 overflow-hidden select-none">
	<Hand />
	<div class="contents" inert={arena.currentView === 'perks'}>
		<Slots />
		<div class="mr-10 flex w-fit gap-4 self-end lg:mr-32">
			<CastButton />
			<PerksButton />
		</div>
		<div class="my-0 flex w-dvw items-end justify-between px-20 md:my-10">
			<PileButton glyphs={Object.values(arena.drawPile)} title="Draw pile" />
			<PileButton glyphs={Object.values(arena.discardPile)} title="Discard pile" />
		</div>
	</div>
	{#if arena.currentView === 'perks'}
		<PerksRack />
	{/if}
</div>

<style>
	.bg {
		background: radial-gradient(ellipse 75% 65% at 50% 45%, #144434 0%, #0b2b20 55%, #04160f 100%);
	}
</style>
