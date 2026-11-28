<script lang="ts">
	import { getArena } from '#lib/utils/arena.svelte.ts';

	let { myName, opponentName }: { myName: string; opponentName: string } = $props();

	const arena = getArena();
	const text = $derived(arena.turn === 'me' ? `Your turn, ${myName}!` : `${opponentName}'s turn`);
</script>

{#if arena.turn !== null}
	{#key arena.turnNumber}
		<div
			class="banner pointer-events-none absolute inset-x-0 top-1/3 z-30 overflow-hidden py-4 text-center md:py-6"
			data-turn={arena.turn}
		>
			<div class="light-swap"></div>

			<div class="relative px-4 py-2 md:py-4">
				<p class="text-md tracking-[0.35em] uppercase">
					Turn <span class="font-serif"> #{arena.turnNumber}</span>
				</p>
				<p class="font-display text-3xl md:text-5xl lg:text-8xl">
					{text}
				</p>
			</div>

			<div class="banner-rule"></div>
		</div>
	{/key}
{/if}

<style>
	.banner {
		background: linear-gradient(
			90deg,
			transparent 0%,
			rgb(4 22 15 / 82%) 18%,
			rgb(4 22 15 / 82%) 82%,
			transparent 100%
		);
		animation: banner-wrap 1.9s cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}

	.light-swap {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			110deg,
			transparent 35%,
			color-mix(in srgb, rgb(255 255 255 / 20%) 28%, transparent) 50%,
			transparent 65%
		);
		animation: light-swap-pass 1.9s ease-in-out forwards;
	}

	@keyframes banner-wrap {
		0% {
			opacity: 0;
			transform: scaleY(0.75);
		}
		18% {
			opacity: 1;
			transform: scaleY(1);
		}
		72% {
			opacity: 1;
			transform: scaleY(1);
		}
		100% {
			opacity: 0;
			transform: scaleY(0.92);
			visibility: hidden;
		}
	}

	@keyframes light-swap-pass {
		0%,
		14% {
			opacity: 0;
			transform: translateX(-85%);
		}
		30% {
			opacity: 1;
		}
		58% {
			opacity: 0;
			transform: translateX(85%);
		}
		100% {
			opacity: 0;
			transform: translateX(85%);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.banner {
			animation: reduced-banner 1.6s ease-in-out forwards;
		}
	}

	@keyframes reduced-banner {
		0% {
			opacity: 0;
		}
		15%,
		75% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			visibility: hidden;
		}
	}
</style>
