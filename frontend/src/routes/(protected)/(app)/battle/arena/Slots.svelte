<script lang="ts">
	import { FEEL, getArena } from '#lib/utils/arena.svelte.ts';
	import draggable from '#lib/utils/draggable.ts';
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';

	const arena = getArena();
</script>

<div class="flex items-start justify-center gap-2 px-4">
	{#each arena.slots as position, i}
		{@const glyph = position !== null ? arena.glyph(position) : undefined}
		<div
			{@attach arena.slotEl(i)}
			style:aspect-ratio={FEEL.glyphAspectRatio}
			class={[
				'w-36 rounded border border-dashed border-amber-100/30',
				arena.overIndex === i && arena.currentView === 'slots' ? 'suspanse-pulse' : ''
			]}
		>
			{#key position}
				{#if glyph !== undefined}
					<button
						class="pulse w-full translate-x-(--dx) translate-y-(--dy) cursor-pointer transition-all"
						class:pointer-events-none={arena.phase === 'checking'}
						class:blur-xs={arena.phase === 'checking'}
						class:suspanse-pulse={arena.phase === 'checking'}
						class:valid-animation={arena.phase === 'valid'}
						class:invalid-animation={arena.phase === 'invalid'}
						{@attach draggable(
							(x, y) => arena.dragOver(x, y),
							() => arena.drop(glyph.position),
							() => arena.toggle(glyph.position)
						)}
					>
						<GlyphFace {glyph} />
					</button>
				{/if}
			{/key}
		</div>
	{/each}
</div>

<style>
	.valid-animation {
		animation: valid-frames 300ms cubic-bezier(0.45, 0, 0.55, 1) infinite;
		--filter: sepia(1) saturate(4) hue-rotate(80deg);
	}
	.invalid-animation {
		animation: valid-frames 300ms cubic-bezier(0.45, 0, 0.55, 1) infinite;
		--filter: sepia(1) saturate(4) hue-rotate(-40deg);
	}

	@keyframes valid-frames {
		0% {
			transform: translate(0, 0);
			filter: none;
		}
		15% {
			transform: translate(-12px, 4px);
			filter: var(--filter);
		}
		40% {
			transform: translate(10px, 4px);
		}
		60% {
			transform: translate(-6px, 3px);
		}
		80% {
			transform: translate(3px, 1px);
			filter: var(--filter);
		}
		100% {
			transform: translate(0, 0);
		}
	}
</style>
