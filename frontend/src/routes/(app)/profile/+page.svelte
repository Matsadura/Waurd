<script lang="ts">
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import Stat from '#lib/components/ui/Stat.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Profile</title>
</svelte:head>

<div class="grid gap-8 lg:grid-cols-[1fr_21rem]">
	<section aria-labelledby="duels" class="order-2 lg:order-0">
		<h2 id="duels" class="font-display text-2xl">
			Chronicle of duels
			<span class="text-lg text-ash">({data.stats.games})</span>
		</h2>

		{#if data.stats.games === 0}
			<div class="mt-6 border-l-2 border-bronze/40 py-4 pl-5">
				<p class="font-display text-xl text-bone">Your chronicle is empty</p>
				<p class="mt-2 text-lg text-ash italic">
					No battles have been recorded. Your victories and defeats will be written here once you
					enter the arena.
				</p>
			</div>
		{:else}
			<p class="mt-6 text-lg text-ash italic">Duel records will be available here soon.</p>
		{/if}
	</section>

	<Frame variant="double-border" as="aside" aria-label="Player status" class="order-1 lg:order-0">
		<Frame variant="border" class="text-lg">{data.user.username}</Frame>

		<dl class="mt-4 text-lg">
			<Stat label="Level">{data.user.level}</Stat>

			<Stat label="Experience">
				{data.user.xpIntoLevel} / {data.user.xpForNextLevel}
			</Stat>

			<Meter
				value={data.user.xpIntoLevel}
				max={data.user.xpForNextLevel}
				label="Experience"
				class="mt-1"
			/>

			<Divider class="my-3" />

			<Stat label="Elo">{data.stats.elo}</Stat>
			<Stat label="Duels">{data.stats.games}</Stat>
			<Stat label="Victories">{data.stats.wins}</Stat>

			<Divider class="my-3" />

			<Stat label="Friends">{data.friendCount}</Stat>
			<Stat label="Joined">{data.user.joined}</Stat>
		</dl>
	</Frame>
</div>

<Divider class="my-6" />

<Button href="/settings">Edit Profile</Button>
