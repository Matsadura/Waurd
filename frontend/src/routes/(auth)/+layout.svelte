<script lang="ts">
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';

	let { children } = $props();
</script>

<div class="stage" aria-hidden="true"></div>

<div class="flex min-h-dvh w-full min-w-0 flex-col items-center px-4 pt-8 pb-10 font-body text-bone sm:pt-12">
	<header class="mt-6 mb-10">
		<WaurdLogo href="/login" size="large" />
	</header>

	<Frame class="w-full max-w-lg">
		<main class="mx-auto w-full max-w-sm">
			{@render children()}
		</main>
	</Frame>
</div>