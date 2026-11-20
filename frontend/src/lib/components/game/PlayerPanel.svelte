<script lang="ts">
	import type { PlayerView } from '#lib/game/types.ts';

	let {
		name,
		player,
		maxHp,
		clockMs,
		active,
		you = false
	}: {
		name: string;
		player: PlayerView;
		maxHp: number;
		clockMs: number;
		active: boolean;
		you?: boolean;
	} = $props();

	const percent = $derived(Math.max(0, Math.min(100, (player.hp / maxHp) * 100)));
	const clock = $derived.by(() => {
		const total = Math.max(0, Math.ceil(clockMs / 1000));
		return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
	});
</script>

<section
	class={[
		'flex flex-col gap-2 rounded-xl border bg-black/45 p-3 backdrop-blur-sm sm:p-4',
		active
			? 'border-accent-action shadow-[0_0_0_1px_var(--color-accent-action)]'
			: 'border-white/10'
	]}
	aria-label={you ? 'You' : 'Opponent'}
>
	<div class="flex items-center justify-between gap-3">
		<div class="min-w-0">
			<p class="truncate text-xl leading-tight">{name}{you ? ' (you)' : ''}</p>
			<p class="text-sm text-white/60">
				{active ? (you ? 'Your turn' : 'Playing…') : 'Waiting'} · {player.hand_size} in hand · {player.draw_count}
				in deck
			</p>
		</div>
		<p
			class={[
				'shrink-0 rounded-md px-3 py-1 font-mono text-2xl tabular-nums',
				active ? 'bg-accent-action text-white' : 'bg-white/10 text-white/80',
				active && clockMs < 20000 && 'bg-accent-red'
			]}
			aria-label="Clock"
		>
			{clock}
		</p>
	</div>

	<div class="flex items-center gap-3">
		<div
			class="h-4 grow overflow-hidden rounded-full bg-white/10"
			role="meter"
			aria-valuemin="0"
			aria-valuemax={maxHp}
			aria-valuenow={player.hp}
			aria-label="HP"
		>
			<div
				class="h-full rounded-full bg-[#ef4637] transition-[width] duration-500"
				style={`width: ${percent}%`}
			></div>
		</div>
		<p class="w-20 shrink-0 text-right font-mono text-lg tabular-nums">{player.hp}/{maxHp}</p>
	</div>

	<div class="flex flex-wrap gap-2 text-sm">
		{#if player.defense > 0}
			<span class="rounded-full bg-[#2fb5a6]/20 px-2.5 py-0.5 text-[#5fe0cf]"
				>🛡 {player.defense} Defense</span
			>
		{/if}
		{#each player.statuses as status (status.effect)}
			<span class="rounded-full bg-[#f0b955]/20 px-2.5 py-0.5 text-[#f0b955]">
				{status.effect === 'WEAK' ? 'Weak' : 'Vulnerable'} · {status.turns_left}
			</span>
		{/each}
	</div>
</section>
