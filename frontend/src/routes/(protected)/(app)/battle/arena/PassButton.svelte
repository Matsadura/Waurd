<script lang="ts">
	import { getArena } from '#lib/utils/arena.svelte.ts';
	const arena = getArena();
</script>

<button
	class="cursor-pointer rounded-md border-2 border-arena-yallow-100/50 bg-green-950/90 px-8 py-3 font-kreon text-2xl font-bold text-arena-yallow-100/80 transition enabled:hover:border-arena-yallow-100 enabled:hover:bg-green-900/80 enabled:hover:text-arena-yallow-100 enabled:hover:shadow-md enabled:hover:shadow-green-300/40 enabled:active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:grayscale"
	onclick={() => arena.passTurn()}
	disabled={arena.turn !== 'me' ||
		arena.battle.status !== 'connected' ||
		arena.phase === 'checking'}
>
	Pass Turn
</button>
