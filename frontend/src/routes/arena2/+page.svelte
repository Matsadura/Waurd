<!-- GlyphCard.svelte -->
<script lang="ts">
	import { FEEL, getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	setArena();
	const glyph = { letter: 'a' };
	const arena = getArena();
</script>

<div class="absolute inset-x-0 top-1/3 flex items-start justify-center gap-2 px-4">
	{#each Array(arena.slotCount) as _, i}
		<div
			{@attach arena.slot(i)}
			style:aspect-ratio={FEEL.glyphAspectRatio}
			class={[
				'w-36 rounded border border-dashed border-amber-800 transition-colors duration-150',
				arena.overSlot === i ? 'bg-red-500' : ''
			]}
		></div>
	{/each}
</div>

<div class="hand fixed inset-x-0 bottom-0 z-40 flex" style:--n={14}>
	{#each Array(14) as _, i}
		<button
			class="card absolute bottom-0 left-1/2 -ml-24 w-48 touch-none"
			style:--i={i}
			{@attach draggable((x, y) => arena.dragOver(x, y))}
		>
			<div class="card__entry">
				<div class="card__visual">
					<GlyphFace letter="B" />
				</div>
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

		transition: translate 480ms var(--easing);
	}

	.card__entry {
		width: 100%;

		animation: deal 380ms var(--easing) both;
		animation-delay: calc(var(--i) * 60ms);
	}

	.card__visual {
		--rot: var(--angle);
		--scale: 1;

		width: 100%;
		transform-origin: center bottom;

		rotate: var(--rot);
		scale: var(--scale);
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

	@keyframes deal {
		from {
			translate: 0 56px;
			opacity: 0;
		}

		to {
			translate: 0 0;
			opacity: 1;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.card,
		.card__visual {
			transition: none;
		}

		.card__entry {
			animation: none;
		}
	}
</style>
