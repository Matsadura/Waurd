<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link
		rel="preload"
		href="/fonts/HennyPenny-Regular.ttf"
		as="font"
		type="font/ttf"
		crossorigin="anonymous"
	/>

	<link
		rel="preload"
		href="/fonts/Rajdhani-Bold.ttf"
		as="font"
		type="font/ttf"
		crossorigin="anonymous"
	/>
</svelte:head>

{@render children()}
