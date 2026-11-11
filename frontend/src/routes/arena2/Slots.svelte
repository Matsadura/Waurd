<script lang="ts">
	import { FEEL, getArena, setArena, type Glyph } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	const arena = getArena();
</script>

<div class="flex items-start justify-center gap-2 px-4 ">
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
