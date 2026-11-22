<script lang="ts">
	let {
		value,
		max,
		label,
		class: className = ''
	}: { value: number; max: number; label: string; class?: string } = $props();
	const percentage = $derived(Math.min((value / max) * 100, 100));
</script>

<div
	class={['meter', className]}
	role="progressbar"
	aria-label={label}
	aria-valuemin={0}
	aria-valuemax={max}
	aria-valuenow={value}
>
	<i style:width="{percentage}%"></i>
</div>
