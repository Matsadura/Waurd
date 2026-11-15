<script lang="ts">
	import PerkFace from '#lib/components/arena/PerkFace.svelte';
	import { getArena } from '#lib/utils/arena.svelte.ts';
	import { fade, fly, slide } from 'svelte/transition';
	import Hand from '../../../routes/arena/Hand.svelte';
	import { bounceIn, circIn, cubicInOut, sineIn } from 'svelte/easing';

	let scrollContainer: HTMLElement;

	let isLeftActive = $state(false);
	let isRightActive = $state(false);

	function scrollLeft() {
		isLeftActive = true;
		if (scrollContainer) {
			scrollContainer.scrollBy({ left: -scrollContainer.clientWidth, behavior: 'smooth' });
		}
	}

	function scrollRight() {
		isRightActive = true;
		if (scrollContainer) {
			scrollContainer.scrollBy({ left: scrollContainer.clientWidth, behavior: 'smooth' });
		}
	}
	let arena = getArena();
</script>

<div
	transition:fly={{ y: '100%', duration: 300, easing: cubicInOut }}
	class="absolute inset-0 z-10 flex flex-col items-center bg-gray-950/80"
>
	<h2 class="mt-20 text-center font-kreon text-4xl text-gray-200">
		Drag and drop glyph into a Perk to use
	</h2>
	<div class="flex w-full items-center justify-center gap-6 px-40">
		<button
			onclick={scrollLeft}
			onanimationend={() => (isLeftActive = false)}
			class="flex text-6xl text-white drop-shadow-md transition-colors select-none hover:text-amber-50"
			class:click-animation={isLeftActive}
			style="--dir: -12px;"
		>
			◁
		</button>

		<div
			bind:this={scrollContainer}
			class="flex w-full snap-x snap-mandatory scrollbar-thumb-green-900 gap-8 overflow-x-scroll p-8 shadow-sm shadow-gray-700/60 select-none"
		>
			{#each { length: 40 } as _, i}
				<div
					class={[
						'flex w-64 shrink-0 snap-center items-center justify-center text-4xl',
						arena.overIndex === i ? 'suspanse-pulse' : ''
					]}
					{@attach arena.perkEl(i)}
				>
					<PerkFace artBackground={'' + i} />
				</div>
			{/each}
		</div>

		<button
			onclick={scrollRight}
			onanimationend={() => (isRightActive = false)}
			class="flex text-6xl text-white drop-shadow-md transition-colors select-none hover:text-amber-50"
			class:click-animation={isRightActive}
			style="--dir: 12px;"
		>
			▷
		</button>
	</div>
	<button
		class="mt-8 mr-24 cursor-pointer self-end rounded-md border-2 border-arena-yallow-100/50 bg-transparent px-8 py-3 font-kreon text-2xl font-bold text-arena-yallow-100/80 transition enabled:hover:border-arena-yallow-100 enabled:hover:bg-green-900/60 enabled:hover:text-arena-yallow-100 enabled:hover:shadow-lg enabled:hover:shadow-green-300/20 enabled:active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:grayscale"
		onclick={() => {
			arena.currentView = 'slots';
		}}
	>
		Back
	</button>
</div>

<style>
	.click-animation {
		animation: spring 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	@keyframes spring {
		0% {
			transform: scale(1) translateX(0);
		}
		40% {
			transform: scale(0.65) translateX(var(--dir));
		}
		100% {
			transform: scale(1) translateX(0);
		}
	}
</style>
