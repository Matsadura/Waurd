<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		name: string;
		checked?: boolean;
		required?: boolean;
		class?: string;
		children: Snippet; // the label text, can contain links
	};

	let {
		name,
		checked = $bindable(false),
		required = false,
		class: className = '',
		children
	}: Props = $props();
</script>

<label class={['flex cursor-pointer items-center gap-3 text-md text-bone', className]}>
	<input type="checkbox" {name} {required} bind:checked class="mt-1 form-checkbox check" />
	<span>{@render children()}</span>
</label>

<style>
	.check {
		accent-color: var(--color-primary-light);
		cursor: pointer;
	}
</style>
