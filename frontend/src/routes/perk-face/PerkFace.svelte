<script lang="ts">
	import perkFrame from '#lib/assets/arena/Perk_frame.png';

	let { artBackground = '' } = $props();
</script>

<div class="perk relative w-full font-bold">
	<div
		class="art absolute bg-cover bg-center"
		style:background-image={`url("${artBackground || 'https://cataas.com/avatar/cute?format=webp'}")`}
	></div>
	<img src={perkFrame} alt="park frame" class="absolute select-none" draggable="false" />

	<span
		class="title absolute text-center font-kreon text-white text-shadow-lg text-shadow-taupe-300/90"
	>
		Blood for Blood</span
	>
	<span class="duribility absolute text-center text-white">4</span>
	<span
		class="rarity absolute text-center font-kreon text-white uppercase text-shadow-sm text-shadow-taupe-300/80"
		>Uncommon</span
	>
	<p class="desc absolute text-center font-normal text-white text-shadow-amber-800 text-shadow-sm">
		Transform this glyph into "RE" and increase its effect value by 5.
	</p>
	<span class="divider absolute w-1/2"></span>
	<q class="quote absolute font-normal text-gray-300">You miss 100% of the shots you didn't take</q>
</div>

<style>
	.perk {
		container-type: inline-size;
		font-family: 'Times New Roman', Times, serif;
	}
	.art {
		width: 78cqi;
		height: 62cqi;
		top: 25cqi;
		left: 13cqi;
	}

	.title {
		font-size: 7cqi;
		color: #361f1c;
		top: 15cqi;
		line-height: 1;
		left: 26cqi;
		width: 15ch;
	}
	.duribility {
		font-size: 16cqi;
		top: 8cqi;
		line-height: 1;
		left: 6.5cqi;
		width: 2ch;
	}

	.rarity {
		font-size: 6cqi;
		color: #392a1f;
		top: 85.5cqi;
		left: 30.5cqi;
		width: 10cap;
	}

	.desc {
		font-size: 5.5cqi;
		line-height: 1.1;
		top: 105cqi;
		left: 16cqi;
		width: 20cap;
	}

	.divider {
		border-top: 0.2cqi dashed rgba(192, 192, 9, 0.507);
		top: 132cqi;
		left: 18cqi;
	}

	q {
		font-size: 4cqi;
		top: 135cqi;
		line-height: 1;
		left: 16cqi;
		width: 35ch;
	}
</style>
