<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import Stat from '#lib/components/ui/Stat.svelte';
	import { fade, fly } from 'svelte/transition';

	type TimeControl = {
		minutes: 3 | 5 | 10;
		label: string;
		pace: string;
	};

	const timeControls: TimeControl[] = [
		{ minutes: 3, label: '3 min', pace: 'Blitz' },
		{ minutes: 5, label: '5 min', pace: 'Rapid' },
		{ minutes: 10, label: '10 min', pace: 'Standard' }
	];

	// Placeholder open challenges to populate the lobby; replace with live WebSocket/load data
	const openChallenges = [
		{ id: 'c1', challenger: 'sakibbbb', elo: '580', minutes: 5, mode: 'Ranked' },
		{ id: 'c2', challenger: 'assan', elo: '601', minutes: 10, mode: 'Ranked' },
		{ id: 'c3', challenger: 'shadowfox', elo: '590', minutes: 3, mode: 'Casual' }
	];

	let queuedMinutes = $state<3 | 5 | 10 | null>(null);

	function startQuickMatch(minutes: 3 | 5 | 10) {
		queuedMinutes = queuedMinutes === minutes ? null : minutes;
		// Hook into your WebSocket matchmaking message here
	}

	function createPrivateGame() {
		queuedMinutes = null;
		// Trigger private room creation / navigation here
	}
</script>

<Frame variant="torn" class="mx-auto max-w-5xl py-6 sm:p-10">
	<header class="flex flex-wrap items-end justify-between gap-4">
		<div>
			<h1 class="text-3xl text-bone sm:text-4xl">Enter the Arena</h1>
			<p class="mt-1 text-sm italic opacity-75">
				Select a time control for ranked matchmaking or forge a private duel.
			</p>
		</div>
	</header>

	<Divider class="my-6" />

	<div class="grid items-start gap-8">
		<!-- Left column: Time controls, Private game, and Open challenges -->
		<section aria-label="Matchmaking">
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
				{#each timeControls as tc (tc.minutes)}
					{@const isQueued = queuedMinutes === tc.minutes}
					<Button
						variant={isQueued ? 'primary' : 'secondary'}
						outline={!isQueued}
						size="lg"
						class="flex h-28 flex-col items-center justify-center gap-1"
						onclick={() => startQuickMatch(tc.minutes)}
					>
						<span class="text-2xl sm:text-3xl">{tc.label}</span>
						<span class="text-xs tracking-wider uppercase opacity-75">
							{isQueued ? 'Searching...' : tc.pace}
						</span>
					</Button>
				{/each}
			</div>

			<div class="mt-4">
				<Button
					variant="primary"
					size="lg"
					class="w-full justify-center"
					onclick={createPrivateGame}
				>
					Private game
				</Button>
			</div>

			{#if queuedMinutes}
				<div in:fade class="mt-4 flex flex-wrap items-center justify-between gap-3">
					<Notice variant="info" class="flex-1">
						Searching for a <span class="font-bold font-body text-xl">{queuedMinutes}</span> min opponent<span class="animate-ping">...</span>
					</Notice>
					<Button variant="danger" outline size="sm" onclick={() => (queuedMinutes = null)}>
						Cancel
					</Button>
				</div>
			{/if}

			<Divider class="my-6" />

			<!-- <div>
				<h2 class="mb-2 text-xl text-bone sm:text-2xl">
					Open challenges <span class="text-base opacity-60">({openChallenges.length})</span>
				</h2>

				<div>
					{#each openChallenges as challenge (challenge.id)}
						<Row
							href={`/play/challenge/${challenge.id}`}
							title={challenge.challenger}
							note={challenge.elo}
							subtitle={`${challenge.minutes} min · ${challenge.mode}`}
						>
							<span class="text-sm tracking-wide uppercase opacity-85 group-hover:opacity-100">
								Accept
							</span>
						</Row>
					{/each}
				</div>
			</div> -->
		</section>
		
	</div>
</Frame>
