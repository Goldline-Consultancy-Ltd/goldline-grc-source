<script lang="ts">
	// Goldline: public page with the AGPL v3 text and the source code offer (AGPL sections 5 and 13).
	import Logo from '$lib/components/Logo/Logo.svelte';
	import agplText from '$lib/legal/LICENSE-AGPL.txt?raw';

	const SOURCE_URL = 'https://github.com/goldlineconsultancy/goldline-grc-source';
	const UPSTREAM_URL = 'https://github.com/intuitem/ciso-assistant-community';
</script>

<svelte:head>
	<title>Goldline GRC | Licence and source</title>
</svelte:head>

<main class="min-h-screen bg-surface-50-950 text-surface-950-50 overflow-y-auto">
	<div class="max-w-3xl mx-auto px-4 py-10 space-y-6">
		<div class="flex items-center gap-3">
			<Logo height={48} width={48} />
			<h1 class="text-2xl font-bold">Licence and source</h1>
		</div>

		<section class="space-y-3 text-sm leading-relaxed">
			<p>
				Goldline GRC is a modified version of CISO Assistant Community Edition, copyright © intuitem
				SARL and contributors. It is free software, licensed under the GNU Affero General Public
				License version 3 (AGPL v3). The full licence text is below.
			</p>
			<p>
				Modified by Goldline Consultancy in October 2026. The changes are limited to branding: name,
				logo, favicon, colours, email wording and this page. They are recorded in
				<code>goldline-brand.patch</code> in the source repository.
			</p>
			<p>
				<strong>Source code.</strong> The complete source code of the version running here, with the
				patch applied, is available at
				<a class="underline text-primary-500 dark:text-tertiary-400" href={SOURCE_URL} rel="noopener">{SOURCE_URL}</a>. The original upstream
				project is at <a class="underline text-primary-500 dark:text-tertiary-400" href={UPSTREAM_URL} rel="noopener">{UPSTREAM_URL}</a>.
			</p>
			<p>
				<strong>No warranty.</strong> This program is distributed in the hope that it will be useful,
				but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
				A PARTICULAR PURPOSE. See sections 15 and 16 of the licence for details.
			</p>
		</section>

		<section>
			<h2 class="text-lg font-semibold pb-2">GNU Affero General Public License v3</h2>
			<pre
				class="whitespace-pre-wrap text-xs bg-surface-100-900 border border-surface-200-800 rounded-container p-4">{agplText}</pre>
		</section>

		<p class="text-sm"><a class="underline text-primary-500 dark:text-tertiary-400" href="/">Back to Goldline GRC</a></p>
	</div>
</main>
