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
	import PlayerHUD from './PlayerHUD.svelte';

	setArena();
	let arena = getArena();
</script>

<div
	class="bg relative flex h-dvh flex-col justify-end gap-10 overflow-hidden select-none md:gap-0"
>
	<Hand />
	<div class="contents" inert={arena.currentView === 'perks'}>
		<div
			class="mt-4 mb-auto flex flex-col items-stretch gap-2 px-3 md:flex-row md:items-start md:justify-between md:px-10"
		>
			<PlayerHUD player={arena.me} side="right" isTurn={arena.turn === 'me'} />
			<PlayerHUD player={arena.opponent} side="left" isTurn={arena.turn === 'opponent'} />
		</div>
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

	<div class="absolute top-10 left-1/2 flex -translate-1/2 bg-red-200/20 p-4">
		<button onclick={() => arena.changeToNextPlayerTurn()} class="bg-green-950 text-arena-yallow-100 py-1 px-1 rounded cursor-pointer">Change turn</button>
	</div>
</div>

<style>
	.bg {
		background: radial-gradient(ellipse 75% 65% at 50% 45%, #144434 0%, #0b2b20 55%, #04160f 100%);
	}
</style>
