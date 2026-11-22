<script lang="ts">
	import { page } from '$app/state';

	type Props = {
		items: { label: string; href: string }[];
		label?: string;
		match?: 'exact' | 'prefix'; // prefix keeps "/profile" active on "/profile/history"
		class?: string;
	};

	let { items, label = 'Sections', match = 'exact', class: className = '' }: Props = $props();

	const isActive = (href: string) =>
		match === 'prefix'
			? page.url.pathname === href || page.url.pathname.startsWith(href + '/')
			: page.url.pathname === href;
</script>

<nav aria-label={label} class={['flex flex-wrap gap-x-6 gap-y-1', className]}>
	{#each items as item}
		<a href={item.href} class="tab" aria-current={isActive(item.href) ? 'page' : undefined}>
			{item.label}
		</a>
	{/each}
</nav>
