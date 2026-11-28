<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Presence from '#lib/components/ui/Presence.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	const sorted = $derived([...data.friends].sort((a, b) => Number(b.online) - Number(a.online)));
</script>

<svelte:head>
	<title>Friends · Profile</title>
</svelte:head>

{#if form?.section === 'removeFriend'}
	{#if form.error}
		<Notice class="mb-4">{form.error}</Notice>
	{:else if form.message}
		<Notice variant="success" class="mb-4">
			{form.message}
		</Notice>
	{/if}
{/if}

<section aria-labelledby="fellowship">
	<h2 id="fellowship" class="font-display text-2xl">
		Fellowship <span class="text-lg text-ash">({data.friendCount})</span>
	</h2>

	{#if sorted.length}
		<ul class="mt-4 divide-y divide-bronze/20">
			{#each sorted as friend (friend.id)}
				<li>
					<Row title={friend.username}>
						{#snippet lead()}
							<Avatar
								name={friend.username}
								src={friend.avatarUrl}
								alt=""
								class="size-12 text-xl"
							/>
						{/snippet}

						{#snippet subtitle()}
							<Presence online={friend.online} lastSeen={friend.lastSeen} />
						{/snippet}

						<div class="flex flex-col gap-2 sm:flex-row">
							<Button size="sm" outline disabled>Challenge</Button>

							<form method="POST" action="?/removeFriend">
								<input type="hidden" name="friendId" value={friend.id} />

								<Button type="submit" size="sm" variant="secondary" outline>Remove</Button>
							</form>
						</div>
					</Row>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-6 text-ash italic">
			Your fellowship is empty. Visit Requests to send a friend request.
		</p>
	{/if}
</section>
