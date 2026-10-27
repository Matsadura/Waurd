<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { Spring, prefersReducedMotion } from 'svelte/motion';

	type Glyph = { id: string; letter: string };
	type Size = { width: number; height: number };
	type Pose = { x: number; y: number; rotation: number; scale: number };
	type Drag = {
		glyph_id: string;
		pointer_id: number;
		start_x: number;
		start_y: number;
		x: number;
		y: number;
		grab_x: number;
		grab_y: number;
		pose: Pose;
		active: boolean;
	};

	const SLOT_COUNT = 8;
	const FEEL = {
		drag_threshold: 6,
		slot_tolerance: 12,
		spacing: 0.48, // Fraction of measured card width.
		fan_angle: 15,
		curvature: 0.12, // Fraction of measured card height.
		hover_lift: 0.14,
		neighbor_push: 0.12,
		stiffness: 0.18,
		damping: 0.7
	};

	// 1. Game data and placement. No animation state belongs here.
	let glyphs_by_id = $state<Record<string, Glyph>>(
		Object.fromEntries(
			'ALIJBAEIISMYN'.split('').map((letter, i) => {
				const id = `g${i}`;
				return [id, { id, letter }];
			})
		)
	);
	let hand_ids = $state<string[]>(Object.keys(glyphs_by_id));
	let slot_ids = $state<(string | null)[]>(Array(SLOT_COUNT).fill(null));
	let hand_hovered_id = $state<string | null>(null);
	let drag = $state<Drag | null>(null);
	let target_slot = $state<number | null>(null);

	// Stable rendering order; moving a card never recreates its DOM node.
	let rendered_ids = $derived(
		Object.keys(glyphs_by_id).filter((id) => hand_ids.includes(id) || slot_ids.includes(id))
	);

	function moveToSlot(id: string, index: number) {
		if (!glyphs_by_id[id] || index < 0 || index >= SLOT_COUNT) return;
		if (slot_ids[index] !== null && slot_ids[index] !== id) return;
		hand_ids = hand_ids.filter((value) => value !== id);
		slot_ids = slot_ids.map((value) => (value === id ? null : value));
		slot_ids[index] = id;
		hand_hovered_id = null;
	}

	function moveToHand(id: string) {
		if (!glyphs_by_id[id]) return;
		slot_ids = slot_ids.map((value) => (value === id ? null : value));
		if (!hand_ids.includes(id)) hand_ids = [...hand_ids, id];
		hand_hovered_id = null;
	}

	function toggleGlyph(id: string) {
		if (drag) return;
		if (slot_ids.includes(id)) moveToHand(id);
		else {
			const empty = slot_ids.indexOf(null);
			if (empty !== -1) moveToSlot(id, empty);
		}
	}

	// 2. Measured layout. All positions below use viewport coordinates.
	let arena_el: HTMLDivElement;
	let hand_el: HTMLDivElement;
	let anchor_el: HTMLDivElement;
	let slots_el: HTMLDivElement;
	const slot_els: HTMLDivElement[] = [];
	let sizes = $state<Record<string, Size>>({});
	let layout = $state<{
		anchor: { x: number; y: number };
		hand: DOMRect;
		slots: DOMRect[];
	} | null>(null);

	function measureLayout() {
		const anchor = anchor_el.getBoundingClientRect();
		layout = {
			anchor: { x: anchor.left, y: anchor.top },
			hand: hand_el.getBoundingClientRect(),
			slots: slot_els.map((el) => el.getBoundingClientRect())
		};
	}

	onMount(() => {
		const observer = new ResizeObserver(measureLayout);
		[arena_el, hand_el, anchor_el, slots_el, ...slot_els].forEach((el) => observer.observe(el));
		measureLayout();
		// Capture also catches scrolling in an ancestor container.
		window.addEventListener('scroll', measureLayout, true);
		window.addEventListener('resize', measureLayout);
		return () => {
			observer.disconnect();
			window.removeEventListener('scroll', measureLayout, true);
			window.removeEventListener('resize', measureLayout);
		};
	});

	function getPose(id: string): Pose | null {
		const size = sizes[id];
		if (!layout || !size?.width || !size.height) return null;

		if (drag?.glyph_id === id) {
			if (!drag.active) return drag.pose;
			return {
				x: drag.x - drag.grab_x * size.width * drag.pose.scale,
				y: drag.y - drag.grab_y * size.height * drag.pose.scale,
				rotation: 0,
				scale: drag.pose.scale
			};
		}

		const slot_index = slot_ids.indexOf(id);
		if (slot_index !== -1) {
			const rect = layout.slots[slot_index];
			if (!rect) return null;
			return {
				x: rect.left + rect.width / 2,
				y: rect.top + rect.height / 2,
				rotation: 0,
				scale: Math.min(rect.width / size.width, rect.height / size.height)
			};
		}

		const index = hand_ids.indexOf(id);
		const middle = (hand_ids.length - 1) / 2;
		const offset = index - middle;
		const normalized = offset / Math.max(middle, 1);
		const focused = hand_ids.indexOf(hand_hovered_id ?? '');
		const hovered = index === focused;
		const available = Math.max(0, layout.hand.width - size.width * 1.4);
		const step = Math.min(size.width * FEEL.spacing, available / Math.max(hand_ids.length - 1, 1));
		const push =
			focused !== -1 && !hovered ? Math.sign(index - focused) * size.width * FEEL.neighbor_push : 0;

		return {
			x: layout.anchor.x + offset * step + push,
			y:
				layout.anchor.y +
				normalized ** 2 * size.height * FEEL.curvature -
				(hovered ? size.height * FEEL.hover_lift : 0),
			rotation: hovered ? 0 : normalized * FEEL.fan_angle,
			scale: 1
		};
	}

	const motions = new Map<string, Spring<Pose>>();
	const card_els = new Map<string, HTMLButtonElement>();

	function animateCard(node: HTMLButtonElement, id: string) {
		const motion = new Spring<Pose>(
			{ x: 0, y: 0, rotation: 0, scale: 1 },
			{ stiffness: FEEL.stiffness, damping: FEEL.damping }
		);
		motions.set(id, motion);
		card_els.set(id, node);
		let initialized = false;

		const observer = new ResizeObserver(([entry]) => {
			const box = entry.borderBoxSize[0];
			sizes[id] = {
				width: box?.inlineSize ?? node.offsetWidth,
				height: box?.blockSize ?? node.offsetHeight
			};
		});
		observer.observe(node, { box: 'border-box' });

		$effect(() => {
			const pose = getPose(id);
			if (!pose) return;
			const instant = !initialized || drag?.glyph_id === id || prefersReducedMotion.current;
			untrack(() => {
				void motion.set(pose, { instant });
			});
			initialized = true;
			node.style.visibility = 'visible';
		});

		$effect(() => {
			const p = motion.current;
			node.style.transform = `translate3d(${p.x}px, ${p.y}px, 0)
        translate(-50%, -50%) rotate(${p.rotation}deg) scale(${p.scale})`;
		});

		return {
			destroy() {
				observer.disconnect();
				motions.delete(id);
				card_els.delete(id);
				delete sizes[id];
				if (drag?.glyph_id === id) cancelDrag();
			}
		};
	}

	let suppressed_click_id: string | null = null;

	function press(event: PointerEvent, id: string) {
		if (drag || !event.isPrimary || event.button !== 0) return;
		const size = sizes[id];
		const current = motions.get(id)?.current;
		if (!size || !current) return;
		measureLayout();
		suppressed_click_id = null;
		drag = {
			glyph_id: id,
			pointer_id: event.pointerId,
			start_x: event.clientX,
			start_y: event.clientY,
			x: event.clientX,
			y: event.clientY,
			grab_x: (event.clientX - current.x) / (size.width * current.scale),
			grab_y: (event.clientY - current.y) / (size.height * current.scale),
			pose: { ...current },
			active: false
		};
		hand_hovered_id = null;
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	}

	function findSlot(x: number, y: number): number | null {
		if (!layout) return null;
		let best: number | null = null;
		let distance = Infinity;
		layout.slots.forEach((rect, index) => {
			if (!inside(rect, x, y, FEEL.slot_tolerance)) return;
			const d = (x - rect.left - rect.width / 2) ** 2 + (y - rect.top - rect.height / 2) ** 2;
			if (d < distance) {
				distance = d;
				best = index;
			}
		});
		return best;
	}

	function inside(rect: DOMRect, x: number, y: number, padding = 0) {
		return (
			x >= rect.left - padding &&
			x <= rect.right + padding &&
			y >= rect.top - padding &&
			y <= rect.bottom + padding
		);
	}

	function move(event: PointerEvent) {
		if (!drag || drag.pointer_id !== event.pointerId) return;
		drag.x = event.clientX;
		drag.y = event.clientY;
		if (!drag.active) {
			const distance = (drag.x - drag.start_x) ** 2 + (drag.y - drag.start_y) ** 2;
			if (distance < FEEL.drag_threshold ** 2) return;
			drag.active = true;
			suppressed_click_id = drag.glyph_id;
		}
		target_slot = findSlot(drag.x, drag.y);
	}

	function finish(event: PointerEvent) {
		if (!drag || drag.pointer_id !== event.pointerId) return;
		const current = drag;
		if (current.active) {
			measureLayout();
			const index = findSlot(event.clientX, event.clientY);
			if (index !== null) moveToSlot(current.glyph_id, index);
			else if (layout && inside(layout.hand, event.clientX, event.clientY)) {
				moveToHand(current.glyph_id);
			}
		}
		clearPointer();
	}

	function clearPointer() {
		if (!drag) return;
		const current = drag;
		drag = null;
		target_slot = null;
		const node = card_els.get(current.glyph_id);
		if (node?.hasPointerCapture(current.pointer_id)) {
			node.releasePointerCapture(current.pointer_id);
		}
	}

	function cancelDrag(event?: PointerEvent) {
		if (!drag || (event && event.pointerId !== drag.pointer_id)) return;
		suppressed_click_id = drag.glyph_id;
		clearPointer();
	}

	function activate(event: MouseEvent, id: string) {
		if (event.detail !== 0 && suppressed_click_id === id) return;
		toggleGlyph(id);
	}
