<script lang="ts">
	import { page } from '$app/state';

	type Result = 'win' | 'loss' | 'draw';

	type Match = {
		id: number;
		opponent: string;
		opponentElo: number;
		playerElo: number;
		score: string;
		result: Result;
		mode: string;
		turns: number;
		date: string;
	};

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

	// `result` should come from the backend later, so we never parse it from the score text.
	const matches: Match[] = [
		{
			id: 1,
			opponent: 'sakibbbb',
			opponentElo: 580,
			playerElo: 606,
			score: '1–0',
			result: 'win',
			mode: '5 min',
			turns: 10,
			date: 'Oct 6, 2026'
		},
		{
			id: 2,
			opponent: 'darky',
			opponentElo: 625,
			playerElo: 606,
			score: '0–1',
			result: 'loss',
			mode: '1 min',
			turns: 16,
			date: 'Sep 19, 2026'
		},
		{
			id: 3,
			opponent: 'assan',
			opponentElo: 601,
			playerElo: 606,
			score: '½–½',
			result: 'draw',
			mode: '10 min',
			turns: 8,
			date: 'Sep 14, 2026'
		},
		{
			id: 4,
			opponent: 'shadowfox',
			opponentElo: 590,
			playerElo: 606,
			score: '1–0',
			result: 'win',
			mode: '5 min',
			turns: 12,
			date: 'Sep 9, 2026'
		},
		{
			id: 5,
			opponent: 'novastrike',
			opponentElo: 612,
			playerElo: 606,
			score: '0–1',
			result: 'loss',
			mode: '5 min',
			turns: 14,
			date: 'Sep 2, 2026'
		}
	];

	// Each result gets a letter AND a color, so it never relies on color alone.
	const resultStyles: Record<Result, { letter: string; label: string; classes: string }> = {
		win: {
			letter: 'W',
			label: 'Win',
			classes: 'border-green-400/50 bg-green-400/15 text-green-400'
		},
		loss: {
			letter: 'L',
			label: 'Loss',
			classes: 'border-red-400/50 bg-red-400/15 text-red-400'
		},
		draw: {
			letter: 'D',
			label: 'Draw',
			classes: 'border-white/30 bg-white/10 text-text-primary/70'
		}
	};

	const recentForm = matches.slice(0, 5);

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

