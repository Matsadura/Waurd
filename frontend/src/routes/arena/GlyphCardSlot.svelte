<script lang="ts">
	import { FEEL } from '#lib/configs/arenaFeel.ts';
	import { Spring } from 'svelte/motion';

	type Glyph = {
		id: string;
		letter: string;
	};

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

	let drag = $state<Drag | null>(null);

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

		el.setPointerCapture(e.pointerId);
		onDrag(e.clientX, e.clientY);
	}

	function move(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

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
	class="card w-full"
	style:aspect-ratio={FEEL.glyphAspectRatio}
	style:transform-origin="center bottom"
	style:translate="{motion.current.x}px {motion.current.y}px"
	// style:scale={drag ? 1.2 : motion.current.scale}
	// style:z-index={pose.zIndex}
	onpointerdown={press}
	onpointermove={move}
	onpointerup={release}
	onpointercancel={release}
	onlostpointercapture={release}
	onclick={onClickHandler}
>
	<div
		class="flex h-full w-full items-center justify-center
           rounded-xl border-2 border-amber-700 bg-amber-900 text-5xl text-white transition-all duration-1000 ease-in-out"
	>
		{glyph.letter}
	</div>
</button>

<style>
	.card {
		transition:
			rotate 160ms ease-out,
			scale 50ms ease-out;
	}
</style>
