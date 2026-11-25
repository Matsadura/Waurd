<script lang="ts">
	import type { Snippet } from 'svelte';
	import Divider from '#lib/components/ui/Divider.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<h1 class="text-center font-display text-2xl text-bone sm:text-3xl">
	{@render children()}
</h1>

<Divider class="my-6" />