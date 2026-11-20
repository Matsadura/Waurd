<script lang="ts">
	import type { Draft } from '#lib/game/types.ts';

	let {
		draft,
		onpick,
		onreroll
	}: { draft: Draft; onpick: (perkId: string) => void; onreroll: () => void } = $props();

	const RARITY: Record<string, string> = {
		COMMON: 'text-white/70 border-white/20',
		UNCOMMON: 'text-[#5fe0cf] border-[#2fb5a6]',
		RARE: 'text-[#9fb0ff] border-[#6f83ff]',
		LEGENDARY: 'text-[#f0b955] border-[#f0b955] bg-[#f0b955]/10'
	};
</script>

<div
	class="fixed inset-0 z-40 grid place-items-center bg-black/70 p-4"
	role="dialog"
	aria-modal="true"
	aria-labelledby="draft-title"
>
	<div class="w-full max-w-3xl rounded-2xl border border-white/15 bg-[#17141d] p-5 sm:p-6">
		<h2 id="draft-title" class="text-2xl">Pick a perk</h2>
		<p class="mt-1 text-white/60">Your clock is still running.</p>
		{#if draft.options.length === 0}
			<p class="mt-6 text-white/70">Nothing to draft this turn.</p>
		{/if}
		<div class="mt-5 grid gap-3 sm:grid-cols-3">
			{#each draft.options as option (option.perk_id)}
				<button
					type="button"
					class="flex flex-col gap-2 rounded-xl border border-white/15 bg-black/40 p-4 text-left transition hover:-translate-y-1 hover:border-accent-action focus-visible:outline-2 focus-visible:outline-white"
					onclick={() => onpick(option.perk_id)}
				>
					<span class="text-xl leading-tight">{option.name}</span>
					<span
						class={[
							'w-fit rounded-full border px-2 py-0.5 text-xs uppercase',
							RARITY[option.rarity]
						]}>{option.rarity.toLowerCase()}</span
					>
					<span class="text-sm text-white/80">{option.description}</span>
					<span class="mt-auto text-xs text-white/50">{option.durability ?? '∞'} uses</span>
				</button>
			{/each}
		</div>
		<div class="mt-5 flex items-center justify-between gap-3">
			<p class="text-sm text-white/60">{draft.rerolls_left} rerolls left this match</p>
			<button
				type="button"
				class="rounded-lg bg-white/10 px-4 py-2 hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40"
				disabled={draft.rerolls_left === 0}
				onclick={onreroll}
			>
				Reroll
			</button>
		</div>
	</div>
</div>
