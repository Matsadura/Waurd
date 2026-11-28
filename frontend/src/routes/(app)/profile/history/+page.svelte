<script lang="ts">
	import MatchRow from '#lib/components/profile/MatchRow.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const winRate = $derived(
		data.stats.games ? Math.round((data.stats.wins / data.stats.games) * 100) : 0
	);

	const pageNumbers = $derived.by(() => {
		const current = data.pagination.page;
		const total = data.pagination.pages;

		const start = Math.max(1, Math.min(current - 2, total - 4));
		const end = Math.min(total, start + 4);

		return Array.from({ length: Math.max(0, end - start + 1) }, (_, i) => start + i);
	});
</script>

<svelte:head>
	<title>Duels · Profile</title>
</svelte:head>

<section aria-labelledby="duels">
	<h2 id="duels" class="font-display text-2xl">
		Chronicle of duels
		<span class="text-lg text-ash">({data.pagination.total})</span>
	</h2>

	<p class="text-ash italic">
		{data.stats.wins} victories ·
		{data.stats.losses} defeats ·
		{winRate}% win rate
		{#if data.stats.draws > 0}
			· {data.stats.draws} draws
		{/if}
	</p>

	{#if data.pagination.total === 0}
		<div class="mt-6 border-l-2 border-bronze/40 py-4 pl-5">
			<p class="font-display text-xl text-bone">Your chronicle is empty</p>
			<p class="mt-2 text-lg text-ash italic">
				No battles have been recorded. Your victories and defeats will be written here once you
				enter the arena.
			</p>
		</div>
	{:else if data.matches.length === 0}
		<p class="mt-6 text-ash italic">No duels on this page.</p>
		<Button href="/profile/history" outline variant="secondary" size="sm" class="mt-4">
			Back to first page
		</Button>
	{:else}
		<ol class="mt-3 divide-y divide-bronze/20">
			{#each data.matches as match (match.id)}
				<li><MatchRow {match} /></li>
			{/each}
		</ol>

		<!-- maybe we do scrolling! -->

		{#if data.pagination.pages > 1}
			<nav
				aria-label="Duel history pages"
				class="mt-5 flex flex-wrap items-center justify-center gap-2"
			>
				{#if data.pagination.page > 1}
					<Button href="/profile/history?page=1" outline variant="secondary" size="sm">
						First
					</Button>

					<Button
						href={`/profile/history?page=${data.pagination.page - 1}`}
						outline
						variant="secondary"
						size="sm"
					>
						Previous
					</Button>
				{/if}

				{#if pageNumbers[0] > 1}
					<span class="text-ash">…</span>
				{/if}

				{#each pageNumbers as pageNumber}
					{#if pageNumber === data.pagination.page}
						<span aria-current="page" class="rounded border border-bronze px-3 py-1 text-bone">
							{pageNumber}
						</span>
					{:else}
						<Button
							href={`/profile/history?page=${pageNumber}`}
							outline
							variant="secondary"
							size="sm"
						>
							{pageNumber}
						</Button>
					{/if}
				{/each}

				{#if pageNumbers[pageNumbers.length - 1] < data.pagination.pages}
					<span class="text-ash">…</span>
				{/if}

				{#if data.pagination.page < data.pagination.pages}
					<Button
						href={`/profile/history?page=${data.pagination.page + 1}`}
						outline
						variant="secondary"
						size="sm"
					>
						Next
					</Button>

					<Button
						href={`/profile/history?page=${data.pagination.pages}`}
						outline
						variant="secondary"
						size="sm"
					>
						Last
					</Button>
				{/if}
			</nav>
		{/if}
	{/if}
</section>
