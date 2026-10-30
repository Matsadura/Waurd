<script lang="ts">
	import GlyphCardHand from './GlyphCardHand.svelte';
	import GlyphCardSlot from './GlyphCardSlot.svelte';
	import { FEEL } from '#lib/configs/arenaFeel.ts';

	const SLOT_COUNT = 8;
	type Glyph = { id: string; letter: string };

	let glyphs_by_id = $state<Record<string, Glyph>>(
		Object.fromEntries(
			'ALIJBAEIISM1'.split('').map((letter, i) => {
				const id = `g${i}`;
				return [id, { id, letter }];
			})
		)
	);

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

	let slot_ids = $state<(string | null)[]>(Array(SLOT_COUNT).fill(null));
	let hand_ids = $derived(Object.keys(glyphs_by_id).filter((key) => !slot_ids.includes(key)));
	let hand_hovered_id = $state<string | null>(null);

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

	const FAN = {
		radius: 2050,
		anglePerCard: 2,
		maxSpread: 30
	};

	function calculateLayout(glyphId: string): Pose {
		const count = hand_ids.length;
		const index = hand_ids.indexOf(glyphId);
		const offset = index - (count - 1) / 2;
		const hoveredIndex = hand_hovered_id ? hand_ids.indexOf(hand_hovered_id) : -1;
		const stepAngle = Math.min(FAN.anglePerCard, FAN.maxSpread / Math.max(count - 1, 1));
		const angle = offset * stepAngle;
		const rad = (angle * Math.PI) / 180;

		const rest: Pose = {
			x: FAN.radius * Math.sin(rad),
			y: FAN.radius * (1 - Math.cos(rad)) * 1.3,
			rotation: angle,
			scale: 1,
			zIndex: 1 + index
		};

		if (glyphId === hand_hovered_id) {
			return { ...rest, rotation: 0, y: 0, x: rest.x + 1 * offset, scale: FEEL.scale, zIndex: 50 };
		}
		if (hand_hovered_id === null) return rest;

		const side = index < hoveredIndex ? -1 : 1;
		return { ...rest, x: rest.x + side * FEEL.neighborPush };
	}

	function moveToSlot(id: string, index: number) {
		if (!glyphs_by_id[id] || index < 0 || index >= SLOT_COUNT) return;
		if (slot_ids[index] !== null && slot_ids[index] !== id) return;
		slot_ids = slot_ids.map((value) => (value === id ? null : value));
		slot_ids[index] = id;
		hand_hovered_id = null;
	}

	function toggleGlyph(id: string) {
		if (slot_ids.includes(id)) {
			const index = slot_ids.indexOf(id);
			slot_ids[index] = null;
		} else {
			const empty = slot_ids.indexOf(null);
			moveToSlot(id, empty);
		}
	}
</script>

<div class="relative h-dvh overflow-hidden bg-gray-950 select-none">
	<div class="absolute inset-x-0 top-1/3 flex items-start justify-center gap-2 px-4">
		{#each slot_ids as glyphId, i}
			<div
				bind:this={slotEls[i]}
				style:aspect-ratio={FEEL.glyphAspectRatio}
				class={[
					'w-36 rounded border border-dashed border-amber-800 transition-colors duration-150',
					targetSlot === i ? 'border-amber-100' : 'border-gray-600'
				]}
			>
				{#if glyphId}
					<GlyphCardSlot
						glyph={glyphs_by_id[glyphId]}
						onDrag={updateTargetSlot}
						onDragEnd={() => (targetSlot = null)}
						onClickHandler={() => toggleGlyph(glyphId)}
					/>
				{/if}
			</div>
		{/each}
	</div>

	<p class="absolute top-2 left-3 text-2xl text-gray-500">Target: {targetSlot ?? 'none'}</p>

	{#each hand_ids as glyphId, i (glyphId)}
		<GlyphCardHand
			glyph={glyphs_by_id[glyphId]}
			pose={calculateLayout(glyphId)}
			onDrag={updateTargetSlot}
			onDragEnd={() => (targetSlot = null)}
			onClickHandler={() => toggleGlyph(glyphId)}
			onHover={(hovered) => (hand_hovered_id = hovered ? glyphId : null)}
		/>
	{/each}
</div>
