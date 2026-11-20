<script lang="ts">
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import { session } from '#lib/session.svelte.ts';
	import { MatchConnection, END_REASONS } from '#lib/game/match.svelte.ts';
	import type { Glyph, Perk } from '#lib/game/types.ts';
	import GlyphTile from '#lib/components/game/GlyphTile.svelte';
	import PlayerPanel from '#lib/components/game/PlayerPanel.svelte';
	import DraftDialog from '#lib/components/game/DraftDialog.svelte';
	import EndDialog from '#lib/components/game/EndDialog.svelte';

	type MatchInfo = {
		player1: { id: string; username: string };
		player2: { id: string; username: string } | null;
		time_control_seconds: number;
	};

	const matchId = page.params.id ?? '';
	const me = session.user?.id ?? '';

	let names = $state<Record<string, string>>({});
	let catalog = $state(new Map<string, Perk>());
	let selected = $state<string[]>([]);
	let armed = $state<string | null>(null);
	let confirmResign = $state(false);
	let now = $state(performance.now());

	const match = new MatchConnection(
		matchId,
		me,
		(id) => names[id] ?? 'Opponent',
		() => catalog
	);

	$effect(() => {
		api<MatchInfo>(`/matchmaking/matches/${matchId}`)
			.then((info) => {
				names = Object.fromEntries(
					[info.player1, info.player2].filter((p) => p !== null).map((p) => [p.id, p.username])
				);
			})
			.catch(() => {});
		api<Perk[]>('/perks')
			.then((perks) => (catalog = new Map(perks.map((p) => [p.id, p]))))
			.catch(() => {});
		match.open();
		const ticker = setInterval(() => (now = performance.now()), 250);
		return () => {
			clearInterval(ticker);
			match.close();
		};
	});

	const snap = $derived(match.snapshot);
	const mine = $derived(snap?.players.find((p) => p.id === me) ?? null);
	const theirs = $derived(snap?.players.find((p) => p.id !== me) ?? null);
	const hand = $derived<Glyph[]>(snap?.hand ?? []);
	const canAct = $derived(match.isMyTurn && snap?.phase === 'ACTION');
	const word = $derived(
		selected.map((id) => hand.find((g) => g.id === id)?.letters ?? '').join('')
	);
	const armedPerk = $derived(snap?.perks.find((p) => p.instance_id === armed) ?? null);
	const armedTarget = $derived(
		armedPerk ? catalog.get(armedPerk.perk_id)?.target_glyph_type : null
	);

	// Drop selections of glyphs that left the hand.
	$effect(() => {
		const ids = new Set(hand.map((g) => g.id));
		if (selected.some((id) => !ids.has(id))) selected = selected.filter((id) => ids.has(id));
		if (!canAct) armed = null;
	});

	function clockFor(userId: string): number {
		if (!snap) return 0;
		const base = snap.clocks[userId] ?? 0;
		return snap.clock_running_for === userId ? base - (now - match.snapshotAt) : base;
	}

	function supports(glyph: Glyph): boolean {
		return !armedTarget || armedTarget === 'ANY' || armedTarget === glyph.type;
	}

	function tap(glyph: Glyph, index: number): void {
		if (!canAct || !snap) return;
		if (armedPerk) {
			if (!supports(glyph)) return;
			match.send('APPLY_PERK', {
				turn: snap.turn,
				glyph_index: index,
				perk_instance_id: armedPerk.instance_id
			});
			armed = null;
			return;
		}
		selected = selected.includes(glyph.id)
			? selected.filter((id) => id !== glyph.id)
			: [...selected, glyph.id];
	}

	function cast(): void {
		if (!snap || selected.length === 0) return;
		const sequence = selected.map((id) => hand.findIndex((g) => g.id === id));
		match.send('CAST_WORD', { turn: snap.turn, glyph_sequence: sequence });
		selected = [];
	}

	function pass(): void {
		if (!snap) return;
		match.send('PASS_TURN', { turn: snap.turn });
		selected = [];
	}

	function perkName(perkId: string | null): string | null {
		return perkId ? (catalog.get(perkId)?.name ?? perkId) : null;
	}
</script>

<svelte:head>
	<title>Match · Waurd</title>
</svelte:head>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (armed = null)} />

