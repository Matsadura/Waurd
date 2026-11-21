<script lang="ts">
	import { FEEL, getArena, setArena } from '#lib/utils/arena.svelte.ts';
	import './layout.css';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';
	import PileButton from './PileButton.svelte';
	import CastButton from './CastButton.svelte';
	import PerksRack from '#lib/components/arena/PerksRack.svelte';
	import PerksButton from './PerksButton.svelte';
	import PlayerHUD from './PlayerHUD.svelte';
	import TurnBanner from './TurnBanner.svelte';
	import GlyphsList from '#lib/components/arena/GlyphsList.svelte';

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
			<PileButton
				onclick={() => arena.setCurrentView('draw')}
				number={Object.keys(arena.drawPile).length}
				label="Show draw pile"
				type="draw"
			/>
			<!-- NOTE(ALI): This is a dirty hack to up left the slots and make them not touch the hand, do somthing better! -->
			<div
				class={['invisible cursor-pointer touch-none', FEEL.CardWidth]}
				style:aspect-ratio={FEEL.glyphAspectRatio}
			></div>

			<PileButton
				onclick={() => arena.setCurrentView('discard')}
				number={Object.keys(arena.discardPile).length}
				label="Show discard pile"
				type="discard"
			/>
		</div>
	</div>
	{#if arena.currentView === 'perks'}
		<PerksRack />
	{:else if arena.currentView === 'draw'}
		<GlyphsList title="Draw pile" glyphs={Object.values(arena.drawPile)} />
	{:else if arena.currentView === 'discard'}
		<GlyphsList title="Discard pile" glyphs={Object.values(arena.discardPile)} />
	{/if}

	<!-- debugging buttons -->
	<div class="absolute top-10 left-1/2 flex -translate-1/2 bg-red-200/20 p-4">
		<button
			onclick={() => arena.changeToNextPlayerTurn()}
			class="cursor-pointer rounded bg-green-950 px-1 py-1 text-arena-yallow-100"
			>Change turn</button
		>
	</div>
	<TurnBanner />
</div>

<style>
	.bg {
		background: radial-gradient(ellipse 75% 65% at 50% 45%, #144434 0%, #0b2b20 55%, #04160f 100%);
	}
</style>
