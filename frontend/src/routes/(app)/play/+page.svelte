<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '#lib/api.ts';

	type Ticket = {
		status: 'QUEUED' | 'CLAIMING' | 'MATCHED' | 'WAITING' | 'ACTIVE' | 'CANCELLED';
		time_control_seconds: number;
		matched_match_id: string | null;
	};
	type Lobby = { id: string; invite_code: string | null; time_control_seconds: number };

	const CLOCKS = [
		{ seconds: 180, label: '3 min', hint: 'Fast' },
		{ seconds: 300, label: '5 min', hint: 'Standard' },
		{ seconds: 600, label: '10 min', hint: 'Relaxed' }
	];

	let seconds = $state(300);
	let mode = $state<'idle' | 'queued' | 'lobby'>('idle');
	let lobby = $state<Lobby | null>(null);
	let code = $state('');
	let error = $state('');
	let busy = $state(false);

	async function check(): Promise<void> {
		try {
			const ticket = await api<Ticket>('/matchmaking/status');
			if (ticket.status === 'MATCHED' && ticket.matched_match_id) {
				await goto(`/play/${ticket.matched_match_id}`);
				return;
			}
			if (ticket.status === 'QUEUED' || ticket.status === 'CLAIMING') {
				mode = 'queued';
				seconds = ticket.time_control_seconds;
			}
		} catch {
			// 404: not queued and not in a match.
			if (mode === 'queued') mode = 'idle';
		}
	}

	$effect(() => {
		check();
		const timer = setInterval(() => {
			if (mode !== 'idle') check();
		}, 1500);
		return () => clearInterval(timer);
	});

	async function run(task: () => Promise<void>): Promise<void> {
		error = '';
		busy = true;
		try {
			await task();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Something went wrong.';
		} finally {
			busy = false;
		}
	}

	const findMatch = () =>
		run(async () => {
			await api('/matchmaking/queue', { method: 'POST', body: { time_control_seconds: seconds } });
			mode = 'queued';
		});

	const leaveQueue = () =>
		run(async () => {
			await api('/matchmaking/queue', {
				method: 'DELETE',
				body: { time_control_seconds: seconds }
			});
			mode = 'idle';
		});

	const createLobby = () =>
		run(async () => {
			lobby = await api<Lobby>('/matchmaking/matches/custom', {
				method: 'POST',
				body: { time_control_seconds: seconds }
			});
			mode = 'lobby';
		});

	const cancelLobby = () =>
		run(async () => {
			if (lobby) await api(`/matchmaking/matches/${lobby.id}`, { method: 'DELETE' });
			lobby = null;
			mode = 'idle';
		});

	const joinLobby = (event: SubmitEvent) => {
		event.preventDefault();
		return run(async () => {
			const match = await api<Lobby>('/matchmaking/matches/join', {
				method: 'POST',
				body: { invite_code: code.trim().toUpperCase() }
			});
			await goto(`/play/${match.id}`);
		});
	};
</script>

<svelte:head>
	<title>Play · Waurd</title>
</svelte:head>

<section class="mx-auto flex max-w-3xl flex-col gap-6 p-4 sm:p-6">
	<header>
		<h1 class="font-henny-penny text-4xl text-accent-action sm:text-5xl">Play</h1>
		<p class="mt-1 text-lg text-white/70">Spell words, deal damage, outlast your opponent.</p>
	</header>

	{#if mode === 'queued'}
		<div
			class="flex flex-col items-center gap-4 rounded-2xl border border-white/10 bg-black/45 p-8 text-center"
		>
			<div
				class="size-12 animate-spin rounded-full border-4 border-white/20 border-t-accent-action"
				aria-hidden="true"
			></div>
			<p class="text-2xl">Finding an opponent…</p>
			<p class="text-white/60">
				{seconds / 60}-minute clock. This page opens the match when one is found.
			</p>
			<button
				type="button"
				class="rounded-lg bg-white/10 px-5 py-2 hover:bg-white/20"
				disabled={busy}
				onclick={leaveQueue}
			>
				Cancel
			</button>
		</div>
	{:else if mode === 'lobby' && lobby}
		<div
			class="flex flex-col items-center gap-4 rounded-2xl border border-white/10 bg-black/45 p-8 text-center"
		>
			<p class="text-white/70">Share this code with your friend</p>
			<p class="font-mono text-5xl tracking-[0.3em] text-accent-action" aria-label="Invite code">
				{lobby.invite_code}
			</p>
			<p class="text-white/60">
				Waiting for them to join… ({lobby.time_control_seconds / 60}-minute clock)
			</p>
			<button
				type="button"
				class="rounded-lg bg-white/10 px-5 py-2 hover:bg-white/20"
				disabled={busy}
				onclick={cancelLobby}
			>
				Cancel lobby
			</button>
		</div>
	{:else}
		<fieldset class="flex flex-col gap-3">
			<legend class="mb-2 text-xl">Clock per player</legend>
			<div class="grid grid-cols-3 gap-3">
				{#each CLOCKS as clock (clock.seconds)}
					<label
						class={[
							'flex cursor-pointer flex-col items-center rounded-xl border bg-black/45 p-3 text-center transition',
							seconds === clock.seconds
								? 'border-accent-action'
								: 'border-white/10 hover:border-white/30'
						]}
					>
						<input
							type="radio"
							name="clock"
							class="sr-only"
							value={clock.seconds}
							bind:group={seconds}
						/>
						<span class="text-2xl">{clock.label}</span>
						<span class="text-sm text-white/60">{clock.hint}</span>
					</label>
				{/each}
			</div>
		</fieldset>

		<div class="grid gap-3 sm:grid-cols-2">
			<button
				type="button"
				class="rounded-xl bg-accent-action px-5 py-4 text-2xl text-white shadow-[0_4px_8px_rgba(0,0,0,0.45)] hover:brightness-110 disabled:opacity-50"
				disabled={busy}
				onclick={findMatch}
			>
				Find a match
			</button>
			<button
				type="button"
				class="rounded-xl border border-white/20 bg-black/45 px-5 py-4 text-2xl hover:border-white/40 disabled:opacity-50"
				disabled={busy}
				onclick={createLobby}
			>
				Private lobby
			</button>
		</div>

		<form class="flex flex-col gap-2 sm:flex-row sm:items-end" onsubmit={joinLobby}>
			<label class="flex grow flex-col gap-1">
				<span class="text-lg">Have an invite code?</span>
				<input
					id="invite-code"
					bind:value={code}
					maxlength="6"
					placeholder="ABC123"
					class="h-11 rounded-lg border-0 bg-[#2d353c] px-4 font-mono text-lg tracking-widest text-white uppercase"
				/>
			</label>
			<button
				type="submit"
				class="h-11 rounded-lg bg-white/10 px-5 hover:bg-white/20 disabled:opacity-50"
				disabled={busy || code.trim().length !== 6}
			>
				Join
			</button>
		</form>
	{/if}

	<p class="min-h-6 text-[#ff6b5e]" role="alert">{error}</p>
</section>
