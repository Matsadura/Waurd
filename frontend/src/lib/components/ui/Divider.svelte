<script lang="ts">
	let { class: className = '' }: { class?: string } = $props();
</script>

<hr class={['rule', className]} />
