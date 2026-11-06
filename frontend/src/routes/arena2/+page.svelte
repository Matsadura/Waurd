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

<div class="hand fixed inset-x-0 bottom-0 z-40 h-0" style:--n={14}>
	{#each Array(14) as _, i}
		<button
			class="card absolute bottom-0 left-1/2 -ml-24 w-48 touch-none"
			style:--i={i}
			{@attach draggable((x, y) => arena.dragOver(x, y))}
		>
			<GlyphFace letter="A" />
		</button>
	{/each}
</div>

<style>
	.hand {
		--radius: 2050px;
		--max-spread: 30deg;
		--step: min(2deg, calc(var(--max-spread) / max(var(--n) - 1, 1)));
		--lift: 0px;
		--spring: cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	.card {
		/* rest pose, derived from the index */
		--offset: calc(var(--i) - (var(--n) - 1) / 2);
		--angle: calc(var(--offset) * var(--step));
		--x: calc(var(--radius) * sin(var(--angle)));
		--y: calc(var(--radius) * (1 - cos(var(--angle))) * 1.3);
		--rot: var(--angle);
		--scale: 1;
		--push: 0px;
		--lift: 0px;

		translate: calc(var(--x) + var(--push) + var(--dx, 0px))
			calc(var(--y) - var(--lift) + var(--dy, 0px));
		rotate: var(--rot);
		scale: var(--scale);
		z-index: calc(1 + var(--i));
		transform-origin: center bottom;
		--duration: 0.45s;
		transition:
			translate var(--duration) var(--spring),
			rotate var(--duration) var(--spring),
			scale var(--duration) var(--spring),
			filter 0.9s;

		/* deal-in animation, staggered by index */
		animation: deal 0.6s var(--spring) backwards;
		animation-delay: calc(var(--i) * 60ms);
	}

	/* hover: straighten, lift, grow, and push the neighbours away */
	.card:hover {
		--rot: 0deg;
		--scale: 1.3;
		--lift: 3rem;
		z-index: 50;
		filter: brightness(1.1);
	}
	.card:hover ~ .card {
		--push: 70px;
	}
	.card:has(~ .card:hover) {
		--push: -70px;
	}

	.card::after {
		content: '';
		position: absolute;
		inset: 100% 0 -5rem 0;
	}

	.card:global([data-dragging]) {
		--rot: 0deg;
		--scale: 1.2;
		--lift: 0px;
		--push: 0px;
		z-index: 99;
		transition-property: rotate, scale, filter; /* not translate */
	}
	/* neighbours stop reacting while something is being dragged */
	.hand:has(:global([data-dragging])) .card:not(:global([data-dragging])) {
		--push: 0px;
	}

	@keyframes deal {
		from {
			translate: 0 40vh;
			rotate: 0deg;
			opacity: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.card {
			transition: none;
			animation: none;
		}
	}
</style>
