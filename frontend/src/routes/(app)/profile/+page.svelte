<script lang="ts">
	import { page } from '$app/state';

	// Temporary profile data
	const player = {
		username: 'kirito_1723',
		joined: 'Nov 10, 2024',
		friends: 11,
		online: true,
		level: 12,
		xp: 650,
		nextLevelXp: 1000,
		elo: 606,
		games: 28,
		wins: 18,
		winRate: 64
	};

	const xpProgress = Math.min((player.xp / player.nextLevelXp) * 100, 100);

	const stats = [
		{ label: 'Elo', value: player.elo, icon: '◈' },
		{ label: 'Games', value: player.games, icon: '⚔' },
		{ label: 'Wins', value: player.wins, icon: '♛' },
		{ label: 'Win Rate', value: `${player.winRate}%`, icon: '%' }
	];

	const profileTabs = [
		{ label: 'Overview', href: '/profile' },
		{ label: 'Games History', href: '/profile/history' },
		{ label: 'Friends', href: '/profile/friends' },
		{ label: 'Achievements', href: '/profile/achievements' },
		{ label: 'Collected Perks', href: '/profile/perks' }
	];

	const matches = [
		{
			opponent: 'sakibbbb',
			opponentElo: 580,
			playerElo: 606,
			score: '1–0',
			mode: '5 min',
			turns: 10,
			date: 'Oct 6, 2026'
		},
		{
			opponent: 'darky',
			opponentElo: 625,
			playerElo: 606,
			score: '0–1',
			mode: '1 min',
			turns: 16,
			date: 'Sep 19, 2026'
		},
		{
			opponent: 'assan',
			opponentElo: 601,
			playerElo: 606,
			score: '½–½',
			mode: '10 min',
			turns: 8,
			date: 'Sep 14, 2026'
		},
		{
			opponent: 'shadowfox',
			opponentElo: 590,
			playerElo: 606,
			score: '1–0',
			mode: '5 min',
			turns: 12,
			date: 'Sep 9, 2026'
		}
	];

	function isActiveTab(href: string): boolean {
		return page.url.pathname === href;
	}
</script>

<svelte:head>
	<title>Profile</title>
	<meta
		name="description"
		content="View your Waurd player profile, statistics, and game history."
	/>
</svelte:head>

