<script lang="ts">
	import PerkFace from '#lib/components/arena/PerkFace.svelte';
	import { FEEL, getArena } from '#lib/utils/arena.svelte.ts';
	import { fly } from 'svelte/transition';
	import { cubicInOut } from 'svelte/easing';

	let scrollContainer: HTMLElement;

	let isLeftActive = $state(false);
	let isRightActive = $state(false);

	let arena = getArena();

	function scrollLeft() {
		isLeftActive = true;
		scrollContainer?.scrollBy({
			left: -scrollContainer.clientWidth,
			behavior: 'smooth'
		});
	}

	function scrollRight() {
		isRightActive = true;
		scrollContainer?.scrollBy({
			left: scrollContainer.clientWidth,
			behavior: 'smooth'
		});
	}
</script>

<div
	transition:fly={{ y: '100%', duration: 300, easing: cubicInOut }}
	class="absolute inset-0 z-10 flex flex-col items-center bg-gray-950/90"
>
	<h2
		class="mt-8 mb-5 text-center font-kreon text-xl text-arena-yallow-100 sm:mt-12 md:mt-20 md:text-4xl"
	>
		Drag and drop glyph into a Perk to use
	</h2>

	<div
		class="grid min-h-0 w-full flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)_auto] gap-3 px-3 sm:px-5 md:grid-cols-[minmax(0,1fr)_auto] md:grid-rows-1 md:items-center md:gap-6 md:pr-20 md:pl-40"
	>
		<!-- Perks carousel -->
		<div class="flex h-full min-h-0 min-w-0 items-center gap-3 overflow-hidden">
			<button
				onclick={scrollLeft}
				onanimationend={() => (isLeftActive = false)}
				class="flex shrink-0 text-3xl text-white drop-shadow-md transition-colors select-none hover:text-amber-50 md:text-6xl"
				class:click-animation={isLeftActive}
				style="--dir: -12px;"
			>
				◁
			</button>

			<div
				bind:this={scrollContainer}
				class="flex h-full min-w-0 flex-1 snap-x snap-mandatory scrollbar-thumb-green-900 gap-8 overflow-x-auto p-4 shadow-sm shadow-gray-700/60 select-none md:p-8"
			>
				{#each { length: 40 } as _, i}
					<div
						class={[
							'flex h-full shrink-0 snap-center items-center justify-center text-4xl',
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
				class="flex shrink-0 text-3xl text-white drop-shadow-md transition-colors select-none hover:text-amber-50 md:text-6xl"
				class:click-animation={isRightActive}
				style="--dir: 12px;"
			>
				▷
			</button>
		</div>

		<!-- Back button -->
		<button
			class="mb-4 cursor-pointer self-end rounded-md border-2 border-arena-yallow-100/50 bg-green-950/90 px-8 py-3 font-kreon text-2xl font-bold text-arena-yallow-100/80 transition hover:border-arena-yallow-100 hover:bg-green-900 hover:text-arena-yallow-100 hover:shadow-md hover:shadow-green-300/40 active:scale-95"
			onclick={() => {
				arena.currentView = 'slots';
			}}
		>
			Back
		</button>
	</div>
	<!-- NOTE(ALI): This is a dirty hack to up left the slots and make them not touch the hand, do somthing better! -->
	<div
		class={['pointer-events-none touch-none bg-amber-950', FEEL.CardWidth]}
		style:aspect-ratio={FEEL.glyphAspectRatio}
	></div>
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
