<script>
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Meter from '#lib/components/ui/Meter.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import Stat from '#lib/components/ui/Stat.svelte';
	import Tabs from '#lib/components/ui/Tabs.svelte';
</script>

<div class="frame flex min-h-dvh flex-col gap-6 bg-gray-800 p-8 font-display">
	<Avatar name="Anass" class="size-24 text-5xl" />
	<Avatar
		name="Anass"
		class="size-10"
		src="https://avatars.githubusercontent.com/u/104344010?v=4"
	/>

	<div class="flex-col items-center justify-center gap-4">
		<Button variant="primary">primary</Button>
		<Button variant="primary" disabled={true}>primary disabled</Button>
		<Button variant="secondary">secondary</Button>
		<Button variant="success">success</Button>
		<Button variant="danger">danger</Button>
		<Button variant="warning">warning</Button>
		<Button variant="warning" outline={true}>warning outline</Button>
		<Button variant="info">info</Button>
		<Button variant="info" href="https://github.com">hrep make the button an ancher</Button>
		<Button variant="info" class="animate-bounce">You overide class by using class=...</Button>
	</div>

	<Frame variant="double-border">Frame with variant double-border</Frame>
	<Frame variant="torn">Frame torn</Frame>
	<Frame variant="border">Frame border</Frame>
	<Frame variant="border" as="a" href="http://google.com">Frame can be any HTML element</Frame>

	<div class="flex items-center gap-1">
		<div class="text-2xl">Meter &gt;</div>
		<div class="flex-1">
			<Meter max={100} value={60} label="health" />
		</div>
	</div>

	<Row href="" title="Title" note="Note" subtitle="Subtitle" class="border-b border-b-primary/50"
		>children</Row
	>
	<Row href="" title="Title" note="Note" subtitle="Subtitle">children</Row>

	<h2 class="text-2xl text-info-light">Stat: use insize dt html element</h2>
	<dl class="w-20">
		<Stat label="Key">Value</Stat>
	</dl>

	<h1>Tab</h1>
	<div>
		<Tabs
			items={[
				{ label: 'Comp', href: '/Comp' },
				{ label: 'login', href: '/label1' }
			]}
		/>
	</div>

	<h2 class="text-2xl text-info-light">line Divider</h2>
	<Divider />

	<div class="rule text-center">line-divider ^^^^^</div>

	<div class="flex gap-4">
		<div class="tab" data-variant="page" aria-current="page">
			ta with <code>aria-current=page</code>
		</div>
		<div class="tab" data-variant="page" aria-current="page">
			ta with <code>aria-current=page</code>
		</div>
	</div>

	<div class="row">
		<div class="row-sub">this is div with class: <code>row-sub</code></div>
		<div class="row-note">this div with class: <code>row-note</code></div>
	</div>

	<div>check the stat usage later...</div>
</div>
