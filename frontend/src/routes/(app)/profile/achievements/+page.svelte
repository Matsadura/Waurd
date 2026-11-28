<script lang="ts">
	import AchievementCard from '#lib/components/profile/AchievementCard.svelte';
	import Filter from '#lib/components/ui/Filter.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const filters = [
		{ label: 'All', value: 'all' },
		{ label: 'Achieved', value: 'done' },
		{ label: 'In progress', value: 'open' }
	];

	let status = $state('all');

	const isDone = (a: PageData['achievements'][number]) => a.completed;

	const doneCount = $derived(data.achievements.filter(isDone).length);

	const xpEarned = $derived(
		data.achievements.filter(isDone).reduce((sum, a) => sum + a.xpReward, 0)
	);

	const shown = $derived(
		data.achievements.filter((a) => status === 'all' || (status === 'done') === isDone(a))
	);
</script>

<svelte:head>
	<title>Achievements · Profile</title>
</svelte:head>

<section aria-labelledby="deeds">
	<h2 id="deeds" class="font-display text-2xl">
		Deeds achieved <span class="text-lg text-ash">({doneCount} / {data.achievements.length})</span>
	</h2>
	<p class="text-ash italic">{xpEarned} XP earned from your deeds</p>

	<Filter bind:value={status} options={filters} label="Filter achievements" class="mt-4 text-lg" />

	{#if shown.length}
		<ul class="mt-4 grid gap-4 md:grid-cols-2">
			{#each shown as achievement (achievement.id)}
				<li><AchievementCard {achievement} /></li>
			{/each}
		</ul>
	{:else}
		<p class="mt-6 text-ash italic">Nothing here yet.</p>
	{/if}
</section>
