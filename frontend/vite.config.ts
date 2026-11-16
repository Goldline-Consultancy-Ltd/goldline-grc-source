import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/paraglide',
			outputStructure: 'locale-modules',
			cookieName: 'LOCALE',
			strategy: ['custom-userPreference', 'cookie', 'custom-fallback', 'baseLocale']
		}),
		tailwindcss(),
		// SvelteKit 3 reads its configuration here; svelte.config.js is no longer used (config_file_unsupported).
		sveltekit({
			preprocess: vitePreprocess(),
			adapter: adapter(),
			// $lib is no longer built in from SvelteKit 3 (module_removed_lib); kept as an alias so imports are unchanged.
			alias: {
				$lib: 'src/lib',
				$paraglide: './src/paraglide/'
			}
		})
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
});
