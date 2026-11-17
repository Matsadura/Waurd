<script lang="ts">
	import Navbar from '#lib/components/navbar/Navbar.svelte';

	let { children } = $props();
</script>

<div class="min-h-dvh min-w-0 overflow-x-clip bg
		bg-cover bg-center bg-no-repeat bg-fixed text-text-primary">
	<div class="lg:container mx-auto lg:px-4 sm:w-full">
		<Navbar />

		<main>
			{@render children()}
		</main>
	</div>
</div>

<style>
	.bg {
		background: linear-gradient(to bottom, var(--color-gray-900), var(--color-gray-950) 116px) no-repeat;
	}
</style>
