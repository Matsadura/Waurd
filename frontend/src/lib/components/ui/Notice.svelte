<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		variant?: 'danger' | 'success' | 'warning' | 'info';
		class?: string;
		children: Snippet;
	};

	let { variant = 'danger', class: className = '', children }: Props = $props();
</script>

<p
	class={['notice', className]}
	data-variant={variant}
	role={variant === 'danger' ? 'alert' : 'status'}
>
	{@render children()}
</p>
