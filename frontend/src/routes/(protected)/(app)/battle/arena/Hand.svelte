<script lang="ts">
	import { FEEL, getArena } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';

	const arena = getArena();

	let inspected = $state<number | null>(null);
	let inspectTimer: ReturnType<typeof setTimeout> | undefined;

	function inspect(event: MouseEvent, position: number) {
		event.preventDefault();
		clearTimeout(inspectTimer);
		inspected = position;
		inspectTimer = setTimeout(() => {
			inspected = null;
		}, 2000);
	}

	$effect(() => {
		return () => {
			clearTimeout(inspectTimer);
		};
	});
</script>

<div class="hand fixed inset-x-0 bottom-0 z-40 flex" style:--n={arena.hand.length}>
	{#each arena.hand as glyph, i (glyph.position)}
		<button
			class={['card absolute bottom-0 left-1/2 ml-[-6%] cursor-pointer touch-none', FEEL.CardWidth]}
			style:--i={i}
			data-inspected={inspected === glyph.position ? '' : undefined}
			oncontextmenu={(event) => inspect(event, glyph.position)}
			{@attach draggable(
				(x, y) => arena.dragOver(x, y),
				() => arena.drop(glyph.position),
				() => arena.toggle(glyph.position)
			)}
		>
			<div class="pulse">
				<GlyphFace {glyph} />
			</div>
		</button>
	{/each}
	{#if arena.turn === 'opponent'}
		<Notice variant="info" class="absolute bottom-10 left-1/2 -translate-x-1/2 text-center"
			>Patience, my lord. Your glyphs will arrive when your turn comes.</Notice
		>
	{/if}
</div>

<style>
	.hand {
		--radius: 1000%;
		--max-spread: 30deg;
		--step: min(2deg, calc(var(--max-spread) / max(var(--n) - 1, 1)));

		--easing: cubic-bezier(0.2, 0.8, 0.2, 1);
		--animation-duration: 350ms;
		--animation-delay: 0ms;
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

	.card[data-inspected] {
		--lift: calc(1.1rem * abs(var(--offset)));

		z-index: 50;
		scale: 1.2;
		box-shadow: 0 25px 50px -12px rgb(253 230 138 / 20%);
	}

	.card[data-inspected] ~ .card {
		--push: 60%;
	}

	.card:has(~ .card[data-inspected]) {
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
