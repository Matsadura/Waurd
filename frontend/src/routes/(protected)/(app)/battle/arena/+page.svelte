<script lang="ts">
	import { enhance, type SubmitFunction } from '$app/forms';
	import Button from '#lib/components/ui/Button.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';

	let { data, form } = $props();
	let abandoning = $state(false);

	const handleSubmit: SubmitFunction = () => {
		abandoning = true;
		return async ({ update }) => {
			try {
				await update();
			} finally {
				abandoning = false;
			}
		};
	};
</script>

<div class="mx-auto w-full max-w-md px-3 py-10 font-body text-bone sm:px-4">
	<Frame class="text-center">
		{#if form?.error}
			<Notice variant="danger" class="mb-4 text-left">{form.error}</Notice>
		{/if}

		<form method="POST" use:enhance={handleSubmit}>
			<input type="hidden" name="match_id" value={data.ticket.matched_match_id} />
			<Button type="submit" variant="danger" outline loading={abandoning} class="w-full">
				Abandon Match
			</Button>
		</form>
	</Frame>
</div>
