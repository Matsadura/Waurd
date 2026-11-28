<script lang="ts">
	import Tabs from '#lib/components/ui/Tabs.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	const tabs = [
		{ label: 'Friends', href: '/profile/friends' },
		{ label: 'Requests', href: '/profile/friends/requests' }
	];
</script>

<Tabs items={tabs} label="Friends sections" class="text-lg" />

<Divider class="my-5" />

{@render children()}
