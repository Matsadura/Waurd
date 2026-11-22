<script lang="ts">
	// Size and font use tailwind: <Avatar name="Anass" class="size-24 text-5xl" />
	let {
		name,
		src,
		alt,
		class: className = ''
	}: { name: string; src?: string; alt?: string; class?: string } = $props();
</script>

<span class={['avatar', className]} role="img" aria-label={name}>
	{#if src}
		<img {src} {alt} class="size-full object-cover" />
	{:else}
		{name.charAt(0).toUpperCase()}
	{/if}
</span>
