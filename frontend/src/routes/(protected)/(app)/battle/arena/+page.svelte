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

	let { data } = $props();

	setArena(() => data.ticket.matched_match_id);
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
				number={arena.drawPile.length}
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
				number={arena.discardPile.length}
				label="Show discard pile"
				type="discard"
			/>
		</div>
	</div>
	{#if arena.currentView === 'perks'}
		<PerksRack />
	{:else if arena.currentView === 'draw'}
		<GlyphsList title="Draw pile" glyphs={arena.drawPile} />
	{:else if arena.currentView === 'discard'}
		<GlyphsList title="Discard pile" glyphs={arena.discardPile} />
	{/if}

	<!-- debugging buttons -->
	<!-- <div class="absolute top-10 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2">
		<div class="flex gap-2 bg-red-200/20 p-2">
			<button
				onclick={() => arena.changeToNextPlayerTurn()}
				class="cursor-pointer rounded bg-green-950 px-2 py-1 text-arena-yallow-100"
				>Change turn</button
			>
		</div>
	</div> -->
	<TurnBanner />
	<pre
		class="absolute inset-0 max-h-[60%] w-full overflow-auto rounded border border-white/20 bg-black/80 p-3 text-left text-xs text-green-200 select-text">{JSON.stringify(
			{
				battleId: data.ticket.matched_match_id,
				status: arena.battle?.status,
				error: arena.battle?.error,
				aborted: arena.battle?.aborted,
				opponentGraceSeconds: arena.battle?.opponentGraceSeconds,
				state: arena.battle?.state
			},
			null,
			2
		)}</pre>
</div>

<style>
	.bg {
		background: radial-gradient(ellipse 75% 65% at 50% 45%, #144434 0%, #0b2b20 55%, #04160f 100%);
	}
</style>