<!-- Result badge (W / L / D) + score, shared by the table and the mobile cards -->
{#snippet resultChip(match: Match)}
	{@const style = resultStyles[match.result]}
	<span class="inline-flex items-center gap-2">
		<span
			class={[
				'inline-flex size-6 items-center justify-center rounded-full border text-xs font-bold',
				style.classes
			]}
			aria-hidden="true"
		>
			{style.letter}
		</span>
		<span class="sr-only">{style.label}:</span>
		<span class="font-bold tabular-nums">{match.score}</span>
	</span>
{/snippet}

<section
	class="mx-auto w-full max-w-4xl space-y-5 px-3 py-5 font-serif text-text-primary sm:px-4 sm:py-6"
>
	<!-- Profile header -->
	<header
		class="frame reveal relative border border-white/30 bg-gray-950/60 shadow-xl
			shadow-accent/10 backdrop-blur-sm"
		style:--i="0"
	>
		<!-- Layout: avatar on the left; name + Edit Profile, level bar and meta row on the right.
		     On mobile the level bar and meta row drop below and use the full width. -->
		<div class="grid grid-cols-[auto_1fr_auto] items-start gap-x-5 gap-y-3 p-4 sm:p-6">
			<!-- Avatar (placeholder, will become an image later) with the level emblem -->
			<div class="relative shrink-0 sm:row-span-3">
				<div
					class="flex size-16 items-center justify-center border border-accent/40
						bg-white/10 text-2xl font-bold text-accent sm:size-32 sm:text-5xl"
					aria-label="Player avatar placeholder"
				>
					K
				</div>

				<!-- Level emblem: a rotated square (diamond) with the number straightened inside -->
				<div
					class="absolute -right-2.5 -bottom-2.5 flex size-7 rotate-45 items-center
						justify-center border-2 border-accent bg-gray-950 shadow-[0_0_12px]
						shadow-accent/60 sm:-right-3 sm:-bottom-3 sm:size-9"
					role="img"
					aria-label="Level {player.level}"
				>
					<span class="-rotate-45 text-xs font-bold text-accent sm:text-sm">
						{player.level}
					</span>
				</div>
			</div>

			<!-- Top row, left: name + online status -->
			<div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 self-center">
				<h1 class="text-xl font-bold wrap-break-word sm:text-3xl">
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

			<!-- Top row, right: Edit Profile (icon only on mobile) -->
			<a
				href="/settings"
				class="inline-flex size-10 shrink-0 items-center justify-center gap-2 self-center
					rounded-lg bg-accent-action font-bold text-white
					shadow-[0_2px_4px_rgba(0,0,0,0.4)] transition
					hover:shadow-lg hover:shadow-accent-action/40 hover:brightness-110
					focus-visible:outline-2 focus-visible:outline-offset-[3px]
					focus-visible:outline-white sm:w-auto sm:px-5
					motion-safe:hover:-translate-y-0.5 motion-safe:active:translate-y-0
					motion-safe:active:scale-[0.97]"
			>
				<svg
					viewBox="0 0 24 24"
					class="size-5 sm:hidden"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M12 20h9" />
					<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
				</svg>
				<span class="sr-only sm:not-sr-only">Edit Profile</span>
			</a>

			<!-- Level and XP: runs from the avatar to the right edge of the card -->
			<div class="col-span-3 space-y-1.5 sm:col-span-2 sm:col-start-2">
				<div class="flex items-center justify-between gap-3 text-sm">
					<span class="font-bold text-accent">Level {player.level}</span>
					<span class="text-xs text-text-primary/60">
						{player.xp} / {player.nextLevelXp} XP
					</span>
				</div>

				<!-- No overflow-hidden on the track, or it would clip the glow -->
				<div
					class="h-2.5 rounded-full bg-white/10"
					role="progressbar"
					aria-label="Experience progress"
					aria-valuemin={0}
					aria-valuemax={player.nextLevelXp}
					aria-valuenow={player.xp}
				>
					<div
						class="xp-fill h-full rounded-full bg-accent shadow-[0_0_10px] shadow-accent/70"
						style:width="{xpProgress}%"
					></div>
				</div>
			</div>

			<!-- Bottom row: join date and friends on the left, recent form on the right -->
			<div
				class="col-span-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm
					text-text-primary/60 sm:col-span-2 sm:col-start-2"
			>
				<span>Joined {player.joined}</span>
				<span>•</span>
				<a href="/profile/friends" class="transition-colors hover:text-accent">
					{player.friends} Friends
				</a>

				<!-- Recent form: last 5 results, newest first -->
				<div class="flex items-center gap-2 sm:ml-auto">
					<span>Recent form</span>
					<ul class="flex gap-1.5">
						{#each recentForm as match (match.id)}
							{@const style = resultStyles[match.result]}
							<li
								class={[
									'flex size-6 items-center justify-center rounded-full border text-xs font-bold',
									style.classes
								]}
								title="{style.label} vs {match.opponent}"
							>
								<span aria-hidden="true">{style.letter}</span>
								<span class="sr-only">{style.label} vs {match.opponent}</span>
							</li>
						{/each}
					</ul>
				</div>
			</div>
		</div>

		<!-- Profile navigation (same orange underline as the login/register tabs) -->
		<nav aria-label="Profile sections" class="border-t border-white/20 max-md:overflow-x-auto">
			<div class="flex min-w-max items-center gap-1 px-2 sm:gap-3 sm:px-4">
				{#each profileTabs as tab (tab.href)}
					<a
						href={tab.href}
						aria-current={isActiveTab(tab.href) ? 'page' : undefined}
						class={[
							'inline-flex min-h-12 items-center border-b-2 px-3 text-sm font-bold transition-colors sm:px-4 sm:text-base',
							'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent',
							isActiveTab(tab.href)
								? 'border-b-accent text-accent'
								: 'border-b-transparent text-text-primary/60 hover:border-b-accent/60 hover:text-text-primary'
						]}
					>
						{tab.label}
					</a>
				{/each}
			</div>
		</nav>
	</header>

	<!-- Player statistics -->
	<section aria-label="Player statistics">
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each stats as stat, i (stat.label)}
				<!-- Not clickable, so hover only brightens the border and adds a glow (no lift) -->
				<div
					class="reveal flex min-w-0 items-center gap-3 border border-white/30 bg-gray-950/60
						p-3 backdrop-blur-sm transition hover:border-accent/60 hover:shadow-lg
						hover:shadow-accent/15 sm:p-4"
					style:--i={i + 1}
				>
					<span
						class="flex size-9 shrink-0 items-center justify-center text-2xl text-accent"
						aria-hidden="true"
					>
						{stat.icon}
					</span>

					<div class="min-w-0">
						<p class="text-sm text-text-primary/60">{stat.label}</p>
						<p class="text-2xl leading-tight font-bold sm:text-3xl">{stat.value}</p>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Game history -->
	<section
		aria-labelledby="history-heading"
		class="frame reveal relative border border-white/30 bg-gray-950/60 shadow-xl
			shadow-accent/10 backdrop-blur-sm"
		style:--i="5"
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
					{#each matches as match (match.id)}
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

							<td class="px-3 py-4">
								{@render resultChip(match)}
							</td>

							<td class="px-3 py-4 whitespace-nowrap text-text-primary/70">
								<span class="text-accent">⚡</span>
								{match.mode}
							</td>

							<td class="px-3 py-4 text-text-primary/70">
								{match.turns}
							</td>

							<td class="px-4 py-4 text-right whitespace-nowrap text-text-primary/60">
								{match.date}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Mobile match cards -->
		<div class="divide-y divide-white/10 md:hidden">
			{#each matches as match (match.id)}
				<article class="space-y-3 p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 space-y-1">
							<p class="font-bold wrap-break-word">
								{player.username}
								<span class="text-sm font-normal text-text-primary/50">
									({match.playerElo})
								</span>
							</p>

							<p class="text-sm wrap-break-word text-text-primary/70">
								vs. {match.opponent}
								<span class="text-text-primary/50">
									({match.opponentElo})
								</span>
							</p>
						</div>

						<div class="shrink-0 text-lg">
							{@render resultChip(match)}
						</div>
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
			class="flex min-h-12 items-center justify-center gap-2 border-t border-white/10
				px-4 py-3 text-sm font-bold text-accent transition-colors
				hover:bg-white/5 active:bg-white/10"
		>
			Show more games
			<span aria-hidden="true">→</span>
		</a>
	</section>
</section>

<style>
	/* Entrance animations only run if the user hasn't asked for reduced motion */
	@media (prefers-reduced-motion: no-preference) {
		/* Panels and stat cards fade up one after another (--i sets the order) */
		.reveal {
			animation: rise 0.5s ease-out backwards;
			animation-delay: calc(var(--i, 0) * 70ms);
		}

		/* The XP bar fills from empty to its real width */
		.xp-fill {
			animation: fill 0.9s ease-out 0.3s backwards;
		}
	}

	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
	}

	@keyframes fill {
		from {
			width: 0;
		}
	}

	.frame::before,
	.frame::after {
		content: '';
		position: absolute;
		width: 18px;
		height: 18px;
		border: 2px solid var(--color-accent);
		pointer-events: none;
	}
	.frame::before {
		top: -2px;
		left: -2px;
		border-right: 0;
		border-bottom: 0;
	}
	.frame::after {
		right: -2px;
		bottom: -2px;
		border-left: 0;
		border-top: 0;
	}
</style>
