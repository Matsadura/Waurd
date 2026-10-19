<script lang="ts">
	import { Spring } from 'svelte/motion';

	type Glyph = {
		id: string;
		letter: string;
	};

	type Pose = {
		x: number;
		y: number;
		rotation: number;
		scale: number;
		zIndex: number;
	};

	let {
		glyph,
		pose,
		onHover
	}: {
		glyph: Glyph;
		pose: Pose;
		onHover: (hovered: boolean) => void;
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
		onHover(false);
	}

	function move(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		motion.set(
			{
				...motion.current,
				x: drag.x + e.clientX - drag.startX,
				y: drag.y + e.clientY - drag.startY
			},
			{ instant: true }
		);
	}

	function release(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;

		drag = null;

		motion.target = {
			x: pose.x,
			y: pose.y,
			rotation: pose.rotation,
			scale: pose.scale
		};
	}

	const motion = Spring.of(
		() => ({
			x: pose.x,
			y: pose.y,
			rotation: pose.rotation,
			scale: pose.scale
		}),
		{ stiffness: 0.1, damping: 0.3 }
	);
</script>

<button
	class="absolute bottom-0 left-1/2 -ml-24 h-60 w-40 card"
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
