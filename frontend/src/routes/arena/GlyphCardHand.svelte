<script lang="ts">
	import { FEEL } from '#lib/configs/arenaFeel.ts';
	import { Spring } from 'svelte/motion';
	import { fade } from 'svelte/transition';
	import type { Glyph, Pose } from './types';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	let {
		glyph,
		pose,
		onHover,
		onDrag,
		onDragEnd,
		onClickHandler
	}: {
		glyph: Glyph;
		pose: Pose;
		onHover: (hovered: boolean) => void;
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
		onHover(false);
	}

	function move(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		const dx = e.clientX - drag.startX;
		const dy = e.clientY - drag.startY;

		if (!movedEnoughToBeDrag) {
			if (Math.hypot(dx, dy) < SIZE_OF_DRAG_TO_BE_DRAG) return;
			movedEnoughToBeDrag = true;
			onHover(false);
		}

		motion.set(
			{
				...motion.current,
				x: drag.x + e.clientX - drag.startX,
				y: drag.y + e.clientY - drag.startY
			},
			{ instant: true }
		);
		onDrag(e.clientX, e.clientY);
	}

	function release(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		motion.target = {
			x: pose.x,
			y: pose.y,
			rotation: pose.rotation,
			scale: pose.scale
		};

		drag = null;
		onDragEnd();
	}

	function click() {
		if (!movedEnoughToBeDrag) {
			onClickHandler();
		}
	}

	const motion = Spring.of(
		() => ({
			x: pose.x,
			y: pose.y,
			rotation: pose.rotation,
			scale: pose.scale
		}),
		{ stiffness: 0.05, damping: 0.4 }
	);
</script>

<button
	transition:fade={{ duration: 200 }}
	class="card absolute bottom-0 left-1/2 -ml-24 w-[calc((1em+1vw)*4)]"
	style:aspect-ratio={FEEL.glyphAspectRatio}
	style:transform-origin="center bottom"
	style:translate="{motion.current.x}px {motion.current.y}px"
	style:rotate="{drag ? 0 : motion.current.rotation}deg"
	style:scale={drag ? 1.2 : motion.current.scale}
	style:z-index={pose.zIndex}
	onpointerenter={() => onHover(true)}
	onpointerleave={() => onHover(false)}
	onpointerdown={press}
	onpointermove={move}
	onpointerup={release}
	onpointercancel={release}
	onlostpointercapture={release}
	onclick={click}
>
	<div class="flash h-full w-full rounded transition-all ease-in-out">
		<GlyphFace letter={glyph.letter} />
	</div>
</button>

<style>
	.flash {
		animation: flash 650ms ease-out;
	}

	@keyframes flash {
		from {
			filter: brightness(3);
			box-shadow: 0 0 5px 25px rgba(206, 204, 76, 0.6);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.flash {
			animation: none;
		}
	}
</style>
