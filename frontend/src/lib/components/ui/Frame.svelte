<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	type Props = {
		variant?: 'torn' | 'double-border' | 'border' | 'bg'; // torn = big ragged panel, double-border = thin double line, border = small name box
		as?: string;
		class?: string;
		children: Snippet;
	} & Omit<HTMLAttributes<HTMLElement>, 'class' | 'children'>;

	let {
		variant = 'torn',
		as: tag = 'div',
		class: className = '',
		children,
		...rest
	}: Props = $props();
</script>

<svelte:element this={tag} class={['frame', className]} data-variant={variant} {...rest}>
	{@render children()}
</svelte:element>
