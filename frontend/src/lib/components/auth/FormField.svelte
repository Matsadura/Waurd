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

<div class={['flex flex-col items-center', className]}>
	<label for={id} class="mb-[0.1rem] text-center text-xl font-bold text-white">
		{label}
	</label>

	<input
		{id}
		{name}
		{type}
		{autocomplete}
		{required}
		bind:value
		class="h-11 w-full rounded-xl border-0 bg-[#2d353c] px-4 text-center text-[1.1rem] text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] focus:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a00]"
	/>
</div>
