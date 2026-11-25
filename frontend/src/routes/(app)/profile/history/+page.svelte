<script lang="ts">
	import MatchRow from '#lib/components/profile/MatchRow.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Filter from '#lib/components/ui/Filter.svelte';
	import { matches, player } from '../mock';

	const PAGE_SIZE = 8;

	const filters = [
		{ label: 'All', value: 'all' },
		{ label: 'Victories', value: 'win' },
		{ label: 'Defeats', value: 'loss' }
	];

	let result = $state('all');
	let visible = $state(PAGE_SIZE);

	// Going back to the first page when the filter changes
	$effect(() => {
		result;
		visible = PAGE_SIZE;
	});

	const filtered = $derived(matches.filter((m) => result === 'all' || m.result === result));
	const shown = $derived(filtered.slice(0, visible));

	const losses = player.games - player.wins;
	const winRate = player.games ? Math.round((player.wins / player.games) * 100) : 0;
</script>

<svelte:head>
	<title>Duels · Profile</title>
</svelte:head>

<section aria-labelledby="duels">
	<h2 id="duels" class="font-display text-2xl">
		Chronicle of duels <span class="text-lg text-ash">({player.games})</span>
	</h2>
	<p class="text-ash italic">{player.wins} victories · {losses} defeats · {winRate}% win rate</p>

	<Filter bind:value={result} options={filters} label="Filter duels" class="mt-4 text-lg" />

	{#if shown.length}
		<ol class="mt-3 divide-y divide-bronze/20">
			{#each shown as match (match.id)}
				<li><MatchRow {match} /></li>
			{/each}
		</ol>
	{:else}
		<p class="mt-6 text-ash italic">No duels to show here.</p>
	{/if}

	{#if filtered.length > visible}
		<Button
			outline
			variant="secondary"
			size="sm"
			class="mt-4"
			onclick={() => (visible += PAGE_SIZE)}>Show more duels</Button
		>
	{/if}
</section>
