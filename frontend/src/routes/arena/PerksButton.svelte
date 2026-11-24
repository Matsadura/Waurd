<script lang="ts">
	import { getArena } from '#lib/utils/arena.svelte.ts';
	const arena = getArena();
</script>

<button
	class="cursor-pointer rounded-md border-2 border-arena-yallow-100/50 bg-green-950/90 px-8 py-3 font-kreon text-2xl font-bold text-arena-yallow-100/80 transition hover:border-arena-yallow-100 hover:bg-green-900/80 hover:text-arena-yallow-100 hover:shadow-md hover:shadow-green-300/40 active:scale-95"
	onclick={() => arena.showPerksView()}
>
	Perks
</button>
