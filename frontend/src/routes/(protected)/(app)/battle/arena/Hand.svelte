<script lang="ts">
	import { FEEL, getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
	const arena = getArena();
</script>

<div class="hand fixed inset-x-0 bottom-0 z-40 flex" style:--n={arena.hand.length}>
	{#each arena.hand as glyphId, i (glyphId)}
		<button
			class={[
				'card absolute bottom-0 left-1/2 ml-[-6%] cursor-pointer touch-none hover:shadow-2xl hover:shadow-amber-200/20',
				FEEL.CardWidth
			]}
			style:--i={i}
			{@attach draggable(
				(x, y) => arena.dragOver(x, y),
				() => arena.drop(glyphId),
				() => arena.toggle(glyphId)
			)}
		>
			<div class="pulse">
				<GlyphFace letter={arena.glyph(glyphId)?.letter} />
			</div>
		</button>
	{/each}
</div>

<style>
	.hand {
		--radius: 1000%;
		--max-spread: 30deg;
		--step: min(2deg, calc(var(--max-spread) / max(var(--n) - 1, 1)));

		--easing: cubic-bezier(0.2, 0.8, 0.2, 1);
		--animation-duration: 900ms;
		--animation-delay: 50ms;
		--z-index-delay: 300ms;
	}

	.card {
		--offset: calc(var(--i) - (var(--n) - 1) / 2);
		--angle: calc(var(--offset) * var(--step));

		--x: calc(var(--radius) * sin(var(--angle)));
		--y: calc(var(--radius) * (1 - cos(var(--angle))) * 1.3);

		--push: 0px;
		--lift: 0px;
		--dx: 0px;
		--dy: 0px;

		translate: calc(var(--x) + var(--push) + var(--dx)) calc(var(--y) - var(--lift) + var(--dy));

		z-index: calc(1 + var(--i));

		transition:
			translate var(--animation-duration) var(--easing) var(--animation-delay),
			scale var(--animation-duration) var(--easing) var(--animation-delay);
	}

	.card:hover {
		--lift: calc(1.1rem * abs(var(--offset)));

		z-index: 50;
		scale: 1.2;

		transition:
			z-index 0s var(--z-index-delay),
			translate var(--animation-duration) var(--easing) var(--animation-delay),
			scale var(--animation-duration) var(--easing) var(--animation-delay);
	}

	.card:hover ~ .card {
		--push: 60%;
	}

	.card:has(~ .card:hover) {
		--push: -10%;
	}

	.card::after {
		content: '';
		position: absolute;
		inset: 100% 0 -5rem;
	}

	.card:first-child::after {
		width: 100%;
		height: 100%;
		top: 0;
		left: -30%;
	}

	.card:last-child::after {
		width: 100%;
		height: 100%;
		top: 0;
		left: 30%;
	}

	.card:global([data-dragging]) {
		--lift: 0px;
		--push: 0px;

		z-index: 99;
		scale: 1;
		transition: none;
		--animation-delay: none;
	}

	.hand:has(:global([data-dragging])) .card:not(:global([data-dragging])) {
		--push: 0px;
	}
</style>
