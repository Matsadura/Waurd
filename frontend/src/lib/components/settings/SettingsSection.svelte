<script lang="ts">
	import type { Snippet } from 'svelte';

	// A settings block: title and a short description on the left, the form on the right.
	let { title, description, children }: { title: string; description?: string; children: Snippet } =
		$props();

	const id = $props.id();
</script>

<section aria-labelledby={id} class="grid gap-4 lg:grid-cols-[14rem_1fr] lg:gap-10">
	<div>
		<h2 {id} class="font-display text-2xl">{title}</h2>
		{#if description}
			<p class="text-ash italic">{description}</p>
		{/if}
	</div>

	<div class="max-w-md min-w-0">{@render children()}</div>
</section>
