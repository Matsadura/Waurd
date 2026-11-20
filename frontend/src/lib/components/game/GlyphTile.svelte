<script lang="ts">
	import type { Effect } from '#lib/game/types.ts';

	let {
		letters,
		value,
		effect,
		order = null,
		bonus = null,
		selected = false,
		dim = false,
		size = 'md',
		onclick
	}: {
		letters: string;
		value: number;
		effect: Effect;
		order?: number | null;
		bonus?: string | null;
		selected?: boolean;
		dim?: boolean;
		size?: 'sm' | 'md';
		onclick?: () => void;
	} = $props();

	const LABEL: Record<Effect, string> = {
		DAMAGE: 'damage',
		DEFENSE: 'defense',
		HEAL: 'heal',
		WEAK: 'weak · turns',
		VULNERABLE: 'vulnerable · turns'
	};
	const TONE: Record<Effect, string> = {
		DAMAGE: 'border-b-[#ef4637] text-[#ff7a66]',
		DEFENSE: 'border-b-[#2fb5a6] text-[#5fe0cf]',
		HEAL: 'border-b-[#2fb5a6] text-[#5fe0cf]',
		WEAK: 'border-b-[#f0b955] text-[#f0b955]',
		VULNERABLE: 'border-b-[#f0b955] text-[#f0b955]'
	};

	const classes = $derived([
		'relative flex flex-col justify-between rounded-lg border border-white/15 border-b-4 bg-[#1c1a24] text-left shadow-[0_3px_6px_rgba(0,0,0,0.45)] transition',
		size === 'md' ? 'h-24 w-16 p-2 sm:h-28 sm:w-20' : 'h-16 w-12 p-1.5',
		TONE[effect],
		selected && '-translate-y-2 ring-2 ring-accent-action',
		dim && 'opacity-40'
	]);
</script>

{#snippet face()}
	{#if order !== null}
		<span
			class="absolute -top-2 -left-2 grid size-6 place-items-center rounded-full bg-accent-action text-sm font-bold text-white"
		>
			{order}
		</span>
	{/if}
	{#if bonus}
		<span class="absolute top-1 right-1 text-xs text-[#f0b955]" aria-label="Has a bonus slot"
			>★</span
		>
	{/if}
	<span
		class={['font-mono font-bold text-white', size === 'md' ? 'text-2xl sm:text-3xl' : 'text-lg']}
		>{letters}</span
	>
	<span class="flex items-baseline justify-between gap-1">
		<span class={['font-mono font-bold', size === 'md' ? 'text-lg' : 'text-sm']}>{value}</span>
		{#if size === 'md'}<span class="text-[0.6rem] leading-tight text-white/60">{LABEL[effect]}</span
			>{/if}
	</span>
{/snippet}

{#if onclick}
	<button
		type="button"
		{onclick}
		title={bonus ? `Bonus slot: ${bonus}` : undefined}
		aria-pressed={selected}
		class={[
			classes,
			'cursor-pointer hover:-translate-y-1 hover:brightness-110 focus-visible:outline-2 focus-visible:outline-white'
		]}
	>
		{@render face()}
	</button>
{:else}
	<div title={bonus ? `Bonus slot: ${bonus}` : undefined} class={classes}>
		{@render face()}
	</div>
{/if}
