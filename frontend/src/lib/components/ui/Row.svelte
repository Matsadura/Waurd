<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		href: string;
		title: string;
		note?: string; // small text in brackets after the title
		subtitle?: string;
		class?: string;
		children?: Snippet; // right-hand side content
	};

	let { href, title, note, subtitle, class: className = '', children }: Props = $props();
</script>

<a {href} class={['row group', className]}>
	<span class="min-w-0">
		<span class="block truncate text-xl sm:text-2xl">
			{title}
			{#if note}
				<span class="row-note text-base">({note})</span>
			{/if}
		</span>
		{#if subtitle}
			<span class="row-sub block text-base italic">{subtitle}</span>
		{/if}
	</span>
	{#if children}
		<span class="shrink-0 text-right">{@render children()}</span>
	{/if}
</a>
