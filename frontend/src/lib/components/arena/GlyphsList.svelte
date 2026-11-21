<script lang="ts">
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
	import { getArena, type Glyph } from '#lib/utils/arena.svelte.ts';

	let { title, glyphs = [] }: { title: string; glyphs: Glyph[] } = $props();
	const arena = getArena();
	function onBackdropClick(e: MouseEvent) {
		if ((e.target as HTMLElement).closest('[data-glyph]')) return;
		arena.setCurrentView('slots');
	}
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && arena.setCurrentView('slots')} />

<div
	class="absolute inset-0 z-50 flex h-dvh w-dvw flex-col items-center overflow-y-scroll bg-gray-950/80 p-4 px-4 pt-12 md:pb-16"
	onclick={onBackdropClick}
	role="presentation"
>
	<h2 class="mb-2 text-center font-kreon text-4xl text-arena-yallow-100">{title}</h2>
	<p class="mb-8 text-center text-sm text-white/50">(Tap anywhere outside to go back)</p>

	{#if glyphs.length === 0}
		<p class="mt-56 text-3xl text-amber-100">Nothing here...</p>
	{:else}
		<div
			class="grid w-full max-w-5xl grid-cols-2 gap-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
			data-glyph
		>
			{#each glyphs as glyph, i (i)}
				<div
					class="pop-in drop-shadow-xl transition duration-200 ease-in-out hover:scale-120 hover:brightness-110 hover:drop-shadow-2xl active:scale-95"
					style="--i: {i}"
				>
					<GlyphFace letter={glyph.letter} />
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	@keyframes pop-in {
		from {
			opacity: 0;
			transform: translateY(40px) scale(0.8);
		}
	}

	.pop-in {
		animation: pop-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
		animation-delay: calc(var(--i) * 40ms);
	}
</style>
