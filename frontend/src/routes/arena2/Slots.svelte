<script lang="ts">
	import { FEEL, getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	const arena = getArena();
</script>

<div class="absolute inset-x-0 top-1/3 flex items-start justify-center gap-2 px-4">
	{#each arena.slots as glyphId, i}
		<div
			{@attach arena.slot(i)}
			style:aspect-ratio={FEEL.glyphAspectRatio}
			class={[
				'w-36 rounded ',
				arena.overSlot === i ? 'suspanse' : '',
				glyphId ? '' : 'border border-dashed border-amber-100/50'
			]}
		>
			{#if glyphId}
				<button
					class="flash w-full translate-x-(--dx) translate-y-(--dy) transition-[scale] hover:scale-120"
					{@attach draggable(
						(x, y) => arena.dragOver(x, y),
						() => arena.drop(glyphId),
						() => arena.toggle(glyphId)
					)}
				>
					<GlyphFace letter={arena.glyph(glyphId).letter} />
				</button>
			{/if}
		</div>
	{/each}
</div>

<style>
	.suspanse {
		animation: suspanse 800ms ease-in-out infinite;
	}

	@keyframes suspanse {
		from {
			filter: brightness(1.1);
			box-shadow: 0 0 2px 5px #fff1c3f6;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.suspanse {
			animation: none;
		}
	}

	.flash {
		animation: flash 950ms ease-out;
	}

	@keyframes flash {
		from {
			filter: brightness(1);
			box-shadow: 0 0 5px 15px rgba(206, 204, 76, 0.6);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.flash {
			animation: none;
		}
	}
</style>
