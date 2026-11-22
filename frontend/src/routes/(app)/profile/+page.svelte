<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import Stat from '#lib/components/ui/Stat.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';

	type Result = 'win' | 'loss';

	const player = {
		username: 'kirito_19',
		joined: 'Nov 10, 2024',
		friends: 11,
		online: true,
		level: 12,
		xp: 650,
		nextLevelXp: 1000,
		elo: 606,
		games: 28,
		wins: 18
	};

	const matches: {
		id: number;
		opponent: string;
		opponentElo: number;
		result: Result;
		mode: string;
		turns: number;
		date: string;
	}[] = [
		{
			id: 1,
			opponent: 'sakibbbb',
			opponentElo: 580,
			result: 'win',
			mode: '5 min',
			turns: 10,
			date: 'Oct 6, 2026'
		},
		{
			id: 2,
			opponent: 'darky',
			opponentElo: 625,
			result: 'loss',
			mode: '1 min',
			turns: 16,
			date: 'Sep 19, 2026'
		},
		{
			id: 3,
			opponent: 'assan',
			opponentElo: 601,
			result: 'win',
			mode: '10 min',
			turns: 8,
			date: 'Sep 14, 2026'
		},
		{
			id: 4,
			opponent: 'shadowfox',
			opponentElo: 590,
			result: 'win',
			mode: '5 min',
			turns: 12,
			date: 'Sep 9, 2026'
		}
	];

	const resultWord: Record<Result, string> = { win: 'Victory', loss: 'Defeat' };
	const resultColor: Record<Result, string> = {
		win: 'text-warning-light',
		loss: 'text-danger-light'
	};

	// Placeholder titles, the team should decide the real thresholds.
	const ranks: [number, string][] = [
		[0, 'change-me'],
		[500, 'change-me'],
		[800, 'change-me'],
		[1100, 'change-me'],
		[1400, 'change-me'],
		[1700, 'change-me']
	];
	const rank = [...ranks].reverse().find(([min]) => player.elo >= min)![1];

	const tabs = [
		{ label: 'Overview', href: '/profile' },
		{ label: 'Duels', href: '/profile/history' },
		{ label: 'Friends', href: '/profile/friends' },
		{ label: 'Achievements', href: '/profile/achievements' },
		{ label: 'Perks', href: '/profile/perks' }
	];
</script>

<svelte:head>
	<title>Profile</title>
</svelte:head>

<div class="mx-auto w-full max-w-5xl px-3 py-6 font-body text-bone sm:px-4">
	<Frame class="fade-in">
		<header class="flex flex-wrap items-start justify-between gap-x-8 gap-y-5">
			<div class="flex items-center gap-4">
				<Avatar name={player.username} class="sm:size-20 sm:text-4xl" />
				<div class="min-w-0">
					<h1 class="text-3xl wrap-break-word sm:text-4xl">{player.username}</h1>
					<p class="text-lg text-ash">
						<span class="font-bold">{rank}</span>
						<span class="ml-3 inline-flex items-center gap-1.5 text-base not-italic">
							<span
								class={['size-2 rounded-full', player.online ? 'bg-primary-light' : 'bg-secondary']}
							></span>
							{player.online ? 'Online now' : 'Offline'}
						</span>
					</p>
				</div>
			</div>

			<Tabs items={tabs} label="Profile sections" class="text-lg" />
		</header>

		<Divider class="my-6" />

		<div class="grid gap-8 lg:grid-cols-[1fr_21rem]">
			<section aria-labelledby="duels" class="order-2 lg:order-0">
				<h2 id="duels" class="font-display text-2xl">
					Chronicle of duels <span class="text-lg text-ash">({player.games})</span>
				</h2>
				<ol class="mt-3 divide-y divide-bronze/20">
					{#each matches as match (match.id)}
						<li>
							<Row
								href="/profile/history"
								title={match.opponent}
								note={String(match.opponentElo)}
								subtitle="{match.mode} · {match.turns} turns · {match.date}"
							>
								<span
									class={[
										'block text-lg group-hover:text-bone group-focus-visible:text-bone',
										resultColor[match.result]
									]}>{resultWord[match.result]}</span
								>
							</Row>
						</li>
					{/each}
				</ol>
				<Button href="/profile/history" outline variant="secondary" size="sm" class="mt-4"
					>Show more duels</Button
				>
			</section>

			<Frame
				variant="double-border"
				as="aside"
				aria-label="Player status"
				class="order-1 lg:order-0"
			>
				<Frame variant="border" class="text-lg">{player.username}</Frame>

				<dl class="mt-4 text-lg">
					<Stat label="Covenant">{rank}</Stat>
					<Stat label="Level">{player.level}</Stat>
					<Stat label="Experience">{player.xp} / {player.nextLevelXp}</Stat>
					<Meter value={player.xp} max={player.nextLevelXp} label="Experience" class="mt-1" />

					<Divider class="my-3" />

					<Stat label="Elo">{player.elo}</Stat>
					<Stat label="Duels">{player.games}</Stat>
					<Stat label="Victories">{player.wins}</Stat>

					<Divider class="my-3" />

					<Stat label="Friends">{player.friends}</Stat>
					<Stat label="Joined">{player.joined}</Stat>
				</dl>
			</Frame>
		</div>

		<Divider class="my-6" />

		<Button href="/settings">Edit Profile</Button>
	</Frame>
</div>
