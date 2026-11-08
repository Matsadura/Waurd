<script lang="ts">
	import { Arena, getArena, setArena } from '#lib/utils/arena.svelte.ts';
	import './layout.css';
	import drawDeckImg from '#lib/assets/arena/draw-deck.png';

	import Slots from './Slots.svelte';
	import Hand from './Hand.svelte';
	import GlyphsList from '#lib/components/arena/GlyphsList.svelte';
	let showDrawPile = $state(false);
	let showDiscardPile = $state(false);
	setArena();
</script>

<div class="relative h-dvh overflow-hidden bg-gray-950 select-none">
	<Slots />
	<Hand />

	<button
		class="draw-button absolute bottom-16 left-16 w-32 cursor-pointer transition-[scale] duration-500 hover:scale-110"
		onclick={() => (showDrawPile = !showDrawPile)}
		style:z-index={showDrawPile ? '99' : 'auto'}
	>
		<p class="tooltip font-kreon text-green-900">{showDrawPile ? 'Hide' : 'Show'} draw pile</p>
		<img alt="draw pile icon" src={drawDeckImg} />
		<p
			class="absolute right-0 bottom-4 flex aspect-square w-10 items-center justify-center rounded-full border-2 border-green-900 bg-arena-yallow-100 font-kreon text-xl text-green-900"
		>
			{Object.values(getArena().draw_pile).length}
		</p>
	</button>

	<GlyphsList
		show={showDrawPile}
		title={'You draw pile'}
		glyphs={Object.values(getArena().draw_pile)}
	/>
</div>

<style>
	.draw-button {
		animation: bubble-anim 2s ease-out infinite;
	}
	.draw-button .tooltip {
		opacity: 0;
		transform: translateY(10px);
		transform-origin: 50% 100%;
		transition:
			opacity 0.3s ease-in-out,
			transform 0.3s ease-in-out;
		transition-timing-function: cubic-bezier(1, -0.4, 0.35, 0.95);
	}

	.draw-button:hover .tooltip {
		opacity: 1;
		transform: translateY(0px);
	}

	.tooltip {
		max-width: 28ch;
		text-align: center;
		margin-bottom: 15px;
		line-height: 1;
	}

	.tooltip {
		--b: 2em; /* base */
		--h: 1em; /* height */

		--p: 50%; /* triangle position (0%:left 100%:right) */
		--r: 1.2em; /* the radius */
		--c: var(--color-arena-yallow-100);

		padding: 1em;
		border-radius: var(--r) var(--r) min(var(--r), 100% - var(--p) - var(--b) / 2)
			min(var(--r), var(--p) - var(--b) / 2) / var(--r);
		clip-path: polygon(
			0 100%,
			0 0,
			100% 0,
			100% 100%,
			min(100%, var(--p) + var(--b) / 2) 100%,
			var(--p) calc(100% + var(--h)),
			max(0%, var(--p) - var(--b) / 2) 100%
		);
		background: var(--c);
		border-image: conic-gradient(var(--c) 0 0) fill 0 / var(--r)
			calc(100% - var(--p) - var(--b) / 2) 0 calc(var(--p) - var(--b) / 2) / 0 0 var(--h) 0;
	}
</style>
