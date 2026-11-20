import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

import { BASE_API_URL } from '$lib/utils/constants';
import { type TableSource } from '$lib/components/ModelTable/types';
import { headData } from '$lib/utils/table';
import { discardBody } from '$lib/utils/responses';
import type { urlModel } from '$lib/utils/types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'requirement-assessments';
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	// Goldline (v4.1.1-goldline.5): a requirement the user may not see (another domain, or no such id) is a clean 404,
	// never a server error, and nothing of it is read.
	const requirementResponse = await fetch(baseEndpoint);
	if (!requirementResponse.ok) {
		await discardBody(requirementResponse);
		error(404, 'Not found');
	}
	const requirementAssessment = await requirementResponse.json();
	const complianceAssessmentScore = await fetch(
		`${BASE_API_URL}/compliance-assessments/${requirementAssessment.compliance_assessment.id}/global_score/`
	).then((res) => res.json());
	const requirement = requirementAssessment.requirement;
	const parent = requirementAssessment.requirement.parent_requirement;

	const requirementsListData = await fetch(
		`${BASE_API_URL}/compliance-assessments/${requirementAssessment.compliance_assessment.id}/requirements_list/?assessable=true`
	)
		.then((res) => (res.ok ? res.json() : discardBody(res).then(() => null)))
		.catch((error) => {
			console.error('Failed to fetch requirement viewer role:', error);
			return null;
		});
	const viewerRole = requirementsListData?.viewer_role === 'auditor' ? 'auditor' : 'respondent';

	const tables: Record<string, any> = {};

	for (const key of ['applied-controls', 'task-templates', 'evidences', 'findings'] as urlModel[]) {
		const table: TableSource = {
			head: headData(key),
			body: [],
			meta: []
		};
		tables[key] = table;
	}

	return {
		requirementAssessment,
		complianceAssessmentScore,
		requirement,
		parent,
		tables,
		title: requirementAssessment.name,
		viewerRole
	};
}) satisfies PageServerLoad;
