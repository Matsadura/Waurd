<script lang="ts">
	import Divider from '#lib/components/ui/Divider.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';

	let { children } = $props();

	const tabs = [
		{ href: '/login', label: 'Login' },
		{ href: '/register', label: 'Register' }
	];
</script>

<Tabs items={tabs} label="Account" class="justify-center gap-10 text-2xl" />
<Divider class="my-6" />

{@render children()}