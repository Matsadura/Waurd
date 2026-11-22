<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	let {
		label,
		name,
		type = 'text',
		autocomplete,
		required = true,
		value = $bindable(''),
		error,
		class: className = ''
	}: {
		label: string;
		name: string;
		type?: 'text' | 'email' | 'password' | 'checkbox';
		autocomplete?: HTMLInputAttributes['autocomplete'];
		required?: boolean;
		value?: string;
		error?: string; // optional message under the field
		class?: string;
	} = $props();

	// Unique id, so the label and the input are always linked
	const id = $props.id();
</script>

<div class={['flex w-full flex-col gap-1.5', className]}>
	<label for={id} class="field-label">{label}</label>

	<input
		{id}
		{name}
		{type}
		{autocomplete}
		{required}
		bind:value
		class="field"
		aria-invalid={error ? 'true' : undefined}
		aria-describedby={error ? `${id}-error` : undefined}
	/>

	{#if error}
		<p id="{id}-error" class="field-error">{error}</p>
	{/if}
</div>