<section class="mx-auto flex max-w-5xl flex-col gap-4 p-3 sm:p-6">
	{#if match.closedReason}
		<div class="rounded-xl border border-accent-red bg-black/60 p-6 text-center">
			<p class="text-xl">{match.closedReason}</p>
			<a href="/play" class="mt-4 inline-block rounded-lg bg-accent-action px-5 py-2 text-white"
				>Back to Play</a
			>
		</div>
	{:else if !snap || !mine || !theirs}
		<p class="p-6 text-lg text-white/70">Connecting to the match…</p>
	{:else}
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="text-lg text-white/80">
				{#if snap.phase === 'WAITING'}
					Waiting for both players…
				{:else if snap.phase === 'ENDED'}
					Match over after {snap.turn} turns
				{:else}
					Turn {snap.turn} · {match.isMyTurn
						? 'Your turn'
						: `${names[theirs.id] ?? 'Opponent'}'s turn`}
				{/if}
				{#if !match.connected}<span class="ml-2 text-accent-red">Reconnecting…</span>{/if}
			</p>
			{#if snap.phase !== 'ENDED'}
				{#if confirmResign}
					<span class="flex items-center gap-2">
						<span>Resign this match?</span>
						<button
							type="button"
							class="rounded-md bg-accent-red px-3 py-1"
							onclick={() => match.send('SURRENDER')}>Resign</button
						>
						<button
							type="button"
							class="rounded-md bg-white/10 px-3 py-1"
							onclick={() => (confirmResign = false)}>Keep playing</button
						>
					</span>
				{:else}
					<button
						type="button"
						class="rounded-md bg-white/10 px-3 py-1 hover:bg-white/20"
						onclick={() => (confirmResign = true)}>Resign</button
					>
				{/if}
			{/if}
		</div>

		{#if match.opponentAway !== null}
			<p class="rounded-lg bg-accent-red/20 px-4 py-2 text-[#ff9a8f]">
				Your opponent disconnected. They have {match.opponentAway} seconds to come back.
			</p>
		{/if}

		<PlayerPanel
			name={names[theirs.id] ?? 'Opponent'}
			player={theirs}
			maxHp={snap.max_hp}
			clockMs={clockFor(theirs.id)}
			active={snap.active_player_id === theirs.id && snap.phase !== 'ENDED'}
		/>

		<div class="grid gap-4 lg:grid-cols-[1fr_18rem]">
			<section
				class="flex min-h-40 flex-col gap-3 rounded-xl border border-white/10 bg-black/45 p-4"
				aria-label="Last word"
			>
				{#if match.lastWord}
					{@const last = match.lastWord}
					<p class="text-white/70">
						{last.player_id === me ? 'You' : (names[last.player_id] ?? 'Opponent')} cast
						<span class="font-mono text-2xl text-white">{last.word}</span>
					</p>
					<div class="flex flex-wrap gap-2">
						{#each last.steps as step (step.glyph_id)}
							<div class="flex flex-col items-center gap-1">
								<GlyphTile
									letters={step.letters}
									value={step.final_value}
									effect={step.effect}
									size="sm"
								/>
								{#if step.changes.length}
									<span class="text-xs text-white/60">{step.value}→{step.final_value}</span>
								{/if}
							</div>
						{/each}
					</div>
					<p class="text-sm text-white/80">
						{last.totals.damage} damage{last.damage_blocked
							? ` (${last.damage_blocked} blocked)`
							: ''} ·
						{last.totals.defense} Defense · {last.hp_healed} healed
						{#each last.statuses_applied as status (status.effect)}
							· {status.effect === 'WEAK' ? 'Weak' : 'Vulnerable'}{/each}
					</p>
				{:else}
					<p class="text-white/60">
						No words yet. Tap glyphs in order to spell a word, then press Cast.
					</p>
				{/if}
			</section>

			<section
				class="flex max-h-56 flex-col gap-1 overflow-y-auto rounded-xl border border-white/10 bg-black/45 p-3 text-sm"
				aria-label="Match log"
			>
				{#each match.log as entry (entry.id)}
					<p
						class={entry.tone === 'good'
							? 'text-[#5fe0cf]'
							: entry.tone === 'bad'
								? 'text-[#ff9a8f]'
								: 'text-white/70'}
					>
						{entry.text}
					</p>
				{/each}
			</section>
		</div>

		<PlayerPanel
			name={session.user?.username ?? 'You'}
			player={mine}
			maxHp={snap.max_hp}
			clockMs={clockFor(mine.id)}
			active={match.isMyTurn}
			you
		/>

		<section
			class="flex flex-col gap-3 rounded-xl border border-white/10 bg-black/45 p-4"
			aria-label="Your hand"
		>
			<div class="flex flex-wrap items-center justify-between gap-2">
				<p class="text-lg">
					{#if armedPerk}
						Tap a glyph for <strong>{perkName(armedPerk.perk_id)}</strong>
						<span class="text-white/60">(Esc to cancel)</span>
					{:else if canAct}
						Your word: <span class="font-mono text-2xl tracking-widest text-accent-action"
							>{word || '…'}</span
						>
					{:else if snap.phase === 'DRAFT' && match.isMyTurn}
						Pick a perk to end your turn.
					{:else}
						Waiting for your turn…
					{/if}
				</p>
				<div class="flex gap-2">
					<button
						type="button"
						class="rounded-lg bg-white/10 px-4 py-2 hover:bg-white/20 disabled:opacity-40"
						disabled={!canAct || selected.length === 0}
						onclick={() => (selected = [])}>Clear</button
					>
					<button
						type="button"
						class="rounded-lg bg-white/10 px-4 py-2 hover:bg-white/20 disabled:opacity-40"
						disabled={!canAct}
						onclick={pass}>Pass</button
					>
					<button
						type="button"
						class="rounded-lg bg-accent-action px-5 py-2 text-white hover:brightness-110 disabled:opacity-40"
						disabled={!canAct || selected.length === 0}
						onclick={cast}>Cast</button
					>
				</div>
			</div>

			{#if match.rejection}
				<p class="rounded-md bg-accent-red/20 px-3 py-1.5 text-[#ff9a8f]" role="alert">
					{match.rejection}
				</p>
			{/if}

			<div class="flex flex-wrap gap-3 pt-2">
				{#each hand as glyph, index (glyph.id)}
					<GlyphTile
						letters={glyph.letters}
						value={glyph.value}
						effect={glyph.effect}
						bonus={perkName(glyph.conditional_slot)}
						order={selected.includes(glyph.id) ? selected.indexOf(glyph.id) + 1 : null}
						selected={selected.includes(glyph.id)}
						dim={!canAct || (armedPerk !== null && !supports(glyph))}
						onclick={canAct ? () => tap(glyph, index) : undefined}
					/>
				{:else}
					<p class="text-white/50">Your hand is empty until your turn.</p>
				{/each}
			</div>

			{#if snap.perks.length}
				<div class="flex flex-col gap-2 border-t border-white/10 pt-3">
					<p class="text-sm text-white/60">Your perks: tap one, then tap a glyph</p>
					<div class="flex flex-wrap gap-2">
						{#each snap.perks as perk (perk.instance_id)}
							{@const info = catalog.get(perk.perk_id)}
							<button
								type="button"
								title={info?.description}
								class={[
									'rounded-lg border px-3 py-1.5 text-left text-sm transition disabled:opacity-40',
									armed === perk.instance_id
										? 'border-accent-action bg-accent-action/20'
										: 'border-white/15 bg-white/5 hover:border-white/40'
								]}
								disabled={!canAct}
								onclick={() => (armed = armed === perk.instance_id ? null : perk.instance_id)}
							>
								<span class="block">{info?.name ?? perk.perk_id}</span>
								<span class="block text-xs text-white/60"
									>{perk.durability ?? '∞'} uses · {info?.description ?? ''}</span
								>
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</section>
	{/if}
</section>

{#if match.draft && !match.ended}
	<DraftDialog
		draft={match.draft}
		onpick={(perkId) => snap && match.send('SELECT_PERKS', { turn: snap.turn, perk_ids: [perkId] })}
		onreroll={() => snap && match.send('REROLL_PERKS', { turn: snap.turn })}
	/>
{/if}

{#if match.ended}
	<EndDialog
		won={match.ended.winner_id === me}
		reason={END_REASONS[match.ended.end_reason] ?? match.ended.end_reason}
		eloDelta={match.ended.elo_delta[me] ?? null}
	/>
{/if}
