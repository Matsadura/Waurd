<script lang="ts">
	let { children } = $props();
</script>

{@render children()}

<style>
	@font-face {
		font-family: 'Kreon';
		src: url('/fonts/Kreon-Medium.ttf') format('woff2');
		font-weight: normal;
		font-style: normal;
		font-display: swap;
	}
</style>
