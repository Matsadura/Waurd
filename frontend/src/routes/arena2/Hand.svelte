<script lang="ts">
	import { getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
	const arena = getArena();
</script>

<div class="hand fixed inset-x-0 bottom-0 z-40 flex" style:--n={arena.hand.length}>
	{#each arena.hand as glyphId, i (glyphId)}
		<button
			class="card absolute bottom-0 left-1/2 -ml-24 w-48 touch-none hover:shadow-2xl hover:shadow-amber-200/20"
			style:--i={i}
			{@attach draggable(
				(x, y) => arena.dragOver(x, y),
				() => arena.drop(glyphId),
				() => arena.toggle(glyphId)
			)}
		>
			<div class="card__visual">
				<GlyphFace letter={arena.glyph(glyphId)?.letter} />
			</div>
		</button>
	{/each}
</div>

<style>
	.hand {
		--radius: 2050px;
		--max-spread: 30deg;
		--step: min(2deg, calc(var(--max-spread) / max(var(--n) - 1, 1)));

		--easing: cubic-bezier(0.2, 0.8, 0.2, 1);
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

		transition: translate 900ms var(--easing);
		/* width: 100%;

		
		/**
		 * Animation source: https://easingwizard.com/
		 */
		animation-timing-function: ease-in-out;
	}

	.card__visual {
		--rot: var(--angle);
		--scale: 1;

		width: 100%;
		transform-origin: center bottom;

		rotate: var(--rot);
		scale: var(--scale);
		animation: flash 600ms ease-in-out both;
		animation-delay: calc(var(--i) * 40ms);
	}

	.card:hover {
		--lift: calc(1rem * abs(var(--offset)));
		z-index: 50;
		scale: 1.2;
	}

	.card:hover .card__visual {
		--rot: 0deg;
		--scale: 1.12;
	}

	.card:hover ~ .card {
		--push: 9rem;
	}

	.card:has(~ .card:hover) {
		--push: -4rem;
	}

	.card::after {
		content: '';
		position: absolute;
		inset: 100% 0 -5rem;
	}

	.card:global([data-dragging]) {
		--lift: 0px;
		--push: 0px;

		transition: none;
		z-index: 99;
		scale: 1;
	}

	.card:global([data-dragging]) .card__visual {
		--rot: 0deg;
		--scale: 1.08;

		transition: none;
	}

	.hand:has(:global([data-dragging])) .card:not(:global([data-dragging])) {
		--push: 0px;
	}

	.card:first-child::after {
		content: '';
		width: 100%;
		height: 100%;
		top: 0;
		left: -30%;
		/* background-color: red !important; */
	}
	.card:last-child::after {
		content: '';
		width: 100%;
		height: 100%;
		top: 0;
		left: 30%;
		/* background-color: red !important; */
	}

	@keyframes flash {
		from {
			filter: brightness(1);
			box-shadow: 0 0 5px 15px rgba(206, 204, 76, 0.6);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.card,
		.card__visual {
			transition: none;
			animation: none;
		}
	}
</style>
