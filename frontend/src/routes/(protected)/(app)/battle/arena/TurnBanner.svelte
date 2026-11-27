<script lang="ts">
	import { fade } from 'svelte/transition';
	import { cubicOut, cubicInOut } from 'svelte/easing';
	import { getArena } from '#lib/utils/arena.svelte.ts';

	const arena = getArena();
	const isMe = $derived(arena.turn === 'me');
	const text = $derived(isMe ? `Your turn, ${arena.me.name}!` : `${arena.opponent.name}'s turn`);
</script>

{#if arena.turnBanner}
	<div
		class={[
			'pointer-events-none absolute inset-x-0 top-1/3 z-30 bg-card-skill/95 py-1 text-center shadow-2xl shadow-black/90 md:py-2'
			// isMe ? 'border-arena-yallow-100' : 'border-rose-700'
		]}
		in:fade={{ duration: 500, easing: cubicOut }}
		out:fade={{ duration: 700, easing: cubicInOut }}
	>
		<div class="bg-card-skill/95 py-2">
			<p
				class={[
					'border-y py-4 font-kreon text-3xl md:text-3xl lg:text-5xl',
					isMe ? 'text-arena-yallow-100' : 'text-rose-400',
					isMe ? 'border-arena-yallow-100' : 'border-rose-400'
				]}
			>
				{text}
			</p>
		</div>
	</div>
{/if}
