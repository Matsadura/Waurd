<script>
	import { getArena } from '#lib/utils/arena.svelte.ts';
	const arena = getArena();
</script>

<button
	class="cursor-pointer rounded-md border-2 border-arena-yallow-100 bg-green-950 px-10 py-3 font-kreon text-2xl font-bold text-arena-yallow-100 transition enabled:hover:animate-none enabled:hover:bg-green-900 enabled:hover:shadow-lg enabled:hover:shadow-green-300/40 enabled:active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:grayscale motion-safe:enabled:animate-ready-pulse"
	onclick={() => arena.playSubmitAnimation()}
	disabled={arena.isBouncing || !arena.slots.some(Boolean)}
>
	{arena.isBouncing ? 'Checking...' : 'End Turn'}
</button>
