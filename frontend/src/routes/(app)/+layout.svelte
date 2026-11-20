<script lang="ts">
	import { goto } from '$app/navigation';
	import Navbar from '#lib/components/navbar/Navbar.svelte';
	import { loadUser, session } from '#lib/session.svelte.ts';

	let { children } = $props();

	$effect(() => {
		if (!session.checked) {
			loadUser().then((user) => {
				if (!user) goto('/login');
			});
		}
	});
</script>

<div
	class="min-h-dvh min-w-0 overflow-x-clip bg-background bg-[url('/images/background.png')]
		bg-cover bg-fixed bg-center bg-no-repeat text-text-primary"
>
	<div class="mx-auto sm:w-full lg:container lg:px-4">
		<Navbar />

		<main>
			{#if session.user}
				{@render children()}
			{:else}
				<p class="p-6 text-lg text-white/70">Loading…</p>
			{/if}
		</main>
	</div>
</div>
