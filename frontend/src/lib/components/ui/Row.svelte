<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		href?: string; // with href the whole row is a link and gets the copper hover bar
		title: string;
		note?: string; // small text in brackets after the title
		subtitle?: string | Snippet; // plain text, or a snippet when it needs markup
		class?: string;
		lead?: Snippet; // left-hand side content, like an Avatar
		children?: Snippet; // right-hand side content
	};

	let { href, title, note, subtitle, class: className = '', lead, children }: Props = $props();
</script>

<svelte:element this={href ? 'a' : 'div'} {href} class={['row group', className]}>
	{#if lead}
		{@render lead()}
	{/if}
	<span class="min-w-0 flex-1">
		<span class="block truncate text-xl sm:text-2xl">
			{title}
			{#if note}
				<span class="row-note text-base">({note})</span>
			{/if}
		</span>
		{#if subtitle}
			<span class="row-sub block text-base italic">
				{#if typeof subtitle === 'string'}
					{subtitle}
				{:else}
					{@render subtitle()}
				{/if}
			</span>
		{/if}
	</span>
	{#if children}
		<div class="shrink-0 text-right">{@render children()}</div>
	{/if}
</svelte:element>
