<script lang="ts">
	import GlyphCard from './GlyphCard.svelte';

	// TODO(ALI): Maybe we should move this to a config file?
	const FEEL = {
		cardWidth: 144,
		cardHeight: 216,
		cardBottom: -12,
		spacing: 62,
		curvature: 3.2,
		rotation: 3.5,
		maxFan: 12,
		scale: 1.25,
		neighborPush: 70
	};
    
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

<div class="relative h-screen overflow-hidden bg-gray-950 select-none">
	{#each glyphs as glyph, i (glyph.id)}
		<GlyphCard
			{glyph}
			pose={calculateLayout(i, glyphs.length, hoveredIndex)}
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
