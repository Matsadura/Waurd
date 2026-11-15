<script lang="ts">
	import { getArena } from '#lib/utils/arena.svelte.ts';
	const arena = getArena();
</script>

<button
	class="cursor-pointer rounded-md border-2 border-arena-yallow-100/50 bg-transparent px-8 py-3 font-kreon text-2xl font-bold text-arena-yallow-100/80 transition enabled:hover:border-arena-yallow-100 enabled:hover:bg-green-900/60 enabled:hover:text-arena-yallow-100 enabled:hover:shadow-lg enabled:hover:shadow-green-300/20 enabled:active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:grayscale"
	onclick={() => arena.showPerksView()}
>
	Perks
</button>