<section class="mx-auto w-full max-w-4xl space-y-5 px-3 py-5 text-text-primary sm:px-4 sm:py-6">

	<!-- Profile header -->
	<header class="overflow-hidden  border border-white/50 bg-gray-900/40">

		<div class="flex flex-col gap-5 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">

			<div class="flex min-w-0 items-center gap-4 sm:gap-5">

				<!-- Avatar, will be replaced later with an image maybe :) -->
				<div
					class="flex size-20 shrink-0 items-center justify-center
						 border border-white/10 bg-white/10
						text-3xl font-bold text-accent sm:size-24"
					aria-label="Player avatar placeholder"
				>
					K
				</div>

				<div class="min-w-0 flex-1 space-y-2">

					<div class="flex flex-wrap items-center gap-2">
						<h1 class="wrap-break-word text-2xl font-bold sm:text-3xl">
							{player.username}
						</h1>

						{#if player.online}
							<span class="inline-flex items-center gap-1.5 text-xs text-green-400">
								<span class="size-1.5 rounded-full bg-green-400"></span>
								Online now
							</span>
						{:else}
							<span class="inline-flex items-center gap-1.5 text-xs text-red-400">
								<span class="size-1.5 rounded-full bg-red-400"></span>
								Offline
							</span>
						{/if}
					</div>

					<!-- Level and XP -->
					<div class="max-w-sm space-y-1.5">
						<div class="flex items-center justify-between gap-3 text-sm">
							<span class="font-bold text-accent">Level {player.level}</span>
							<span class="text-xs text-text-primary/55">
								{player.xp} / {player.nextLevelXp} XP
							</span>
						</div>

						<div
							class="h-2 overflow-hidden rounded-full bg-white/10"
							role="progressbar"
							aria-label="Experience progress"
							aria-valuemin={0}
							aria-valuemax={player.nextLevelXp}
							aria-valuenow={player.xp}
						>
							<div
								class="h-full rounded-full bg-accent transition-all"
								style={`width: ${xpProgress}%`}
							></div>
						</div>
					</div>

					<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-text-primary/55">
						<span>Joined {player.joined}</span>
						<span>•</span>
						<a href="/profile/friends" class="transition-colors hover:text-accent">
							{player.friends} Friends
						</a>
					</div>
				</div>
			</div>

			<a
				href="/settings"
				class="inline-flex min-h-10 shrink-0 items-center justify-center
					rounded-lg bg-accent-action px-5 py-2 text-base font-bold
					text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)]
					transition hover:brightness-[1.08]
					focus-visible:outline-2 focus-visible:outline-offset-[3px]
					focus-visible:outline-white"
			>
				Edit Profile
			</a>
		</div>

		<!-- Profile navigation -->
		 <nav
			aria-label="Profile sections"
			class="overflow-x-auto border-t border-white/10 px-2 py-3 sm:px-4"
		>
			<div class="flex min-w-max justify-center items-center gap-2">
				{#each profileTabs as tab (tab.href)}
					<a
						href={tab.href}
						aria-current={isActiveTab(tab.href) ? 'page' : undefined}
						class="profile-tab relative inline-flex min-h-10 items-center
							justify-center rounded-md bg-accent-red px-4 py-2
							text-sm font-bold text-white shadow-[0_4px_8px_rgba(0,0,0,0.3)]
							transition-opacity hover:opacity-90 sm:px-5 sm:text-base"
					>
						{tab.label}
					</a>
				{/each}
			</div>
		</nav>
		<!-- <nav
			aria-label="Profile sections"
			class="max-md:overflow-x-auto border-t border-white/10"
		>
			<div class="flex min-w-max items-center gap-1 px-2 sm:gap-3 sm:px-4">
				{#each profileTabs as tab (tab.href)}
					<a
						href={tab.href}
						aria-current={isActiveTab(tab.href) ? 'page' : undefined}
						class="profile-tab relative inline-flex min-h-12 items-center
							px-3 text-sm font-bold text-text-primary/60
							transition-colors hover:text-text-primary sm:px-4 sm:text-base"
					>
						{tab.label}
					</a>
				{/each}
			</div>
		</nav> -->
	</header>

	<!-- Player statistics -->
	<section aria-label="Player statistics">
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each stats as stat (stat.label)}
				<div class="flex min-w-0 items-center gap-3  border border-white/50 bg-gray-900/40 p-3 sm:p-4">
					<span class="flex size-9 shrink-0 items-center justify-center text-2xl text-accent" aria-hidden="true">
						{stat.icon}
					</span>

					<div class="min-w-0">
						<p class="text-sm text-text-primary/60">{stat.label}</p>
						<p class="text-2xl font-bold leading-tight sm:text-3xl">{stat.value}</p>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Game history -->
	<section
		aria-labelledby="history-heading"
		class="overflow-hidden  border border-white/10 shadow-md shadow-gray-500/30 bg-gray-900/40"
	>
		<div class="border-b border-white/10 px-4 py-4 sm:px-5">
			<h2 id="history-heading" class="text-lg font-bold sm:text-xl">
				Game History
				<span class="text-text-primary/50">({player.games})</span>
			</h2>
		</div>

		<!-- Desktop table -->
		<div class="hidden overflow-x-auto md:block">
			<table class="w-full text-left text-sm">
				<thead class="bg-white/5 text-accent">
					<tr>
						<th scope="col" class="px-4 py-3 font-bold">Players</th>
						<th scope="col" class="px-3 py-3 font-bold">Result</th>
						<th scope="col" class="px-3 py-3 font-bold">Time</th>
						<th scope="col" class="px-3 py-3 font-bold">Turns</th>
						<th scope="col" class="px-4 py-3 text-right font-bold">Date</th>
					</tr>
				</thead>

				<tbody class="divide-y divide-white/10">
					{#each matches as match (match.opponent)}
						<tr class="transition-colors hover:bg-white/5">
							<td class="px-4 py-4">
								<div class="space-y-1">
									<p class="font-bold">
										{player.username}
										<span class="font-normal text-text-primary/50">
											({match.playerElo})
										</span>
									</p>
									<p class="text-text-primary/70">
										vs. {match.opponent}
										<span class="text-text-primary/50">
											({match.opponentElo})
										</span>
									</p>
								</div>
							</td>

							<td class="px-3 py-4 font-bold tabular-nums">
								{match.score}
							</td>

							<td class="whitespace-nowrap px-3 py-4 text-text-primary/70">
								<span class="text-accent">⚡</span>
								{match.mode}
							</td>

							<td class="px-3 py-4 text-text-primary/70">
								{match.turns}
							</td>

							<td class="whitespace-nowrap px-4 py-4 text-right text-text-primary/55">
								{match.date}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Mobile match cards -->
		<div class="divide-y divide-white/10 md:hidden">
			{#each matches as match (match.opponent)}
				<article class="space-y-3 p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 space-y-1">
							<p class="wrap-break-word font-bold">
								{player.username}
								<span class="text-sm font-normal text-text-primary/50">
									({match.playerElo})
								</span>
							</p>

							<p class="wrap-break-word text-sm text-text-primary/70">
								vs. {match.opponent}
								<span class="text-text-primary/50">
									({match.opponentElo})
								</span>
							</p>
						</div>

						<span class="shrink-0 text-lg font-bold tabular-nums">
							{match.score}
						</span>
					</div>

					<div class="flex flex-wrap gap-x-4 gap-y-2 text-xs text-text-primary/60">
						<span><span class="text-accent">⚡</span> {match.mode}</span>
						<span>{match.turns} turns</span>
						<span>{match.date}</span>
					</div>
				</article>
			{/each}
		</div>

		<a
			href="/profile/history"
			class="flex min-h-12 items-center justify-center gap-2
				border-t border-white/10 px-4 py-3 text-sm font-bold
				text-accent transition-colors hover:bg-white/5"
		>
			Show more games
			<span aria-hidden="true">→</span>
		</a>
	</section>
</section>

<style>
	/* .profile-tab[aria-current='page'] {
		color: var(--color-accent);
	} */

	.profile-tab[aria-current='page']::before {
		content: '';
		position: absolute;
		top: -0.5rem;
		left: 50%;
		transform: translateX(-50%);
		border-top: 0.5rem solid var(--color-accent-red);
		border-left: 0.4rem solid transparent;
		border-right: 0.4rem solid transparent;
	}
</style>
