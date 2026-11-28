<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();

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
		<header class="flex flex-wrap items-center justify-between gap-x-8 gap-y-5">
			<div class="flex min-w-0 items-center gap-5">
				<Avatar
					name={data.profile.username}
					src={data.profile.avatarUrl ?? undefined}
					alt=""
					class="size-16 shrink-0 sm:size-20 sm:text-4xl"
				/>

				<div class="min-w-0">
					<h1 class="text-2xl wrap-break-word sm:text-3xl">
						{data.profile.username}
					</h1>
					<p class="text-lg text-ash">
						Level {data.profile.level}
					</p>
				</div>
			</div>

			<Tabs items={tabs} match="prefix" label="Profile sections" class="text-lg" />
		</header>

		<Divider class="my-6" />

		{@render children()}
	</Frame>
</div>
