<script lang="ts">
	import { FEEL } from '#lib/configs/arenaFeel.ts';
	import { Spring } from 'svelte/motion';
	import { fade } from 'svelte/transition';
	import type { Glyph } from './types';

	let {
		glyph,
		onDrag,
		onDragEnd,
		onClickHandler
	}: {
		glyph: Glyph;
		onDrag: (x: number, y: number) => void;
		onDragEnd: () => void;
		onClickHandler: () => void;
	} = $props();

	type Drag = {
		pointerId: number;
		startX: number;
		startY: number;
		x: number;
		y: number;
	};

	const SIZE_OF_DRAG_TO_BE_DRAG = 10;

	let drag = $state<Drag | null>(null);
	let movedEnoughToBeDrag = $state(false);

	function press(e: PointerEvent) {
		if (drag || !e.isPrimary) return;
		if (e.pointerType === 'mouse' && e.button !== 0) return;

		const el = e.currentTarget as HTMLElement;

		drag = {
			pointerId: e.pointerId,
			startX: e.clientX,
			startY: e.clientY,
			x: motion.current.x,
			y: motion.current.y
		};
		movedEnoughToBeDrag = false;

		el.setPointerCapture(e.pointerId);
		onDrag(e.clientX, e.clientY);
	}

	function move(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		const dx = e.clientX - drag.startX;
		const dy = e.clientY - drag.startY;

		if (!movedEnoughToBeDrag) {
			if (Math.hypot(dx, dy) < SIZE_OF_DRAG_TO_BE_DRAG) return;
			movedEnoughToBeDrag = true;
		}

		motion.set({
			...motion.current,
			x: drag.x + e.clientX - drag.startX,
			y: drag.y + e.clientY - drag.startY
		});
		onDrag(e.clientX, e.clientY);
	}

	function release(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		drag = null;

		motion.target = {
			x: 0,
			y: 0,
			rotation: 0,
			scale: 1
		};
		onDragEnd();
	}

	function click() {
		if (!movedEnoughToBeDrag) {
			onClickHandler();
		}
	}

	const motion = Spring.of(
		() => ({
			x: 0,
			y: 0,
			rotation: 0,
			scale: 1
		}),
		{ stiffness: 0.07, damping: 0.3 }
	);
</script>

<button
	transition:fade={{ duration: 200 }}
	class="card w-full"
	style:aspect-ratio={FEEL.glyphAspectRatio}
	style:transform-origin="center bottom"
	style:translate="{motion.current.x}px {motion.current.y}px"
	style:z-index={drag ? 500 : 'auto'}
	onpointerdown={press}
	onpointermove={move}
	onpointerup={release}
	onpointercancel={release}
	onlostpointercapture={release}
	onclick={click}
>
	<div
		class="flash relative flex h-full w-full items-center justify-center
           rounded border-2 border-amber-700 bg-amber-900 text-5xl text-white"
	>
		{glyph.letter}
	</div>
</button>

<style>
	.flash {
		animation: flash 450ms ease-out;
	}

	@keyframes flash {
		from {
			filter: brightness(2);
			box-shadow: 0 0 22px 6px rgb(251 191 36 / 0.7);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.flash {
			animation: none;
		}
	}
</style>
