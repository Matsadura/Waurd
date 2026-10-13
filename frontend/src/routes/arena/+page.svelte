<script lang="ts">
	type Glyph = {
		id: string;
		letter: string;
	};

	const EASE = 'cubic-bezier(0.2, 0.85, 0.2, 1)';

	const FEEL = {
		// Card
		cardWidth: 144,
		cardHeight: 216,
		cardBottom: -12,

		// Resting hand
		spacing: 62,
		curvature: 3.2,
		rotation: 3.5,
		maxFan: 12,
		edgePadding: 16,

		// Focused glyph
		lift: 15,
		scale: 1.06,

		// Neighbors of the focused glyph
		neighborPush: 68,

		// Shadows
		shadow: '0 6px 14px #0007',
		focusShadow: '0 18px 35px #0009, 0 0 16px #e8b86655',

		// Motion profiles
		motion: {
			idle: { duration: 460, easing: EASE },
			focus: { duration: 460, easing: EASE },
			neighbor: { duration: 460, easing: EASE }
		}
	};

	let hand = $state<Glyph[]>([
		{ id: 'g1', letter: 'C' },
		{ id: 'g2', letter: 'A' },
		{ id: 'g3', letter: 'A' },
		{ id: 'g4', letter: 'A' },
		{ id: 'g5', letter: 'A' },
		{ id: 'g6', letter: 'A' },
		{ id: 'g7', letter: 'A' },
		{ id: 'g8', letter: 'A' },
		{ id: 'g9', letter: 'A' },
		{ id: 'g10', letter: 'A' },
		{ id: 'g11', letter: 'A' },
		{ id: 'g12', letter: 'A' }
	]);

	let focusedIndex = $state<number>(-1);

	type Pose = 'idle' | 'focus' | 'before' | 'after';

	function poseOf(index: number): Pose {
		if (focusedIndex === -1) return 'idle';
		if (index === focusedIndex) return 'focus';
		return index < focusedIndex ? 'before' : 'after';
	}

	function hover(glyphIndex: number, event: PointerEvent) {
		if (event.pointerType !== 'touch') {
			if (glyphIndex !== hand.length - 1) {
				focusedIndex = glyphIndex;
			} else {
				// const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
				// const isInLeftHalf = event.clientX < rect.left + rect.width / 3*2;
				// console.log('isInLeftHalf', isInLeftHalf, event.clientX, rect.left + rect.width / 2);
				// if (isInLeftHalf) {
				//     focusedIndex = glyphIndex;
				// }
				focusedIndex = glyphIndex;
			}
		}
	}

	const motionVars = Object.entries(FEEL.motion)
		.map(([pose, m]) => `--${pose}-duration: ${m.duration}ms; --${pose}-ease: ${m.easing};`)
		.join('\n');

	const feelVars = `
        --card-w: ${FEEL.cardWidth}px;
        --card-h: ${FEEL.cardHeight}px;
        --card-bottom: ${FEEL.cardBottom}px;
        --spacing: ${FEEL.spacing}px;
        --edge: ${FEEL.edgePadding}px;
        --curvature: ${FEEL.curvature}px;
        --rotation: ${FEEL.rotation}deg;
        --max-fan: ${FEEL.maxFan}deg;
        --lift: ${FEEL.lift}px;
        --scale: ${FEEL.scale};
        --push: ${FEEL.neighborPush}px;
        --shadow-rest: ${FEEL.shadow};
        --shadow-focus: ${FEEL.focusShadow};
        ${motionVars}
    `;
</script>

<div class="arena">
	<div class="word">
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
		<div class="word-slot"></div>
	</div>

	<div
		class="hand"
		role="group"
		aria-label="Glyph hand"
		style={feelVars}
		style:--n={hand.length}
		onpointerleave={() => (focusedIndex = -1)}
	>
		{#each hand as glyph, i (glyph.id)}
			<div
				class="card"
				role="presentation"
				data-pose={poseOf(i)}
				style:--o={i - (hand.length - 1) / 2}
				onpointerenter={(event) => hover(i, event)}
			>
				{glyph.letter}
			</div>
		{/each}
	</div>
</div>

<style>
	.arena {
		position: relative;
		height: 100vh;
	}

	.word {
		position: absolute;
		margin: 0;
		padding: 0;

		transform: translate(-50%, 50%);
		bottom: 60%;
		left: 50%;

		display: flex;
		justify-content: center;
	}

	.word-slot {
		display: inline-block;
		--by: 1.3;
		width: calc(144px / var(--by));
		height: calc(216px / var(--by));
		margin: 0 4px;
		border: 2px solid #b68c43;
		border-radius: 4px;
		background-color: #272b35;
	}

	.hand {
		position: fixed;
		inset: auto 0 0;
		margin-inline: auto;
		width: min(95vw, 800px);
		height: 0;
		user-select: none;
		--step: max(
			0px,
			min(var(--spacing), (100cqw - var(--card-w) - 2 * var(--edge)) / max(var(--n) - 1, 1))
		);
		--angle-step: min(var(--rotation), var(--max-fan) / max((var(--n) - 1) / 2, 1));
	}

	.card {
		position: absolute;
		bottom: var(--card-bottom);
		left: calc(50% + var(--o) * var(--step) - var(--card-w) / 2);
		width: var(--card-w);
		height: var(--card-h);
		z-index: var(--z);
		pointer-events: auto;

		display: grid;
		place-items: center;
		box-sizing: border-box;
		border: 3px solid #b68c43;
		border-radius: 12px;
		background: #272b35;
		color: #f5e8c8;
		font-size: 64px;
		font-weight: 700;

		transform-origin: center bottom;
		translate: var(--x) var(--y);
		rotate: var(--a);
		scale: var(--s);
		box-shadow: var(--shadow);

		transition-property: translate, rotate, scale, box-shadow;
		transition-duration: var(--duration);
		transition-timing-function: var(--ease);

		--x: 0px;
		--y: calc(var(--o) * var(--o) * var(--curvature));
		--a: calc(var(--o) * var(--angle-step));
		--s: 1;
		--z: 0;
		--shadow: var(--shadow-rest);
		--duration: var(--idle-duration);
		--ease: var(--idle-ease);
	}

	.card[data-pose='focus'] {
		--y: calc(var(--lift) * -1);
		--a: 0deg; /* this causes to move in buggy way when hovere in its edge */
		--s: calc(var(--scale) * 1.2);
		--z: 10;
		--shadow: var(--shadow-focus);
		--duration: var(--focus-duration);
		--ease: var(--focus-ease);
	}

	.card[data-pose='before'] {
		--x: calc(var(--push) * -1);
		--duration: var(--neighbor-duration);
		--ease: var(--neighbor-ease);
	}

	.card[data-pose='after'] {
		--x: var(--push);
		--duration: var(--neighbor-duration);
		--ease: var(--neighbor-ease);
	}

	@media (prefers-reduced-motion: reduce) {
		.card {
			transition-duration: 0ms;
		}
	}
</style>
