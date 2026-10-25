<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		children,
		type = 'submit',
		disabled = false,
		class: className = ''
	}: {
		children: Snippet;
		type?: 'submit' | 'button';
		disabled?: boolean;
		class?: string;
	} = $props();
</script>

<button
	{type}
	{disabled}
	class={[
		'mx-auto h-11 w-[90%] cursor-pointer rounded-[0.4rem] border-0 bg-[#ff8a00] text-[1.2rem] font-bold text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] transition hover:brightness-[1.08] focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-white disabled:cursor-not-allowed disabled:opacity-50',
		className
	]}
>
	{@render children()}
</button>
