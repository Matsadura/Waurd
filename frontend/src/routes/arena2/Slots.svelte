<script lang="ts">
	import { FEEL, getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	const arena = getArena();
</script>

<div class="flex items-start justify-center gap-2 px-4">
	{#each arena.slots as glyphId, i}
		<div
			{@attach arena.slot(i)}
			style:aspect-ratio={FEEL.glyphAspectRatio}
			class={[
				'w-36 rounded border border-dashed border-amber-100/30',
				arena.overSlot === i ? 'suspanse-pulse' : ''
			]}
		>
			{#key glyphId}
				{#if glyphId}
					<button
						class="pulse w-full translate-x-(--dx) translate-y-(--dy) cursor-pointer"
						class:pointer-events-none={arena.isBouncing}
						class:bounce={arena.isBouncing}
						class:shake={arena.isError}
						class:cool={arena.isGood}
						style:--i={i}
						style:--dur="{FEEL.bounceDuration}ms"
						style:--stagger="{FEEL.bounceStagger}ms"
						{@attach draggable(
							(x, y) => arena.dragOver(x, y),
							() => arena.drop(glyphId),
							() => arena.toggle(glyphId)
						)}
					>
						<GlyphFace letter={arena.glyph(glyphId).letter} />
					</button>
				{/if}
			{/key}
		</div>
	{/each}
</div>

<style>
	.cool {
		animation: coolAnim var(--dur) cubic-bezier(0.45, 0, 0.55, 1) backwards;
		animation-delay: calc(var(--i) * var(--stagger));
	}

	@keyframes coolAnim {
		0% {
			transform: translate(0, 0);
			filter: none;
		}
		15% {
			transform: translate(-12px, 4px);
			filter: sepia(1) saturate(5) hue-rotate(85deg);
		}
		40% {
			transform: translate(10px, 4px);
		}
		60% {
			transform: translate(-6px, 3px);
		}
		80% {
			transform: translate(3px, 1px);
			filter: sepia(1) saturate(5) hue-rotate(85deg);
		}
		100% {
			transform: translate(0, 0);
		}
	}

	.shake {
		animation: shakeAnim var(--dur) cubic-bezier(0.45, 0, 0.55, 1) backwards;
		animation-delay: calc(var(--i) * var(--stagger));
	}

	@keyframes shakeAnim {
		0% {
			transform: translate(0, 0);
			filter: none;
		}
		15% {
			transform: translate(-12px, 4px);
			filter: sepia(1) saturate(5) hue-rotate(-50deg);
		}
		40% {
			transform: translate(10px, 4px);
		}
		60% {
			transform: translate(-6px, 3px);
		}
		80% {
			transform: translate(3px, 1px);
			filter: sepia(1) saturate(5) hue-rotate(-50deg);
		}
		100% {
			transform: translate(0, 0);
		}
	}

	.bounce {
		animation: bounceAnim var(--dur) cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
		animation-delay: calc(var(--i) * var(--stagger));
	}

	@keyframes bounceAnim {
		0% {
			transform: translateY(0);
		}
		35% {
			transform: translateY(-40px);
		}
		100% {
			transform: translateY(0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.bounce {
			animation: none;
		}
	}
</style>
