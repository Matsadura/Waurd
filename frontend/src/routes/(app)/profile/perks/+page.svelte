<script lang="ts">
	import PerkCard from '#lib/components/profile/PerkCard.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Filter from '#lib/components/ui/Filter.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import { perkSlots, perks } from '../mock';

	const filters = [
		{ label: 'All', value: 'all' },
		{ label: 'Common', value: 'common' },
		{ label: 'Uncommon', value: 'uncommon' },
		{ label: 'Rare', value: 'rare' },
		{ label: 'Legendary', value: 'legendary' }
	];

	// TODO: equipping only changes this page's local state, save it with the loadout API.
	let equipped = $state(['blood-for-blood', 'wordbreaker']);
	let rarity = $state('all');

	const full = $derived(equipped.length >= perkSlots);
	const slots = $derived(
		Array.from({ length: perkSlots }, (_, i) => perks.find((p) => p.id === equipped[i]))
	);
	const shown = $derived(perks.filter((p) => rarity === 'all' || p.rarity === rarity));
	const ownedCount = perks.filter((p) => p.owned).length;

	const unequip = (id: string) => (equipped = equipped.filter((e) => e !== id));
	const equip = (id: string) => (equipped = [...equipped, id]);
</script>

<svelte:head>
	<title>Perks · Profile</title>
</svelte:head>

<section aria-labelledby="loadout">
	<h2 id="loadout" class="font-display text-2xl">
		Loadout <span class="text-lg text-ash">({equipped.length} / {perkSlots})</span>
	</h2>
	<p class="text-ash italic">The perks you carry into every duel.</p>

	<ul class="mt-4 grid gap-4 sm:grid-cols-3">
		{#each slots as perk, i (i)}
			<li class="flex">
				{#if perk}
					<Frame
						variant="double-border"
						class="flex w-full items-center justify-between gap-3 px-4 py-3"
					>
						<span class="min-w-0">
							<span class="block truncate font-display text-xl">{perk.name}</span>
							<span class="block text-base text-ash capitalize">{perk.rarity}</span>
						</span>
						<Button size="sm" outline variant="secondary" onclick={() => unequip(perk.id)}
							>Unequip</Button
						>
					</Frame>
				{:else}
					<div
						class="flex min-h-18 w-full items-center justify-center border border-dashed border-bronze/40 px-4 py-3 text-ash italic"
					>
						Empty slot
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</section>

<Divider class="my-6" />

<section aria-labelledby="codex">
	<h2 id="codex" class="font-display text-2xl">
		Codex of perks <span class="text-lg text-ash">({ownedCount} / {perks.length})</span>
	</h2>

	<Filter
		bind:value={rarity}
		options={filters}
		label="Filter perks by rarity"
		class="mt-4 text-lg"
	/>

	{#if shown.length}
		<ul class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each shown as perk (perk.id)}
				<li>
					<PerkCard {perk}>
						{#if equipped.includes(perk.id)}
							<Button size="sm" outline variant="secondary" onclick={() => unequip(perk.id)}
								>Unequip</Button
							>
						{:else}
							<Button size="sm" outline disabled={full} onclick={() => equip(perk.id)}
								>{full ? 'Loadout full' : 'Equip'}</Button
							>
						{/if}
					</PerkCard>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-6 text-ash italic">No perks of this rarity.</p>
	{/if}
</section>
