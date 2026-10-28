<script lang="ts">
	let {
		href = '/play',
		size = 'small'
	}: {
		href?: string;
		size?: 'small' | 'large';
	} = $props();
</script>

<a
	{href}
	class={`font-henny-penny font-normal tracking-[2px] text-accent no-underline
		[text-shadow:5px_5px_8px_rgba(115,20,20,0.8),10px_7px_16px_rgba(100,15,15,0.55)]
		${size === 'large' ? 'text-[calc((1em+1vw)*3)]' : 'text-2xl sm:text-3xl'}`}
>
	Waurd
</a>
