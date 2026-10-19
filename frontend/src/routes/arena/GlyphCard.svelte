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

	const motion = Spring.of(
		() => ({
			x: pose.x,
			y: pose.y,
			rotation: pose.rotation,
			scale: pose.scale
		}),
		{ stiffness: 0.1, damping: 0.30 }
	);
</script>

<button
	class="absolute bottom-0 left-1/2 -ml-24 h-60 w-40"
	style:transform-origin="center bottom"
	style:translate="{motion.current.x}px {motion.current.y}px"
	style:rotate="{motion.current.rotation}deg"
	style:scale={motion.current.scale}
	style:z-index={pose.zIndex}
	onpointerenter={() => onHover(true)}
	onpointerleave={() => onHover(false)}
>
	<div
		class="flex h-full w-full items-center justify-center
           border-2 text-white text-5xl border-amber-700 bg-amber-900 rounded-xl duration-1000 transition-all ease-in-out"
	>
		{glyph.letter}
	</div>
</button>
