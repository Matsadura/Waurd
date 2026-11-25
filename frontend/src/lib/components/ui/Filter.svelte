<script lang="ts">
	// A row of toggle buttons that look like Tabs, for filtering a list on the same page:
	// <Filter bind:value options={[{ label: 'All', value: 'all' }, ...]} />
	type Props = {
		options: { label: string; value: string }[];
		value: string;
		label?: string;
		class?: string;
	};

	let { options, value = $bindable(), label = 'Filter', class: className = '' }: Props = $props();
</script>

<div role="group" aria-label={label} class={['flex flex-wrap gap-x-5 gap-y-1', className]}>
	{#each options as option (option.value)}
		<button
			type="button"
			class="tab cursor-pointer"
			aria-pressed={value === option.value}
			onclick={() => (value = option.value)}
		>
			{option.label}
		</button>
	{/each}
</div>
