<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		label,
		class: className = '',
		children
	}: { label: string; class?: string; children: Snippet } = $props();
</script>

<!-- Use inside a <dl> -->
<div class={['stat', className]}>
	<dt>{label}</dt>
	<dd>{@render children()}</dd>
</div>
