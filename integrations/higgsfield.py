"""Explicit mock until API entitlement, pricing, terms and account access are verified."""
def storyboard_mock(concept):
    if not concept.strip():raise ValueError('Concept required')
    return {'mode':'mock','concept':concept,'generated_video':None,'api_calls':0,
            'blocker':'Higgsfield supported API access and commercial terms not verified'}
