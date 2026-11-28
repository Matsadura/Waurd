<script lang="ts">
	// Small online / offline indicator: <Presence online={true} />
	let {
		online,
		lastSeen,
		class: className = ''
	}: { online: boolean; lastSeen?: string; class?: string } = $props();
</script>

<span class={['inline-flex items-center gap-1.5 not-italic', className]}>
	<span class={['size-2 rounded-full', online ? 'bg-primary-light' : 'bg-secondary']}></span>
	{#if online}
		Online now
	{:else}
		{lastSeen ? `Seen ${lastSeen}` : 'Offline'}
	{/if}
</span>
