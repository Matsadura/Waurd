<script lang="ts">
	import './layout.css';
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { PUBLIC_BACKEND_URL } from '$app/env/public';
	import favicon from '#lib/assets/favicon.svg';
	import Frame from '#lib/components/ui/Frame.svelte';

	let { children } = $props();

	afterNavigate((nav) => {
		if (nav.type === 'popstate' && window.location.pathname !== page.url.pathname) {
			window.history.replaceState(window.history.state, '', page.url.href);
		}
	});

	const userId = $derived(page.data.user?.id);

	$effect(() => {
		if (!userId) return;

		const url = new URL('/ws/chat', PUBLIC_BACKEND_URL);
		url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';

		const socket = new WebSocket(url);

		return () => socket.close();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="font-display">
	<!-- This is the torn effect that we use for the torned borders, make sure to never delete it from here! -->
	<svg width="0" height="0" class="absolute" aria-hidden="true">
		<filter id="torn" x="-5%" y="-5%" width="110%" height="110%">
			<feTurbulence
				type="fractalNoise"
				baseFrequency="0.03 0.05"
				numOctaves="4"
				seed="7"
				result="noise"
			/>
			<feDisplacementMap in="SourceGraphic" in2="noise" scale="10" />
		</filter>
	</svg>
	<Frame
		class="min-h-dvh min-w-0 overflow-x-clip bg-cover bg-fixed bg-center bg-no-repeat"
		variant="bg"
	>
		{@render children()}
	</Frame>
</div>
