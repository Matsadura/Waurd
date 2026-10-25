<script lang="ts">
	import GlyphCard from './GlyphCard.svelte';
	import { FEEL } from '#lib/configs/arenaFeel.ts';

	const SLOT_COUNT = 8;

	const glyphs = 'ALIJBAEIISMYN'.split('').map((c, i) => {
		return {
			id: `id-${i}`,
			letter: c
		};
	});

	type Pose = {
		x: number;
		y: number;
		rotation: number;
		scale: number;
		zIndex: number;
	};

	let slotEls: HTMLElement[] = $state([]);
	let targetSlot = $state<number | null>(null);
	const TARGET_RADIUS = 0.9;

	function updateTargetSlot(x: number, y: number) {
		let best: number | null = null;
		let bestDist = Infinity;

		for (let i = 0; i < SLOT_COUNT; i++) {
			const slotEl = slotEls[i];
			if (slotEl) {
				const r = slotEl.getBoundingClientRect();
				// TODO(ALI): Mybe we should just compare it squared without the hypot to avoid sqrt?
				const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
				const rect = slotEl.getBoundingClientRect();
				if (d < r.height * TARGET_RADIUS && d < bestDist) {
					best = i;
					bestDist = d;
				}
			}
		}
		targetSlot = best;
	}

	function calculateLayout(i: number, n: number, focusIdx: number): Pose {
		const outer = (n - 1) / 2;
		const offset = i - outer;

		const step = FEEL.spacing;
		const angle = Math.min(FEEL.rotation, FEEL.maxFan / Math.max(outer, 1));

		const rest: Pose = {
			x: offset * step,
			y: -FEEL.cardBottom + offset * offset * FEEL.curvature,
			rotation: offset * angle,
			scale: 1,
			zIndex: 1 + i
		};

		if (i === focusIdx) {
			return {
				...rest,
				rotation: 0,
				y: 0,
				x: rest.x + 5 * offset,
				scale: FEEL.scale,
				zIndex: 50
			};
		}

		if (focusIdx === -1) {
			return rest;
		}

		const side = i < focusIdx ? -1 : 1;
		return {
			...rest,
			x: rest.x + side * FEEL.neighborPush
		};
	}
	let hoveredId = $state<string | null>(null);
	let hoveredIndex = $derived(glyphs.findIndex((g) => g.id === hoveredId));
</script>

<div class="relative h-dvh overflow-hidden bg-gray-950 select-none">
	<div class="absolute inset-x-0 top-1/3 flex items-start justify-center gap-2 px-4">
		{#each Array(SLOT_COUNT) as _, i}
			<div
				bind:this={slotEls[i]}
				style:aspect-ratio={FEEL.glyphAspectRatio}
				class={[
					'w-36 rounded-2xl border border-dashed border-amber-800 transition-colors duration-150',
					targetSlot === i ? 'border-amber-100' : 'border-gray-600'
				]}
			></div>
		{/each}
	</div>

	<p class="absolute top-2 left-3 text-2xl text-gray-500">Target: {targetSlot ?? 'none'}</p>

	{#each glyphs as glyph, i (glyph.id)}
		<GlyphCard
			{glyph}
			pose={calculateLayout(i, glyphs.length, hoveredIndex)}
			onDrag={updateTargetSlot}
			onDragEnd={() => (targetSlot = null)}
			onHover={(hovered) => {
				if (hovered) {
					hoveredId = glyph.id;
				} else if (hoveredId === glyph.id) {
					hoveredId = null;
				}
			}}
		/>
	{/each}
</div>
