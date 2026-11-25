<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Presence from '#lib/components/ui/Presence.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';
	import { player, rank } from './mock';

	let { children } = $props();

	const tabs = [
		{ label: 'Overview', href: '/profile' },
		{ label: 'Duels', href: '/profile/history' },
		{ label: 'Friends', href: '/profile/friends' },
		{ label: 'Achievements', href: '/profile/achievements' },
		{ label: 'Perks', href: '/profile/perks' }
	];
</script>

<div class="mx-auto w-full max-w-5xl px-3 py-6 font-body text-bone sm:px-4">
	<Frame class="fade-in">
		<header class="flex flex-wrap items-start justify-between gap-x-8 gap-y-5">
			<div class="flex items-center gap-4">
				<Avatar name={player.username} class="sm:size-20 sm:text-4xl" />
				<div class="min-w-0">
					<h1 class="text-3xl wrap-break-word sm:text-4xl">{player.username}</h1>
					<p class="text-lg text-ash">
						<span class="font-bold">{rank}</span>
						<Presence online={player.online} class="ml-3 text-base" />
					</p>
				</div>
			</div>

			<Tabs items={tabs} label="Profile sections" class="text-lg" />
		</header>

		<Divider class="my-6" />

		{@render children()}
	</Frame>
</div>
