<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import Spiner from './Spinner.svelte';

	type Props = {
		variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
		outline?: boolean;
		size?: 'sm' | 'md' | 'lg';
		href?: string; // with href it renders a link that looks like a button
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		target?: string;
		rel?: string;
		class?: string;
		children: Snippet;
	} & Omit<HTMLAttributes<HTMLElement>, 'class' | 'children'>;

	let {
		variant = 'primary',
		outline = false,
		size = 'md',
		href,
		type = 'button',
		disabled = false,
		loading = false,
		class: className = '',
		children,
		...rest
	}: Props = $props();
</script>

{#if href}
	<a
		{href}
		class={['btn', className]}
		data-variant={variant}
		data-size={size}
		data-outline={outline || undefined}
		aria-disabled={disabled || loading || undefined}
		aria-busy={loading || undefined}
		{...rest}
	>
		{#if loading}
			<Spiner size={size === 'sm' ? 'sm' : 'md'} />
		{:else}
			{@render children()}
		{/if}
	</a>
{:else}
	<button
		{type}
		disabled={disabled || loading}
		class={['btn', className]}
		data-variant={variant}
		data-size={size}
		data-outline={outline || undefined}
		aria-busy={loading || undefined}
		{...rest}
	>
		{#if loading}
			<Spiner size={size === 'sm' ? 'sm' : 'md'} />
		{:else}
			{@render children()}
		{/if}
	</button>
{/if}
