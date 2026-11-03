<script lang="ts">
	let { children } = $props();
</script>

<svelte:head>
	<link
		rel="preload"
		href="fonts/Kreon-Medium.ttf"
		as="font"
		type="font/woff2"
		crossorigin="anonymous"
	/>
</svelte:head>
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
