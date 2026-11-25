<script lang="ts">
	import type { Snippet } from 'svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import type { Perk, Rarity } from '#lib/types/profile.ts';

	// children = the action area at the bottom, like an Equip button
	let { perk, children }: { perk: Perk; children?: Snippet } = $props();

	const rarityColor: Record<Rarity, string> = {
		common: 'text-ash',
		uncommon: 'text-success-light',
		rare: 'text-info-light',
		legendary: 'text-warning-light'
	};
</script>

<Frame
	variant="double-border"
	as="article"
	class="flex h-full flex-col px-4 py-4 {perk.owned ? '' : 'opacity-60'}"
>
	<h3 class="font-display text-xl">{perk.name}</h3>
	<p class={['text-base tracking-wide uppercase', rarityColor[perk.rarity]]}>
		{perk.rarity} · {perk.target} glyphs
	</p>

	<p class="mt-3">{perk.description}</p>
	{#if perk.quote}
		<p class="mt-2 text-base text-ash italic">“{perk.quote}”</p>
	{/if}

	<p class="mt-auto pt-3 text-base text-ash">
		{perk.durability != null ? `Durability ${perk.durability}` : 'Never breaks'}
	</p>

	{#if perk.owned}
		{#if children}
			<div class="mt-3">{@render children()}</div>
		{/if}
	{:else}
		<p class="mt-3 text-base text-ash italic">Locked, earn it through achievements.</p>
	{/if}
</Frame>
