<script lang="ts">
	import Navbar from '#lib/components/app/Navbar.svelte';

	let { children } = $props();
</script>

<div
	class="min-h-dvh min-w-0 overflow-x-clip bg-background bg-[url('/images/background.png')]
		bg-cover bg-fixed bg-center bg-no-repeat text-text-primary"
>
	<div class="mx-auto sm:w-full lg:container lg:px-4">
		<Navbar />

		<main>
			{@render children()}
		</main>
	</div>
</div>
