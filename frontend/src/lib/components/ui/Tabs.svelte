<script lang="ts">
	import { page } from '$app/state';

	type Props = {
		items: { label: string; href: string }[];
		label?: string;
		match?: 'exact' | 'prefix'; // prefix keeps "/profile" active on "/profile/history"
		class?: string;
	};

	let { items, label = 'Sections', match = 'exact', class: className = '' }: Props = $props();

	const activeHref = $derived.by(() => {
		const pathname = page.url.pathname;

		if (match === 'exact') return pathname;

		return items.reduce(
			(best, item) =>
				(pathname === item.href || pathname.startsWith(item.href + '/')) &&
				item.href.length > best.length
					? item.href
					: best,
			''
		);
	});
</script>

<nav aria-label={label} class={['flex flex-wrap gap-x-6 gap-y-1', className]}>
	{#each items as item}
		<a href={item.href} class="tab" aria-current={activeHref === item.href ? 'page' : undefined}>
			{item.label}
		</a>
	{/each}
</nav>
