<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	let {
		label,
		name,
		type = 'text',
		autocomplete,
		required = true,
		value = $bindable(''),
		class: className = ''
	}: {
		label: string;
		name: string;
		type?: 'text' | 'email' | 'password';
		autocomplete?: HTMLInputAttributes['autocomplete'];
		required?: boolean;
		value?: string;
		class?: string;
	} = $props();

	// Unique id, so the label and the input are always linked
	const id = $props.id();
</script>

<div class={['mb-2 flex w-full flex-col items-center', className]}>
	<label for={id} class="mb-1.5 text-center text-lg font-bold text-white">
		{label}
	</label>

	<input
		{id}
		{name}
		{type}
		{autocomplete}
		{required}
		bind:value
		class="h-10 w-full rounded-xl border-0 bg-[#2d353c] px-4 text-center text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] focus:ring-white"
	/>
</div>
