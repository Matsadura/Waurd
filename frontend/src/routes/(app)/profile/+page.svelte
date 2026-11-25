<script lang="ts">
	import MatchRow from '#lib/components/profile/MatchRow.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import Stat from '#lib/components/ui/Stat.svelte';
	import { matches, player, rank } from './mock';

	const recent = matches.slice(0, 4);
</script>

<svelte:head>
	<title>Profile</title>
</svelte:head>

<div class="grid gap-8 lg:grid-cols-[1fr_21rem]">
	<section aria-labelledby="duels" class="order-2 lg:order-0">
		<h2 id="duels" class="font-display text-2xl">
			Chronicle of duels <span class="text-lg text-ash">({player.games})</span>
		</h2>
		<ol class="mt-3 divide-y divide-bronze/20">
			{#each recent as match (match.id)}
				<li><MatchRow {match} /></li>
			{/each}
		</ol>
		<Button href="/profile/history" outline variant="secondary" size="sm" class="mt-4"
			>Show more duels</Button
		>
	</section>

	<Frame variant="double-border" as="aside" aria-label="Player status" class="order-1 lg:order-0">
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