import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';

// Goldline v4.1.1-goldline.11 (FND-280, 22 Nov 2026): fewer, larger client chunks. Default splitting made the
// assessment tool home and the audit list load 113 and 98 requests (perf budget TC-PERF-005/007: under 80 per page).
// Measured from the client build manifest (entries, layout chain and page, static imports): 103 -> 40 files
// (home), 89-91 -> 39 (lists), 101 -> 39 (audit); largest chunk unchanged (4.2 MB). Client build only (the server
// build is unchanged). Libraries that only heavy pages use (charts, diagrams, document preview, spreadsheet export)
// stay in their own chunks, so ordinary pages never load them.
const HEAVY =
	/node_modules[\\/](\.pnpm[\\/][^\\/]+[\\/]node_modules[\\/])?(echarts|zrender|mermaid|exceljs|docx-preview|@xyflow|@dagrejs|@unovis|d3-[a-z-]+|cytoscape|katex|dompurify|elkjs|khroma|lodash-es)[\\/]/;
const clientChunkGroups = [
	{
		name: 'framework',
		test: /node_modules[\\/](\.pnpm[\\/][^\\/]+[\\/]node_modules[\\/])?(svelte|@sveltejs[\\/]kit|devalue|esm-env|clsx)[\\/]/,
		priority: 40
	},
	{
		name: 'ui',
		test: /node_modules[\\/](\.pnpm[\\/][^\\/]+[\\/]node_modules[\\/])?(@skeletonlabs|bits-ui|@floating-ui|svelte-multiselect|@zag-js|tailwind-merge|tailwind-variants)[\\/]/,
		priority: 30
	},
	{
		name: 'vendor',
		test: (id: string) => /node_modules[\\/]/.test(id) && !HEAVY.test(id),
		minShareCount: 2,
		maxSize: 2000000,
		priority: 20
	},
	{
		name: 'shared',
		minShareCount: 2,
		minSize: 20000,
		maxSize: 3000000,
		priority: 10
	}
];

export default defineConfig(({ isSsrBuild }) => ({
	build: isSsrBuild
		? {}
		: { rolldownOptions: { output: { codeSplitting: { groups: clientChunkGroups } } } },
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/paraglide',
			outputStructure: 'locale-modules',
			cookieName: 'LOCALE',
			strategy: ['custom-userPreference', 'cookie', 'custom-fallback', 'baseLocale']
		}),
		tailwindcss(),
		sveltekit()
	],
	optimizeDeps: {
		// @svelte-put/qr exports ./svg/QR.svelte under the "svelte" condition only.
		// Vite 8's dep scanner doesn't apply it, so scope the condition to the
		// scanner rather than resolve.conditions (which would break SSR node/browser).
		rolldownOptions: {
			resolve: {
				conditionNames: ['svelte', 'module', 'browser', 'import', 'default']
			}
		}
	},
	test: {
		include: ['{src}/**/*.{test,spec}.{js,ts}']
	}
}));
