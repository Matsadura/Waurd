<script lang="ts">
	import { FEEL, getArena, setArena } from '#lib/utils/arena.svelte.ts';
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

<div
	class="bg relative flex h-dvh flex-col justify-end gap-10 overflow-hidden select-none md:gap-0"
>
	<Hand />
	<div class="contents" inert={arena.currentView === 'perks'}>
		<Slots />
		<div class="mt-4 mr-10 flex w-fit gap-4 self-end lg:mr-32">
			<CastButton />
			<PerksButton />
		</div>

		<div class="flex w-dvw items-end justify-between px-8 md:pb-5">
			<PileButton glyphs={Object.values(arena.drawPile)} title="Draw pile" />
			<!-- NOTE(ALI): This is a dirty hack to up left the slots and make them not touch the hand, do somthing better! -->
			<div
				class={['invisible cursor-pointer touch-none', FEEL.CardWidth]}
				style:aspect-ratio={FEEL.glyphAspectRatio}
			></div>
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
