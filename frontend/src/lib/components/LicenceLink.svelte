<script lang="ts">
	// Goldline: small footer link to the AGPL licence text and the source code offer.
	interface Props {
		class?: string;
	}

	let { class: className = '' }: Props = $props();
</script>

<a
	href="/licence"
	class="unstyled text-xs text-surface-600-400 hover:text-surface-950-50 hover:underline {className}"
	data-testid="licence-link">Licence and source</a
>
