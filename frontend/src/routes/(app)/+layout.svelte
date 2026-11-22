<script lang="ts">
	import Navbar from '#lib/components/navbar/Navbar.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';

	let { children } = $props();
</script>

<div class="mx-auto sm:w-full lg:container lg:px-4">
	<Navbar />

	<main>
		{@render children()}
	</main>
</div>
