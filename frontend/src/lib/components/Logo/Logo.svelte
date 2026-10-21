<script lang="ts">
	import mark from '$lib/assets/goldline-grc-mark.svg';
	import markWhite from '$lib/assets/goldline-grc-mark-white.svg';

	interface Props {
		height?: number;
		width?: number;
	}

	let { height = 200, width = 200 }: Props = $props();
</script>

<img
	class="c dark:hidden"
	{height}
	{width}
	src={mark}
	alt="Goldline GRC logo"
	data-testid="logo-image"
/>
<img class="c hidden dark:block" {height} {width} src={markWhite} alt="Goldline GRC logo" />
