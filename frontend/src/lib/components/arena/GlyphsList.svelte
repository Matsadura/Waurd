<script lang="ts">
	import GlyphFace from '#lib/components/arena/GlyphFace.svelte';
	import { fly } from 'svelte/transition';
	import { backIn, backOut } from 'svelte/easing';

	let { show, title }: { show: Boolean, title: string } = $props();
</script>

<!-- pinned to the left of the viewport, stays visible while the page scrolls
<div class="fixed top-2 left-2 z-20 flex flex-col gap-2">
	<button onclick={() => (show = !show)}>{show ? 'close' : 'show'}</button>
	{#if show}
		<button class="bg-red-500 px-4 py-2" onclick={() => (show = false)}>close</button>
	{/if}
</div> -->

{#if show}
	<div
		// in:fly={{ y: 300, duration: 450, easing: backOut }}
		// out:fly={{ y: 300, duration: 200, easing: backIn }}
		class="relative z-50 flex max-h-dvh flex-col items-center bg-gray-950/80 p-4 px-4 pt-12 md:pb-16 overflow-y-scroll"
	>
		<h2 class="mb-10 text-center text-4xl text-gray-300">{title}</h2>

		<div
			class="grid w-full max-w-5xl grid-cols-2 gap-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
		>
			{#each Array(40) as _, i (i)}
				<div
					class="pop-in cursor-pointer drop-shadow-xl transition duration-200 ease-in-out hover:scale-120 hover:brightness-110 hover:drop-shadow-2xl active:scale-95"
					style="--i: {i}"
				>
					<GlyphFace letter="0" />
				</div>
			{/each}
		</div>
	</div>
{/if}

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
