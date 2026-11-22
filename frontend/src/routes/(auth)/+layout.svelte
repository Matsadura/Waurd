<script lang="ts">
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';

	let { children } = $props();

	const tabs = [
		{ href: '/login', label: 'Login' },
		{ href: '/register', label: 'Register' }
	];
</script>

<div class="stage" aria-hidden="true"></div>

<div
	class="flex min-h-dvh w-full min-w-0 flex-col items-center px-4 pt-8 pb-10 font-body text-bone sm:pt-12"
>
	<header class="mt-6 mb-10">
		<WaurdLogo href="/login" size="large" />
	</header>

	<Frame class="w-full max-w-lg">
		<Tabs items={tabs} label="Account" class="justify-center gap-10 text-2xl" />
		<Divider class="my-6" />

		<main class="mx-auto w-full max-w-sm">
			{@render children()}
		</main>
	</Frame>
</div>
