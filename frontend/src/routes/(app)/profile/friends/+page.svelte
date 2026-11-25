<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Presence from '#lib/components/ui/Presence.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { Friend } from '#lib/types/profile.ts';
	import { friends, incomingRequests, outgoingRequests } from '../mock';

	// TODO: every action below only changes this page's local state, call the friendship API.
	let list = $state<Friend[]>(friends);
	let incoming = $state<Friend[]>(incomingRequests);
	let outgoing = $state<Friend[]>(outgoingRequests);

	let username = $state('');
	let sent = $state('');

	// Friends who are online come first
	const sorted = $derived([...list].sort((a, b) => Number(b.online) - Number(a.online)));
	const without = (people: Friend[], friend: Friend) => people.filter((p) => p.id !== friend.id);

	function accept(friend: Friend) {
		incoming = without(incoming, friend);
		list = [...list, friend];
	}

	function sendRequest(event: SubmitEvent) {
		event.preventDefault();
		const name = username.trim();
		if (!name) return;
		outgoing = [...outgoing, { id: name, username: name, online: false }];
		sent = name;
		username = '';
	}
</script>

<svelte:head>
	<title>Friends · Profile</title>
</svelte:head>

<section aria-labelledby="fellowship">
	<h2 id="fellowship" class="font-display text-2xl">
		Fellowship <span class="text-lg text-ash">({list.length})</span>
	</h2>

	<form onsubmit={sendRequest} class="mt-3 flex flex-wrap items-end gap-3">
		<div class="w-full max-w-sm">
			<label for="friend-username" class="field-label">Send a friend request</label>
			<input
				id="friend-username"
				bind:value={username}
				class="field mt-1"
				placeholder="Username"
				autocomplete="off"
			/>
		</div>
		<Button type="submit" outline>Send</Button>
	</form>
	{#if sent}
		<Notice variant="success" class="mt-2">Request sent to {sent}.</Notice>
	{/if}

	{#if sorted.length}
		<ul class="mt-4 divide-y divide-bronze/20">
			{#each sorted as friend (friend.id)}
				<li>
					<Row title={friend.username}>
						{#snippet lead()}
							<Avatar name={friend.username} class="size-12 text-xl" />
						{/snippet}
						{#snippet subtitle()}
							<Presence online={friend.online} lastSeen={friend.lastSeen} />
						{/snippet}
						<span class="flex flex-col gap-2 sm:flex-row">
							<Button size="sm" outline>Challenge</Button>
							<Button
								size="sm"
								outline
								variant="secondary"
								onclick={() => (list = without(list, friend))}>Remove</Button
							>
						</span>
					</Row>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-6 text-ash italic">Your fellowship is empty, send a request to someone.</p>
	{/if}
</section>

{#if incoming.length || outgoing.length}
	<Divider class="my-6" />

	<section aria-labelledby="pending">
		<h2 id="pending" class="font-display text-2xl">Pending requests</h2>

		<ul class="mt-3 divide-y divide-bronze/20">
			{#each incoming as friend (friend.id)}
				<li>
					<Row title={friend.username} subtitle="Wants to join your fellowship">
						{#snippet lead()}
							<Avatar name={friend.username} class="size-12 text-xl" />
						{/snippet}
						<span class="flex flex-col gap-2 sm:flex-row">
							<Button size="sm" variant="success" outline onclick={() => accept(friend)}
								>Accept</Button
							>
							<Button
								size="sm"
								variant="danger"
								outline
								onclick={() => (incoming = without(incoming, friend))}>Decline</Button
							>
						</span>
					</Row>
				</li>
			{/each}

			{#each outgoing as friend (friend.id)}
				<li>
					<Row title={friend.username} subtitle="Awaiting their answer">
						{#snippet lead()}
							<Avatar name={friend.username} class="size-12 text-xl" />
						{/snippet}
						<Button
							size="sm"
							variant="secondary"
							outline
							onclick={() => (outgoing = without(outgoing, friend))}>Withdraw</Button
						>
					</Row>
				</li>
			{/each}
		</ul>
	</section>
{/if}