</script>

<svelte:window
	onblur={() => cancelDrag()}
	onkeydown={(event) => {
		if (event.key === 'Escape') cancelDrag();
	}}
/>

<div class="arena" bind:this={arena_el}>
	<div class="slots" bind:this={slots_el}>
		{#each slot_ids as id, i}
			<div
				class="slot"
				bind:this={slot_els[i]}
				class:target={target_slot === i && (id === null || id === drag?.glyph_id)}
				class:blocked={target_slot === i && id !== null && id !== drag?.glyph_id}
			>
				<span>{i + 1}</span>
			</div>
		{/each}
	</div>

	<div class="hand-area" bind:this={hand_el}>
		<div class="hand-anchor" bind:this={anchor_el}></div>
	</div>

	{#each rendered_ids as id (id)}
		<button
			type="button"
			class="glyph"
			use:animateCard={id}
			class:dragging={drag?.glyph_id === id && drag.active}
			style:z-index={drag?.glyph_id === id
				? 1000
				: hand_hovered_id === id
					? 100
					: slot_ids.includes(id)
						? 30
						: 10 + hand_ids.indexOf(id)}
			aria-label={`${glyphs_by_id[id].letter}: ${
				slot_ids.includes(id) ? 'return to hand' : 'move to first empty slot'
			}`}
			aria-pressed={slot_ids.includes(id)}
			onpointerdown={(event) => press(event, id)}
			onpointermove={move}
			onpointerup={finish}
			onpointercancel={cancelDrag}
			onlostpointercapture={cancelDrag}
			onclick={(event) => activate(event, id)}
			onpointerenter={(event) => {
				if (!drag && event.pointerType !== 'touch' && hand_ids.includes(id)) {
					hand_hovered_id = id;
				}
			}}
			onpointerleave={() => {
				if (hand_hovered_id === id) hand_hovered_id = null;
			}}
			onfocus={() => {
				if (!drag && hand_ids.includes(id)) hand_hovered_id = id;
			}}
			onblur={() => {
				if (hand_hovered_id === id) hand_hovered_id = null;
			}}
		>
			<span>{glyphs_by_id[id].letter}</span>
		</button>
	{/each}
</div>

<style>
	.arena {
		--glyph-width: clamp(64px, 12vw, 144px);
		--glyph-ratio: 2 / 3;
		--slot-width: 112px;
		position: relative;
		width: 100%;
		height: 100dvh;
		min-height: 360px;
		overflow: hidden;
		background: black;
		color: #e6d9bd;
		font-family: system-ui, sans-serif;
		user-select: none;
	}
	.slots {
		position: absolute;
		top: 29%;
		left: 50%;
		transform: translateX(-50%);
		display: grid;
		grid-template-columns: repeat(8, minmax(0, 1fr));
		gap: clamp(4px, 1vw, 10px);
		width: calc(100% - 24px);
		max-width: calc(8 * var(--slot-width) + 70px);
	}
	.slot {
		box-sizing: border-box;
		aspect-ratio: var(--glyph-ratio);
		border: 1px dashed #69604e;
		border-radius: 10px;
		display: grid;
		place-items: center;
		color: #69604e;
	}
	.slot.target {
		background: #40381f;
		border-color: #f1ce7d;
	}
	.slot.blocked {
		background: #432527;
		border-color: #c77878;
	}
	.hand-area {
		position: absolute;
		inset: auto 12px 0;
		height: 42%;
	}

	.hand-anchor {
		position: absolute;
		left: 50%;
		bottom: calc(var(--glyph-width) * 0.5);
	}
	.glyph {
		box-sizing: border-box;
		position: fixed;
		top: 0;
		left: 0;
		width: var(--glyph-width);
		aspect-ratio: var(--glyph-ratio);
		margin: 0;
		padding: 0;
		border: 1px solid black;
		border-radius: 10px;
    background: red;
		font:
			600 clamp(26px, 4vw, 52px) Georgia,
			serif;
		transform-origin: center;
		touch-action: none;
		cursor: grab;
		will-change: transform;
	}
	.glyph.dragging {
		cursor: grabbing;
	}
	.glyph:focus-visible {
		outline: 3px solid #fff1cf;
		outline-offset: 4px;
	}
	@media (max-height: 500px) {
		.arena {
			--glyph-width: clamp(52px, 16vh, 80px);
			--slot-width: 60px;
		}
	}
</style>
