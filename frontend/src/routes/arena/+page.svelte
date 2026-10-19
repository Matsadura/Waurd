<script lang="ts">
	import { Spring } from 'svelte/motion';

	type Glyph = {
		id: string;
		letter: string;
	};

	type Kind = 'idle' | 'focus' | 'before' | 'after';

	type Pose = {
		kind: Kind;
		offsetX: number;
		offsetY: number;
		rotationAngle: number;
		scale: number;
		zIndex: number;
	};

	function clamp(v: number, lo: number, hi: number) {
		return Math.min(hi, Math.max(lo, v));
	}

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
		neighborPush: 70,
		tilt: 9
	};

	const glyphs: Glyph[] = 'GLYPHWORDSAT'.split('').map((letter, i) => ({
		id: `g${i + 1}`,
		letter
	}));

	let focusedId = $state<string | null>(null);
	let focusedIndex = $derived(focusedId ? glyphs.findIndex((g) => g.id === focusedId) : -1);

	function handPose(i: number, n: number, focusIdx: number): Pose {
		const outer = (n - 1) / 2;
		const offset = i - outer;

		const step = FEEL.spacing;
		const angle = Math.min(FEEL.rotation, FEEL.maxFan / Math.max(outer, 1));

		const rest: Pose = {
			kind: 'idle',
			offsetX: offset * step,
			offsetY: -FEEL.cardBottom + offset * offset * FEEL.curvature,
			rotationAngle: offset * angle,
			scale: 1,
			zIndex: 1 + i
		};

		if (i === focusIdx) {
			return {
				...rest,
				kind: 'focus',
				rotationAngle: 0,
				offsetY: 0,
				offsetX: rest.offsetX + 5 * offset,
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
			kind: side < 0 ? 'before' : 'after',
			offsetX: rest.offsetX + side * FEEL.neighborPush
		};
	}

	let poses = $derived(glyphs.map((_, i) => handPose(i, glyphs.length, focusedIndex)));

	const movements = glyphs.map((_, i) => {
		const pose = handPose(i, glyphs.length, -1);
		return new Spring({ x: pose.offsetX, y: pose.offsetY }, { stiffness: 0.1, damping: 0.4 });
	});

	$effect(() => {
		poses.forEach((pose, i) => {
			movements[i].target = {
				x: pose.offsetX,
				y: pose.offsetY
			};
		});
	});

	function enter(e: PointerEvent, id: string) {
		if (e.pointerType === 'touch') return;
		focusedId = id;
	}

	function leave(e: PointerEvent, id: string) {
		if (focusedId === id) focusedId = null;
		setLean(e.currentTarget as HTMLElement, null);
	}

	function setLean(el: HTMLElement, at: { u: number; v: number } | null) {
		const { u, v } = at ?? { u: 0.5, v: 0.5 };

		el.style.setProperty('--ry', `${(u - 0.5) * 2 * FEEL.tilt}deg`);
		el.style.setProperty('--rx', `${(0.5 - v) * 2 * FEEL.tilt}deg`);
		el.style.setProperty('--gx', `${u * 100}%`);
		el.style.setProperty('--gy', `${v * 100}%`);
	}

	function move(e: PointerEvent, id: string) {
		if (id !== focusedId) return;

		setLean(e.currentTarget as HTMLElement, {
			u: clamp(e.offsetX / FEEL.cardWidth, 0, 1),
			v: clamp(e.offsetY / FEEL.cardHeight, 0, 1)
		});
	}

	const rootVars = `
        --card-w: ${FEEL.cardWidth}px;
        --card-h: ${FEEL.cardHeight}px;
    `;
</script>

<div class="arena" style={rootVars}>
	{#each glyphs as glyph, i (glyph.id)}
		<div
			class="card"
			role="presentation"
			data-pose={poses[i].kind}
			style:--x="{movements[i].current.x}px"
			style:--y="{movements[i].current.y}px"
			style:--a="{poses[i].rotationAngle}deg"
			style:--s={poses[i].scale}
			style:--z={poses[i].zIndex}
			onpointerenter={(e) => enter(e, glyph.id)}
			onpointerleave={(e) => leave(e, glyph.id)}
			onpointermove={(e) => move(e, glyph.id)}
		>
			<div class="face">
				<span class="letter">{glyph.letter}</span>
			</div>
		</div>
	{/each}
</div>

<style>
	/* [data-pose='idle'] {
		--duration: 700ms;
		--ease: cubic-bezier(0.2, 0.8, 0.2, 1);
	}

	[data-pose='focus'] {
		--duration: 120ms;
		--ease: ease;
	}

	[data-pose='before'],
	[data-pose='after'] {
		--duration: 500ms;
		--ease: cubic-bezier(0.52, -0.39, 0.27, 1.55);
	} */

	/* Arena */
	.arena {
		position: relative;
		height: 100vh;
		overflow: hidden;
		user-select: none;
		background: #171c26;
	}

	/* Card: positioning and pointer interaction */
	.card {
		position: absolute;
		left: 50%;
		bottom: 0;

		width: var(--card-w);
		height: var(--card-h);
		margin-left: calc(var(--card-w) / -2);

		z-index: var(--z);
		cursor: grab;
		touch-action: none;

		transform-origin: center bottom;
		translate: var(--x) var(--y);
		rotate: var(--a);
		scale: var(--s);

		will-change: translate, rotate, scale;

		transition-property: translate, rotate, scale;
		transition-duration: var(--duration);
		transition-timing-function: var(--ease);
	}

	/* Face: appearance and perspective */
	.face {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		box-sizing: border-box;

		border: 3px solid #b68c43;
		border-radius: 12px;
		background: linear-gradient(160deg, #323848, #232733);
		color: #f5e8c8;

		transform: perspective(700px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg));

		transition:
			transform 140ms ease-out,
			box-shadow 200ms ease;

		pointer-events: none;
	}

	/* Focus shadow */
	.card[data-pose='focus'] .face {
		box-shadow:
			0 16px 20px #0009,
			0 0 28px 2px #e8b8666b;
	}

	/* Inner border */
	.face::before {
		content: '';
		position: absolute;
		inset: 6px;
		border: 1px solid #b68c4366;
		border-radius: 7px;
	}

	/* Cursor-following light */
	.face::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: 9px;

		background: radial-gradient(
			circle at var(--gx, 50%) var(--gy, 30%),
			#fff2cc17,
			transparent 62%
		);

		opacity: 0;
		transition: opacity 200ms;
	}

	.card:hover .face::after {
		opacity: 1;
	}

	/* Letter */
	.letter {
		font-family: Georgia, serif;
		font-size: 64px;
		font-weight: 700;
		text-shadow: 0 2px 0 #0006;
	}

	/* A11y */
	@media (prefers-reduced-motion: reduce) {
		.card,
		.face {
			transition-duration: 0ms;
		}

		.face::after {
			transition-duration: 0ms;
		}
	}
</style>
